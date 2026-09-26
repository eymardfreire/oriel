"""Load trade sources and which families the operator has enabled."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

FAMILIES = ("policy", "freight", "supply-chain")
FAMILY_TITLE = {
    "policy": "Policy",
    "freight": "Freight",
    "supply-chain": "Supply chain",
}
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    fetch: str
    note: str


@dataclass(frozen=True)
class FamilySelection:
    enabled: bool


def load_sources(path: Path) -> dict[str, tuple[Source, ...]]:
    raw = _object(path)
    _exact_families(raw, path)
    sources: dict[str, tuple[Source, ...]] = {}
    for family in FAMILIES:
        body = raw[family]
        rows = body if isinstance(body, list) else [body]
        if not rows or not all(isinstance(row, dict) for row in rows):
            raise ValueError(f"{path}: {family} must be a source or a list of sources")
        parsed = tuple(_source(row, path, family, index) for index, row in enumerate(rows))
        sources[family] = parsed
    return sources


def _source(body: dict, path: Path, family: str, index: int) -> Source:
    label = family if index == 0 else f"{family}[{index}]"
    allowed = {"id", "name", "fetch", "note"}
    extra = set(body) - allowed
    if extra:
        raise ValueError(f"{path}: {label} has unknown fields {', '.join(sorted(extra))}")
    source_id = _text(body.get("id"), path, f"{label}.id")
    if not _ID.fullmatch(source_id):
        raise ValueError(f"{path}: {label}.id must be lowercase words separated by hyphens")
    return Source(
        id=source_id,
        name=_text(body.get("name"), path, f"{label}.name"),
        fetch=_fetch_url(body.get("fetch"), path, label),
        note=_text(body.get("note"), path, f"{label}.note"),
    )


def load_selection(path: Path) -> dict[str, FamilySelection]:
    raw = _object(path)
    _exact_families(raw, path)
    selection: dict[str, FamilySelection] = {}
    for family in FAMILIES:
        body = raw[family]
        if not isinstance(body, dict):
            raise ValueError(f"{path}: {family} must be an object")
        extra = set(body) - {"enabled"}
        if extra:
            raise ValueError(f"{path}: {family} has unknown fields {', '.join(sorted(extra))}")
        enabled = body.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError(f"{path}: {family}.enabled must be true or false")
        selection[family] = FamilySelection(enabled=enabled)
    return selection


def _object(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: unreadable trade catalog") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: trade catalog must be an object")
    return raw


def _exact_families(raw: dict, path: Path) -> None:
    if set(raw) != set(FAMILIES):
        raise ValueError(f"{path}: families must be {', '.join(FAMILIES)}")


def _text(value: object, path: Path, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {field} must be a non-empty string")
    return value.strip()


def _fetch_url(value: object, path: Path, label: str) -> str:
    url = _text(value, path, f"{label}.fetch")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{path}: {label}.fetch must be an http(s) URL")
    return url
