import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from oriel_server.config import Config, HomePlace, MarketsConfig, TradeConfig, WeatherConfig, WiresConfig
from oriel_server.main import create_app
from oriel_server.markets.catalog import FAMILIES, load_selection, load_sources
from oriel_server.markets.poller import MarketPoller

REPO = Path(__file__).resolve().parents[2]
WHEN = datetime(2026, 9, 23, 16, 0, tzinfo=timezone.utc)

YAHOO = json.dumps(
    {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 100.5,
                        "fulldayChange": 1.25,
                        "priceHint": 2,
                        "regularMarketTime": 1790195782,
                    }
                }
            ]
        }
    }
).encode()

FRANKFURTER = json.dumps(
    {
        "rates": {
            "2026-09-22": {"USD": 1.1463, "GBP": 0.86, "JPY": 157.1},
            "2026-09-23": {"USD": 1.1411, "GBP": 0.85, "JPY": 157.92},
        }
    }
).encode()

COINGECKO = json.dumps(
    {"bitcoin": {"usd": 100.0, "usd_24h_change": -10.0}, "dogecoin": {"usd": 1.0, "usd_24h_change": 1.0}}
).encode()

TREASURY = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed>
  <entry>
    <updated>2026-09-22T15:00:00Z</updated>
    <content><properties>
      <NEW_DATE>2026-09-22T00:00:00</NEW_DATE>
      <BC_10YEAR>5.00</BC_10YEAR>
    </properties></content>
  </entry>
  <entry>
    <updated>2026-09-23T15:50:12Z</updated>
    <content><properties>
      <NEW_DATE>2026-09-23T00:00:00</NEW_DATE>
      <BC_10YEAR>5.11</BC_10YEAR>
    </properties></content>
  </entry>
</feed>
"""


def test_shipped_sources_are_the_verified_delayed_boards() -> None:
    directory = REPO / "catalog" / "markets"
    sources = load_sources(directory / "sources.json")
    selection = load_selection(directory / "selection.json", sources)
    assert set(sources) == set(FAMILIES)
    assert {family: sources[family].id for family in FAMILIES} == {
        "indices": "yahoo-chart",
        "equities": "yahoo-chart",
        "fx": "frankfurter",
        "rates": "us-treasury",
        "commodities": "yahoo-chart",
        "crypto": "coingecko",
    }
    assert all(source.delayed for source in sources.values())
    assert [item.symbol for item in selection["fx"].instruments] == ["EURUSD", "USDJPY"]
    assert selection["crypto"].instruments[0].query == "bitcoin"
    assert all(source.id != "fred" for source in sources.values())


def test_hidden_family_is_not_fetched_or_shown(tmp_path: Path) -> None:
    write_markets(tmp_path, crypto=False)
    seen: list[str] = []

    def fetch(url: str) -> bytes:
        seen.append(url)
        if "frankfurter" in url:
            return FRANKFURTER
        raise AssertionError(url)

    poller = MarketPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    assert seen
    assert all("coingecko" not in url for url in seen)
    assert poller.panel("markets-crypto") is None
    fx = poller.panel("markets-fx")
    assert [item["fields"]["symbol"] for item in fx["items"]] == ["EURUSD", "USDJPY"]
    assert "GBP" not in json.dumps(fx)


def test_fx_rows_are_delayed_and_keep_the_source_change(tmp_path: Path) -> None:
    write_markets(tmp_path, crypto=False)
    poller = MarketPoller(tmp_path, fetcher=lambda url: FRANKFURTER, now=lambda: WHEN)
    poller.refresh()
    eur = poller.panel("markets-fx")["items"][0]
    assert eur["source"] == "Frankfurter"
    assert eur["fields"]["delayed"] is True
    assert eur["fields"]["price"] == 1.1411
    assert eur["fields"]["change"] == -0.0052
    assert eur["row"] == "quote"


def test_missing_change_is_omitted(tmp_path: Path) -> None:
    write_markets(tmp_path, crypto=False, fx=False, rates=True)
    payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed><entry>
  <updated>2026-09-23T15:50:12Z</updated>
  <content><properties>
    <NEW_DATE>2026-09-23T00:00:00</NEW_DATE>
    <BC_10YEAR>5.11</BC_10YEAR>
  </properties></content>
</entry></feed>"""
    poller = MarketPoller(tmp_path, fetcher=lambda url: payload, now=lambda: WHEN)
    poller.refresh()
    fields = poller.panel("markets-rates")["items"][0]["fields"]
    assert fields["price"] == 5.11
    assert "change" not in fields


def test_failed_refresh_keeps_the_last_price(tmp_path: Path) -> None:
    write_markets(tmp_path, crypto=False)
    calls = {"n": 0}

    def fetch(url: str) -> bytes:
        calls["n"] += 1
        if calls["n"] > 2:
            raise TimeoutError()
        return FRANKFURTER

    poller = MarketPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    first = poller.panel("markets-fx")["items"][0]["fields"]["price"]
    poller.refresh()
    panel = poller.panel("markets-fx")
    assert panel["stale"] is True
    assert "timeout" in panel["stale_reason"]
    assert panel["items"][0]["fields"]["price"] == first


