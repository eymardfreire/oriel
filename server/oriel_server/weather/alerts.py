"""National Weather Service active alerts for a point. US coverage only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode


@dataclass(frozen=True)
class Alert:
    id: str
    severity: str
    headline: str
    source: str
    observed_at: datetime


def alerts_url(latitude: float, longitude: float) -> str:
    query = urlencode({"point": f"{latitude:.4f},{longitude:.4f}"})
    return f"https://api.weather.gov/alerts/active?{query}"


def parse_alerts(payload: bytes, *, fallback: datetime) -> list[Alert]:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("unreadable alerts") from exc
    features = raw.get("features") if isinstance(raw, dict) else None
    if not isinstance(features, list):
        raise ValueError("unreadable alerts")
    alerts: list[Alert] = []
    for feature in features:
        alert = _alert(feature, fallback)
        if alert is not None:
            alerts.append(alert)
    return alerts


def _alert(raw: object, fallback: datetime) -> Alert | None:
    if not isinstance(raw, dict):
        return None
    props = raw.get("properties")
    if not isinstance(props, dict):
        return None
    headline = props.get("headline") or props.get("event")
    if not isinstance(headline, str) or not headline.strip():
        return None
    severity = props.get("severity")
    if not isinstance(severity, str):
        severity = ""
    source = props.get("senderName")
    if not isinstance(source, str) or not source.strip():
        source = "National Weather Service"
    identity = props.get("id")
    if not isinstance(identity, str) or not identity:
        identity = headline.strip()
    moment = _time(props.get("sent")) or fallback
    return Alert(identity, severity.strip(), headline.strip(), source.strip(), moment)


def _time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
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
