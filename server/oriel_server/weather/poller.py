"""Poll configured places and weather-news outlets. Never invent a temperature."""

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

from oriel_server.config import HomePlace
from oriel_server.weather.alerts import Alert, alerts_url, parse_alerts
from oriel_server.weather.meteo import ForecastDay, Observation, forecast_batch_url, parse_meteo, split_forecasts
from oriel_server.weather.news import Outlet, load_outlets
from oriel_server.weather.places import Place, load_places
from oriel_server.wires.poller import fetch_url, short_error
from oriel_server.wires.rss import FeedEntry, parse_feed

logger = logging.getLogger("oriel.weather")

PANEL_IDS = ("weather-observation", "weather-forecast", "weather-alerts", "weather-news")
NEWS_LIMIT = 24
Fetcher = Callable[[str], bytes]


@dataclass
class StoredPanel:
    panel: dict
    updated_at: datetime


class WeatherPoller:
    def __init__(
        self,
        catalog_dir: Path,
        news_dir: Path,
        home: HomePlace,
        *,
        fetcher: Fetcher | None = None,
        stale_after_seconds: int = 3600,
        state_path: Path | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._catalog_dir = catalog_dir
        self._news_dir = news_dir
        self._home = home
        self._fetcher = fetcher or fetch_url
        self._stale_after = stale_after_seconds
        self._state_path = state_path
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._stored: dict[str, StoredPanel] = {}
        self._ready = False
        self._lock = threading.Lock()
        self._load_state()

    def refresh(self) -> None:
        try:
            self._refresh()
        except Exception:
            logger.exception("weather refresh failed")
            self._mark_failure("fetch failed")

    def panels(self) -> list[dict]:
        now = self._now()
        with self._lock:
            if not self._ready:
                return []
            return [self._public(self._stored[panel_id], now) for panel_id in PANEL_IDS if panel_id in self._stored]

    def panel(self, panel_id: str) -> dict | None:
        for payload in self.panels():
            if payload["id"] == panel_id:
                return payload
        return None

    def _refresh(self) -> None:
        try:
            places = load_places(self._catalog_dir / "places.json", self._home)
            outlets = load_outlets(self._news_dir)
        except ValueError as exc:
            logger.warning("weather catalog: %s", exc)
            self._mark_failure("catalog unreadable")
            return
        now = self._now()
        enabled = [outlet for outlet in outlets if outlet.enabled]
        jobs = _jobs(places, enabled)
        fetched = self._fetch(jobs)
        with self._lock:
            self._stored = {
                "weather-observation": self._observation(places, fetched, now),
                "weather-forecast": self._forecast(places, fetched, now),
                "weather-alerts": self._alerts(places, fetched, now),
                "weather-news": self._news(enabled, fetched, now),
            }
            self._ready = True
            self._save()

    def _observation(self, places: list[Place], fetched: dict[str, tuple[bytes, str]], now: datetime) -> StoredPanel:
        payloads, batch_error = self._forecast_payloads(places, fetched)
        items: list[dict] = []
        errors: list[str] = []
        for place in places:
            if not place.configured:
                items.append(_unavailable_observation(place, now))
                continue
            payload = payloads.get(place.id)
            previous = _previous_item(self._stored.get("weather-observation"), place.id)
            if payload is None:
                errors.append(f"{place.id}: {batch_error or 'unreadable forecast'}")
                items.append(previous or _unavailable_observation(place, now))
                continue
            try:
                observation, _days = parse_meteo(payload)
            except ValueError:
                errors.append(f"{place.id}: unreadable forecast")
                items.append(previous or _unavailable_observation(place, now))
                continue
            if observation is None:
                items.append(previous or _unavailable_observation(place, now))
                continue
            items.append(_observation_item(place, observation))
        items = _extremes(items) + _by_region(items)
        return StoredPanel(_panel("weather-observation", "weather", "Observation", now, bool(errors), "; ".join(errors), items), now)

    def _forecast(self, places: list[Place], fetched: dict[str, tuple[bytes, str]], now: datetime) -> StoredPanel:
        payloads, batch_error = self._forecast_payloads(places, fetched)
        items: list[dict] = []
        errors: list[str] = []
        for place in places:
            if not place.configured:
                items.append(_unavailable_forecast(place, now))
                continue
            payload = payloads.get(place.id)
            if payload is None:
                errors.append(f"{place.id}: {batch_error or 'unreadable forecast'}")
                items.extend(_previous_place_items(self._stored.get("weather-forecast"), place.id) or [_unavailable_forecast(place, now)])
                continue
            try:
                _observation, days = parse_meteo(payload)
            except ValueError:
                errors.append(f"{place.id}: unreadable forecast")
                items.extend(_previous_place_items(self._stored.get("weather-forecast"), place.id) or [_unavailable_forecast(place, now)])
                continue
            if not days:
                items.append(_unavailable_forecast(place, now))
                continue
            items.extend(_forecast_item(place, day) for day in days)
        return StoredPanel(_panel("weather-forecast", "weather", "Forecast", now, bool(errors), "; ".join(errors), items), now)

    def _alerts(self, places: list[Place], fetched: dict[str, tuple[bytes, str]], now: datetime) -> StoredPanel:
        items: list[dict] = []
        errors: list[str] = []
        uncovered: set[str] = set()
        for place in places:
            if not place.configured:
                items.append(_alerts_unavailable(place, now))
                continue
            if place.alerts != "nws":
                region = place.region or "Uncovered"
                if region not in uncovered:
                    uncovered.add(region)
                    items.append(_uncovered_region(region, now))
                continue
            payload, error = fetched[alerts_url(place.latitude or 0, place.longitude or 0)]
            if error:
                errors.append(f"{place.id}: {error}")
                kept = _previous_place_items(self._stored.get("weather-alerts"), place.id)
                items.extend(kept or [_alerts_unavailable(place, now)])
                continue
            try:
                alerts = parse_alerts(payload, fallback=now)
            except ValueError:
                errors.append(f"{place.id}: unreadable alerts")
                kept = _previous_place_items(self._stored.get("weather-alerts"), place.id)
                items.extend(kept or [_alerts_unavailable(place, now)])
                continue
            if not alerts:
                items.append(_no_alerts(place, now))
                continue
            items.extend(_alert_item(place, alert) for alert in alerts)
        return StoredPanel(_panel("weather-alerts", "weather", "Alerts", now, bool(errors), "; ".join(errors), items), now)

    def _news(self, outlets: list[Outlet], fetched: dict[str, tuple[bytes, str]], now: datetime) -> StoredPanel:
        if not outlets:
            return StoredPanel(_panel("weather-news", "weather-news", "Weather news", now, False, "", []), now)
        items: list[dict] = []
        errors: list[str] = []
        for outlet in outlets:
            payload, error = fetched[outlet.fetch]
            if error:
                errors.append(f"{outlet.id}: {error}")
                continue
            try:
                entries = parse_feed(payload, fallback=now)
            except ValueError:
                errors.append(f"{outlet.id}: unreadable feed")
                continue
            items.extend(_news_item(outlet, entry) for entry in entries)
        if errors and not items:
            previous = self._stored.get("weather-news")
            if previous is not None and self._ready:
                panel = copy.deepcopy(previous.panel)
                panel["stale"] = True
                panel["stale_reason"] = "; ".join(errors)
                return StoredPanel(panel, previous.updated_at)
        return StoredPanel(
            _panel("weather-news", "weather-news", "Weather news", now, bool(errors), "; ".join(errors), _limit(items)),
            now,
        )

    def _fetch(self, urls: list[str]) -> dict[str, tuple[bytes, str]]:
        if not urls:
            return {}
        results: dict[str, tuple[bytes, str]] = {}
        with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
            futures = {pool.submit(self._one, url): url for url in urls}
            for future, url in futures.items():
                results[url] = future.result()
        return results

    def _forecast_payloads(self, places: list[Place], fetched: dict[str, tuple[bytes, str]]) -> tuple[dict[str, bytes], str]:
        configured = [place for place in places if place.configured and place.latitude is not None and place.longitude is not None]
        if not configured:
            return {}, ""
        url = forecast_batch_url([place.latitude or 0 for place in configured], [place.longitude or 0 for place in configured])
        payload, error = fetched.get(url, (b"", "not fetched"))
        if error:
            return {}, error
        try:
            parts = split_forecasts(payload, len(configured))
        except ValueError:
            return {}, "unreadable forecast"
        return {place.id: part for place, part in zip(configured, parts)}, ""

    def _one(self, url: str) -> tuple[bytes, str]:
        try:
            return self._fetcher(url), ""
        except Exception as exc:
            logger.warning("weather %s: %s", url, exc)
            return b"", short_error(exc)

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
            now = self._now()
            if not self._ready:
                self._stored = {
                    panel_id: StoredPanel(_panel(panel_id, _domain(panel_id), _title(panel_id), now, True, reason, []), now)
                    for panel_id in PANEL_IDS
                }
                self._ready = True
            else:
                for panel_id, stored in list(self._stored.items()):
                    panel = copy.deepcopy(stored.panel)
                    panel["stale"] = True
                    panel["stale_reason"] = reason
                    self._stored[panel_id] = StoredPanel(panel, stored.updated_at)
            self._save()

    def _load_state(self) -> None:
        if self._state_path is None or not self._state_path.is_file():
            return
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        panels = raw.get("panels") if isinstance(raw, dict) else None
        if not isinstance(panels, dict):
            return
        for panel_id, body in panels.items():
            if panel_id not in PANEL_IDS or not isinstance(body, dict):
                continue
            panel = body.get("panel")
            updated = _parse_iso(body.get("updated_at")) if isinstance(body.get("updated_at"), str) else None
            if isinstance(panel, dict) and updated is not None:
                self._stored[panel_id] = StoredPanel(panel, updated)
        if self._stored:
            self._ready = True

    def _save(self) -> None:
        if self._state_path is None:
            return
        payload = {
            "panels": {
                panel_id: {"updated_at": _iso(stored.updated_at), "panel": stored.panel}
                for panel_id, stored in self._stored.items()
            }
        }
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self._state_path)


