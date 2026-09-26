"""The brief strip chooses one place, one wire outlet, and one market family."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from oriel_server.config import HomePlace
from oriel_server.markets.catalog import FAMILIES, FAMILY_TITLE
from oriel_server.weather.places import load_places
from oriel_server.wires.catalog import load_outlets

SLOTS = ("place", "outlet", "family")


@dataclass
class BriefStore:
    selection_path: Path
    places_path: Path
    outlets_dir: Path
    home: HomePlace

    @classmethod
    def open(cls, root: Path, home: HomePlace) -> BriefStore:
        return cls(
            root / "catalog" / "brief" / "selection.json",
            root / "catalog" / "weather" / "places.json",
            root / "catalog" / "outlets",
            home,
        )

    def choose(self, slot: str, choice_id: str) -> None:
        if slot not in SLOTS:
            raise ValueError("slot is not a brief choice")
        if not isinstance(choice_id, str):
            raise ValueError("id is not in the catalog")
        known = self._known()
        if choice_id != "" and choice_id not in known[slot]:
            raise ValueError("id is not in the catalog")
        current = load_selection(self.selection_path)
        current[slot] = choice_id
        save_selection(self.selection_path, current)

    def payload(self) -> dict:
        current = load_selection(self.selection_path)
        now = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "place": current["place"],
            "outlet": current["outlet"],
            "family": current["family"],
            "items": self._items(current, now),
        }

    def _known(self) -> dict[str, set[str]]:
        return {
            "place": {place_id for place_id, _name in self._places()},
            "outlet": {outlet_id for outlet_id, _name in self._outlets()},
            "family": set(FAMILIES),
        }

    def _places(self) -> list[tuple[str, str]]:
        if not self.places_path.is_file():
            return []
        places = load_places(self.places_path, self.home)
        return [(place.id, place.name) for place in places if place.id != self.home.id]

    def _outlets(self) -> list[tuple[str, str]]:
        if not self.outlets_dir.is_dir():
            return []
        outlets = [outlet for outlet in load_outlets(self.outlets_dir) if outlet.enabled]
        names = [outlet.name for outlet in outlets]
        rows = []
        for outlet in outlets:
            title = outlet.name
            if names.count(outlet.name) > 1:
                title = f"{outlet.name} ({outlet.region})"
            rows.append((outlet.id, title))
        return rows

    def _items(self, current: dict[str, str], now: str) -> list[dict]:
        items = [_row("place", "", "Home", current["place"] == "", now)]
        for place_id, name in self._places():
            items.append(_row("place", place_id, name, current["place"] == place_id, now))
        items.append(_row("outlet", "", "First headline", current["outlet"] == "", now))
        for outlet_id, name in self._outlets():
            items.append(_row("outlet", outlet_id, name, current["outlet"] == outlet_id, now))
        items.append(_row("family", "", "First quote", current["family"] == "", now))
        for family in FAMILIES:
            items.append(_row("family", family, FAMILY_TITLE[family], current["family"] == family, now))
        return items


def load_selection(path: Path) -> dict[str, str]:
    empty = {slot: "" for slot in SLOTS}
    if not path.is_file():
        return empty
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty
    if not isinstance(raw, dict):
        return empty
    loaded = dict(empty)
    for slot in SLOTS:
        value = raw.get(slot, "")
        if isinstance(value, str):
            loaded[slot] = value
    return loaded


def save_selection(path: Path, selection: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {slot: selection.get(slot, "") for slot in SLOTS}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _row(slot: str, choice_id: str, title: str, selected: bool, now: str) -> dict:
    suffix = choice_id or "default"
    return {
        "id": f"brief-{slot}-{suffix}",
        "title": title,
        "source": "Oriel",
        "source_url": "",
        "observed_at": now,
        "row": "follow",
        "fields": {"slot": slot, "choice_id": choice_id, "followed": selected},
    }
