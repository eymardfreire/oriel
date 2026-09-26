"""Parse delayed quotes from the verified market sources."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote
from xml.etree import ElementTree

from oriel_server.markets.catalog import Instrument


@dataclass(frozen=True)
class Quote:
    symbol: str
    title: str
    price: float
    change: float | None
    observed_at: datetime
    source: str
    source_url: str
    delayed: bool


def yahoo_url(query: str) -> str:
    symbol = quote(query, safe="")
    return f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"


def frankfurter_url(base: str, counters: list[str], start: datetime, end: datetime) -> str:
    joined = ",".join(counters)
    return (
        "https://api.frankfurter.app/"
        f"{start.date().isoformat()}..{end.date().isoformat()}?from={base}&to={joined}"
    )


def treasury_url(year: int) -> str:
    return (
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
        f"?data=daily_treasury_yield_curve&field_tdr_date_value={year}"
    )


_COIN_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,15}$")
_COIN_ID = re.compile(r"^[a-z0-9-]{1,64}$")


def coingecko_url(ids: list[str]) -> str:
    joined = ",".join(ids)
    return (
        "https://api.coingecko.com/api/v3/simple/price"
        f"?ids={joined}&vs_currencies=usd&include_24hr_change=true"
    )


def parse_yahoo(payload: bytes, instrument: Instrument, *, source: str, delayed: bool) -> Quote:
    try:
        body = json.loads(payload)
        result = body["chart"]["result"][0]
        meta = result["meta"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise ValueError("unreadable quote") from exc
    price = _number(meta.get("regularMarketPrice"))
    if price is None:
        raise ValueError("unreadable quote")
    hint = meta.get("priceHint")
    digits = hint if isinstance(hint, int) and not isinstance(hint, bool) and 0 <= hint <= 8 else 2
    change = _number(meta.get("fulldayChange"))
    observed = _unix(meta.get("regularMarketTime"))
    return Quote(
        symbol=instrument.symbol,
        title=instrument.title,
        price=round(price, digits),
        change=None if change is None else round(change, digits),
        observed_at=observed,
        source=source,
        source_url=f"https://finance.yahoo.com/quote/{quote(instrument.query, safe='')}",
        delayed=delayed,
    )


def parse_frankfurter(
    payload: bytes,
    instruments: list[Instrument],
    *,
    source: str,
    delayed: bool,
) -> dict[str, Quote]:
    try:
        body = json.loads(payload)
        rates = body["rates"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("unreadable quote") from exc
    if not isinstance(rates, dict) or not rates:
        raise ValueError("unreadable quote")
    dates = sorted(day for day in rates if isinstance(day, str))
    quotes: dict[str, Quote] = {}
    for instrument in instruments:
        last = _rate(rates, dates[-1], instrument.counter)
        if last is None:
            continue
        change = None
        if len(dates) >= 2:
            previous = _rate(rates, dates[-2], instrument.counter)
            if previous is not None:
                change = round(last - previous, 4)
        quotes[instrument.symbol] = Quote(
            symbol=instrument.symbol,
            title=instrument.title,
            price=round(last, 4),
            change=change,
            observed_at=_date_stamp(dates[-1]),
            source=source,
            source_url="https://www.frankfurter.app/",
            delayed=delayed,
        )
    return quotes


def parse_treasury(
    payload: bytes,
    instruments: list[Instrument],
    *,
    source: str,
    delayed: bool,
) -> dict[str, Quote]:
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise ValueError("unreadable quote") from exc
    rows = [_yield_row(node) for node in root.iter() if _local(node.tag) == "entry"]
    rows = [row for row in rows if row[0] is not None]
    rows.sort(key=lambda row: row[0])
    if not rows:
        raise ValueError("unreadable quote")
    latest_date, latest, observed = rows[-1]
    previous = rows[-2][1] if len(rows) >= 2 else {}
    quotes: dict[str, Quote] = {}
    for instrument in instruments:
        price = _number(latest.get(instrument.field))
        if price is None:
            continue
        earlier = _number(previous.get(instrument.field))
        change = None if earlier is None else round(price - earlier, 2)
        quotes[instrument.symbol] = Quote(
            symbol=instrument.symbol,
            title=instrument.title,
            price=round(price, 2),
            change=change,
            observed_at=observed or _date_stamp(latest_date.date().isoformat()),
            source=source,
            source_url="https://home.treasury.gov/resource-center/data-chart-center/interest-rates/",
            delayed=delayed,
        )
    return quotes


def coingecko_markets_url(limit: int) -> str:
    return (
        "https://api.coingecko.com/api/v3/coins/markets"
        f"?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1&sparkline=false"
    )


def parse_coingecko_markets(
    payload: bytes,
    *,
    source: str,
    delayed: bool,
    observed_at: datetime,
    limit: int,
) -> list[tuple[Instrument, Quote]]:
    try:
        body = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("unreadable quote") from exc
    if not isinstance(body, list):
        raise ValueError("unreadable quote")
    found: list[tuple[Instrument, Quote]] = []
    seen: set[str] = set()
    for row in body:
        if len(found) >= limit:
            break
        if not isinstance(row, dict):
            continue
        raw_symbol = row.get("symbol")
        name = row.get("name")
        coin_id = row.get("id")
        price = _number(row.get("current_price"))
        if not isinstance(raw_symbol, str) or not isinstance(name, str) or not isinstance(coin_id, str):
            continue
        if price is None:
            continue
        symbol = raw_symbol.upper()
        if symbol in seen or not _COIN_SYMBOL.fullmatch(symbol) or not _COIN_ID.fullmatch(coin_id):
            continue
        seen.add(symbol)
        change = _number(row.get("price_change_24h"))
        instrument = Instrument(symbol=symbol, title=name, query=coin_id)
        found.append(
            (
                instrument,
                Quote(
                    symbol=symbol,
                    title=name,
                    price=round(price, 2 if price >= 1 else 6),
                    change=None if change is None else round(change, 2),
                    observed_at=observed_at,
                    source=source,
                    source_url=f"https://www.coingecko.com/en/coins/{coin_id}",
                    delayed=delayed,
                ),
            )
        )
    if not found:
        raise ValueError("unreadable quote")
    return found


def parse_coingecko(
    payload: bytes,
    instruments: list[Instrument],
    *,
    source: str,
    delayed: bool,
    observed_at: datetime,
) -> dict[str, Quote]:
    try:
        body = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("unreadable quote") from exc
    if not isinstance(body, dict):
        raise ValueError("unreadable quote")
    quotes: dict[str, Quote] = {}
    for instrument in instruments:
        row = body.get(instrument.query)
        if not isinstance(row, dict):
            continue
        price = _number(row.get("usd"))
        if price is None:
            continue
        pct = _number(row.get("usd_24h_change"))
        change = _change_from_percent(price, pct)
        quotes[instrument.symbol] = Quote(
            symbol=instrument.symbol,
            title=instrument.title,
            price=round(price, 2 if price >= 1 else 6),
            change=None if change is None else round(change, 2),
            observed_at=observed_at,
            source=source,
            source_url=f"https://www.coingecko.com/en/coins/{instrument.query}",
            delayed=delayed,
        )
    return quotes


def _yield_row(
    node: ElementTree.Element,
) -> tuple[datetime | None, dict[str, str], datetime | None]:
    values: dict[str, str] = {}
    new_date = ""
    updated = ""
    for child in node.iter():
        name = _local(child.tag)
        text = (child.text or "").strip()
        if not text:
            continue
        if name == "NEW_DATE":
            new_date = text
        elif name == "updated" and "T" in text:
            updated = text
        elif name.startswith("BC_"):
            values[name] = text
    parsed = _date_stamp(new_date[:10]) if len(new_date) >= 10 else None
    published = _iso(updated) if updated else None
    return parsed, values, published


def _change_from_percent(price: float, pct: float | None) -> float | None:
    if pct is None:
        return None
    factor = 1 + pct / 100
    if factor == 0:
        return None
    return price - (price / factor)


def _rate(rates: dict, day: str, counter: str) -> float | None:
    row = rates.get(day)
    if not isinstance(row, dict):
        return None
    return _number(row.get(counter))


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _unix(value: object) -> datetime:
    number = _number(value)
    if number is None:
        raise ValueError("unreadable quote")
    return datetime.fromtimestamp(number, timezone.utc).replace(microsecond=0)


def _date_stamp(day: str) -> datetime:
    parsed = datetime.fromisoformat(day)
    return parsed.replace(tzinfo=timezone.utc)


def _iso(value: str) -> datetime | None:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