def _jobs(places: list[Place], outlets: list[Outlet]) -> list[str]:
    urls: list[str] = []
    configured = [place for place in places if place.latitude is not None and place.longitude is not None]
    if configured:
        urls.append(forecast_batch_url([place.latitude or 0 for place in configured], [place.longitude or 0 for place in configured]))
    for place in configured:
        if place.alerts == "nws":
            urls.append(alerts_url(place.latitude or 0, place.longitude or 0))
    urls.extend(outlet.fetch for outlet in outlets)
    return list(dict.fromkeys(urls))


def _extremes(items: list[dict]) -> list[dict]:
    watched = [
        item
        for item in items
        if item.get("row") == "observation" and item.get("fields", {}).get("home") is False and item["fields"].get("configured")
    ]
    strip: list[dict] = []
    for key, label, choose in (
        ("temperature_c", "hottest", max),
        ("temperature_c", "coldest", min),
        ("precipitation_mm", "wettest", max),
        ("wind_speed_kmh", "windiest", max),
    ):
        ranked = [(item["fields"][key], item) for item in watched if key in item["fields"]]
        if not ranked:
            continue
        value, item = choose(ranked, key=lambda pair: pair[0])
        fields = {"extreme": label, "place": item["fields"]["place"], key: value}
        if item["fields"].get("region"):
            fields["region"] = item["fields"]["region"]
        strip.append(
            {
                "id": f"extreme:{label}",
                "title": label,
                "source": item.get("source", ""),
                "source_url": item.get("source_url", ""),
                "observed_at": item.get("observed_at", ""),
                "row": "observation",
                "fields": fields,
            }
        )
    return strip


