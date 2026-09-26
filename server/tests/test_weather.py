import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from oriel_server.config import Config, HomePlace, MarketsConfig, TradeConfig, WeatherConfig, WiresConfig
from oriel_server.main import create_app
from oriel_server.weather.alerts import alerts_url
from oriel_server.weather.meteo import forecast_url
from oriel_server.weather.news import load_outlets
from oriel_server.weather.poller import WeatherPoller

REPO = Path(__file__).resolve().parents[2]
WHEN = datetime(2026, 9, 23, 18, 0, tzinfo=timezone.utc)
LAT = 38.9
LON = -77.0

METEO = json.dumps(
    {
        "current": {
            "time": "2026-09-23T18:00",
            "temperature_2m": 22.5,
            "apparent_temperature": 24.0,
            "relative_humidity_2m": 81,
            "weather_code": 1,
            "wind_speed_10m": 12.5,
        },
        "daily": {
            "time": ["2026-09-23", "2026-09-24"],
            "weather_code": [1, 61],
            "temperature_2m_max": [26.0, 19.0],
            "temperature_2m_min": [15.0, 12.0],
        },
    }
).encode()

ALERTS = json.dumps(
    {
        "features": [
            {
                "properties": {
                    "id": "alert-1",
                    "severity": "Severe",
                    "headline": "Severe thunderstorm warning",
                    "senderName": "NWS Test",
                    "sent": "2026-09-23T18:00:00Z",
                }
            }
        ]
    }
).encode()

NONE = b'{"features": []}'

NEWS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><item>
  <title>Storm story</title>
  <link>https://example.test/storm</link>
  <guid>storm-1</guid>
  <pubDate>Wed, 23 Sep 2026 18:00:00 GMT</pubDate>
