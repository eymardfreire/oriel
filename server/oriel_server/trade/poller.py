"""Poll enabled trade families and keep the last good panel for each one."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from oriel_server.trade.catalog import FAMILIES, FAMILY_TITLE, Source, load_selection, load_sources
from oriel_server.wires.poller import fetch_url, short_error
from oriel_server.wires.rss import FeedEntry, parse_feed

logger = logging.getLogger("oriel.trade")

PANEL_ITEM_LIMIT = 24
Fetcher = Callable[[str], bytes]


@dataclass
class FamilyCache:
    entries: list[FeedEntry]
    last_success: datetime | None
    error: str


@dataclass
class StoredPanel:
    panel: dict
    updated_at: datetime


class TradePoller:
    def __init__(
        self,
        catalog_dir: Path,
        *,
        fetcher: Fetcher | None = None,
        stale_after_seconds: int = 3600,
        state_path: Path | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._catalog_dir = catalog_dir
        self._fetcher = fetcher or fetch_url
        self._stale_after = stale_after_seconds
        self._state_path = state_path
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._cache: dict[str, FamilyCache] = {}
        self._stored: dict[str, StoredPanel] = {}
        self._ready = False
        self._lock = threading.Lock()
        self._load_state()

    def refresh(self) -> None:
        try:
            self._refresh()
        except Exception:
            logger.exception("trade refresh failed")
            self._mark_failure("fetch failed")

    def panels(self) -> list[dict]:
        now = self._now()
        with self._lock:
            if not self._ready:
                return []
            return [self._public(self._stored[family], now) for family in FAMILIES if family in self._stored]

    def panel(self, panel_id: str) -> dict | None:
        for payload in self.panels():
            if payload["id"] == panel_id:
                return payload
        return None

    def _refresh(self) -> None:
        try:
            sources = load_sources(self._catalog_dir / "sources.json")
            selection = load_selection(self._catalog_dir / "selection.json")
        except ValueError as exc:
            logger.warning("trade catalog: %s", exc)
            self._mark_failure("catalog unreadable")
            return
        now = self._now()
        enabled = [family for family in FAMILIES if selection[family].enabled]
        fetched = self._fetch_enabled(enabled, sources) if enabled else {}
        with self._lock:
            self._cache = {key: value for key, value in self._cache.items() if key in enabled}
            self._apply(enabled, sources, fetched, now)
            self._save()

    def _apply(
        self,
        enabled: list[str],
        sources: dict[str, tuple[Source, ...]],
        fetched: dict[str, tuple[list[FeedEntry], str]],
        now: datetime,
    ) -> None:
        stored: dict[str, StoredPanel] = {}
        for family in enabled:
            entries, error = fetched[family]
            previous_cache = self._cache.get(family)
            if error == "":
                self._cache[family] = FamilyCache(entries, now, "")
            else:
                logger.warning("trade %s: %s", family, error)
                self._cache[family] = FamilyCache(
                    previous_cache.entries if previous_cache else [],
                    previous_cache.last_success if previous_cache else None,
                    error,
                )
            cached = self._cache[family]
            previous = self._stored.get(family)
            if cached.error and not cached.entries and previous is not None and self._ready:
                panel = copy.deepcopy(previous.panel)
                panel["stale"] = True
                panel["stale_reason"] = cached.error
                stored[family] = StoredPanel(panel, previous.updated_at)
                continue
            items = _items(sources[family][0], family, cached.entries) if cached.entries else []
            stored[family] = StoredPanel(
                _panel(family, now, bool(cached.error), cached.error, _limit(items)),
                now,
            )
        self._stored = stored
        self._ready = True

    def _fetch_enabled(
        self,
        families: list[str],
        sources: dict[str, tuple[Source, ...]],
    ) -> dict[str, tuple[list[FeedEntry], str]]:
        results: dict[str, tuple[list[FeedEntry], str]] = {}
        workers = min(3, len(families))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._fetch_family, sources[family]): family for family in families
            }
            for future, family in futures.items():
                results[family] = future.result()
        return results

    def _fetch_family(self, sources: tuple[Source, ...]) -> tuple[list[FeedEntry], str]:
        entries: list[FeedEntry] = []
        errors: list[str] = []
        for source in sources:
            try:
                payload = self._fetcher(source.fetch)
            except Exception as exc:
                errors.append(f"{source.id}: {short_error(exc)}")
                continue
            try:
                parsed = parse_feed(payload, fallback=self._now())
            except Exception as exc:
                errors.append(f"{source.id}: {short_error(exc)}")
                continue
            entries.extend(
                FeedEntry(
                    id=entry.id,
                    title=entry.title,
                    link=entry.link,
                    observed_at=entry.observed_at,
                    summary=entry.summary,
                    source_name=source.name,
                )
                for entry in parsed
            )
        if entries:
            return entries, ""
        return [], "; ".join(errors) or "fetch failed"

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
            now = self._now()
            if not self._ready:
                self._stored = {
                    family: StoredPanel(_panel(family, now, True, reason, []), now) for family in FAMILIES
                }
                self._ready = True
            else:
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
            logger.warning("ignoring unreadable trade state %s", self._state_path)
            return
        if not isinstance(raw, dict):
            return
        families = raw.get("families")
        if isinstance(families, dict):
            for family, body in families.items():
                if family not in FAMILIES or not isinstance(body, dict):
                    continue
                entries = []
                for item in body.get("items") or []:
                    entry = _entry_from_state(item)
                    if entry is not None:
                        entries.append(entry)
                last = body.get("last_success")
                parsed = _parse_iso(last) if isinstance(last, str) else None
                error = body.get("error") if isinstance(body.get("error"), str) else ""
                self._cache[family] = FamilyCache(entries, parsed, error)
        panels = raw.get("panels")
        if isinstance(panels, dict):
            for family, body in panels.items():
                if family not in FAMILIES or not isinstance(body, dict):
                    continue
                panel = body.get("panel")
                updated = _parse_iso(body.get("updated_at")) if isinstance(body.get("updated_at"), str) else None
                if not isinstance(panel, dict) or updated is None:
                    continue
                self._stored[family] = StoredPanel(panel, updated)
        if self._stored:
            self._ready = True

    def _save(self) -> None:
        if self._state_path is None:
            return
        payload = {
            "families": {
                family: {
                    "last_success": _iso(cache.last_success) if cache.last_success else None,
                    "error": cache.error,
                    "items": [_entry_state(entry) for entry in cache.entries],
                }
                for family, cache in sorted(self._cache.items())
            },
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
        "id": f"trade-{family}",
        "domain": "trade",
        "title": FAMILY_TITLE[family],
        "updated_at": _iso(updated_at),
        "stale": stale,
        "stale_reason": reason if stale else "",
        "items": items,
    }


def _items(source: Source, family: str, entries: list[FeedEntry]) -> list[dict]:
    items = []
    for entry in entries:
        if not source.name or not entry.title:
            continue
        digest = hashlib.sha256(f"{source.id}:{entry.id}".encode()).hexdigest()[:16]
        items.append(
            {
                "id": f"{source.id}:{digest}",
                "title": entry.title,
                "source": entry.source_name or source.name,
                "source_url": entry.link,
                "observed_at": _iso(entry.observed_at),
                "row": "headline",
                "fields": _headline_fields(family, entry.summary),
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


def _headline_fields(family: str, summary: str) -> dict:
    fields = {"family": family}
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
    if entry.source_name:
        body["source_name"] = entry.source_name
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
    source_name = raw.get("source_name")
    if not isinstance(source_name, str):
        source_name = ""
    return FeedEntry(
        id=identity,
        title=title,
        link=link,
        observed_at=parsed,
        summary=summary.strip(),
        source_name=source_name.strip(),
    )
