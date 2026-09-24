"""Load the market source record and the operator's instrument selection."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

FAMILIES = ("indices", "equities", "fx", "rates", "commodities", "crypto")
FAMILY_TITLE = {
    "indices": "Indices",
    "equities": "Equities",
    "fx": "FX",
    "rates": "Rates",
    "commodities": "Commodities",
    "crypto": "Crypto",
}
_KINDS = {"yahoo-chart", "frankfurter", "treasury-yields", "coingecko"}
_QUERY = re.compile(r"^[A-Za-z0-9^=._-]{1,24}$")
_COIN = re.compile(r"^[a-z0-9-]{1,64}$")
_CCY = re.compile(r"^[A-Z]{3}$")
_FIELD = re.compile(r"^BC_[A-Z0-9_]{1,32}$")
_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,15}$")


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    kind: str
    delayed: bool
    fetch: str
    note: str


@dataclass(frozen=True)
class Instrument:
    symbol: str
    title: str
    query: str = ""
    base: str = ""
    counter: str = ""
    field: str = ""


@dataclass(frozen=True)
class FamilySelection:
    enabled: bool
    instruments: tuple[Instrument, ...]


def load_sources(path: Path) -> dict[str, Source]:
    raw = _object(path)
    _exact_families(raw, path)
    sources: dict[str, Source] = {}
    for family in FAMILIES:
        body = raw[family]
        if not isinstance(body, dict):
            raise ValueError(f"{path}: {family} must be an object")
        kind = body.get("kind")
        if kind not in _KINDS:
            raise ValueError(f"{path}: {family} has unknown kind {kind!r}")
        delayed = body.get("delayed")
        if not isinstance(delayed, bool):
            raise ValueError(f"{path}: {family}.delayed must be true or false")
        sources[family] = Source(
            id=_text(body.get("id"), path, f"{family}.id"),
            name=_text(body.get("name"), path, f"{family}.name"),
            kind=kind,
            delayed=delayed,
            fetch=_text(body.get("fetch"), path, f"{family}.fetch"),
            note=_text(body.get("note"), path, f"{family}.note"),
        )
    return sources


def load_selection(path: Path, sources: dict[str, Source]) -> dict[str, FamilySelection]:
    raw = _object(path)
    _exact_families(raw, path)
    selection: dict[str, FamilySelection] = {}
    for family in FAMILIES:
        body = raw[family]
        if not isinstance(body, dict):
            raise ValueError(f"{path}: {family} must be an object")
        enabled = body.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError(f"{path}: {family}.enabled must be true or false")
        rows = body.get("instruments")
        if not isinstance(rows, list):
            raise ValueError(f"{path}: {family}.instruments must be a list")
        instruments = tuple(
            _instrument(row, family, sources[family].kind, path, index)
            for index, row in enumerate(rows)
        )
        symbols = [item.symbol for item in instruments]
        if len(symbols) != len(set(symbols)):
            raise ValueError(f"{path}: {family} repeats a symbol")
        selection[family] = FamilySelection(enabled=enabled, instruments=instruments)
    return selection


def _instrument(raw: object, family: str, kind: str, path: Path, index: int) -> Instrument:
    where = f"{path}: {family}.instruments[{index}]"
    if not isinstance(raw, dict):
        raise ValueError(f"{where} must be an object")
    allowed = {"symbol", "title", "query", "base", "counter", "field"}
    extra = set(raw) - allowed
    if extra:
        raise ValueError(f"{where} has unknown fields {', '.join(sorted(extra))}")
    symbol = _text(raw.get("symbol"), path, f"{family} symbol")
    if not _SYMBOL.fullmatch(symbol):
        raise ValueError(f"{where} symbol {symbol!r} is not a display symbol")
    title = _text(raw.get("title"), path, f"{family} title")
    query = _optional(raw, "query", where)
    base = _optional(raw, "base", where)
    counter = _optional(raw, "counter", where)
    field = _optional(raw, "field", where)
    if kind == "yahoo-chart":
        if not isinstance(query, str) or not _QUERY.fullmatch(query):
            raise ValueError(f"{where} needs a Yahoo symbol in query")
    elif kind == "coingecko":
        if not isinstance(query, str) or not _COIN.fullmatch(query):
            raise ValueError(f"{where} needs a CoinGecko id in query")
    elif kind == "frankfurter":
        if not isinstance(base, str) or not _CCY.fullmatch(base):
            raise ValueError(f"{where} needs a base currency")
        if not isinstance(counter, str) or not _CCY.fullmatch(counter):
            raise ValueError(f"{where} needs a counter currency")
    elif kind == "treasury-yields":
        if not isinstance(field, str) or not _FIELD.fullmatch(field):
            raise ValueError(f"{where} needs a Treasury field")
    return Instrument(
        symbol=symbol,
        title=title,
        query=query,
        base=base,
        counter=counter,
        field=field,
    )


def _optional(raw: dict, key: str, where: str) -> str:
    if key not in raw or raw[key] is None:
        return ""
    value = raw[key]
    if not isinstance(value, str):
        raise ValueError(f"{where} {key} must be a string")
    return value


def _object(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: unreadable market file") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected an object")
    return raw


def _exact_families(raw: dict, path: Path) -> None:
    found = set(raw)
    expected = set(FAMILIES)
    if found != expected:
        missing = ", ".join(sorted(expected - found))
        extra = ", ".join(sorted(found - expected))
        detail = ", ".join(part for part in (f"missing {missing}" if missing else "", f"unknown {extra}" if extra else "") if part)
        raise ValueError(f"{path}: {detail}")


def _text(value: object, path: Path, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {field} must be a non-empty string")
    return value.strip()
