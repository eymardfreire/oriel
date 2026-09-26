import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from oriel_server.config import Config, HomePlace, MarketsConfig, SportsConfig, TradeConfig, WeatherConfig, WiresConfig
from oriel_server.main import create_app
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
        "bundesliga-2": "delayed",
        "premier-league": "delayed",
        "la-liga": "delayed",
        "champions-league": "delayed",
        "serie-a": "delayed",
        "ligue-1": "delayed",
        "brasileirao": "delayed",
        "nfl": "delayed",
        "nba": "delayed",
        "cfl": "delayed",
        "nrl": "delayed",
        "liga-3": "far",
        "npb": "far",
    }
    premier = next(item for item in competitions if item.id == "premier-league")
    assert premier.season_start == "2026-08-21"
    assert premier.season_end == "2027-05-30"
    assert "esports" not in {item.family for item in competitions}
    follows = json.loads((REPO / "catalog" / "sports" / "follows.json").read_text(encoding="utf-8"))
    known = {item.id for item in competitions}
    assert set(follows) == {"competitions", "sports", "competitors"}
    assert set(follows["competitions"]) <= known
    assert isinstance(follows["sports"], list)
    assert isinstance(follows["competitors"], list)


def test_follow_row_carries_the_season_window_and_active_flag(tmp_path: Path) -> None:
    write_catalog(
        tmp_path,
        follows=[],
        extra={
            "id": "premier-league",
            "family": "football",
            "name": "Premier League",
            "country": "England",
            "season": "2026/2027",
            "season_start": "2026-08-21",
            "season_end": "2027-05-30",
            "tier": "delayed",
            "source_id": "openligadb",
            "source_name": "OpenLigaDB",
            "kind": "openligadb",
            "fetch": "https://api.openligadb.de/getmatchdata/pl/2026",
            "note": "test",
        },
    )
    poller = SportsPoller(tmp_path, fetcher=lambda url: FAILED, now=lambda: WHEN)
    poller.refresh()
    fields = {item["title"]: item["fields"] for item in poller.panel("field-follows")["items"] if item["row"] == "follow"}
    assert fields["Premier League"]["season_start"] == "2026-08-21"
    assert fields["Premier League"]["season_end"] == "2027-05-30"
    assert fields["Premier League"]["flag"] == "active"
    assert "flag" not in fields["Major League Baseball"]


def test_thesportsdb_keeps_one_event_and_a_source_clock() -> None:
    from oriel_server.sports.catalog import Competition
    from oriel_server.sports.scores import parse_competition

    competition = Competition(
        id="nfl",
        family="american-football",
        name="NFL",
        tier="delayed",
        source_id="thesportsdb",
        source_name="TheSportsDB",
        kind="thesportsdb",
        fetch="https://example.test/next",
        note="test",
        country="United States",
        season="2026",
    )
    payload = json.dumps(
        {
            "events": [
                {
                    "idEvent": "1",
                    "strHomeTeam": "Atlanta Falcons",
                    "strAwayTeam": "Green Bay Packers",
                    "dateEvent": "2026-09-25",
                    "strStatus": "NS",
                    "intHomeScore": None,
                    "intAwayScore": None,
                },
                {
                    "idEvent": "1",
                    "strHomeTeam": "Atlanta Falcons",
                    "strAwayTeam": "Green Bay Packers",
                    "dateEvent": "2026-09-25",
                    "strStatus": "NS",
                },
                {
                    "idEvent": "2",
                    "strHomeTeam": "Home",
                    "strAwayTeam": "Away",
                    "strTimestamp": "2026-09-23T18:00:00",
                    "strStatus": "1H",
                    "strProgress": "12:04",
                    "intHomeScore": "7",
                    "intAwayScore": "3",
                },
            ]
        }
    ).encode()
    rows = parse_competition(competition, payload, WHEN)
    assert len(rows) == 2
    live = next(row for row in rows if row.state == "in progress")
    assert live.score == "7-3"
    assert live.clock == "12:04"


