"""Load the wire outlet catalog. The server is the only reader that fetches these URLs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

WIRE_DESKS = ("world", "regional", "business", "politics", "technology", "science")
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Outlet:
    id: str
    name: str
    fetch: str
    language: str
    region: str
    desks: tuple[str, ...]
    enabled: bool


def find_repo_root() -> Path:
    starts = [Path.cwd(), Path(__file__).resolve().parent]
    seen: set[Path] = set()
    for start in starts:
        for candidate in [start, *start.parents]:
            if candidate in seen:
                continue
            seen.add(candidate)
            outlets = candidate / "catalog" / "outlets"
            config = candidate / "server" / "config.toml"
            if outlets.is_dir() and config.is_file():
                return candidate
    raise FileNotFoundError("Oriel root not found (catalog/outlets and server/config.toml)")


def load_outlets(directory: Path) -> list[Outlet]:
    if not directory.is_dir():
        raise ValueError(f"outlet catalog not found: {directory}")
    outlets: list[Outlet] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        outlet = _read_outlet(path)
        if outlet.id in seen:
            raise ValueError(f"{path}: duplicate outlet id {outlet.id}")
        seen.add(outlet.id)
        outlets.append(outlet)
    return outlets


def _read_outlet(path: Path) -> Outlet:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: unreadable outlet file") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: outlet must be an object")
    allowed = {"id", "name", "fetch", "language", "region", "desks", "enabled"}
    extra = set(raw) - allowed
    if extra:
        raise ValueError(f"{path}: unknown fields {', '.join(sorted(extra))}")
    missing = allowed - set(raw)
    if missing:
        raise ValueError(f"{path}: missing {', '.join(sorted(missing))}")

    outlet_id = _token(raw["id"], path, "id")
    if not _ID.fullmatch(outlet_id):
        raise ValueError(f"{path}: id must be lowercase words separated by hyphens")
    if path.stem != outlet_id:
        raise ValueError(f"{path}: file name must match id {outlet_id}")

    desks = raw["desks"]
    if not isinstance(desks, list) or not desks:
        raise ValueError(f"{path}: desks must be a non-empty list")
    if len(set(desks)) != len(desks):
        raise ValueError(f"{path}: desks must be unique")
    parsed_desks: list[str] = []
    for desk in desks:
        if desk not in WIRE_DESKS:
            raise ValueError(f"{path}: unknown desk {desk!r}")
        parsed_desks.append(desk)

    enabled = raw["enabled"]
    if not isinstance(enabled, bool):
        raise ValueError(f"{path}: enabled must be true or false")

    return Outlet(
        id=outlet_id,
        name=_token(raw["name"], path, "name"),
        fetch=_fetch_url(raw["fetch"], path),
        language=_token(raw["language"], path, "language"),
        region=_token(raw["region"], path, "region"),
        desks=tuple(parsed_desks),
        enabled=enabled,
    )


def _token(value: object, path: Path, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {field} must be a non-empty string")
    return value.strip()


def _fetch_url(value: object, path: Path) -> str:
    url = _token(value, path, "fetch")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{path}: fetch must be an http(s) URL")
    return url
