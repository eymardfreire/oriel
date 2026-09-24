from pathlib import Path

from fastapi.testclient import TestClient

from oriel_server.config import Config, HomePlace, MarketsConfig, TradeConfig, WeatherConfig, WiresConfig, load_config
from oriel_server.main import create_app

SERVER_DIR = Path(__file__).resolve().parents[1]


def test_health_reports_bind_and_placeholder_home() -> None:
    config = Config(
        bind_host="127.0.0.1",
        bind_port=8787,
        home_place=HomePlace(id="home", name="unset"),
        wires=WiresConfig(enabled=False),
        markets=MarketsConfig(enabled=False),
        trade=TradeConfig(enabled=False),
        weather=WeatherConfig(enabled=False),
    )
    response = TestClient(create_app(config)).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "oriel"
    assert body["bind"] == "127.0.0.1:8787"
    assert body["home_place"] == {
        "id": "home",
        "name": "unset",
        "coordinates_set": False,
    }


def test_shipped_config_uses_tampa_as_the_primary_home() -> None:
    config = load_config(SERVER_DIR / "config.toml")
    assert config.bind_host == "127.0.0.1"
    assert config.bind_port == 8787
    assert config.home_place.id == "tampa"
    assert config.home_place.name == "Tampa"
    assert config.home_place.coordinates_set is True
    assert config.home_place.latitude == 27.94752
    assert config.home_place.longitude == -82.45843
    assert config.wires.enabled is True
    assert config.wires.refresh_seconds == 120
    assert config.wires.stale_after_seconds == 900
    assert config.markets.enabled is True
    assert config.markets.refresh_seconds == 60
    assert config.markets.stale_after_seconds == 900
    assert config.trade.enabled is True
    assert config.trade.refresh_seconds == 300
    assert config.trade.stale_after_seconds == 3600
    assert config.weather.enabled is True
    assert config.weather.refresh_seconds == 300
    assert config.weather.stale_after_seconds == 3600
