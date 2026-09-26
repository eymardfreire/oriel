"""Poll followed sports and build the field, far, and fantasy bays."""

from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from oriel_server.sports.catalog import (
    FIELD_TIERS,
    LINEUP_SLOTS,
    POINT_KEYS,
    Competition,
    Player,
    Roster,
    Follows,
    load_competitions,
    load_follows,
    load_roster,
    save_follows,
    save_roster,
)
from oriel_server.sports.roster import assign_flex, drop_player, pin_player, select_player, set_scoring, unpin_player
from oriel_server.sports.scores import ScoreRow, parse_competition
from oriel_server.sports.standings import parse_standings, standings_url
from oriel_server.wires.poller import short_error

logger = logging.getLogger("oriel.sports")

Fetcher = Callable[[str], bytes]
SLEEPER_STATE = "https://api.sleeper.app/v1/state/nfl"
SLEEPER_PLAYERS = "https://api.sleeper.app/v1/players/nfl"
SLEEPER_STATS = "https://api.sleeper.app/v1/stats/nfl/{season_type}/{season}/{week}"
MAX_SPORTS_BYTES = 30_000_000


class SportsPoller:
    def __init__(
        self,
        catalog_dir: Path,
        *,
        fetcher: Fetcher | None = None,
        stale_after_seconds: int = 900,
        state_path: Path | None = None,
        now: Callable[[], datetime] | None = None,
        players: dict[str, Player] | None = None,
    ) -> None:
        self._catalog_dir = catalog_dir
        self._fetcher = fetcher or fetch_sports
        self._stale_after = stale_after_seconds
        self._state_path = state_path
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._players = dict(players or {})
        self._points: dict[str, dict] = {}
        self._rows: dict[str, list[ScoreRow]] = {}
        self._tables: dict[str, list[dict]] = {}
        self._errors: dict[str, str] = {}
        self._recent: dict[str, str] = {}
        self._nfl: dict[str, str] = {}
        self._ready = False
        self._lock = threading.Lock()
        self._load_state()

    def refresh(self) -> None:
        try:
            self._refresh()
        except Exception:
            logger.exception("sports refresh failed")

    def panels_for(self, bay: str) -> list[dict]:
        now = self._now()
        with self._lock:
            if bay == "field":
                panels = [self._field(now)]
                panels.extend(self._standings_panels(now))
                panels.append(self._follows(now))
                return panels
            if bay == "far":
                return [self._far(now)]
            if bay == "fantasy":
                return self._fantasy(now)
        return []

    def panel(self, panel_id: str) -> dict | None:
        for bay in ("field", "far", "fantasy"):
            for payload in self.panels_for(bay):
                if payload["id"] == panel_id:
                    return payload
        return None

    def select(self, player_id: str) -> Roster:
        player = self._lookup(player_id)
        roster = self._mutate(lambda current: select_player(current, player))
        self.refresh()
        return roster

    def pin(self, player_id: str) -> Roster:
        player = self._lookup(player_id)
        roster = self._mutate(lambda current: pin_player(current, player))
        self.refresh()
        return roster

    def unpin(self, player_id: str) -> Roster:
        roster = self._mutate(lambda current: unpin_player(current, player_id))
        self.refresh()
        return roster

    def flex(self, player_id: str) -> Roster:
        roster = self._mutate(lambda current: assign_flex(current, player_id))
        self.refresh()
        return roster

    def drop(self, player_id: str) -> Roster:
        roster = self._mutate(lambda current: drop_player(current, player_id))
        self.refresh()
        return roster

    def scoring(self, scoring: str) -> Roster:
        roster = self._mutate(lambda current: set_scoring(current, scoring))
        self.refresh()
        return roster

    def follow(self, competition_id: str, on: bool) -> None:
        """Write one competition follow. An unknown id leaves the file unchanged."""
        competitions = load_competitions(self._catalog_dir / "competitions.json")
        if competition_id not in {item.id for item in competitions}:
            raise ValueError("competition is not in the catalog")
        path = self._catalog_dir / "follows.json"
        current = load_follows(path)
        kept = [item for item in current.competitions if item != competition_id]
        if on:
            kept.append(competition_id)
        save_follows(path, Follows(competitions=tuple(kept), sports=current.sports, competitors=current.competitors))

    def _mutate(self, change: Callable[[Roster], Roster]) -> Roster:
        path = self._catalog_dir / "roster.json"
        roster = change(load_roster(path))
        save_roster(path, roster)
        return roster

    def _lookup(self, player_id: str) -> Player:
        if player_id in self._players:
            return self._players[player_id]
        self._load_players()
        player = self._players.get(player_id)
        if player is None:
            raise KeyError(player_id)
        return player

    def _refresh(self) -> None:
        competitions = load_competitions(self._catalog_dir / "competitions.json")
        follows = load_follows(self._catalog_dir / "follows.json")
        now = self._now()
        rows: dict[str, list[ScoreRow]] = {}
        tables: dict[str, list[dict]] = {}
        errors: dict[str, str] = {}
        for competition in competitions:
            if not _wanted(competition, follows):
                continue
            try:
                payload = self._fetch_competition(competition, now)
                rows[competition.id] = parse_competition(competition, payload, now)
            except Exception as exc:
                errors[competition.id] = short_error(exc)
                rows[competition.id] = list(self._rows.get(competition.id) or [])
            table_url = standings_url(competition)
            if not table_url:
                continue
            try:
                tables[competition.id] = parse_standings(competition.kind, self._fetcher(table_url))
            except Exception:
                tables[competition.id] = list(self._tables.get(competition.id) or [])
        recent = dict(self._recent)
        for competition in competitions:
            if competition.kind != "thesportsdb" or competition.season_end:
                continue
            try:
                past_url = competition.fetch.replace("eventsnextleague.php", "eventspastleague.php")
                stamp = _event_date(_events(self._fetcher(past_url)))
            except Exception:
                continue
            if stamp:
                recent[competition.id] = stamp
        nfl = dict(self._nfl)
        if any(competition.id == "nfl" for competition in competitions):
            try:
                state = json.loads(self._fetcher("https://api.sleeper.app/v1/state/nfl").decode("utf-8"))
                if isinstance(state, dict):
                    phase = str(state.get("season_type") or "")
                    start = str(state.get("season_start_date") or "")
                    if phase:
                        nfl = {"phase": phase, "start": start}
            except Exception:
                logger.warning("nfl season state unavailable", exc_info=True)
        self._refresh_points()
        with self._lock:
            self._rows = rows
            self._tables = tables
            self._errors = errors
            self._recent = recent
            self._nfl = nfl
            self._ready = True
            self._save_state()

    def _fetch_competition(self, competition: Competition, now: datetime) -> bytes:
        if competition.kind == "thesportsdb":
            upcoming = self._fetcher(competition.fetch)
            past_url = competition.fetch.replace("eventsnextleague.php", "eventspastleague.php")
            past = self._fetcher(past_url)
            return json.dumps({"events": _events(upcoming) + _events(past)}).encode()
        if competition.kind != "mlb-schedule":
            return self._fetcher(competition.fetch)
        yesterday = (now - timedelta(days=1)).date().isoformat()
        today = now.date().isoformat()
        first = self._fetcher(f"{competition.fetch}&date={yesterday}")
        second = self._fetcher(f"{competition.fetch}&date={today}")
        return json.dumps({"dates": _dates(first) + _dates(second)}).encode()

    def _refresh_points(self) -> None:
        roster = load_roster(self._catalog_dir / "roster.json")
        if not roster.pins and all(player is None for player in roster.starters) and not roster.bench:
            self._points = {}
            return
        try:
            state = json.loads(self._fetcher(SLEEPER_STATE).decode("utf-8"))
            season = state.get("season")
            week = state.get("week")
            season_type = state.get("season_type") or "regular"
            if not season or not week:
                return
            url = SLEEPER_STATS.format(season_type=season_type, season=season, week=week)
            stats = json.loads(self._fetcher(url).decode("utf-8"))
        except Exception:
            logger.warning("fantasy points unavailable", exc_info=True)
            return
        if not isinstance(stats, dict):
            return
        key = POINT_KEYS[roster.scoring]
        points: dict[str, dict] = {}
        for player_id, body in stats.items():
            if not isinstance(body, dict):
                continue
            raw = body.get(key)
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                continue
            points[str(player_id)] = {
                "points": raw,
                "week": week,
                "source": "Sleeper",
                "source_url": url,
            }
        self._points = points

    def _load_players(self) -> None:
        try:
            payload = json.loads(self._fetcher(SLEEPER_PLAYERS).decode("utf-8"))
        except Exception as exc:
            raise KeyError("player directory unavailable") from exc
        if not isinstance(payload, dict):
            raise KeyError("player directory unavailable")
        for player_id, body in payload.items():
            player = _sleeper_player(str(player_id), body)
            if player is not None:
                self._players[player.id] = player

    def _field(self, now: datetime) -> dict:
        follows = load_follows(self._catalog_dir / "follows.json")
        competitions = {item.id: item for item in load_competitions(self._catalog_dir / "competitions.json")}
        if follows.empty:
            return _panel("field-scores", "Field", now, False, "", [_choose_follows(now)])
        items: list[dict] = []
        stale = False
        reasons: list[str] = []
        for ident, competition in competitions.items():
            if competition.tier not in FIELD_TIERS or not _wanted(competition, follows):
                continue
            error = self._errors.get(ident, "")
            cached = self._rows.get(ident) or []
            if error and not any(row.score for row in cached):
                items.append(_named_only(competition, now, error))
                stale = True
                reasons.append(error)
                continue
            if error:
                stale = True
                reasons.append(error)
            for row in cached:
                if follows.competitors and not _competitor(row, follows.competitors):
                    continue
                items.append(_score_item(competition, row, now))
        return _panel("field-scores", "Field", now, stale, "; ".join(dict.fromkeys(reasons)), items)

    def _standings_panels(self, now: datetime) -> list[dict]:
        follows = load_follows(self._catalog_dir / "follows.json")
        panels: list[dict] = []
        for competition in load_competitions(self._catalog_dir / "competitions.json"):
            if not _wanted(competition, follows):
                continue
            rows = self._tables.get(competition.id) or []
            if not rows:
                continue
            items = [
                {
                    "id": f"standing:{competition.id}:{row['rank']}:{row['team']}",
                    "title": row["team"],
                    "source": competition.source_name,
                    "source_url": standings_url(competition),
                    "observed_at": _iso(now),
                    "row": "standing",
                    "fields": {
                        "rank": row["rank"],
                        "team": row["team"],
                        "line": row["line"],
                        "family": competition.family,
                        "league": competition.name,
                    },
                }
                for row in rows
            ]
            panels.append(_panel(f"field-standings-{competition.id}", competition.name, now, False, "", items))
        return panels

    def _follows(self, now: datetime) -> dict:
        follows = load_follows(self._catalog_dir / "follows.json")
        chosen = set(follows.competitions)
        items = []
        for competition in load_competitions(self._catalog_dir / "competitions.json"):
            items.append(
                {
                    "id": f"follow-{competition.id}",
                    "title": competition.name,
                    "source": "Oriel",
                    "source_url": "",
                    "observed_at": _iso(now),
                    "row": "follow",
                    "fields": _follow_fields(
                        competition,
                        competition.id in chosen,
                        now,
                        recent=self._recent.get(competition.id, ""),
                        nfl=self._nfl if competition.id == "nfl" else None,
                    ),
                }
            )
        return _panel("field-follows", "Follows", now, False, "", items)

    def _far(self, now: datetime) -> dict:
        competitions = load_competitions(self._catalog_dir / "competitions.json")
        far = [competition for competition in competitions if competition.tier == "far"]
        if not far:
            return _panel("far-desk", "Far Desk", now, False, "", [_no_far_coverage(now)])
        items: list[dict] = []
        for competition in far:
            for row in self._rows.get(competition.id) or []:
                items.append(_far_item(competition, row, now))
        return _panel("far-desk", "Far Desk", now, False, "", items)

    def _fantasy(self, now: datetime) -> list[dict]:
        roster = load_roster(self._catalog_dir / "roster.json")
        pinned = {player.id for player in roster.pins}
        pins = [_fantasy_item(player, "pin", now, roster.scoring, self._points.get(player.id), pinned=False) for player in roster.pins]
        lineup = []
        for index, slot in enumerate(LINEUP_SLOTS):
            player = roster.starters[index]
            if player is None:
                lineup.append(_empty_slot(slot, index, now))
            else:
                lineup.append(_fantasy_item(player, slot, now, roster.scoring, self._points.get(player.id), pinned=player.id in pinned))
        bench = [
            _fantasy_item(player, "BN", now, roster.scoring, self._points.get(player.id), pinned=player.id in pinned)
            for player in roster.bench
        ]
        return [
            _panel("fantasy-pins", "Pins", now, False, "", pins),
            _panel("fantasy-lineup", "Lineup", now, False, "", lineup),
            _panel("fantasy-bench", "Bench", now, False, "", bench),
        ]

    def _load_state(self) -> None:
        if self._state_path is None or not self._state_path.is_file():
            return
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        points = raw.get("points")
        if isinstance(points, dict):
            self._points = {str(key): value for key, value in points.items() if isinstance(value, dict)}

    def _save_state(self) -> None:
        if self._state_path is None:
            return
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        body = {"points": self._points}
        self._state_path.write_text(json.dumps(body), encoding="utf-8")


