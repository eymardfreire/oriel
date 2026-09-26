"""Load the sports catalog, follows, and fantasy roster."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

TIERS = ("live", "delayed", "results", "schedule", "far")
KINDS = ("mlb-schedule", "nhl-schedule", "openligadb", "jolpica-results", "thesportsdb", "fixture")
FIELD_TIERS = ("live", "delayed", "results", "schedule")
LINEUP_SLOTS = ("QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DST")
FLEX_POSITIONS = frozenset({"RB", "WR", "TE"})
SCORING = ("ppr", "half-ppr", "standard")
POINT_KEYS = {"ppr": "pts_ppr", "half-ppr": "pts_half_ppr", "standard": "pts_std"}
RECENT_HOURS = 48


@dataclass(frozen=True)
class Competition:
    id: str
    family: str
    name: str
    tier: str
    source_id: str
    source_name: str
    kind: str
    fetch: str
    note: str
    country: str = ""
    season: str = ""
    season_start: str = ""
    season_end: str = ""
    last_event: str = ""
    next_event: str = ""


@dataclass(frozen=True)
class Follows:
    competitions: tuple[str, ...]
    sports: tuple[str, ...]
    competitors: tuple[str, ...]

    @property
    def empty(self) -> bool:
        return not self.competitions and not self.sports and not self.competitors


@dataclass(frozen=True)
class Player:
    id: str
    name: str
    position: str
    team: str


@dataclass
class Roster:
    scoring: str
    starters: list[Player | None]
    bench: list[Player]
    pins: list[Player]


def load_competitions(path: Path) -> tuple[Competition, ...]:
    raw = _object(path)
    rows = raw.get("competitions")
    if not isinstance(rows, list):
        raise ValueError(f"{path}: competitions must be a list")
    found: list[Competition] = []
    seen: set[str] = set()
    for index, body in enumerate(rows):
        if not isinstance(body, dict):
            raise ValueError(f"{path}: competitions[{index}] must be an object")
        tier = body.get("tier")
        kind = body.get("kind")
        if tier not in TIERS:
            raise ValueError(f"{path}: competitions[{index}] has unknown tier {tier!r}")
        if kind not in KINDS:
            raise ValueError(f"{path}: competitions[{index}] has unknown kind {kind!r}")
        ident = _text(body.get("id"), path, f"competitions[{index}].id")
        if ident in seen:
            raise ValueError(f"{path}: duplicate competition {ident}")
        seen.add(ident)
        found.append(
            Competition(
                id=ident,
                family=_text(body.get("family"), path, f"competitions[{index}].family"),
                name=_text(body.get("name"), path, f"competitions[{index}].name"),
                tier=tier,
                source_id=_text(body.get("source_id"), path, f"competitions[{index}].source_id"),
                source_name=_text(body.get("source_name"), path, f"competitions[{index}].source_name"),
                kind=kind,
                fetch=_text(body.get("fetch"), path, f"competitions[{index}].fetch"),
                note=_text(body.get("note"), path, f"competitions[{index}].note"),
                country=_optional_text(body.get("country")),
                season=_optional_text(body.get("season")),
                season_start=_optional_date(body.get("season_start"), path, f"competitions[{index}].season_start"),
                season_end=_optional_date(body.get("season_end"), path, f"competitions[{index}].season_end"),
                last_event=_optional_date(body.get("last_event"), path, f"competitions[{index}].last_event"),
                next_event=_optional_date(body.get("next_event"), path, f"competitions[{index}].next_event"),
            )
        )
    return tuple(found)


def load_follows(path: Path) -> Follows:
    raw = _object(path)
    return Follows(
        competitions=_names(raw.get("competitions"), path, "competitions"),
        sports=_names(raw.get("sports"), path, "sports"),
        competitors=_names(raw.get("competitors"), path, "competitors"),
    )


def save_follows(path: Path, follows: Follows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "competitions": list(follows.competitions),
        "sports": list(follows.sports),
        "competitors": list(follows.competitors),
    }
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def load_roster(path: Path) -> Roster:
    if not path.is_file():
        return empty_roster()
    raw = _object(path)
    scoring = raw.get("scoring", "ppr")
    if scoring not in SCORING:
        raise ValueError(f"{path}: scoring must be ppr, half-ppr, or standard")
    starters = raw.get("starters", [None] * len(LINEUP_SLOTS))
    if not isinstance(starters, list) or len(starters) != len(LINEUP_SLOTS):
        raise ValueError(f"{path}: starters must be {len(LINEUP_SLOTS)} slots")
    return Roster(
        scoring=scoring,
        starters=[None if slot is None else _player(slot, path) for slot in starters],
        bench=[_player(row, path) for row in _list(raw.get("bench"), path, "bench")],
        pins=[_player(row, path) for row in _list(raw.get("pins"), path, "pins")],
    )


def save_roster(path: Path, roster: Roster) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "scoring": roster.scoring,
        "starters": [None if player is None else _dump(player) for player in roster.starters],
        "bench": [_dump(player) for player in roster.bench],
        "pins": [_dump(player) for player in roster.pins],
    }
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def empty_roster() -> Roster:
    return Roster(scoring="ppr", starters=[None] * len(LINEUP_SLOTS), bench=[], pins=[])


def followed(competition: Competition, follows: Follows) -> bool:
    if follows.empty:
        return False
    if competition.id in follows.competitions or competition.family in follows.sports:
        return True
    return False


def _dump(player: Player) -> dict[str, str]:
    return {"id": player.id, "name": player.name, "position": player.position, "team": player.team}


def _player(body: object, path: Path) -> Player:
    if not isinstance(body, dict):
        raise ValueError(f"{path}: player must be an object")
    return Player(
        id=_text(body.get("id"), path, "player.id"),
        name=_text(body.get("name"), path, "player.name"),
        position=_text(body.get("position"), path, "player.position"),
        team=_text(body.get("team"), path, "player.team"),
    )


def _names(value: object, path: Path, label: str) -> tuple[str, ...]:
    rows = _list(value, path, label)
    names: list[str] = []
    for index, item in enumerate(rows):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{path}: {label}[{index}] must be a non-empty string")
        names.append(item.strip())
    return tuple(names)


def _list(value: object, path: Path, label: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{path}: {label} must be a list")
    return value


def _object(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: unreadable") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected an object")
    return raw


def _optional_text(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        return ""
    return value.strip()


def _optional_date(value: object, path: Path, label: str) -> str:
    text = _optional_text(value)
    if not text:
        return ""
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise ValueError(f"{path}: {label} must be YYYY-MM-DD")
    return text


def _text(value: object, path: Path, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {label} must be a non-empty string")
    return value.strip()
