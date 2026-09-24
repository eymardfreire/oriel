import json
from datetime import datetime, timezone
from pathlib import Path

from oriel_server.sports.catalog import load_competitions
from oriel_server.sports.poller import SportsPoller

REPO = Path(__file__).resolve().parents[2]
WHEN = datetime(2026, 9, 23, 22, 0, tzinfo=timezone.utc)

MLB = {
    "dates": [
        {
            "games": [
                {
                    "gameDate": "2026-09-23T23:10:00Z",
                    "status": {"abstractGameState": "Live"},
                    "teams": {
                        "away": {"score": 1, "team": {"name": "Fixture Away"}},
                        "home": {"score": 0, "team": {"name": "Fixture Home"}},
                    },
                }
            ]
        }
    ]
}

FAILED = b"not-json"


def test_shipped_catalog_has_a_tier_and_omits_unverified_families() -> None:
    competitions = load_competitions(REPO / "catalog" / "sports" / "competitions.json")
    assert {item.tier for item in competitions} <= {"live", "delayed", "results", "schedule", "far"}
    assert {item.id: item.tier for item in competitions} == {
        "mlb": "live",
        "nhl": "live",
        "bundesliga": "results",
        "formula-1": "results",
    }
    families = {item.family for item in competitions}
    assert "basketball" not in families
    assert "esports" not in families
    follows = json.loads((REPO / "catalog" / "sports" / "follows.json").read_text(encoding="utf-8"))
    assert follows == {"competitions": [], "sports": [], "competitors": []}


def test_no_follows_fetches_nothing_and_asks_for_follows(tmp_path: Path) -> None:
    seen: list[str] = []
    write_catalog(tmp_path, follows=[])

    def fetch(url: str) -> bytes:
        seen.append(url)
        return json.dumps(MLB).encode()

    poller = SportsPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    assert seen == []
    field = poller.panels_for("field")[0]
    assert field["items"][0]["title"] == "Choose follows"
    assert field["items"][0]["row"] != "score"
    assert all(item["row"] != "score" for item in field["items"])


def test_live_follow_names_the_source_and_a_failed_first_fetch_has_no_score(tmp_path: Path) -> None:
    write_catalog(tmp_path, follows=["mlb"])
    calls = {"n": 0}

    def fetch(url: str) -> bytes:
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("down")
        return json.dumps(MLB).encode()

    poller = SportsPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    row = poller.panel("field-scores")["items"][0]
    assert row["title"] == "Major League Baseball"
    assert "score" not in row["fields"]
    assert "0" not in json.dumps(row["fields"])

    poller.refresh()
    live = poller.panel("field-scores")["items"][0]
    assert live["fields"]["score"] == "0-1"
    assert live["fields"]["state"] == "in progress"
    assert live["source"] == "MLB Stats API"
    assert live["fields"]["tier"] == "live"
    assert poller.panel("fantasy-lineup")["items"]
    assert all(item["row"] != "fantasy" for item in poller.panel("field-scores")["items"])


def test_failed_refresh_keeps_the_last_score_and_marks_it_stale(tmp_path: Path) -> None:
    write_catalog(tmp_path, follows=["mlb"])
    mode = {"ok": True}

    def fetch(url: str) -> bytes:
        if not mode["ok"]:
            raise TimeoutError("down")
        return json.dumps(MLB).encode()

    poller = SportsPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    mode["ok"] = False
    poller.refresh()
    panel = poller.panel("field-scores")
    assert panel["stale"] is True
    assert panel["items"][0]["fields"]["score"] == "0-1"


def test_schedule_follow_has_competitors_and_no_score(tmp_path: Path) -> None:
    write_catalog(
        tmp_path,
        follows=["friendly"],
        extra={
            "id": "friendly",
            "family": "football",
            "name": "Friendly",
            "tier": "schedule",
            "source_id": "fixture",
            "source_name": "Fixture board",
            "kind": "fixture",
            "fetch": "https://example.test/friendly",
            "note": "schedule only",
        },
    )

    def fetch(url: str) -> bytes:
        return json.dumps(
            [{"id": "m1", "home": "Home Side", "away": "Away Side", "when": "2026-09-24T18:00:00Z", "state": "scheduled", "score": "3-0"}]
        ).encode()

    poller = SportsPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    row = poller.panel("field-scores")["items"][0]
    assert row["fields"]["home"] == "Home Side"
    assert row["fields"]["away"] == "Away Side"
    assert "score" not in row["fields"]
    assert row["fields"]["state"].startswith("scheduled")


