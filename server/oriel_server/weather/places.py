"""Home place plus any extra places the operator listed."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from oriel_server.config import HomePlace

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    latitude: float | None
    longitude: float | None
    home: bool = False
    region: str = ""
    alerts: str = "nws"

    @property
    def configured(self) -> bool:
        return self.latitude is not None and self.longitude is not None


def load_places(path: Path, home: HomePlace) -> list[Place]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: unreadable places file") from exc
    if not isinstance(raw, list):
        raise ValueError(f"{path}: places must be a list")
    places = [
        Place(
            id=home.id,
            name=home.name,
            latitude=home.latitude,
            longitude=home.longitude,
            home=True,
            region=home.region,
            alerts=home.alerts or "nws",
        )
    ]
    seen = {home.id}
    for index, row in enumerate(raw):
        place = _place(row, path, index)
        if place.id in seen:
            raise ValueError(f"{path}: duplicate place id {place.id}")
        seen.add(place.id)
        places.append(place)
    return places


def _place(raw: object, path: Path, index: int) -> Place:
    where = f"{path}: places[{index}]"
    if not isinstance(raw, dict):
        raise ValueError(f"{where} must be an object")
    extra = set(raw) - {"id", "name", "latitude", "longitude", "home", "region", "alerts"}
    if extra:
        raise ValueError(f"{where} has unknown fields {', '.join(sorted(extra))}")
    place_id = raw.get("id")
    name = raw.get("name")
    if not isinstance(place_id, str) or not _ID.fullmatch(place_id):
        raise ValueError(f"{where} id must be lowercase words separated by hyphens")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{where} name must be a non-empty string")
    home = raw.get("home", False)
    if not isinstance(home, bool):
        raise ValueError(f"{where} home must be true or false")
    region = raw.get("region", "")
    if not isinstance(region, str):
        raise ValueError(f"{where} region must be a string")
    alerts = raw.get("alerts", "none")
    if alerts not in {"nws", "none"}:
        raise ValueError(f"{where} alerts must be nws or none")
    return Place(
        id=place_id,
        name=name.strip(),
        latitude=_coord(raw.get("latitude"), "latitude", where),
        longitude=_coord(raw.get("longitude"), "longitude", where),
        home=home,
        region=region.strip(),
        alerts=alerts,
    )


def _coord(value: object, name: str, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where} {name} must be a number")
    number = float(value)
    limit = 90 if name == "latitude" else 180
    if not -limit <= number <= limit:
        raise ValueError(f"{where} {name} is out of range")
    return number
