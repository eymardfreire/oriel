"""Parse verified public score feeds into rows. Missing scores stay missing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from oriel_server.sports.catalog import RECENT_HOURS, Competition


@dataclass(frozen=True)
class ScoreRow:
    id: str
    home: str
    away: str
    when: datetime | None
    state: str
    score: str | None = None
    excerpt: str | None = None
    factual: str | None = None


def parse_competition(competition: Competition, payload: bytes, now: datetime) -> list[ScoreRow]:
    if competition.kind == "mlb-schedule":
        return _mlb(competition, payload, now)
    if competition.kind == "nhl-schedule":
        return _nhl(competition, payload, now)
    if competition.kind == "openligadb":
        return _openligadb(competition, payload, now)
    if competition.kind == "jolpica-results":
        return _jolpica(competition, payload, now)
    if competition.kind == "fixture":
        return _fixture(competition, payload, now)
    raise ValueError(f"unknown kind {competition.kind}")


def factual_line(winner: str, loser: str, score: str) -> str:
    return f"{winner} defeated {loser} {score}"


def _mlb(competition: Competition, payload: bytes, now: datetime) -> list[ScoreRow]:
    body = _json(payload)
    rows: list[ScoreRow] = []
    for date in body.get("dates") or []:
        for game in date.get("games") or []:
            teams = game.get("teams") or {}
            home = _name((teams.get("home") or {}).get("team"))
            away = _name((teams.get("away") or {}).get("team"))
            status = ((game.get("status") or {}).get("abstractGameState") or "").lower()
            when = _stamp(game.get("gameDate"))
            home_score = (teams.get("home") or {}).get("score")
            away_score = (teams.get("away") or {}).get("score")
            rows.append(_row(competition, home, away, when, status, home_score, away_score, now))
    return [row for row in rows if row is not None]


def _nhl(competition: Competition, payload: bytes, now: datetime) -> list[ScoreRow]:
    body = _json(payload)
    rows: list[ScoreRow] = []
    for day in body.get("gameWeek") or []:
        for game in day.get("games") or []:
            home = _nhl_name(game.get("homeTeam"))
            away = _nhl_name(game.get("awayTeam"))
            state = str(game.get("gameState") or "").upper()
            when = _stamp(game.get("startTimeUTC"))
            mapped = "final" if state in {"FINAL", "OFF"} else "live" if state in {"LIVE", "CRIT"} else "preview"
            home_score = (game.get("homeTeam") or {}).get("score")
            away_score = (game.get("awayTeam") or {}).get("score")
            rows.append(_row(competition, home, away, when, mapped, home_score, away_score, now))
    return [row for row in rows if row is not None]


def _openligadb(competition: Competition, payload: bytes, now: datetime) -> list[ScoreRow]:
    body = _json(payload)
    if not isinstance(body, list):
        return []
    rows: list[ScoreRow] = []
    for match in body:
        if not isinstance(match, dict) or not match.get("matchIsFinished"):
            continue
        home = _name(match.get("team1"))
        away = _name(match.get("team2"))
        when = _stamp(match.get("matchDateTime"))
        final = _final_result(match.get("matchResults"))
        if final is None:
            continue
        home_score, away_score = final
        rows.append(_row(competition, home, away, when, "final", home_score, away_score, now))
    return [row for row in rows if row is not None]


def _jolpica(competition: Competition, payload: bytes, now: datetime) -> list[ScoreRow]:
    body = _json(payload)
    races = (((body.get("MRData") or {}).get("RaceTable") or {}).get("Races")) or []
    if not races:
        return []
    race = races[0]
    when = _stamp(race.get("date"))
    if when is None or not _recent(when, now):
        return []
    results = race.get("Results") or []
    if len(results) < 2:
        return []
    winner = _driver(results[0])
    second = _driver(results[1])
    if not winner or not second:
        return []
    score = "1-2"
    return [
        ScoreRow(
            id=f"{competition.id}-result",
            home=winner,
            away=second,
            when=when,
            state="final",
            score=score,
            factual=factual_line(winner, second, score),
        )
    ]


def _fixture(competition: Competition, payload: bytes, now: datetime) -> list[ScoreRow]:
    body = _json(payload)
    rows = body if isinstance(body, list) else body.get("rows") or []
    found: list[ScoreRow] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        when = _stamp(row.get("when"))
        state = str(row.get("state") or "scheduled")
        if competition.tier in {"results", "far"} and state == "final" and when is not None and not _recent(when, now):
            continue
        score = row.get("score")
        if competition.tier in {"schedule", "far"} and competition.tier == "schedule":
            score = None
        excerpt = row.get("excerpt")
        factual = row.get("factual")
        if competition.tier == "far" and score and not factual and not excerpt:
            factual = factual_line(str(row.get("home") or ""), str(row.get("away") or ""), str(score))
        found.append(
            ScoreRow(
                id=str(row.get("id") or f"{competition.id}-{index}"),
                home=str(row.get("home") or ""),
                away=str(row.get("away") or ""),
                when=when,
                state=state,
                score=None if score in (None, "") else str(score),
                excerpt=None if not excerpt else str(excerpt),
                factual=None if not factual else str(factual),
            )
        )
    return found


def _row(
    competition: Competition,
    home: str,
    away: str,
    when: datetime | None,
    status: str,
    home_score: object,
    away_score: object,
    now: datetime,
) -> ScoreRow | None:
    if not home or not away:
        return None
    in_play = status in {"live", "in progress"}
    final = status == "final"
    scheduled = not in_play and not final
    if competition.tier == "schedule":
        return ScoreRow(id=_ident(competition, home, away, when), home=home, away=away, when=when, state=_when_label(when))
    if competition.tier in {"results", "far"}:
        if not final or when is None or not _recent(when, now):
            return None
    elif final and when is not None and not _recent(when, now):
        return None
    elif scheduled and competition.tier in {"live", "delayed"}:
        return ScoreRow(id=_ident(competition, home, away, when), home=home, away=away, when=when, state=_when_label(when))
    score = _score(home_score, away_score)
    if in_play or final:
        if score is None and competition.tier in {"live", "delayed"}:
            return ScoreRow(
                id=_ident(competition, home, away, when),
                home=home,
                away=away,
                when=when,
                state="in progress" if in_play else "final",
            )
        if score is None:
            return None
    state = "in progress" if in_play else "final" if final else _when_label(when)
    factual = factual_line(_winner(home, away, home_score, away_score), _loser(home, away, home_score, away_score), score) if competition.tier == "far" and score else None
    return ScoreRow(
        id=_ident(competition, home, away, when),
        home=home,
        away=away,
        when=when,
        state=state,
        score=score,
        factual=factual,
    )


def _winner(home: str, away: str, home_score: object, away_score: object) -> str:
    if _number(home_score) >= _number(away_score):
        return home
    return away


def _loser(home: str, away: str, home_score: object, away_score: object) -> str:
    if _number(home_score) >= _number(away_score):
        return away
    return home


def _score(home_score: object, away_score: object) -> str | None:
    if home_score is None or away_score is None:
        return None
    if isinstance(home_score, bool) or isinstance(away_score, bool):
        return None
    if not isinstance(home_score, (int, float)) or not isinstance(away_score, (int, float)):
        return None
    return f"{_trim(home_score)}-{_trim(away_score)}"


def _trim(value: float | int) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return float(value)


def _recent(when: datetime, now: datetime) -> bool:
    return now - timedelta(hours=RECENT_HOURS) <= when <= now + timedelta(hours=1)


def _when_label(when: datetime | None) -> str:
    if when is None:
        return "scheduled"
    return when.astimezone(timezone.utc).strftime("scheduled %Y-%m-%d %H:%M UTC")


def _ident(competition: Competition, home: str, away: str, when: datetime | None) -> str:
    stamp = when.strftime("%Y%m%dT%H%M") if when else "na"
    return f"{competition.id}-{stamp}-{_slug(away)}-{_slug(home)}"


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def _final_result(results: object) -> tuple[object, object] | None:
    if not isinstance(results, list):
        return None
    final = None
    for result in results:
        if isinstance(result, dict) and result.get("resultTypeKind") in {"After90Minutes", "Final"}:
            final = result
    if final is None:
        for result in results:
            if isinstance(result, dict) and result.get("resultName") == "Endergebnis":
                final = result
    if not isinstance(final, dict):
        return None
    return final.get("pointsTeam1"), final.get("pointsTeam2")


def _nhl_name(team: object) -> str:
    if not isinstance(team, dict):
        return ""
    place = team.get("placeName") or {}
    common = team.get("commonName") or {}
    city = place.get("default") if isinstance(place, dict) else ""
    name = common.get("default") if isinstance(common, dict) else ""
    return " ".join(part for part in (city, name) if part)


def _driver(result: object) -> str:
    if not isinstance(result, dict):
        return ""
    driver = result.get("Driver") or {}
    if not isinstance(driver, dict):
        return ""
    given = driver.get("givenName") or ""
    family = driver.get("familyName") or ""
    return " ".join(part for part in (given, family) if part)


def _name(team: object) -> str:
    if not isinstance(team, dict):
        return ""
    return str(team.get("name") or team.get("teamName") or "")


def _stamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    if len(text) == 10:
        text += "T00:00:00+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _json(payload: bytes) -> dict | list:
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("unreadable sports payload") from exc
    if not isinstance(body, (dict, list)):
        raise ValueError("unreadable sports payload")
    return body