def _by_region(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: item.get("fields", {}).get("region") or "")


def _panel(panel_id: str, domain: str, title: str, updated_at: datetime, stale: bool, reason: str, items: list[dict]) -> dict:
    return {
        "id": panel_id,
        "domain": domain,
        "title": title,
        "updated_at": _iso(updated_at),
        "stale": stale,
        "stale_reason": reason if stale else "",
        "items": items,
    }


def _unavailable_observation(place: Place, now: datetime) -> dict:
    return {
        "id": f"observation:{place.id}",
        "title": "Observation unavailable",
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "observed_at": _iso(now),
        "row": "observation",
        "fields": {"place": place.name, "configured": place.configured, "home": place.home},
    }


def _observation_item(place: Place, observation: Observation) -> dict:
    fields: dict = {"place": place.name, "configured": True, "home": place.home}
    if place.region:
        fields["region"] = place.region
    if observation.temperature_c is not None:
        fields["temperature_c"] = observation.temperature_c
    if observation.condition:
        fields["condition"] = observation.condition
    if observation.apparent_temperature_c is not None:
        fields["apparent_temperature_c"] = observation.apparent_temperature_c
    if observation.humidity_pct is not None:
        fields["humidity_pct"] = observation.humidity_pct
    if observation.wind_speed_kmh is not None:
        fields["wind_speed_kmh"] = observation.wind_speed_kmh
    if observation.precipitation_mm is not None:
        fields["precipitation_mm"] = observation.precipitation_mm
    return {
        "id": f"observation:{place.id}",
        "title": place.name,
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "observed_at": _iso(observation.observed_at),
        "row": "observation",
        "fields": fields,
    }