def test_failure_without_a_last_price_invents_nothing(tmp_path: Path) -> None:
    write_markets(tmp_path, crypto=False)

    def fetch(url: str) -> bytes:
        raise TimeoutError()

    poller = MarketPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    panel = poller.panel("markets-fx")
    assert panel["items"] == []
    assert panel["stale"] is True
    assert "1.1411" not in json.dumps(panel)


def test_crypto_change_comes_from_the_source_percent_and_ignores_extra_coins(tmp_path: Path) -> None:
    write_markets(tmp_path, fx=False)
    seen: list[str] = []

    def fetch(url: str) -> bytes:
        seen.append(url)
        return COINGECKO

    poller = MarketPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    assert len(seen) == 1
    assert "dogecoin" not in seen[0]
    assert "bitcoin" in seen[0]
    item = poller.panel("markets-crypto")["items"][0]
    assert item["fields"]["symbol"] == "BTC"
    assert item["fields"]["price"] == 100.0
    assert item["fields"]["change"] == -11.11
    assert item["fields"]["delayed"] is True
    assert len(poller.panel("markets-crypto")["items"]) == 1


def test_markets_route_returns_only_selected_families(tmp_path: Path) -> None:
    write_markets(tmp_path, crypto=False)
    poller = MarketPoller(tmp_path, fetcher=lambda url: FRANKFURTER, now=lambda: WHEN)
    poller.refresh()
    client = TestClient(
        create_app(
            Config(
                bind_host="127.0.0.1",
                bind_port=8787,
                home_place=HomePlace(id="home", name="unset"),
                wires=WiresConfig(enabled=False),
                markets=MarketsConfig(enabled=True),
                trade=TradeConfig(enabled=False),
                weather=WeatherConfig(enabled=False),
            ),
            market_poller=poller,
        )
    )
    body = client.get("/bays/markets").json()
    assert [panel["id"] for panel in body["panels"]] == ["markets-fx"]
    assert client.get("/panels/markets-fx").json()["items"][0]["source"] == "Frankfurter"
    assert client.get("/panels/markets-crypto").status_code == 404


def test_quote_older_than_budget_is_stale(tmp_path: Path) -> None:
    write_markets(tmp_path, crypto=False)
    clock = {"now": WHEN}
    poller = MarketPoller(
        tmp_path,
        fetcher=lambda url: FRANKFURTER,
        now=lambda: clock["now"],
        stale_after_seconds=900,
    )
    poller.refresh()
    clock["now"] = WHEN + timedelta(seconds=901)
    panel = poller.panel("markets-fx")
    assert panel["stale"] is True
    assert panel["stale_reason"] == "older than budget"
    assert panel["items"][0]["fields"]["price"] == 1.1411


def write_markets(directory: Path, *, fx: bool = True, crypto: bool = True, rates: bool = False) -> None:
    sources = {
        family: {
            "id": "yahoo-chart",
            "name": "Yahoo Finance",
            "kind": "yahoo-chart",
            "delayed": True,
            "fetch": "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            "note": "test",
        }
        for family in FAMILIES
    }
    sources["fx"] = {
        "id": "frankfurter",
        "name": "Frankfurter",
        "kind": "frankfurter",
        "delayed": True,
        "fetch": "https://api.frankfurter.app/{start}..{end}",
        "note": "test",
    }
    sources["rates"] = {
        "id": "us-treasury",
        "name": "US Treasury",
        "kind": "treasury-yields",
        "delayed": True,
        "fetch": "https://home.treasury.gov/example",
        "note": "test",
    }
    sources["crypto"] = {
        "id": "coingecko",
        "name": "CoinGecko",
        "kind": "coingecko",
        "delayed": True,
        "fetch": "https://api.coingecko.com/api/v3/simple/price",
        "note": "test",
    }
    selection = {
        family: {"enabled": False, "instruments": []}
        for family in FAMILIES
    }
    selection["fx"] = {
        "enabled": fx,
        "instruments": [
            {"symbol": "EURUSD", "base": "EUR", "counter": "USD", "title": "Euro / US dollar"},
            {"symbol": "USDJPY", "base": "USD", "counter": "JPY", "title": "US dollar / Yen"},
        ],
    }
    selection["crypto"] = {
        "enabled": crypto,
        "instruments": [{"symbol": "BTC", "query": "bitcoin", "title": "Bitcoin"}],
    }
    selection["rates"] = {
        "enabled": rates,
        "instruments": [{"symbol": "US10Y", "field": "BC_10YEAR", "title": "US 10-year"}],
    }
    (directory / "sources.json").write_text(json.dumps(sources), encoding="utf-8")
    (directory / "selection.json").write_text(json.dumps(selection), encoding="utf-8")
