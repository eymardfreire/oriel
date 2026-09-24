"""Load the server bind address, home place, and wire poll interval."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class HomePlace:
    id: str
    name: str
    latitude: float | None = None
    longitude: float | None = None

    @property
    def coordinates_set(self) -> bool:
        return self.latitude is not None and self.longitude is not None


@dataclass(frozen=True)
class WiresConfig:
    enabled: bool = True
    refresh_seconds: int = 120
    stale_after_seconds: int = 900


@dataclass(frozen=True)
class MarketsConfig:
    enabled: bool = True
    refresh_seconds: int = 60
    stale_after_seconds: int = 900


@dataclass(frozen=True)
class TradeConfig:
    enabled: bool = True
    refresh_seconds: int = 300
    stale_after_seconds: int = 3600


@dataclass(frozen=True)
class WeatherConfig:
    enabled: bool = True
    refresh_seconds: int = 300
    stale_after_seconds: int = 3600


@dataclass(frozen=True)
class SportsConfig:
    enabled: bool = True
    refresh_seconds: int = 60
    stale_after_seconds: int = 900


@dataclass(frozen=True)
class Config:
    bind_host: str
    bind_port: int
    home_place: HomePlace
    wires: WiresConfig = field(default_factory=WiresConfig)
    markets: MarketsConfig = field(default_factory=MarketsConfig)
    trade: TradeConfig = field(default_factory=TradeConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    sports: SportsConfig = field(default_factory=SportsConfig)

    @property
    def bind(self) -> str:
        return f"{self.bind_host}:{self.bind_port}"


def config_path() -> Path:
    override = os.environ.get("ORIEL_CONFIG")
    if override:
        return Path(override)
    cwd = Path.cwd() / "config.toml"
    if cwd.is_file():
        return cwd
    return Path(__file__).resolve().parents[1] / "config.toml"


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.is_file():
        raise FileNotFoundError(f"config file not found: {path}")
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    host = raw.get("bind_host")
    port = raw.get("bind_port")
    if not isinstance(host, str) or not host:
        raise ValueError(f"{path}: bind_host must be a non-empty string")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError(f"{path}: bind_port must be an integer from 1 to 65535")

    place = raw.get("home_place") or {}
    if not isinstance(place, dict):
        raise ValueError(f"{path}: home_place must be a table")

    return Config(
        bind_host=host,
        bind_port=port,
        home_place=HomePlace(
            id=_text(place.get("id"), "home"),
            name=_text(place.get("name"), "unset"),
            latitude=_coord(place.get("latitude"), "latitude", path),
            longitude=_coord(place.get("longitude"), "longitude", path),
        ),
        wires=_wires(raw.get("wires"), path),
        markets=_markets(raw.get("markets"), path),
        trade=_trade(raw.get("trade"), path),
        weather=_weather(raw.get("weather"), path),
        sports=_sports(raw.get("sports"), path),
    )


def _sports(value: object, path: Path) -> SportsConfig:
    enabled, refresh, stale = _service(value, path, "sports", 60, 900)
    return SportsConfig(enabled=enabled, refresh_seconds=refresh, stale_after_seconds=stale)


def _weather(value: object, path: Path) -> WeatherConfig:
    enabled, refresh, stale = _service(value, path, "weather", 300, 3600)
    return WeatherConfig(enabled=enabled, refresh_seconds=refresh, stale_after_seconds=stale)


def _trade(value: object, path: Path) -> TradeConfig:
    enabled, refresh, stale = _service(value, path, "trade", 300, 3600)
    return TradeConfig(enabled=enabled, refresh_seconds=refresh, stale_after_seconds=stale)


def _markets(value: object, path: Path) -> MarketsConfig:
    enabled, refresh, stale = _service(value, path, "markets", 60, 900)
    return MarketsConfig(enabled=enabled, refresh_seconds=refresh, stale_after_seconds=stale)


def _wires(value: object, path: Path) -> WiresConfig:
    enabled, refresh, stale = _service(value, path, "wires", 120, 900)
    return WiresConfig(enabled=enabled, refresh_seconds=refresh, stale_after_seconds=stale)


def _service(
    value: object,
    path: Path,
    name: str,
    refresh_default: int,
    stale_default: int,
) -> tuple[bool, int, int]:
    if value is None:
        return True, refresh_default, stale_default
    if not isinstance(value, dict):
        raise ValueError(f"{path}: {name} must be a table")
    enabled = value.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError(f"{path}: {name}.enabled must be true or false")
    return (
        enabled,
        _positive(value.get("refresh_seconds", refresh_default), f"{name}.refresh_seconds", path),
        _positive(value.get("stale_after_seconds", stale_default), f"{name}.stale_after_seconds", path),
    )


def _positive(value: object, name: str, path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{path}: {name} must be an integer of 1 or more")
    return value


def _text(value: object, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not value:
        raise ValueError(f"expected a non-empty string, got {value!r}")
    return value


def _coord(value: object, name: str, path: Path) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path}: home_place.{name} must be a number")
    number = float(value)
    limit = 90 if name == "latitude" else 180
    if not -limit <= number <= limit:
        raise ValueError(f"{path}: home_place.{name} must be between -{limit} and {limit}")
    return number