def _unavailable_forecast(place: Place, now: datetime) -> dict:
    return {
        "id": f"forecast:{place.id}",
        "title": "Forecast unavailable",
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "observed_at": _iso(now),
        "row": "forecast",
        "fields": {"place": place.name, "period": ""},
    }


def _forecast_item(place: Place, day: ForecastDay) -> dict:
    fields: dict = {"place": place.name, "period": day.period}
    if day.high_c is not None:
        fields["temperature_high_c"] = day.high_c
    if day.low_c is not None:
        fields["temperature_low_c"] = day.low_c
    if day.condition:
        fields["condition"] = day.condition
    return {
        "id": f"forecast:{place.id}:{day.period}",
        "title": f"{place.name} {day.period}",
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/",
        "observed_at": f"{day.period}T00:00:00Z",
        "row": "forecast",
        "fields": fields,
    }


def _alerts_unavailable(place: Place, now: datetime) -> dict:
    return {
        "id": f"alerts:{place.id}:unavailable",
        "title": "Alerts unavailable",
        "source": "National Weather Service",
        "source_url": "https://www.weather.gov/",
        "observed_at": _iso(now),
        "row": "alert",
        "fields": {"headline": "Alerts unavailable", "place": place.name},
    }


def _uncovered_region(region: str, now: datetime) -> dict:
    headline = f"No public alert source covers {region}"
    return {
        "id": f"alerts:uncovered:{region}",
        "title": headline,
        "source": "Oriel",
        "source_url": "",
        "observed_at": _iso(now),
        "row": "alert",
        "fields": {"headline": headline, "region": region, "place": region},
    }


def _no_alerts(place: Place, now: datetime) -> dict:
    return {
        "id": f"alerts:{place.id}:none",
        "title": "No alerts are active",
        "source": "National Weather Service",
        "source_url": "https://www.weather.gov/",
        "observed_at": _iso(now),
        "row": "alert",
        "fields": {"headline": "No alerts are active", "place": place.name},
    }


def _alert_item(place: Place, alert: Alert) -> dict:
    fields: dict = {"headline": alert.headline, "place": place.id}
    if alert.severity:
        fields["severity"] = alert.severity
    return {
        "id": f"alerts:{place.id}:{hashlib.sha256(alert.id.encode()).hexdigest()[:16]}",
        "title": alert.headline,
        "source": alert.source,
        "source_url": "https://www.weather.gov/",
        "observed_at": _iso(alert.observed_at),
        "row": "alert",
        "fields": fields,
    }


def _news_item(outlet: Outlet, entry: FeedEntry) -> dict:
    digest = hashlib.sha256(f"{outlet.id}:{entry.id}".encode()).hexdigest()[:16]
    fields: dict = {}
    if entry.summary:
        fields["summary"] = entry.summary
    return {
        "id": f"{outlet.id}:{digest}",
        "title": entry.title,
        "source": outlet.name,
        "source_url": entry.link,
        "observed_at": _iso(entry.observed_at),
        "row": "headline",
        "fields": fields,
    }


def _previous_item(stored: StoredPanel | None, place_id: str) -> dict | None:
    if stored is None:
        return None
    for item in stored.panel.get("items") or []:
        if item.get("id") == f"observation:{place_id}" and item.get("title") != "Observation unavailable":
            return copy.deepcopy(item)
    return None


def _previous_place_items(stored: StoredPanel | None, place_id: str) -> list[dict]:
    if stored is None:
        return []
    kept = []
    for item in stored.panel.get("items") or []:
        item_id = item.get("id")
        if not isinstance(item_id, str):
            continue
        if f":{place_id}:" in item_id or item_id.endswith(f":{place_id}"):
            if "unavailable" in item_id:
                continue
            kept.append(copy.deepcopy(item))
    return kept


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
    return unique[:NEWS_LIMIT]


def _domain(panel_id: str) -> str:
    return "weather-news" if panel_id == "weather-news" else "weather"


def _title(panel_id: str) -> str:
    return {
        "weather-observation": "Observation",
        "weather-forecast": "Forecast",
        "weather-alerts": "Alerts",
        "weather-news": "Weather news",
    }[panel_id]


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
