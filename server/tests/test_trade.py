import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from oriel_server.config import Config, HomePlace, MarketsConfig, TradeConfig, WeatherConfig, WiresConfig
from oriel_server.main import create_app
from oriel_server.trade.catalog import FAMILIES, load_selection, load_sources
from oriel_server.trade.poller import TradePoller

REPO = Path(__file__).resolve().parents[2]
WHEN = datetime(2026, 9, 23, 22, 1, 17, tzinfo=timezone.utc)

POLICY = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>Tariff notice</title>
    <link>https://example.test/policy</link>
    <guid>policy-1</guid>
    <pubDate>Wed, 23 Sep 2026 22:01:17 GMT</pubDate>
  </item>
</channel></rss>
"""

FREIGHT = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>Freight notice</title>
    <link>https://example.test/freight</link>
    <guid>freight-1</guid>
    <pubDate>Wed, 23 Sep 2026 21:00:00 GMT</pubDate>
  </item>
</channel></rss>
"""

SUPPLY = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>Supply notice</title>
    <link>https://example.test/supply</link>
    <guid>supply-1</guid>
    <pubDate>Wed, 23 Sep 2026 20:00:00 GMT</pubDate>
  </item>
</channel></rss>
"""

FEEDS = {
    "https://example.test/policy": POLICY,
    "https://example.test/freight": FREIGHT,
    "https://example.test/supply": SUPPLY,
}


def test_shipped_trade_sources_are_public_https() -> None:
    directory = REPO / "catalog" / "trade"
    sources = load_sources(directory / "sources.json")
    selection = load_selection(directory / "selection.json")
    assert set(sources) == set(FAMILIES)
    assert sources["policy"][0].name == "WTO"
    assert {item.id for item in sources["policy"]} == {"wto-news", "cbp-news"}
    assert sources["freight"][0].name == "FreightWaves"
    assert {item.id for item in sources["freight"]} == {"freightwaves", "gcaptain"}
    assert sources["supply-chain"][0].name == "Supply Chain Dive"
    assert {item.id for item in sources["supply-chain"]} == {"supply-chain-dive", "loadstar"}
    for family in FAMILIES:
        assert all(item.fetch.startswith("https://") for item in sources[family])
        assert selection[family].enabled is True


def test_hidden_freight_is_not_fetched(tmp_path: Path) -> None:
    seen: list[str] = []

    def fetch(url: str) -> bytes:
        seen.append(url)
        return FEEDS[url]

    write_trade(tmp_path, freight=False)
    poller = TradePoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    assert "https://example.test/freight" not in seen
    assert poller.panel("trade-freight") is None
    policy = poller.panel("trade-policy")
    assert policy is not None
    item = policy["items"][0]
    assert item["title"] == "Tariff notice"
    assert item["source"] == "WTO"
    assert item["observed_at"] == "2026-09-23T22:01:17Z"
    assert item["row"] == "headline"
    assert item["fields"] == {"family": "policy"}
    assert "price" not in item["fields"]
    supply = poller.panel("trade-supply-chain")
    assert supply["items"][0]["source"] == "Supply Chain Dive"


def test_failed_refresh_keeps_last_good_title(tmp_path: Path) -> None:
    write_trade(tmp_path, freight=False, supply=False)
    calls = {"n": 0}

    def fetch(url: str) -> bytes:
        calls["n"] += 1
        if calls["n"] > 1:
            raise TimeoutError()
        return POLICY

    poller = TradePoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    poller.refresh()
    panel = poller.panel("trade-policy")
    assert panel["stale"] is True
    assert panel["stale_reason"] == "wto-news: timeout"
    assert panel["items"][0]["title"] == "Tariff notice"
    assert panel["items"][0]["source"] == "WTO"


def test_trade_route_omits_hidden_family(tmp_path: Path) -> None:
    write_trade(tmp_path, freight=False)
    poller = TradePoller(tmp_path, fetcher=lambda url: FEEDS[url], now=lambda: WHEN)
    poller.refresh()
    client = TestClient(
        create_app(
            Config(
                bind_host="127.0.0.1",
                bind_port=8787,
                home_place=HomePlace(id="home", name="unset"),
                wires=WiresConfig(enabled=False),
                markets=MarketsConfig(enabled=False),
                trade=TradeConfig(enabled=True),
                weather=WeatherConfig(enabled=False),
            ),
            trade_poller=poller,
        )
    )
    body = client.get("/bays/trade").json()
    assert [panel["id"] for panel in body["panels"]] == ["trade-policy", "trade-supply-chain"]
    assert client.get("/panels/trade-freight").status_code == 404
    assert client.get("/bays/markets").json()["panels"] == []


def test_trade_older_than_budget_is_stale(tmp_path: Path) -> None:
    write_trade(tmp_path, freight=False, supply=False)
    clock = {"now": WHEN}
    poller = TradePoller(
        tmp_path,
        fetcher=lambda url: POLICY,
        now=lambda: clock["now"],
        stale_after_seconds=3600,
    )
    poller.refresh()
    clock["now"] = WHEN + timedelta(seconds=3601)
    panel = poller.panel("trade-policy")
    assert panel["stale"] is True
    assert "older than budget" in panel["stale_reason"]
    assert panel["items"][0]["title"] == "Tariff notice"


def test_disabled_trade_domain_has_no_panels() -> None:
    client = TestClient(
        create_app(
            Config(
                bind_host="127.0.0.1",
                bind_port=8787,
                home_place=HomePlace(id="home", name="unset"),
                wires=WiresConfig(enabled=False),
                markets=MarketsConfig(enabled=False),
                trade=TradeConfig(enabled=False),
                weather=WeatherConfig(enabled=False),
            )
        )
    )
    assert client.get("/bays/trade").json() == {"id": "trade", "panels": []}


def write_trade(directory: Path, *, freight: bool = True, supply: bool = True) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    sources = {
        "policy": {"id": "wto-news", "name": "WTO", "fetch": "https://example.test/policy", "note": "test"},
        "freight": {
            "id": "freightwaves",
            "name": "FreightWaves",
            "fetch": "https://example.test/freight",
            "note": "test",
        },
        "supply-chain": {
            "id": "supply-chain-dive",
            "name": "Supply Chain Dive",
            "fetch": "https://example.test/supply",
            "note": "test",
        },
    }
    selection = {
        "policy": {"enabled": True},
        "freight": {"enabled": freight},
        "supply-chain": {"enabled": supply},
    }
    (directory / "sources.json").write_text(json.dumps(sources), encoding="utf-8")
    (directory / "selection.json").write_text(json.dumps(selection), encoding="utf-8")
