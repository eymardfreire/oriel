"""Sports headlines from public feeds. A missing description stays off the row."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from oriel_server.wires.rss import parse_feed

NEWS_LIMIT = 40


@dataclass(frozen=True)
class Outlet:
    id: str
    name: str
    sport: str
    sport_name: str
    fetch: str
    enabled: bool


class SidelinePoller:
    def __init__(self, catalog_dir: Path, focus_path: Path, *, fetcher=None, now=None) -> None:
        self._catalog_dir = catalog_dir
        self._focus_path = focus_path
        self._fetcher = fetcher
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._items: list[dict] = []
        self._errors: list[str] = []

    def refresh(self) -> None:
        if self._fetcher is None:
            from oriel_server.sports.poller import fetch_sports

            fetcher = fetch_sports
        else:
            fetcher = self._fetcher
        now = self._now()
        items: list[dict] = []
        errors: list[str] = []
        for outlet in load_outlets(self._catalog_dir):
            if not outlet.enabled:
                continue
            try:
                payload = fetcher(outlet.fetch)
                entries = parse_feed(payload, fallback=now)
            except Exception as exc:
                errors.append(f"{outlet.id}: {exc}")
                continue
            for entry in entries:
                items.append(_item(outlet, entry))
        items.sort(key=lambda item: item["observed_at"], reverse=True)
        self._items = items
        self._errors = errors

    def focus(self, sport: str, on: bool) -> None:
        sports = set(load_focus(self._focus_path))
        known = {outlet.sport for outlet in load_outlets(self._catalog_dir)}
        if sport == "relevant":
            sports = set()
        elif sport not in known:
            raise ValueError("sport is not in the catalog")
        elif on:
            sports.add(sport)
        else:
            sports.discard(sport)
        save_focus(self._focus_path, sorted(sports))

    def panels(self) -> list[dict]:
        now = self._now()
        chosen = load_focus(self._focus_path)
        return [_headlines(self._items, chosen, now, bool(self._errors)), _picker(self._catalog_dir, chosen, now)]

    def panel(self, panel_id: str) -> dict | None:
        for payload in self.panels():
            if payload["id"] == panel_id:
                return payload
        return None


def load_outlets(path: Path) -> list[Outlet]:
    if not path.is_dir():
        return []
    outlets: list[Outlet] = []
    for file in sorted(path.glob("*.json")):
        raw = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            continue
        outlets.append(
            Outlet(
                id=str(raw.get("id") or file.stem),
                name=str(raw.get("name") or file.stem),
                sport=str(raw.get("sport") or ""),
                sport_name=str(raw.get("sport_name") or raw.get("sport") or ""),
                fetch=str(raw.get("fetch") or ""),
                enabled=raw.get("enabled") is not False,
            )
        )
    return [outlet for outlet in outlets if outlet.fetch.startswith("https://") and outlet.sport]


def load_focus(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    sports = raw.get("sports") if isinstance(raw, dict) else None
    if not isinstance(sports, list):
        return []
    return [sport for sport in sports if isinstance(sport, str) and sport]


def save_focus(path: Path, sports: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"sports": sports}, indent=2) + "\n", encoding="utf-8")


def _item(outlet: Outlet, entry) -> dict:
    digest = hashlib.sha256(f"{outlet.id}:{entry.id}".encode()).hexdigest()[:16]
    fields = {"sport": outlet.sport, "sport_name": outlet.sport_name}
    if entry.summary:
        fields["summary"] = entry.summary
    observed = entry.observed_at
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return {
        "id": f"{outlet.id}:{digest}",
        "title": entry.title,
        "source": outlet.name,
        "source_url": entry.link,
        "observed_at": observed.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "row": "headline",
        "fields": fields,
    }


def _headlines(items: list[dict], chosen: list[str], now: datetime, stale: bool) -> dict:
    if not chosen:
        seen: set[str] = set()
        picked: list[dict] = []
        for item in items:
            sport = item["fields"].get("sport")
            if not isinstance(sport, str) or sport in seen:
                continue
            seen.add(sport)
            picked.append(item)
        title = "Most relevant"
        shown = picked
    else:
        title = "Sports"
        shown = [item for item in items if item["fields"].get("sport") in set(chosen)][:NEWS_LIMIT]
    return {
        "id": "sideline-headlines",
        "domain": "sports",
        "title": title,
        "updated_at": now.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stale": stale,
        "stale_reason": "",
        "items": shown,
    }


def _picker(catalog_dir: Path, chosen: list[str], now: datetime) -> dict:
    sports: dict[str, str] = {}
    for outlet in load_outlets(catalog_dir):
        sports.setdefault(outlet.sport, outlet.sport_name)
    selected = set(chosen)
    items = [
        {
            "id": "focus-relevant",
            "title": "Most relevant",
            "source": "Oriel",
            "source_url": "",
            "observed_at": now.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "row": "follow",
            "fields": {"sport": "relevant", "followed": not selected},
        }
    ]
    for sport in sorted(sports):
        items.append(
            {
                "id": f"focus-{sport}",
                "title": sports[sport],
                "source": "Oriel",
                "source_url": "",
                "observed_at": items[0]["observed_at"],
                "row": "follow",
                "fields": {"sport": sport, "family": sport, "followed": sport in selected},
            }
        )
    return {
        "id": "sideline-focus",
        "domain": "sports",
        "title": "Sports",
        "updated_at": items[0]["observed_at"],
        "stale": False,
        "stale_reason": "",
        "items": items,
    }
