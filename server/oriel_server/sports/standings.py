"""Parse public season tables. A missing figure stays off the row."""

from __future__ import annotations

import json

from oriel_server.sports.catalog import Competition


def standings_url(competition: Competition) -> str:
    if competition.kind == "mlb-schedule":
        season = competition.season or "2026"
        return (
            "https://statsapi.mlb.com/api/v1/standings"
            f"?leagueId=103,104&season={season}&standingsTypes=regularSeason"
        )
    if competition.kind == "nhl-schedule":
        return "https://api-web.nhle.com/v1/standings/now"
    if competition.kind == "openligadb" and "/getmatchdata/" in competition.fetch:
        return competition.fetch.replace("/getmatchdata/", "/getbltable/")
    if competition.kind == "jolpica-results":
        return "https://api.jolpi.ca/ergast/f1/current/driverStandings.json"
    return ""


def parse_standings(kind: str, payload: bytes) -> list[dict]:
    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []
    if kind == "mlb-schedule":
        return _mlb(body)
    if kind == "nhl-schedule":
        return _nhl(body)
    if kind == "openligadb":
        return _openliga(body)
    if kind == "jolpica-results":
        return _jolpica(body)
    return []


def _row(rank: object, team: object, line: str) -> dict | None:
    if not isinstance(team, str) or not team.strip():
        return None
    label = str(rank).strip() if rank is not None else ""
    if not label:
        return None
    return {"rank": label, "team": team.strip(), "line": line}


def _mlb(body: object) -> list[dict]:
    if not isinstance(body, dict):
        return []
    rows: list[dict] = []
    for record in body.get("records") or []:
        if not isinstance(record, dict):
            continue
        for team in record.get("teamRecords") or []:
            if not isinstance(team, dict):
                continue
            name = (team.get("team") or {}).get("name") if isinstance(team.get("team"), dict) else ""
            wins = team.get("wins")
            losses = team.get("losses")
            line = ""
            if isinstance(wins, int) and isinstance(losses, int):
                line = f"{wins}-{losses}"
            parsed = _row(team.get("divisionRank") or team.get("leagueRank"), name, line)
            if parsed:
                rows.append(parsed)
    return rows


def _nhl(body: object) -> list[dict]:
    if not isinstance(body, dict):
        return []
    rows: list[dict] = []
    for team in body.get("standings") or []:
        if not isinstance(team, dict):
            continue
        name = team.get("teamName")
        if isinstance(name, dict):
            name = name.get("default")
        wins = team.get("wins")
        losses = team.get("losses")
        points = team.get("points")
        line = ""
        if isinstance(points, int):
            line = f"{points} pts"
        elif isinstance(wins, int) and isinstance(losses, int):
            line = f"{wins}-{losses}"
        parsed = _row(team.get("divisionSequence") or team.get("leagueSequence"), name, line)
        if parsed:
            rows.append(parsed)
    return rows


def _openliga(body: object) -> list[dict]:
    if not isinstance(body, list):
        return []
    rows: list[dict] = []
    for index, team in enumerate(body, start=1):
        if not isinstance(team, dict):
            continue
        points = team.get("points")
        line = f"{points} pts" if isinstance(points, int) else ""
        parsed = _row(index, team.get("teamName") or team.get("shortName"), line)
        if parsed:
            rows.append(parsed)
    return rows


def _jolpica(body: object) -> list[dict]:
    if not isinstance(body, dict):
        return []
    table = ((body.get("MRData") or {}).get("StandingsTable") or {}).get("StandingsLists") or []
    if not table or not isinstance(table, list) or not isinstance(table[0], dict):
        return []
    rows: list[dict] = []
    for driver in table[0].get("DriverStandings") or []:
        if not isinstance(driver, dict):
            continue
        person = driver.get("Driver") if isinstance(driver.get("Driver"), dict) else {}
        name = " ".join(part for part in (person.get("givenName"), person.get("familyName")) if isinstance(part, str) and part)
        points = driver.get("points")
        line = f"{points} pts" if isinstance(points, str) and points else ""
        parsed = _row(driver.get("position"), name, line)
        if parsed:
            rows.append(parsed)
    return rows