</item></channel></rss>
"""


def test_observation_omits_missing_detail() -> None:
    from oriel_server.weather.meteo import parse_meteo

    observation, _days = parse_meteo(
        b'{"current":{"time":"2026-09-23T18:00","temperature_2m":22.5,"weather_code":0}}'
    )
    assert observation is not None
    assert observation.condition == "clear"
    assert observation.apparent_temperature_c is None
    assert observation.humidity_pct is None
    assert observation.wind_speed_kmh is None


def test_shipped_weather_news_is_public_and_separate() -> None:
    outlets = load_outlets(REPO / "catalog" / "weather-news")
    assert {outlet.id for outlet in outlets} == {"nhc-atlantic", "spc"}
    for outlet in outlets:
        assert outlet.enabled is True
        assert outlet.fetch.startswith("https://")
        assert outlet.name
    places = json.loads((REPO / "catalog" / "weather" / "places.json").read_text(encoding="utf-8"))
    assert len(places) == 40
    assert {row["region"] for row in places} == {
        "North America",
        "South America",
        "Europe",
        "Africa",
        "Middle East",
        "Asia",
        "Oceania",
    }
    assert all(row["home"] is False for row in places)
    tokyo = next(row for row in places if row["id"] == "tokyo")
    assert tokyo["alerts"] == "none"
    assert next(row for row in places if row["id"] == "new-york")["alerts"] == "nws"


def test_unset_home_is_not_fetched_and_has_no_temperature(tmp_path: Path) -> None:
    seen: list[str] = []

    def fetch(url: str) -> bytes:
        seen.append(url)
        return NEWS

    write_news(tmp_path)
    poller = WeatherPoller(
        tmp_path,
        tmp_path / "news",
        HomePlace(id="home", name="unset"),
        fetcher=fetch,
        now=lambda: WHEN,
    )
    poller.refresh()
    assert all("open-meteo.com" not in url and "weather.gov" not in url for url in seen)
    observation = poller.panel("weather-observation")["items"][0]
    assert observation["fields"]["place"] == "unset"
    assert "temperature_c" not in observation["fields"]
    assert observation["fields"]["configured"] is False
    forecast = poller.panel("weather-forecast")["items"][0]
    assert "temperature_high_c" not in forecast["fields"]
    alerts = poller.panel("weather-alerts")["items"][0]
    assert alerts["title"] == "Alerts unavailable"
    assert alerts["fields"]["headline"] != "No alerts are active"
    assert poller.panel("weather-news")["items"][0]["title"] == "Storm story"


def test_configured_place_keeps_observation_forecast_and_alerts_apart(tmp_path: Path) -> None:
    write_news(tmp_path)
    (tmp_path / "places.json").write_text(
        json.dumps([{"id": "camp", "name": "Camp", "latitude": LAT, "longitude": LON}]),
        encoding="utf-8",
    )

    def fetch(url: str) -> bytes:
        if "open-meteo.com" in url:
            return meteo_response(url)
        if "weather.gov" in url:
            return ALERTS
        return NEWS

    poller = WeatherPoller(
        tmp_path,
        tmp_path / "news",
        HomePlace(id="home", name="Home", latitude=LAT, longitude=LON),
        fetcher=fetch,
        now=lambda: WHEN,
    )
    poller.refresh()
    observation = poller.panel("weather-observation")
    assert [item["fields"]["place"] for item in observation["items"] if "extreme" not in item["fields"]] == ["Home", "Camp"]
    home = next(item for item in observation["items"] if item["fields"].get("place") == "Home")
    assert home["fields"]["temperature_c"] == 22.5
    assert home["fields"]["apparent_temperature_c"] == 24.0
    assert home["fields"]["humidity_pct"] == 81
    assert home["fields"]["wind_speed_kmh"] == 12.5
    assert home["fields"]["configured"] is True
    forecast = poller.panel("weather-forecast")
    assert forecast["items"][0]["row"] == "forecast"
    assert forecast["items"][0]["fields"]["temperature_high_c"] == 26.0
    assert "temperature_c" not in forecast["items"][0]["fields"]
    alert = poller.panel("weather-alerts")["items"][0]
    assert alert["fields"]["severity"] == "Severe"
    assert alert["fields"]["headline"] == "Severe thunderstorm warning"
    assert alert["source"] == "NWS Test"
    news = poller.panel("weather-news")["items"][0]
    assert news["row"] == "headline"
    assert "temperature_c" not in news["fields"]
    assert "summary" not in news["fields"]
    assert forecast_url(LAT, LON) != alerts_url(LAT, LON)


def test_extra_homes_are_fetched_and_watched_places_stay_marked(tmp_path: Path) -> None:
    write_news(tmp_path, enabled=False)
    (tmp_path / "places.json").write_text(
        json.dumps(
            [
                {"id": "miami", "name": "Miami", "latitude": 25.7617, "longitude": -80.1918, "home": True},
                {"id": "camp", "name": "Camp", "latitude": LAT, "longitude": LON, "home": False},
            ]
        ),
        encoding="utf-8",
    )
    poller = WeatherPoller(
        tmp_path,
        tmp_path / "news",
        HomePlace(id="tampa", name="Tampa", latitude=27.94752, longitude=-82.45843),
        fetcher=lambda url: meteo_response(url) if "open-meteo.com" in url else NONE,
        now=lambda: WHEN,
    )
    poller.refresh()
    rows = poller.panel("weather-observation")["items"]
    observed = [item for item in rows if "extreme" not in item["fields"]]
    assert [(item["fields"]["place"], item["fields"]["home"]) for item in observed] == [
        ("Tampa", True),
        ("Miami", True),
        ("Camp", False),
    ]
    assert all("temperature_c" in item["fields"] for item in observed)


def test_no_active_alerts_is_explicit(tmp_path: Path) -> None:
    write_news(tmp_path, enabled=False)
    (tmp_path / "places.json").write_text("[]", encoding="utf-8")

    def fetch(url: str) -> bytes:
        if "weather.gov" in url:
            return NONE
        return meteo_response(url)

    poller = WeatherPoller(
        tmp_path,
        tmp_path / "news",
        HomePlace(id="home", name="Home", latitude=LAT, longitude=LON),
        fetcher=fetch,
        now=lambda: WHEN,
    )
    poller.refresh()
    alerts = poller.panel("weather-alerts")["items"]
    assert len(alerts) == 1
    assert alerts[0]["title"] == "No alerts are active"
    assert "severity" not in alerts[0]["fields"]
    assert poller.panel("weather-forecast")["items"][0]["title"] != "No alerts are active"


def test_disabled_outlet_is_not_fetched(tmp_path: Path) -> None:
    seen: list[str] = []
    write_news(tmp_path, enabled=False)
    (tmp_path / "places.json").write_text("[]", encoding="utf-8")

    def fetch(url: str) -> bytes:
        seen.append(url)
        return NEWS

    poller = WeatherPoller(
        tmp_path,
        tmp_path / "news",
        HomePlace(id="home", name="unset"),
        fetcher=fetch,
        now=lambda: WHEN,
    )
    poller.refresh()
    assert seen == []
    assert poller.panel("weather-news")["items"] == []


def test_storm_route_keeps_news_off_an_empty_markets_bay(tmp_path: Path) -> None:
    write_news(tmp_path)
    (tmp_path / "places.json").write_text("[]", encoding="utf-8")
    poller = WeatherPoller(
        tmp_path,
        tmp_path / "news",
        HomePlace(id="home", name="unset"),
        fetcher=lambda url: NEWS,
        now=lambda: WHEN,
    )
    poller.refresh()
    client = TestClient(
        create_app(
            Config(
                bind_host="127.0.0.1",
                bind_port=8787,
                home_place=HomePlace(id="home", name="unset"),
                wires=WiresConfig(enabled=False),
                markets=MarketsConfig(enabled=False),
                trade=TradeConfig(enabled=False),
                weather=WeatherConfig(enabled=True),
            ),
            weather_poller=poller,
        )
    )
    body = client.get("/bays/storm").json()
    assert [panel["id"] for panel in body["panels"]] == [
        "weather-observation",
        "weather-forecast",
        "weather-alerts",
        "weather-news",
    ]
    assert client.get("/panels/weather-news").json()["domain"] == "weather-news"
    assert client.get("/bays/wires").json()["panels"] == []


def test_places_outside_the_united_states_name_the_alert_gap(tmp_path: Path) -> None:
    write_news(tmp_path, enabled=False)
    (tmp_path / "places.json").write_text(
        json.dumps([{"id": "tokyo", "name": "Tokyo", "latitude": 35.68, "longitude": 139.65, "home": False, "region": "Asia", "alerts": "none"}]),
        encoding="utf-8",
    )
    seen: list[str] = []

    def fetch(url: str) -> bytes:
        seen.append(url)
        if "open-meteo.com" in url:
            return meteo_response(url)
        return NONE

    poller = WeatherPoller(
        tmp_path,
        tmp_path / "news",
        HomePlace(id="tampa", name="Tampa", latitude=27.95, longitude=-82.46, region="North America", alerts="nws"),
        fetcher=fetch,
        now=lambda: WHEN,
    )
    poller.refresh()
    assert sum("open-meteo.com" in url for url in seen) == 1
    assert any("weather.gov" in url for url in seen)
    rows = poller.panel("weather-alerts")["items"]
    uncovered = [item for item in rows if item["fields"].get("region") == "Asia"]
    assert len(uncovered) == 1
    assert uncovered[0]["title"] == "No public alert source covers Asia"
    assert "Tokyo" not in uncovered[0]["title"]
    assert "No alerts are active" not in uncovered[0]["title"]


def test_uncovered_cities_in_one_region_share_a_row(tmp_path: Path) -> None:
    write_news(tmp_path, enabled=False)
    (tmp_path / "places.json").write_text(
        json.dumps(
            [
                {"id": "sydney", "name": "Sydney", "latitude": -33.87, "longitude": 151.21, "home": False, "region": "Oceania", "alerts": "none"},
                {"id": "melbourne", "name": "Melbourne", "latitude": -37.81, "longitude": 144.96, "home": False, "region": "Oceania", "alerts": "none"},
                {"id": "auckland", "name": "Auckland", "latitude": -36.85, "longitude": 174.76, "home": False, "region": "Oceania", "alerts": "none"},
            ]
        ),
        encoding="utf-8",
    )
    poller = WeatherPoller(
        tmp_path,
        tmp_path / "news",
        HomePlace(id="tampa", name="Tampa", latitude=27.95, longitude=-82.46, region="North America", alerts="nws"),
        fetcher=lambda url: meteo_response(url) if "open-meteo.com" in url else NONE,
        now=lambda: WHEN,
    )
    poller.refresh()
    alerts = poller.panel("weather-alerts")["items"]
    oceania = [item for item in alerts if "Oceania" in item["title"]]
    assert len(oceania) == 1
    assert oceania[0]["title"] == "No public alert source covers Oceania"
    assert "Sydney" not in oceania[0]["title"]
    active = [item for item in alerts if item["title"] == "No alerts are active"]
    assert len(active) == 1
    assert active[0]["fields"]["place"] == "Tampa"


def test_weather_news_summary_follows_the_feed(tmp_path: Path) -> None:
    write_news(tmp_path)
    described = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><item>
  <title>Storm story</title>
  <link>https://example.test/storm</link>
  <guid>storm-1</guid>
  <description>&lt;p&gt;Hello &lt;b&gt;there&lt;/b&gt;&lt;/p&gt;</description>
  <pubDate>Wed, 23 Sep 2026 18:00:00 GMT</pubDate>
</item></channel></rss>
"""
    poller = WeatherPoller(
        tmp_path,
        tmp_path / "news",
        HomePlace(id="home", name="unset"),
        fetcher=lambda url: described,
        now=lambda: WHEN,
    )
    poller.refresh()
    fields = poller.panel("weather-news")["items"][0]["fields"]
    assert fields["summary"] == "Hello there"
    assert "temperature_c" not in fields


