"""Brief selection writes one slot and rejects an id the catalogs do not have."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from oriel_server.brief.selection import BriefStore
from oriel_server.config import Config, HomePlace, MarketsConfig, TradeConfig, WeatherConfig, WiresConfig
from oriel_server.main import create_app


def test_chosen_place_is_saved_and_an_unknown_outlet_is_rejected(tmp_path: Path) -> None:
    places = tmp_path / "places.json"
    places.write_text(
        json.dumps(
            [
                {
                    "id": "london",
                    "name": "London",
                    "latitude": 51.51,
                    "longitude": -0.13,
                    "home": False,
                    "region": "Europe",
                    "alerts": "none",
                }
            ]
        ),
        encoding="utf-8",
    )
    outlets = tmp_path / "outlets"
    outlets.mkdir()
    (outlets / "guardian-world.json").write_text(
        json.dumps(
            {
                "id": "guardian-world",
                "name": "The Guardian",
                "fetch": "https://example.test/world",
                "language": "en",
                "region": "world",
                "desks": ["world"],
                "enabled": True,
            }
        ),
        encoding="utf-8",
    )
    (outlets / "quiet.json").write_text(
        json.dumps(
            {
                "id": "quiet",
                "name": "Quiet",
                "fetch": "https://example.test/quiet",
                "language": "en",
                "region": "world",
                "desks": ["world"],
                "enabled": False,
            }
        ),
        encoding="utf-8",
    )
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps({"place": "", "outlet": "", "family": ""}) + "\n", encoding="utf-8")
    store = BriefStore(selection, places, outlets, HomePlace(id="tampa", name="Tampa", latitude=27.95, longitude=-82.46))
    config = Config(
        bind_host="127.0.0.1",
        bind_port=8787,
        home_place=store.home,
        wires=WiresConfig(enabled=False),
        markets=MarketsConfig(enabled=False),
        trade=TradeConfig(enabled=False),
        weather=WeatherConfig(enabled=False),
    )
    client = TestClient(create_app(config, brief=store))
    places_before = places.read_text(encoding="utf-8")

    chosen = client.post("/bays/brief/selection", json={"slot": "place", "id": "london"})
    assert chosen.status_code == 200
    body = chosen.json()
    assert body["place"] == "london"
    assert body["outlet"] == ""
    assert body["family"] == ""
    written = json.loads(selection.read_text(encoding="utf-8"))
    assert written == {"place": "london", "outlet": "", "family": ""}
    selected = {item["title"]: item["fields"]["followed"] for item in body["items"] if item["fields"]["slot"] == "place"}
    assert selected["London"] is True
    assert selected["Home"] is False
    assert places.read_text(encoding="utf-8") == places_before

    before = selection.read_text(encoding="utf-8")
    rejected = client.post("/bays/brief/selection", json={"slot": "outlet", "id": "nope"})
    assert rejected.status_code == 400
    assert selection.read_text(encoding="utf-8") == before
    disabled = client.post("/bays/brief/selection", json={"slot": "outlet", "id": "quiet"})
    assert disabled.status_code == 400
    assert selection.read_text(encoding="utf-8") == before

    family = client.post("/bays/brief/selection", json={"slot": "family", "id": "indices"})
    assert family.status_code == 200
    assert family.json()["family"] == "indices"
    assert json.loads(selection.read_text(encoding="utf-8"))["place"] == "london"

    home = client.post("/bays/brief/selection", json={"slot": "place", "id": ""})
    assert home.status_code == 200
    assert home.json()["place"] == ""
    flags = {item["title"]: item["fields"]["followed"] for item in home.json()["items"] if item["fields"]["slot"] == "place"}
    assert flags["Home"] is True
    assert flags["London"] is False
