"""Poll the operator's market selection and keep the last good quote for each instrument."""

from __future__ import annotations

import copy
import json
import logging
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from oriel_server.markets.catalog import (
    FAMILIES,
    FAMILY_TITLE,
    FamilySelection,
    Instrument,
    Source,
    load_selection,
    load_sources,
)
from oriel_server.markets.quotes import (
    Quote,
    coingecko_url,
    frankfurter_url,
    parse_coingecko,
    parse_frankfurter,
    parse_treasury,
    parse_yahoo,
    treasury_url,
    yahoo_url,
)
from oriel_server.wires.poller import fetch_url, short_error

logger = logging.getLogger("oriel.markets")

Fetcher = Callable[[str], bytes]


@dataclass
class StoredPanel:
    panel: dict
    updated_at: datetime


class MarketPoller:
    def __init__(
        self,
        catalog_dir: Path,
        *,
        fetcher: Fetcher | None = None,
        stale_after_seconds: int = 900,
        state_path: Path | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._catalog_dir = catalog_dir
        self._fetcher = fetcher or fetch_url
        self._stale_after = stale_after_seconds
        self._state_path = state_path
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._quotes: dict[str, Quote] = {}
        self._stored: dict[str, StoredPanel] = {}
        self._ready = False
        self._lock = threading.Lock()
        self._load_state()

    def refresh(self) -> None:
        try:
            self._refresh()
        except Exception:
            logger.exception("markets refresh failed")
            self._mark_failure("fetch failed")

    def panels(self) -> list[dict]:
        now = self._now()
        with self._lock:
            if not self._ready:
                return []
            return [self._public(stored, now) for _, stored in self._ordered()]

    def panel(self, panel_id: str) -> dict | None:
        for payload in self.panels():
            if payload["id"] == panel_id:
                return payload
        return None

    def _refresh(self) -> None:
        try:
            sources = load_sources(self._catalog_dir / "sources.json")
            selection = load_selection(self._catalog_dir / "selection.json", sources)
        except ValueError as exc:
            logger.warning("market catalog: %s", exc)
            self._mark_failure("catalog unreadable")
            return
        now = self._now()
        fetched: dict[str, tuple[dict[str, Quote], str]] = {}
        for family in FAMILIES:
            chosen = selection[family]
            if not chosen.enabled or not chosen.instruments:
                continue
            fetched[family] = self._fetch_family(family, sources[family], chosen, now)
        with self._lock:
            stored: dict[str, StoredPanel] = {}
            for family in FAMILIES:
                if family not in fetched:
                    continue
                quotes, error = fetched[family]
                for symbol, quote in quotes.items():
                    self._quotes[f"{family}:{symbol}"] = quote
                previous = self._stored.get(family)
                if error and not quotes and previous is not None and self._ready:
                    panel = copy.deepcopy(previous.panel)
                    panel["stale"] = True
                    panel["stale_reason"] = error
                    stored[family] = StoredPanel(panel, previous.updated_at)
                    continue
                items = [
                    _item(family, quotes[instrument.symbol])
                    for instrument in selection[family].instruments
                    if instrument.symbol in quotes
                ]
                stored[family] = StoredPanel(
                    _panel(family, now, bool(error), error, items),
                    now,
                )
            self._stored = stored
            self._ready = True
            self._save()

    def _fetch_family(
        self,
        family: str,
        source: Source,
        chosen: FamilySelection,
        now: datetime,
    ) -> tuple[dict[str, Quote], str]:
        try:
            if source.kind == "yahoo-chart":
                return self._fetch_yahoo(family, source, chosen)
            if source.kind == "frankfurter":
                return self._fetch_frankfurter(family, source, chosen, now)
            if source.kind == "treasury-yields":
                return self._fetch_treasury(source, chosen, now)
            if source.kind == "coingecko":
                return self._fetch_coingecko(source, chosen, now)
        except Exception as exc:
            logger.warning("markets %s: %s", source.id, exc)
            return self._cached(family, chosen), short_error(exc)
        return {}, "fetch failed"

    def _fetch_yahoo(
        self,
        family: str,
        source: Source,
        chosen: FamilySelection,
    ) -> tuple[dict[str, Quote], str]:
        quotes: dict[str, Quote] = {}
        errors: list[str] = []

        def one(instrument: Instrument) -> tuple[Instrument, Quote | None, str]:
            try:
                payload = self._fetcher(yahoo_url(instrument.query))
                return (
                    instrument,
                    parse_yahoo(payload, instrument, source=source.name, delayed=source.delayed),
                    "",
                )
            except Exception as exc:
                return instrument, None, short_error(exc)

        workers = min(8, len(chosen.instruments))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for instrument, quote, error in pool.map(one, chosen.instruments):
                if quote is not None:
                    quotes[instrument.symbol] = quote
                    continue
                logger.warning("markets %s: %s", instrument.symbol, error)
                errors.append(f"{instrument.symbol}: {error}")
                cached = self._quotes.get(f"{family}:{instrument.symbol}")
                if cached is not None:
                    quotes[instrument.symbol] = cached
        return quotes, "; ".join(errors)

    def _fetch_frankfurter(
        self,
        family: str,
        source: Source,
        chosen: FamilySelection,
        now: datetime,
    ) -> tuple[dict[str, Quote], str]:
        grouped: dict[str, list[Instrument]] = defaultdict(list)
        for instrument in chosen.instruments:
            grouped[instrument.base].append(instrument)
        quotes: dict[str, Quote] = {}
        errors: list[str] = []
        moment = now.astimezone(timezone.utc)
        start = moment - timedelta(days=10)
        for base, instruments in grouped.items():
            counters = list(dict.fromkeys(item.counter for item in instruments))
            url = frankfurter_url(base, counters, start, moment)
            try:
                payload = self._fetcher(url)
                quotes.update(
                    parse_frankfurter(payload, instruments, source=source.name, delayed=source.delayed)
                )
            except Exception as exc:
                errors.append(f"{base}: {short_error(exc)}")
                for instrument in instruments:
                    cached = self._quotes.get(f"{family}:{instrument.symbol}")
                    if cached is not None:
                        quotes[instrument.symbol] = cached
        return quotes, "; ".join(errors)

    def _fetch_treasury(
        self,
        source: Source,
        chosen: FamilySelection,
        now: datetime,
    ) -> tuple[dict[str, Quote], str]:
        payload = self._fetcher(treasury_url(now.astimezone(timezone.utc).year))
        return parse_treasury(payload, list(chosen.instruments), source=source.name, delayed=source.delayed), ""

    def _fetch_coingecko(
        self,
        source: Source,
        chosen: FamilySelection,
        now: datetime,
    ) -> tuple[dict[str, Quote], str]:
        ids = [instrument.query for instrument in chosen.instruments]
        payload = self._fetcher(coingecko_url(ids))
        observed = now.astimezone(timezone.utc).replace(microsecond=0)
        return (
            parse_coingecko(
                payload,
                list(chosen.instruments),
                source=source.name,
                delayed=source.delayed,
                observed_at=observed,
            ),
            "",
        )

    def _cached(self, family: str, chosen: FamilySelection) -> dict[str, Quote]:
        quotes: dict[str, Quote] = {}
        for instrument in chosen.instruments:
            cached = self._quotes.get(f"{family}:{instrument.symbol}")
            if cached is not None:
                quotes[instrument.symbol] = cached
        return quotes

    def _ordered(self) -> list[tuple[str, StoredPanel]]:
        return [(family, self._stored[family]) for family in FAMILIES if family in self._stored]

    def _public(self, stored: StoredPanel, now: datetime) -> dict:
        panel = copy.deepcopy(stored.panel)
        if (now - stored.updated_at).total_seconds() > self._stale_after:
            panel["stale"] = True
            reason = panel.get("stale_reason") or ""
            if "older than budget" not in reason:
                panel["stale_reason"] = f"{reason}; older than budget".strip("; ")
        return panel

    def _mark_failure(self, reason: str) -> None:
        with self._lock:
            if not self._ready:
                self._ready = True
                self._save()
                return
            for family, stored in list(self._stored.items()):
                panel = copy.deepcopy(stored.panel)
                panel["stale"] = True
                panel["stale_reason"] = reason
                self._stored[family] = StoredPanel(panel, stored.updated_at)
            self._save()

    def _load_state(self) -> None:
        if self._state_path is None or not self._state_path.is_file():
            return
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("ignoring unreadable market state %s", self._state_path)
            return
        if not isinstance(raw, dict):
            return
        quotes = raw.get("quotes")
        if isinstance(quotes, dict):
            for key, body in quotes.items():
                if isinstance(key, str):
                    quote = _quote_from_state(body)
                    if quote is not None:
                        self._quotes[key] = quote
        panels = raw.get("panels")
        if isinstance(panels, dict):
            for family, body in panels.items():
                if family not in FAMILIES or not isinstance(body, dict):
                    continue
                panel = body.get("panel")
                updated = _parse_iso(body.get("updated_at")) if isinstance(body.get("updated_at"), str) else None
                if isinstance(panel, dict) and updated is not None:
                    self._stored[family] = StoredPanel(panel, updated)
        if self._stored:
            self._ready = True

    def _save(self) -> None:
        if self._state_path is None:
            return
        payload = {
            "quotes": {key: _quote_state(quote) for key, quote in sorted(self._quotes.items())},
            "panels": {
                family: {"updated_at": _iso(stored.updated_at), "panel": stored.panel}
                for family, stored in self._stored.items()
            },
        }
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self._state_path)