def test_openligadb_keeps_a_near_fixture_and_drops_the_rest_of_the_season() -> None:
    from oriel_server.sports.catalog import Competition
    from oriel_server.sports.scores import parse_competition

    competition = Competition(
        id="premier-league",
        family="football",
        name="Premier League",
        tier="delayed",
        source_id="openligadb",
        source_name="OpenLigaDB",
        kind="openligadb",
        fetch="https://example.test/pl",
        note="test",
    )
    payload = json.dumps(
        [
            {
                "team1": {"teamName": "Sunderland"},
                "team2": {"teamName": "Manchester City"},
                "matchDateTime": "2027-05-30T15:00:00",
                "matchIsFinished": False,
            },
            {
                "team1": {"teamName": "Arsenal"},
                "team2": {"teamName": "Chelsea"},
                "matchDateTime": "2026-09-26T14:00:00",
                "matchIsFinished": False,
            },
        ]
    ).encode()
    rows = parse_competition(competition, payload, WHEN)
    assert [row.home for row in rows] == ["Arsenal"]
    assert rows[0].state.startswith("scheduled")
    assert rows[0].score is None


def test_season_flag_follows_the_source_window_or_a_recent_game() -> None:
    from oriel_server.sports.poller import _season_flag

    competitions = {item.id: item for item in load_competitions(REPO / "catalog" / "sports" / "competitions.json")}
    assert _season_flag(competitions["nfl"], WHEN) == "active"
    assert _season_flag(competitions["nba"], WHEN) == "off season"
    assert _season_flag(competitions["premier-league"], WHEN) == "active"
    assert _season_flag(competitions["nfl"], WHEN, nfl={"phase": "off", "start": "2026-09-09"}) == "off season"


def test_far_desk_names_why_it_is_empty_when_no_far_tier_exists(tmp_path: Path) -> None:
    write_catalog(tmp_path, follows=[])
    poller = SportsPoller(tmp_path, fetcher=lambda url: FAILED, now=lambda: WHEN)
    poller.refresh()
    panel = poller.panel("far-desk")
    assert panel["items"][0]["title"] == "No far-coverage competition is configured"
    assert all(item["row"] != "score" for item in panel["items"])


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