def fetch_sports(url: str, *, timeout: float = 20.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Oriel/0.1", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read(MAX_SPORTS_BYTES + 1)
    except urllib.error.HTTPError:
        raise
    if len(payload) > MAX_SPORTS_BYTES:
        raise ValueError("sports payload too large")
    if not payload:
        raise ValueError("empty sports payload")
    return payload


def _wanted(competition: Competition, follows) -> bool:
    if competition.tier == "far":
        return True
    if follows.empty:
        return False
    named = bool(follows.competitions or follows.sports)
    if named and competition.id not in follows.competitions and competition.family not in follows.sports:
        return False
    return True


def _competitor(row: ScoreRow, names: tuple[str, ...]) -> bool:
    wanted = {name.casefold() for name in names}
    return row.home.casefold() in wanted or row.away.casefold() in wanted


def _events(payload: bytes) -> list:
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []
    events = body.get("events") if isinstance(body, dict) else None
    return events if isinstance(events, list) else []


def _event_date(events: list) -> str:
    for event in events:
        if isinstance(event, dict):
            stamp = str(event.get("dateEvent") or "")
            if len(stamp) == 10:
                return stamp
    return ""


def _follow_fields(
    competition: Competition,
    followed: bool,
    now: datetime,
    *,
    recent: str = "",
    nfl: dict | None = None,
) -> dict:
    fields: dict = {
        "competition_id": competition.id,
        "tier": competition.tier,
        "family": competition.family,
        "followed": followed,
    }
    if competition.country:
        fields["country"] = competition.country
    if competition.season:
        fields["season"] = competition.season
    start = competition.season_start
    if nfl and nfl.get("start"):
        start = nfl["start"]
    if start:
        fields["season_start"] = start
    if competition.season_end:
        fields["season_end"] = competition.season_end
    last = recent or competition.last_event
    if last:
        fields["last_event"] = last
    if competition.next_event:
        fields["next_event"] = competition.next_event
    flag = _season_flag(competition, now, recent=recent, nfl=nfl)
    if flag:
        fields["flag"] = flag
    return fields


def _season_flag(competition: Competition, now: datetime, *, recent: str = "", nfl: dict | None = None) -> str:
    today = now.date()
    if nfl and nfl.get("phase"):
        phase = nfl["phase"]
        start = nfl.get("start") or competition.season_start
        if phase == "off":
            return "off season"
        if phase in {"regular", "post", "pre"} and (not start or today >= datetime.fromisoformat(start).date()):
            return "active"
    if competition.season_start and competition.season_end:
        start = datetime.fromisoformat(competition.season_start).date()
        end = datetime.fromisoformat(competition.season_end).date()
        if start <= today <= end:
            return "active"
        return "off season"
    last = recent or competition.last_event
    if last and 0 <= (today - datetime.fromisoformat(last).date()).days <= 28:
        return "active"
    if competition.next_event and datetime.fromisoformat(competition.next_event).date() > today:
        return "off season"
    return ""


def _dates(payload: bytes) -> list:
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []
    dates = body.get("dates") if isinstance(body, dict) else None
    return dates if isinstance(dates, list) else []


def _sleeper_player(player_id: str, body: object) -> Player | None:
    if not isinstance(body, dict):
        return None
    position = body.get("position") or ""
    name = body.get("full_name") or body.get("last_name") or ""
    team = body.get("team") or ""
    if not isinstance(position, str) or not isinstance(name, str) or not name:
        return None
    if position not in {"QB", "RB", "WR", "TE", "K", "DEF", "DST"}:
        return None
    if position == "DEF":
        position = "DST"
    if not isinstance(team, str):
        team = ""
    return Player(id=player_id, name=name, position=position, team=team)


def _no_far_coverage(now: datetime) -> dict:
    return {
        "id": "no-far-coverage",
        "title": "No far-coverage competition is configured",
        "source": "Oriel",
        "source_url": "",
        "observed_at": _iso(now),
        "row": "headline",
        "fields": {},
    }


def _choose_follows(now: datetime) -> dict:
    return {
        "id": "choose-follows",
        "title": "Choose follows",
        "source": "Oriel",
        "source_url": "",
        "observed_at": _iso(now),
        "row": "headline",
        "fields": {"desk": "field"},
    }


def _named_only(competition: Competition, now: datetime, reason: str) -> dict:
    return {
        "id": f"{competition.id}-unavailable",
        "title": competition.name,
        "source": competition.source_name,
        "source_url": competition.fetch,
        "observed_at": _iso(now),
        "row": "score",
        "fields": {"home": competition.name, "away": "", "state": reason, "tier": competition.tier},
    }


def _score_item(competition: Competition, row: ScoreRow, now: datetime) -> dict:
    state = row.state
    if row.clock and row.state == "in progress":
        state = f"in progress {row.clock}"
    fields: dict = {
        "home": row.home,
        "away": row.away,
        "state": state,
        "tier": competition.tier,
        "league": competition.name,
        "family": competition.family,
    }
    if row.score and competition.tier != "schedule":
        fields["score"] = row.score
    title = " ".join(part for part in (row.away, row.home) if part)
    return _item(row.id, title or competition.name, competition, row, now, fields)


def _far_item(competition: Competition, row: ScoreRow, now: datetime) -> dict:
    if row.excerpt:
        return {
            "id": row.id,
            "title": f"\"{row.excerpt}\"",
            "source": competition.source_name,
            "source_url": competition.fetch,
            "observed_at": _iso(row.when or now),
            "row": "score",
            "fields": {
                "home": row.home,
                "away": row.away,
                "state": "report",
                "tier": "far",
                "excerpt": row.excerpt,
            },
        }
    fields: dict = {
        "home": row.home,
        "away": row.away,
        "state": row.state,
        "tier": "far",
        "factual": True,
    }
    if row.score:
        fields["score"] = row.score
    if row.factual:
        fields["factual_line"] = row.factual
    title = row.factual or " ".join(part for part in (row.home, row.away) if part)
    return _item(row.id, title, competition, row, now, fields)


def _fantasy_item(player: Player, slot: str, now: datetime, scoring: str, points: dict | None, *, pinned: bool) -> dict:
    fields: dict = {
        "player": player.name,
        "position": player.position,
        "team": player.team,
        "slot": slot,
        "scoring": scoring,
    }
    source = ""
    source_url = ""
    if pinned:
        fields["pinned"] = True
    if points is not None:
        fields["points"] = points["points"]
        fields["week"] = points["week"]
        source = points["source"]
        source_url = points["source_url"]
    return {
        "id": f"{slot}-{player.id}",
        "title": player.name,
        "source": source,
        "source_url": source_url,
        "observed_at": _iso(now),
        "row": "fantasy",
        "fields": fields,
    }


def _empty_slot(slot: str, index: int, now: datetime) -> dict:
    return {
        "id": f"slot-{index}-{slot}",
        "title": slot,
        "source": "",
        "source_url": "",
        "observed_at": _iso(now),
        "row": "fantasy",
        "fields": {"player": "", "position": "", "team": "", "slot": slot},
    }


def _item(ident: str, title: str, competition: Competition, row: ScoreRow, now: datetime, fields: dict) -> dict:
    return {
        "id": ident,
        "title": title,
        "source": competition.source_name,
        "source_url": competition.fetch,
        "observed_at": _iso(row.when or now),
        "row": "score",
        "fields": fields,
    }


def _panel(ident: str, title: str, now: datetime, stale: bool, reason: str, items: list[dict]) -> dict:
    return {
        "id": ident,
        "domain": "sports",
        "title": title,
        "updated_at": _iso(now),
        "stale": stale,
        "stale_reason": reason if stale else "",
        "items": items,
    }


def _iso(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