def test_extremes_omit_a_measure_nobody_reported(tmp_path: Path) -> None:
    from oriel_server.weather.poller import _extremes

    items = [
        {"row": "observation", "fields": {"place": "Cairo", "home": False, "configured": True, "temperature_c": 30}},
        {"row": "observation", "fields": {"place": "Oslo", "home": False, "configured": True, "temperature_c": -2}},
    ]
    labels = [item["fields"]["extreme"] for item in _extremes(items)]
    assert labels == ["hottest", "coldest"]
    assert "windiest" not in labels
    assert "wettest" not in labels


def meteo_response(url: str, body: bytes = METEO) -> bytes:
    if "latitude=" not in url:
        return body
    query = url.split("latitude=", 1)[1].split("&", 1)[0]
    count = query.count(",") + 1
    if count == 1:
        return body
    one = json.loads(body)
    return json.dumps([one] * count).encode()


def write_news(directory: Path, *, enabled: bool = True) -> None:
    news = directory / "news"
    news.mkdir(parents=True, exist_ok=True)
    (directory / "places.json").write_text("[]", encoding="utf-8")
    outlet = {
        "id": "nhc-atlantic",
        "name": "National Hurricane Center",
        "fetch": "https://example.test/nhc",
        "enabled": enabled,
        "note": "test",
    }
    (news / "nhc-atlantic.json").write_text(json.dumps(outlet), encoding="utf-8")
