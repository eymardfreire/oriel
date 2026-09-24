"""Weather-news outlets. Separate from observations and from the wire catalog."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Outlet:
    id: str
    name: str
    fetch: str
    enabled: bool
    note: str


def load_outlets(directory: Path) -> list[Outlet]:
    if not directory.is_dir():
        raise ValueError(f"weather-news catalog not found: {directory}")
    outlets: list[Outlet] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        outlet = _read(path)
        if outlet.id in seen:
            raise ValueError(f"{path}: duplicate outlet id {outlet.id}")
        seen.add(outlet.id)
        outlets.append(outlet)
    return outlets


def _read(path: Path) -> Outlet:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: unreadable outlet file") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: outlet must be an object")
    allowed = {"id", "name", "fetch", "enabled", "note"}
    extra = set(raw) - allowed
    if extra:
        raise ValueError(f"{path}: unknown fields {', '.join(sorted(extra))}")
    missing = allowed - set(raw)
    if missing:
        raise ValueError(f"{path}: missing {', '.join(sorted(missing))}")
    outlet_id = _text(raw["id"], path, "id")
    if not _ID.fullmatch(outlet_id) or path.stem != outlet_id:
        raise ValueError(f"{path}: file name must match a hyphenated id")
    enabled = raw["enabled"]
    if not isinstance(enabled, bool):
        raise ValueError(f"{path}: enabled must be true or false")
    fetch = _text(raw["fetch"], path, "fetch")
    parsed = urlparse(fetch)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{path}: fetch must be an http(s) URL")
    return Outlet(
        id=outlet_id,
        name=_text(raw["name"], path, "name"),
        fetch=fetch,
        enabled=enabled,
        note=_text(raw["note"], path, "note"),
    )


def _text(value: object, path: Path, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {field} must be a non-empty string")
    return value.strip()
