"""Poll enabled wire outlets and keep the last good panel for each desk."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from oriel_server.wires.catalog import WIRE_DESKS, Outlet, load_outlets
from oriel_server.wires.rss import FeedEntry, parse_feed

logger = logging.getLogger("oriel.wires")

PANEL_ITEM_LIMIT = 24
MAX_FEED_BYTES = 2_000_000
Fetcher = Callable[[str], bytes]


@dataclass
class OutletCache:
    entries: list[FeedEntry]
    last_success: datetime | None
    error: str


@dataclass
class StoredPanel:
    panel: dict
    updated_at: datetime


class WirePoller:
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
        self._cache: dict[str, OutletCache] = {}
        self._stored: dict[str, StoredPanel] = {}
        self._ready = False
        self._lock = threading.Lock()
        self._load_state()

    def refresh(self) -> None:
        try:
            self._refresh()
        except Exception:
            logger.exception("wires refresh failed")
            self._mark_failure("fetch failed")

    def panels(self) -> list[dict]:
        now = self._now()
        with self._lock:
            result: list[dict] = []
            for desk in WIRE_DESKS:
                stored = self._stored.get(desk)
                if stored is None:
                    result.append(_panel(desk, now, True, "not yet fetched", []))
                    continue
                result.append(self._public(stored, now))
            return result

    def panel(self, panel_id: str) -> dict | None:
        for payload in self.panels():
            if payload["id"] == panel_id:
                return payload
        return None

    def last_success(self) -> dict[str, str | None]:
        with self._lock:
            return {
                outlet_id: _iso(cache.last_success) if cache.last_success else None
                for outlet_id, cache in self._cache.items()
            }

    def _refresh(self) -> None:
        try:
            outlets = load_outlets(self._catalog_dir)
        except ValueError as exc:
            logger.warning("outlet catalog: %s", exc)
            self._mark_failure("catalog unreadable")
            return
        now = self._now()
        enabled = [outlet for outlet in outlets if outlet.enabled]
        fetched = self._fetch_enabled(enabled) if enabled else {}
        with self._lock:
            known = {outlet.id for outlet in outlets}
            self._cache = {key: value for key, value in self._cache.items() if key in known}
            self._apply(enabled, fetched, now)
            self._save()

    def _apply(
        self,
        enabled: list[Outlet],
        fetched: dict[str, tuple[list[FeedEntry], str]],
        now: datetime,
    ) -> None:
        if not enabled:
            self._stored = {
                desk: StoredPanel(_panel(desk, now, False, "", []), now) for desk in WIRE_DESKS
            }
            self._ready = True
            return

        for outlet in enabled:
            entries, error = fetched[outlet.id]
            previous = self._cache.get(outlet.id)
            if error == "":
                self._cache[outlet.id] = OutletCache(entries, now, "")
                continue
            logger.warning("outlet %s: %s", outlet.id, error)
            self._cache[outlet.id] = OutletCache(
                previous.entries if previous else [],
                previous.last_success if previous else None,
                error,
            )

        for desk in WIRE_DESKS:
            group = [outlet for outlet in enabled if desk in outlet.desks]
            if not group:
                self._stored[desk] = StoredPanel(_panel(desk, now, False, "", []), now)
                continue
            failures = [outlet for outlet in group if self._cache[outlet.id].error]
            successes = [outlet for outlet in group if not self._cache[outlet.id].error]
            previous = self._stored.get(desk)
            if not successes and previous is not None and self._ready:
                panel = copy.deepcopy(previous.panel)
                panel["stale"] = True
                panel["stale_reason"] = _failure_reason(failures, self._cache)
                self._stored[desk] = StoredPanel(panel, previous.updated_at)
                continue
            items: list[dict] = []
            for outlet in group:
                cached = self._cache[outlet.id]
                if cached.entries:
                    items.extend(_items(outlet, desk, cached.entries))
            reason = _failure_reason(failures, self._cache) if failures else ""
            self._stored[desk] = StoredPanel(
                _panel(desk, now, bool(failures), reason, _limit(items)),
                now,
            )
        self._ready = True

    def _fetch_enabled(self, outlets: list[Outlet]) -> dict[str, tuple[list[FeedEntry], str]]:
        results: dict[str, tuple[list[FeedEntry], str]] = {}
        workers = min(8, len(outlets))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self._fetch_outlet, outlet): outlet for outlet in outlets}
            for future, outlet in futures.items():
                results[outlet.id] = future.result()
        return results

    def _fetch_outlet(self, outlet: Outlet) -> tuple[list[FeedEntry], str]:
        try:
            payload = self._fetcher(outlet.fetch)
            return parse_feed(payload, fallback=self._now()), ""
        except Exception as exc:
            return [], short_error(exc)

    def _public(self, stored: StoredPanel, now: datetime) -> dict:
        panel = copy.deepcopy(stored.panel)
        age = (now - stored.updated_at).total_seconds()
        if age > self._stale_after:
            panel["stale"] = True
            reason = panel.get("stale_reason") or ""
            if "older than budget" not in reason:
                panel["stale_reason"] = f"{reason}; older than budget".strip("; ")
        return panel

    def _mark_failure(self, reason: str) -> None:
        with self._lock:
            self._mark_failure_locked(reason)
            self._save()

    def _mark_failure_locked(self, reason: str) -> None:
        now = self._now()
        if not self._ready:
            self._stored = {
                desk: StoredPanel(_panel(desk, now, True, reason, []), now) for desk in WIRE_DESKS
            }
            self._ready = True
            return
        for desk, stored in list(self._stored.items()):
            panel = copy.deepcopy(stored.panel)
            panel["stale"] = True
            panel["stale_reason"] = reason
            self._stored[desk] = StoredPanel(panel, stored.updated_at)

    def _load_state(self) -> None:
        if self._state_path is None or not self._state_path.is_file():
            return
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("ignoring unreadable wires state %s", self._state_path)
            return
        if not isinstance(raw, dict):
            return
        outlets = raw.get("outlets")
        if isinstance(outlets, dict):
            for outlet_id, body in outlets.items():
                if not isinstance(outlet_id, str) or not isinstance(body, dict):
                    continue
                entries = []
                for item in body.get("items") or []:
                    entry = _entry_from_state(item)
                    if entry is not None:
                        entries.append(entry)
                last = body.get("last_success")
                parsed = _parse_iso(last) if isinstance(last, str) else None
                error = body.get("error") if isinstance(body.get("error"), str) else ""
                self._cache[outlet_id] = OutletCache(entries, parsed, error)
        panels = raw.get("panels")
        if isinstance(panels, dict):
            for desk, body in panels.items():
                if desk not in WIRE_DESKS or not isinstance(body, dict):
                    continue
                panel = body.get("panel")
                updated = _parse_iso(body.get("updated_at")) if isinstance(body.get("updated_at"), str) else None
                if not isinstance(panel, dict) or updated is None:
                    continue
                self._stored[desk] = StoredPanel(panel, updated)
        if self._stored:
            self._ready = True

    def _save(self) -> None:
        if self._state_path is None:
            return
        payload = {
            "outlets": {
                outlet_id: {
                    "last_success": _iso(cache.last_success) if cache.last_success else None,
                    "error": cache.error,
                    "items": [_entry_state(entry) for entry in cache.entries],
                }
                for outlet_id, cache in sorted(self._cache.items())
            },
            "panels": {
                desk: {"updated_at": _iso(stored.updated_at), "panel": stored.panel}
                for desk, stored in self._stored.items()
            },
        }
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self._state_path)


def fetch_url(url: str, *, timeout: float = 15.0) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("fetch target must be an http(s) URL")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Oriel/0.1",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_FEED_BYTES + 1)
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError("feed too large")
    if not payload:
        raise ValueError("unreadable feed")
    return payload


def short_error(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, urllib.error.HTTPError):
        return f"http {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        if isinstance(exc.reason, TimeoutError):
            return "timeout"
        return "unreachable"
    message = str(exc)
    if message == "unreadable feed":
        return "unreadable feed"
    if message == "feed too large":
        return "feed too large"
    return "fetch failed"


def _panel(desk: str, updated_at: datetime, stale: bool, reason: str, items: list[dict]) -> dict:
    return {
        "id": f"wires-{desk}",
        "domain": "wires",
        "title": desk[:1].upper() + desk[1:],
        "updated_at": _iso(updated_at),
        "stale": stale,
        "stale_reason": reason if stale else "",
        "items": items,
    }


def _items(outlet: Outlet, desk: str, entries: list[FeedEntry]) -> list[dict]:
    items = []
    for entry in entries:
        digest = hashlib.sha256(f"{outlet.id}:{entry.id}".encode()).hexdigest()[:16]
        items.append(
            {
                "id": f"{outlet.id}:{desk}:{digest}",
                "title": entry.title,
                "source": outlet.name,
                "source_url": entry.link,
                "observed_at": _iso(entry.observed_at),
                "row": "headline",
                "fields": _headline_fields(desk, entry.summary),
            }
        )
    return items


def _limit(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        key = item["source_url"] or item["id"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    unique.sort(key=lambda item: item["observed_at"], reverse=True)
    return unique[:PANEL_ITEM_LIMIT]


def _failure_reason(failures: list[Outlet], cache: dict[str, OutletCache]) -> str:
    return "; ".join(f"{outlet.id}: {cache[outlet.id].error}" for outlet in failures)


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


def _headline_fields(desk: str, summary: str) -> dict:
    fields = {"desk": desk}
    if summary:
        fields["summary"] = summary
    return fields


def _entry_state(entry: FeedEntry) -> dict:
    body = {
        "id": entry.id,
        "title": entry.title,
        "link": entry.link,
        "observed_at": _iso(entry.observed_at),
    }
    if entry.summary:
        body["summary"] = entry.summary
    return body


def _entry_from_state(raw: object) -> FeedEntry | None:
    if not isinstance(raw, dict):
        return None
    title = raw.get("title")
    identity = raw.get("id")
    link = raw.get("link")
    observed = raw.get("observed_at")
    if not all(isinstance(value, str) and value for value in (title, identity, observed)):
        return None
    if not isinstance(link, str):
        return None
    parsed = _parse_iso(observed)
    if parsed is None:
        return None
    summary = raw.get("summary")
    if not isinstance(summary, str):
        summary = ""
    return FeedEntry(id=identity, title=title, link=link, observed_at=parsed, summary=summary.strip())