def _panel(family: str, updated_at: datetime, stale: bool, reason: str, items: list[dict]) -> dict:
    return {
        "id": f"markets-{family}",
        "domain": "markets",
        "title": FAMILY_TITLE[family],
        "updated_at": _iso(updated_at),
        "stale": stale,
        "stale_reason": reason if stale else "",
        "items": items,
    }


def _item(family: str, quote: Quote) -> dict:
    fields: dict[str, object] = {
        "symbol": quote.symbol,
        "price": quote.price,
        "delayed": quote.delayed,
    }
    if quote.change is not None:
        fields["change"] = quote.change
    return {
        "id": f"{family}:{quote.symbol}",
        "title": quote.title,
        "source": quote.source,
        "source_url": quote.source_url,
        "observed_at": _iso(quote.observed_at),
        "row": "quote",
        "fields": fields,
    }


def _iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str) -> datetime | None:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _quote_state(quote: Quote) -> dict:
    return {
        "symbol": quote.symbol,
        "title": quote.title,
        "price": quote.price,
        "change": quote.change,
        "observed_at": _iso(quote.observed_at),
        "source": quote.source,
        "source_url": quote.source_url,
        "delayed": quote.delayed,
    }


def _quote_from_state(raw: object) -> Quote | None:
    if not isinstance(raw, dict):
        return None
    symbol = raw.get("symbol")
    title = raw.get("title")
    source = raw.get("source")
    source_url = raw.get("source_url")
    observed = raw.get("observed_at")
    price = raw.get("price")
    delayed = raw.get("delayed")
    if not all(isinstance(value, str) and value for value in (symbol, title, source, observed)):
        return None
    if not isinstance(source_url, str) or not isinstance(delayed, bool):
        return None
    if isinstance(price, bool) or not isinstance(price, (int, float)):
        return None
    parsed = _parse_iso(observed)
    if parsed is None:
        return None
    change = raw.get("change")
    if change is not None and (isinstance(change, bool) or not isinstance(change, (int, float))):
        return None
    return Quote(
        symbol=symbol,
        title=title,
        price=float(price),
        change=None if change is None else float(change),
        observed_at=parsed,
        source=source,
        source_url=source_url,
        delayed=delayed,
    )