def test_delayed_row_keeps_the_delayed_tier(tmp_path: Path) -> None:
    write_catalog(
        tmp_path,
        follows=["lag"],
        extra={
            "id": "lag",
            "family": "football",
            "name": "Lagged league",
            "tier": "delayed",
            "source_id": "fixture",
            "source_name": "Lagged board",
            "kind": "fixture",
            "fetch": "https://example.test/lag",
            "note": "delayed",
        },
    )

    def fetch(url: str) -> bytes:
        return json.dumps(
            [{"id": "m1", "home": "Home Side", "away": "Away Side", "when": "2026-09-23T21:00:00Z", "state": "live", "score": "1-0"}]
        ).encode()

    poller = SportsPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    row = poller.panel("field-scores")["items"][0]
    assert row["fields"]["tier"] == "delayed"
    assert row["fields"]["score"] == "1-0"
    assert all(item["fields"].get("tier") != "far" for item in poller.panel("field-scores")["items"])


def test_far_desk_uses_a_factual_line_or_a_quotation(tmp_path: Path) -> None:
    write_catalog(
        tmp_path,
        follows=[],
        extra={
            "id": "village",
            "family": "football",
            "name": "Village cup",
            "tier": "far",
            "source_id": "fixture",
            "source_name": "Village report",
            "kind": "fixture",
            "fetch": "https://example.test/village",
            "note": "far",
        },
    )
    payloads = [
        [{"id": "final", "home": "North", "away": "South", "when": "2026-09-23T16:00:00Z", "state": "final", "score": "2-1"}],
        [{"id": "clip", "home": "", "away": "", "when": "2026-09-23T16:00:00Z", "excerpt": "North won the cup"}],
    ]

    def fetch(url: str) -> bytes:
        return json.dumps(payloads.pop(0)).encode()

    poller = SportsPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    row = poller.panel("far-desk")["items"][0]
    assert row["fields"]["factual"] is True
    assert row["fields"]["factual_line"] == "North defeated South 2-1"
    assert row["source"] == "Village report"
    assert poller.panel("field-scores")["items"][0]["title"] == "Choose follows"

    poller.refresh()
    excerpt = poller.panel("far-desk")["items"][0]
    assert excerpt["fields"]["excerpt"] == "North won the cup"
    assert "score" not in excerpt["fields"]


def test_fantasy_roster_select_pin_and_flex_stay_separate(tmp_path: Path) -> None:
    write_catalog(tmp_path, follows=[])
    players = {
        "rb1": player("rb1", "First Back", "RB"),
        "rb2": player("rb2", "Second Back", "RB"),
        "rb3": player("rb3", "Third Back", "RB"),
        "qb1": player("qb1", "Passer", "QB"),
    }
    poller = SportsPoller(tmp_path, fetcher=lambda url: FAILED, now=lambda: WHEN, players=players)
    lineup = poller.panels_for("fantasy")[1]["items"]
    assert [item["fields"]["slot"] for item in lineup] == ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DST"]
    assert all(item["fields"]["player"] == "" for item in lineup)
    assert poller.panels_for("fantasy")[0]["items"] == []

    poller.select("rb1")
    running = [item["fields"]["player"] for item in poller.panel("fantasy-lineup")["items"] if item["fields"]["slot"] == "RB"]
    assert running == ["First Back", ""]
    assert sum(1 for item in poller.panel("fantasy-lineup")["items"] if item["fields"]["player"] == "") == 8

    poller.select("rb2")
    poller.select("rb3")
    bench = poller.panel("fantasy-bench")["items"]
    assert [item["fields"]["player"] for item in bench] == ["Third Back"]
    flex = next(item for item in poller.panel("fantasy-lineup")["items"] if item["fields"]["slot"] == "FLEX")
    assert flex["fields"]["player"] == ""

    poller.flex("rb3")
    flex = next(item for item in poller.panel("fantasy-lineup")["items"] if item["fields"]["slot"] == "FLEX")
    assert flex["fields"]["player"] == "Third Back"
    assert poller.panel("fantasy-bench")["items"] == []

    before = json.dumps(poller.panels_for("fantasy"))
    poller.select("rb1")
    assert json.dumps(poller.panels_for("fantasy")) == before

    poller.pin("qb1")
    pins = poller.panel("fantasy-pins")["items"]
    assert pins[0]["fields"]["player"] == "Passer"
    assert all(item["fields"]["player"] != "Passer" for item in poller.panel("fantasy-lineup")["items"])
    poller.pin("rb1")
    assert poller.panel("fantasy-pins")["items"][0]["fields"]["player"] == "First Back"
    pinned = next(item for item in poller.panel("fantasy-lineup")["items"] if item["fields"]["player"] == "First Back")
    assert pinned["fields"]["pinned"] is True

    poller.unpin("rb1")
    assert all(item["fields"]["player"] != "First Back" for item in poller.panel("fantasy-pins")["items"])
    still = next(item for item in poller.panel("fantasy-lineup")["items"] if item["fields"]["slot"] == "RB")
    assert still["fields"]["player"] == "First Back"
    assert "pinned" not in still["fields"]

    poller.drop("rb1")
    assert all(item["fields"].get("player") != "First Back" for item in poller.panel("fantasy-lineup")["items"])


