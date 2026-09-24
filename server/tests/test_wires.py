import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from oriel_server.config import Config, HomePlace, MarketsConfig, TradeConfig, WeatherConfig, WiresConfig
from oriel_server.main import create_app
from oriel_server.wires.catalog import WIRE_DESKS, load_outlets
from oriel_server.wires.poller import WirePoller
from oriel_server.wires.rss import parse_feed

REPO = Path(__file__).resolve().parents[2]
WHEN = datetime(2026, 9, 23, 22, 1, 17, tzinfo=timezone.utc)

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example</title>
    <item>
      <title>Hello &amp; world</title>
      <link>https://example.test/hello</link>
      <guid>https://example.test/hello</guid>
      <pubDate>Wed, 23 Sep 2026 22:01:17 GMT</pubDate>
    </item>
    <item>
      <title>Older</title>
      <link>https://example.test/older</link>
      <guid>https://example.test/older</guid>
      <pubDate>Tue, 22 Sep 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example</title>
  <entry>
    <title>Atom title</title>
    <link href="https://example.test/atom" rel="alternate"/>
    <id>tag:example.test,2026:atom</id>
    <updated>2026-09-23T22:01:17Z</updated>
  </entry>
</feed>
"""

SHIPPED = {
    "ars-technica",
    "bbc-business",
    "bbc-politics",
    "bbc-science",
    "bbc-technology",
    "bbc-uk",
    "bbc-world",
    "guardian-business",
    "guardian-science",
    "guardian-world",
    "npr-politics",
    "nyt-us",
}


def test_shipped_outlets_cover_every_desk() -> None:
    outlets = load_outlets(REPO / "catalog" / "outlets")
    assert {outlet.id for outlet in outlets} == SHIPPED
    desks: set[str] = set()
    for outlet in outlets:
        assert outlet.enabled is True
        assert outlet.fetch.startswith("https://")
        assert outlet.language == "en"
        assert outlet.name
        assert outlet.region
        desks.update(outlet.desks)
    assert desks == set(WIRE_DESKS)


def test_parse_rss_and_atom() -> None:
    rss = parse_feed(RSS, fallback=WHEN)
    assert [(entry.title, entry.link) for entry in rss] == [
        ("Hello & world", "https://example.test/hello"),
        ("Older", "https://example.test/older"),
    ]
    assert rss[0].observed_at == WHEN
    atom = parse_feed(ATOM, fallback=WHEN)
    assert atom[0].title == "Atom title"
    assert atom[0].link == "https://example.test/atom"
    assert atom[0].observed_at == WHEN


def test_enabled_outlet_maps_to_its_desk_only(tmp_path: Path) -> None:
    seen: list[str] = []

    def fetch(url: str) -> bytes:
        seen.append(url)
        return RSS

    write_outlet(tmp_path, "tech", "https://example.test/tech", ["technology"])
    write_outlet(tmp_path, "off", "https://example.test/off", ["technology"], enabled=False)
    write_outlet(tmp_path, "world", "https://example.test/world", ["world"])
    poller = poller_for(tmp_path, fetch)
    poller.refresh()

    assert set(seen) == {
        "https://example.test/tech",
        "https://example.test/world",
    }
    tech = poller.panel("wires-technology")
    assert tech is not None
    assert tech["stale"] is False
    assert tech["stale_reason"] == ""
    assert tech["domain"] == "wires"
    assert [item["fields"]["desk"] for item in tech["items"]] == ["technology", "technology"]
    assert {item["row"] for item in tech["items"]} == {"headline"}
    assert tech["items"][0]["title"] == "Hello & world"
    assert tech["items"][0]["source"] == "Tech Wire"
    assert tech["items"][0]["observed_at"] == "2026-09-23T22:01:17Z"
    assert all(item["source"] != "Off Wire" for item in tech["items"])
    world = poller.panel("wires-world")
    assert world is not None
    assert {item["fields"]["desk"] for item in world["items"]} == {"world"}
    assert poller.last_success()["tech"] == "2026-09-23T22:01:17Z"


def test_disable_removes_rows_only_after_a_successful_refresh(tmp_path: Path) -> None:
    phase = {"fail": False}

    def fetch(url: str) -> bytes:
        if phase["fail"]:
            raise TimeoutError()
        slug = url.rsplit("/", 1)[-1]
        body = RSS.replace(b"https://example.test/hello", f"https://example.test/{slug}".encode())
        return body.replace(b"https://example.test/older", f"https://example.test/{slug}-older".encode())

    write_outlet(tmp_path, "keep", "https://example.test/keep", ["world"])
    write_outlet(tmp_path, "drop", "https://example.test/drop", ["world"])
    clock = {"now": WHEN}
    poller = poller_for(tmp_path, fetch, now=lambda: clock["now"])
    poller.refresh()
    titles = {item["source"] for item in poller.panel("wires-world")["items"]}
    assert titles == {"Keep Wire", "Drop Wire"}

    write_outlet(tmp_path, "drop", "https://example.test/drop", ["world"], enabled=False)
    phase["fail"] = True
    clock["now"] = WHEN + timedelta(minutes=2)
    poller.refresh()
    panel = poller.panel("wires-world")
    assert panel["stale"] is True
    assert panel["stale_reason"] == "keep: timeout"
    assert {item["source"] for item in panel["items"]} == {"Keep Wire", "Drop Wire"}
    assert panel["items"][0]["title"] == "Hello & world"

    phase["fail"] = False
    clock["now"] = WHEN + timedelta(minutes=4)
    poller.refresh()
    panel = poller.panel("wires-world")
    assert panel["stale"] is False
    assert {item["source"] for item in panel["items"]} == {"Keep Wire"}


def test_failed_refresh_keeps_last_good_and_labels_stale(tmp_path: Path) -> None:
    calls = {"n": 0}

    def fetch(url: str) -> bytes:
        calls["n"] += 1
        if calls["n"] > 1:
            raise TimeoutError()
        return RSS

    write_outlet(tmp_path, "world", "https://example.test/world", ["world"])
    poller = poller_for(tmp_path, fetch)
    poller.refresh()
    first = poller.panel("wires-world")
    poller.refresh()
    second = poller.panel("wires-world")
    assert second["stale"] is True
    assert second["stale_reason"] == "world: timeout"
    assert second["items"] == first["items"]
    assert second["updated_at"] == first["updated_at"]


def test_failure_with_no_last_good_does_not_invent_headlines(tmp_path: Path) -> None:
    def fetch(url: str) -> bytes:
        raise TimeoutError()

    write_outlet(tmp_path, "world", "https://example.test/world", ["world"])
    poller = poller_for(tmp_path, fetch)
    poller.refresh()
    panel = poller.panel("wires-world")
    assert panel["items"] == []
    assert panel["stale"] is True
    assert panel["stale_reason"] == "world: timeout"
    assert "Hello" not in json.dumps(panel)


def test_all_outlets_disabled_is_an_empty_fresh_panel(tmp_path: Path) -> None:
    def fetch(url: str) -> bytes:
        raise AssertionError(url)

    write_outlet(tmp_path, "world", "https://example.test/world", ["world"], enabled=False)
    poller = poller_for(tmp_path, fetch)
    poller.refresh()
    panel = poller.panel("wires-world")
    assert panel["items"] == []
    assert panel["stale"] is False
    assert panel["stale_reason"] == ""


def test_payload_older_than_budget_is_stale(tmp_path: Path) -> None:
    clock = {"now": WHEN}

    def fetch(url: str) -> bytes:
        return RSS

    write_outlet(tmp_path, "world", "https://example.test/world", ["world"])
    poller = poller_for(
        tmp_path,
        fetch,
        now=lambda: clock["now"],
        stale_after_seconds=900,
    )
    poller.refresh()
    assert poller.panel("wires-world")["stale"] is False
    clock["now"] = WHEN + timedelta(seconds=901)
    panel = poller.panel("wires-world")
    assert panel["stale"] is True
    assert panel["stale_reason"] == "older than budget"
    assert panel["items"][0]["title"] == "Hello & world"


def test_last_success_survives_a_restart(tmp_path: Path) -> None:
    state = tmp_path / "state" / "wires.json"

    def fetch_ok(url: str) -> bytes:
        return RSS

    write_outlet(tmp_path, "world", "https://example.test/world", ["world"])
    first = poller_for(tmp_path, fetch_ok, state_path=state)
    first.refresh()

    def fetch_fail(url: str) -> bytes:
        raise TimeoutError()

    second = poller_for(tmp_path, fetch_fail, state_path=state)
    second.refresh()
    panel = second.panel("wires-world")
    assert panel["stale"] is True
    assert panel["items"][0]["title"] == "Hello & world"
    assert second.last_success()["world"] == "2026-09-23T22:01:17Z"


def test_wires_route_returns_the_panel(tmp_path: Path) -> None:
    def fetch(url: str) -> bytes:
        return RSS

    write_outlet(tmp_path, "tech", "https://example.test/tech", ["technology"])
    poller = poller_for(tmp_path, fetch)
    poller.refresh()
    client = TestClient(
        create_app(
            Config(
                bind_host="127.0.0.1",
                bind_port=8787,
                home_place=HomePlace(id="home", name="unset"),
                wires=WiresConfig(enabled=True),
                markets=MarketsConfig(enabled=False),
                trade=TradeConfig(enabled=False),
                weather=WeatherConfig(enabled=False),
            ),
            poller=poller,
        )
    )
    bay = client.get("/bays/wires")
    assert bay.status_code == 200
    body = bay.json()
    assert body["id"] == "wires"
    assert [panel["id"] for panel in body["panels"]] == [f"wires-{desk}" for desk in WIRE_DESKS]
    tech = client.get("/panels/wires-technology").json()
    assert tech["items"][0]["source"] == "Tech Wire"
    assert client.get("/panels/not-a-panel").status_code == 404


def test_disabled_wires_domain_has_no_panels() -> None:
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
    assert client.get("/bays/wires").json() == {"id": "wires", "panels": []}
    assert client.get("/panels/wires-world").status_code == 404


def poller_for(
    catalog: Path,
    fetch,
    *,
    now=None,
    stale_after_seconds: int = 900,
    state_path: Path | None = None,
) -> WirePoller:
    kwargs = {
        "fetcher": fetch,
        "stale_after_seconds": stale_after_seconds,
        "state_path": state_path,
    }
    if now is not None:
        kwargs["now"] = now
    else:
        kwargs["now"] = lambda: WHEN
    return WirePoller(catalog, **kwargs)


def write_outlet(
    catalog: Path,
    outlet_id: str,
    url: str,
    desks: list[str],
    *,
    enabled: bool = True,
) -> None:
    name = outlet_id.replace("-", " ").title() + " Wire"
    payload = {
        "id": outlet_id,
        "name": name,
        "fetch": url,
        "language": "en",
        "region": "world",
        "desks": desks,
        "enabled": enabled,
    }
    (catalog / f"{outlet_id}.json").write_text(json.dumps(payload), encoding="utf-8")