def test_follow_unfollow_and_unknown_id(tmp_path: Path) -> None:
    write_catalog(tmp_path, follows=[])
    follows_path = tmp_path / "follows.json"
    roster_path = tmp_path / "roster.json"
    roster_before = roster_path.read_text(encoding="utf-8")
    seen: list[str] = []

    def fetch(url: str) -> bytes:
        seen.append(url)
        return json.dumps(MLB).encode()

    poller = SportsPoller(tmp_path, fetcher=fetch, now=lambda: WHEN)
    follows_path.write_text(
        json.dumps({"competitions": [], "sports": [], "competitors": []}),
        encoding="utf-8",
    )
    config = Config(
        bind_host="127.0.0.1",
        bind_port=8787,
        home_place=HomePlace(id="home", name="unset"),
        wires=WiresConfig(enabled=False),
        markets=MarketsConfig(enabled=False),
        trade=TradeConfig(enabled=False),
        weather=WeatherConfig(enabled=False),
        sports=SportsConfig(enabled=False),
    )
    client = TestClient(create_app(config, sports_poller=poller))
    before = follows_path.read_text(encoding="utf-8")
    rejected = client.post("/bays/field/follows", json={"competition_id": "nope", "follow": True})
    assert rejected.status_code == 400
    assert follows_path.read_text(encoding="utf-8") == before
    assert seen == []
    assert roster_path.read_text(encoding="utf-8") == roster_before

    followed = client.post("/bays/field/follows", json={"competition_id": "mlb", "follow": True})
    assert followed.status_code == 200
    written = json.loads(follows_path.read_text(encoding="utf-8"))
    assert written == {"competitions": ["mlb"], "sports": [], "competitors": []}
    assert any("statsapi.mlb.com" in url for url in seen)
    scores = followed.json()["panels"][0]
    assert scores["items"][0]["fields"]["score"] == "0-1"
    assert scores["items"][0]["title"] != "Choose follows"
    choices = followed.json()["panels"][1]["items"]
    assert choices[0]["row"] == "follow"
    assert choices[0]["fields"]["competition_id"] == "mlb"
    assert choices[0]["fields"]["followed"] is True
    assert "score" not in choices[0]["fields"]
    assert roster_path.read_text(encoding="utf-8") == roster_before

    seen.clear()
    dropped = client.post("/bays/field/follows", json={"competition_id": "mlb", "follow": False})
    assert dropped.status_code == 200
    written = json.loads(follows_path.read_text(encoding="utf-8"))
    assert written == {"competitions": [], "sports": [], "competitors": []}
    assert seen == []
    assert dropped.json()["panels"][0]["items"][0]["title"] == "Choose follows"
    assert all(item["row"] != "score" for item in dropped.json()["panels"][0]["items"])
    assert dropped.json()["panels"][1]["items"][0]["fields"]["followed"] is False

    follows_path.write_text(
        json.dumps({"competitions": ["mlb"], "sports": ["baseball"], "competitors": ["Fixture Home"]}),
        encoding="utf-8",
    )
    poller.follow("mlb", False)
    written = json.loads(follows_path.read_text(encoding="utf-8"))
    assert written == {"competitions": [], "sports": ["baseball"], "competitors": ["Fixture Home"]}


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


def test_standings_keep_only_reported_figures() -> None:
    from oriel_server.sports.standings import parse_standings

    rows = parse_standings("openligadb", b'[{"teamName":"Borussia Dortmund","points":10},{"shortName":"Bayern"}]')
    assert rows[0] == {"rank": "1", "team": "Borussia Dortmund", "line": "10 pts"}
    assert rows[1]["team"] == "Bayern"
    assert rows[1]["line"] == ""


def test_sideline_starts_most_relevant_and_can_keep_one_sport(tmp_path: Path) -> None:
    from oriel_server.sports.news import SidelinePoller

    news = tmp_path / "news"
    news.mkdir()
    for sport, title in (("cricket", "Cricket story"), ("football", "Football story")):
        (news / f"{sport}.json").write_text(
            json.dumps(
                {
                    "id": sport,
                    "name": "Feed",
                    "sport": sport,
                    "sport_name": sport.title(),
                    "fetch": f"https://example.test/{sport}",
                    "enabled": True,
                }
            ),
            encoding="utf-8",
        )

    def fetch(url: str) -> bytes:
        title = "Cricket story" if url.endswith("cricket") else "Football story"
        return f"""<?xml version="1.0"?><rss><channel><item>
          <title>{title}</title><link>{url}</link><guid>{title}</guid>
          <description>Hello there</description>
          <pubDate>Wed, 23 Sep 2026 18:00:00 GMT</pubDate>
        </item></channel></rss>""".encode()

    poller = SidelinePoller(news, tmp_path / "sideline.json", fetcher=fetch, now=lambda: WHEN)
    poller.refresh()
    headlines = poller.panels()[0]
    assert headlines["title"] == "Most relevant"
    assert {item["title"] for item in headlines["items"]} == {"Cricket story", "Football story"}
    assert headlines["items"][0]["fields"]["summary"] == "Hello there"
    poller.focus("cricket", True)
    kept = poller.panels()[0]["items"]
    assert [item["title"] for item in kept] == ["Cricket story"]
    picker = poller.panels()[1]["items"]
    relevant = next(item for item in picker if item["fields"]["sport"] == "relevant")
    assert relevant["fields"]["followed"] is False
    import pytest

    with pytest.raises(ValueError):
        poller.focus("nope", True)
