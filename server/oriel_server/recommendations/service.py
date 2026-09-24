"""Read live panels and operator overrides, then rank a suggestion."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from oriel_server.recommendations.rank import DESKS, Snapshot, Suggestion, rank
from oriel_server.sports.catalog import load_follows

SINGLE_BAY = {
    "brief": ("brief",),
    "wires": ("wires",),
    "markets": ("markets",),
    "field": ("field",),
    "storm": ("storm",),
    "trade": ("trade",),
    "far": ("far",),
    "fantasy": ("fantasy",),
    "three": ("wires", "markets", "field"),
}


class Recommendations:
    def __init__(self, catalog_dir: Path, sports_dir: Path, *, overrides_path: Path | None = None) -> None:
        self._catalog_dir = catalog_dir
        self._sports_dir = sports_dir
        self._overrides_path = overrides_path or catalog_dir / "overrides.json"

    def suggestion(self, sources: dict, now: datetime) -> Suggestion:
        overrides = _load_overrides(self._overrides_path)
        follows = load_follows(self._sports_dir / "follows.json")
        severity, headline = _alert(sources.get("weather"))
        stale = tuple(desk for desk, source in sources.items() if source is not None and _stale(source))
        return rank(
            Snapshot(
                now=now,
                sports_follows=not follows.empty,
                alert_severity=severity,
                alert_headline=headline,
                stale_desks=stale,
                fantasy_player=_fantasy_player(sources.get("sports")),
                pinned_bay=overrides["pinned_bay"],
                dismissed=tuple(overrides["dismissed"]),
            ),
            _panels(self._catalog_dir),
        )

    def pin(self, bay_id: str) -> None:
        if bay_id not in DESKS or bay_id == "three":
            raise ValueError("pin a bay, not a desk")
        overrides = _load_overrides(self._overrides_path)
        overrides["pinned_bay"] = bay_id
        overrides["dismissed"] = [desk for desk in overrides["dismissed"] if desk != bay_id]
        _save_overrides(self._overrides_path, overrides)

    def dismiss(self, desk_id: str) -> None:
        if desk_id not in DESKS:
            raise ValueError("unknown desk")
        overrides = _load_overrides(self._overrides_path)
        if desk_id not in overrides["dismissed"]:
            overrides["dismissed"].append(desk_id)
        if overrides["pinned_bay"] == desk_id:
            overrides["pinned_bay"] = ""
        _save_overrides(self._overrides_path, overrides)

    def clear(self) -> None:
        _save_overrides(self._overrides_path, {"pinned_bay": "", "dismissed": []})


def _panels(catalog_dir: Path) -> dict[str, tuple[str, ...]]:
    found = dict(SINGLE_BAY)
    for desk_id in DESKS:
        path = catalog_dir / "desks" / f"{desk_id}.json"
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        bays = raw.get("bays") if isinstance(raw, dict) else None
        if not isinstance(bays, list):
            continue
        ids = tuple(str(bay.get("id")) for bay in bays if isinstance(bay, dict) and bay.get("id"))
        if ids:
            found[desk_id] = ids
    return found


def _alert(weather) -> tuple[str, str]:
    if weather is None:
        return "", ""
    panel = weather.panel("weather-alerts") if hasattr(weather, "panel") else None
    if not isinstance(panel, dict):
        return "", ""
    best = ("", "")
    rank = {"extreme": 3, "severe": 2}
    for item in panel.get("items") or []:
        fields = item.get("fields") or {}
        severity = str(fields.get("severity") or "")
        headline = str(fields.get("headline") or item.get("title") or "")
        if not severity or headline == "No alerts are active":
            continue
        if rank.get(severity.casefold(), 1) >= rank.get(best[0].casefold(), 0):
            best = (severity, headline)
    return best


def _fantasy_player(sports) -> str:
    if sports is None:
        return ""
    for panel in sports.panels_for("fantasy"):
        for item in panel.get("items") or []:
            fields = item.get("fields") or {}
            state = str(fields.get("game_state") or "").casefold()
            player = str(fields.get("player") or "")
            if state == "in progress" and player:
                return player
    return ""


def _stale(source) -> bool:
    panels = source.panels() if hasattr(source, "panels") else []
    if not panels and hasattr(source, "panels_for"):
        panels = []
        for bay in ("field", "far", "fantasy"):
            panels.extend(source.panels_for(bay))
    return bool(panels) and all(panel.get("stale") for panel in panels)


def _load_overrides(path: Path) -> dict:
    if not path.is_file():
        return {"pinned_bay": "", "dismissed": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"pinned_bay": "", "dismissed": []}
    pinned = raw.get("pinned_bay") if isinstance(raw, dict) else ""
    dismissed = raw.get("dismissed") if isinstance(raw, dict) else []
    if not isinstance(pinned, str):
        pinned = ""
    if not isinstance(dismissed, list):
        dismissed = []
    return {"pinned_bay": pinned, "dismissed": [item for item in dismissed if isinstance(item, str)]}


def _save_overrides(path: Path, overrides: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overrides, indent=2) + "\n", encoding="utf-8")
