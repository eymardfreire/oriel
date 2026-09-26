"""Open-Meteo observation and daily forecast. No API key."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode

WMO = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "fog",
    51: "drizzle",
    53: "drizzle",
    55: "drizzle",
    61: "rain",
    63: "rain",
    65: "rain",
    71: "snow",
    73: "snow",
    75: "snow",
    80: "showers",
    81: "showers",
    82: "showers",
    95: "thunderstorm",
    96: "thunderstorm",
    99: "thunderstorm",
}


@dataclass(frozen=True)
class Observation:
    observed_at: datetime
    temperature_c: float | None
    condition: str
    apparent_temperature_c: float | None = None
    humidity_pct: float | None = None
    wind_speed_kmh: float | None = None
    precipitation_mm: float | None = None


@dataclass(frozen=True)
class ForecastDay:
    period: str
    high_c: float | None
    low_c: float | None
    condition: str


def forecast_url(latitude: float, longitude: float) -> str:
    query = urlencode(
        {
            "latitude": f"{latitude:.4f}",
            "longitude": f"{longitude:.4f}",
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,precipitation",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "timezone": "UTC",
            "forecast_days": "3",
        }
    )
    return f"https://api.open-meteo.com/v1/forecast?{query}"


def forecast_batch_url(latitudes: list[float], longitudes: list[float]) -> str:
    latitude = ",".join(f"{value:.4f}" for value in latitudes)
    longitude = ",".join(f"{value:.4f}" for value in longitudes)
    rest = urlencode(
        {
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,precipitation",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "timezone": "UTC",
            "forecast_days": "3",
        }
    )
    return f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&{rest}"


def split_forecasts(payload: bytes, count: int) -> list[bytes]:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("unreadable forecast") from exc
    if isinstance(raw, dict) and count == 1:
        return [payload]
    if isinstance(raw, list) and len(raw) == count and all(isinstance(item, dict) for item in raw):
        return [json.dumps(item).encode() for item in raw]
    raise ValueError("unreadable forecast")


def parse_meteo(payload: bytes) -> tuple[Observation | None, list[ForecastDay]]:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("unreadable forecast") from exc
    if not isinstance(raw, dict):
        raise ValueError("unreadable forecast")
    return _observation(raw.get("current")), _days(raw.get("daily"))


def _observation(raw: object) -> Observation | None:
    if not isinstance(raw, dict):
        return None
    moment = _time(raw.get("time"))
    if moment is None:
        return None
    return Observation(
        moment,
        _number(raw.get("temperature_2m")),
        _condition(raw.get("weather_code")),
        _number(raw.get("apparent_temperature")),
        _number(raw.get("relative_humidity_2m")),
        _number(raw.get("wind_speed_10m")),
        _number(raw.get("precipitation")),
    )


def _days(raw: object) -> list[ForecastDay]:
    if not isinstance(raw, dict):
        return []
    times = raw.get("time")
    highs = raw.get("temperature_2m_max")
    lows = raw.get("temperature_2m_min")
    codes = raw.get("weather_code")
    if not isinstance(times, list):
        return []
    days: list[ForecastDay] = []
    for index, period in enumerate(times):
        if not isinstance(period, str) or not period:
            continue
        days.append(
            ForecastDay(
                period=period,
                high_c=_at(highs, index),
                low_c=_at(lows, index),
                condition=_condition(_at(codes, index)),
            )
        )
    return days[:3]


def _condition(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ""
    return WMO.get(int(value), "")


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _at(values: object, index: int) -> float | None:
    if not isinstance(values, list) or index >= len(values):
        return None
    return _number(values[index])


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