def test_points_come_only_from_the_selected_scoring_key(tmp_path: Path) -> None:
    write_catalog(tmp_path, follows=[])
    poller = SportsPoller(
        tmp_path,
        fetcher=sleeper_fetch,
        now=lambda: WHEN,
        players={"11": player("11", "Scorer", "WR")},
    )
    poller.select("11")
    row = next(item for item in poller.panel("fantasy-lineup")["items"] if item["fields"]["player"] == "Scorer")
    assert row["fields"]["points"] == 18.5
    assert row["fields"]["week"] == 3
    assert row["source"] == "Sleeper"

    poller.scoring("standard")
    row = next(item for item in poller.panel("fantasy-lineup")["items"] if item["fields"]["player"] == "Scorer")
    assert row["fields"]["points"] == 12.5

    empty = SportsPoller(
        tmp_path,
        fetcher=lambda url: b'{"week":3,"season":"2026","season_type":"regular"}' if "state" in url else b"{}",
        now=lambda: WHEN,
        players={"11": player("11", "Scorer", "WR")},
    )
    pinned = empty.panel("fantasy-pins")
    empty.pin("11")
    row = empty.panel("fantasy-pins")["items"][0]
    assert row["fields"]["player"] == "Scorer"
    assert row["fields"]["position"] == "WR"
    assert row["fields"]["team"] == "FIX"
    assert "points" not in row["fields"]
    assert pinned is not None


def player(ident: str, name: str, position: str):
    from oriel_server.sports.catalog import Player

    return Player(id=ident, name=name, position=position, team="FIX")


def sleeper_fetch(url: str) -> bytes:
    if url.endswith("/state/nfl"):
        return b'{"week":3,"season":"2026","season_type":"regular"}'
    if "/stats/" in url:
        return json.dumps({"11": {"pts_ppr": 18.5, "pts_half_ppr": 15.5, "pts_std": 12.5}}).encode()
    return b"{}"


def write_catalog(path: Path, *, follows: list[str], extra: dict | None = None) -> None:
    competitions = [
        {
            "id": "mlb",
            "family": "baseball",
            "name": "Major League Baseball",
            "tier": "live",
            "source_id": "mlb-stats",
            "source_name": "MLB Stats API",
            "kind": "mlb-schedule",
            "fetch": "https://statsapi.mlb.com/api/v1/schedule?sportId=1",
            "note": "test",
        }
    ]
    if extra is not None:
        competitions.append(extra)
    path.mkdir(parents=True, exist_ok=True)
    (path / "competitions.json").write_text(
        json.dumps({"checked": "2026-09-23", "note": "test", "competitions": competitions}),
        encoding="utf-8",
    )
    (path / "follows.json").write_text(
        json.dumps({"competitions": follows, "sports": [], "competitors": []}),
        encoding="utf-8",
    )
    (path / "roster.json").write_text(
        json.dumps({"scoring": "ppr", "starters": [None] * 9, "bench": [], "pins": []}),
        encoding="utf-8",
    )
