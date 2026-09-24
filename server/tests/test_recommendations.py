from datetime import datetime, timezone

from oriel_server.recommendations.rank import Snapshot, rank

PANELS = {
    "markets": ("markets",),
    "fantasy": ("fantasy",),
    "storm": ("storm",),
    "wires": ("wires",),
    "brief": ("brief",),
    "three": ("wires", "markets", "field"),
}


def test_new_york_session_favors_markets() -> None:
    suggestion = rank(Snapshot(now=_at(15, 0)), PANELS)
    assert suggestion.desk_id == "markets"
    assert "New York" in suggestion.reason
    assert "session" in suggestion.reason


def test_fantasy_game_on_a_closed_market_day_names_the_player() -> None:
    suggestion = rank(Snapshot(now=_at(22, 0), fantasy_player="Scorer"), PANELS)
    assert suggestion.desk_id == "fantasy"
    assert suggestion.reason == "Scorer is in progress"


def test_open_session_is_not_demoted_by_a_fantasy_game() -> None:
    suggestion = rank(Snapshot(now=_at(15, 0), fantasy_player="Scorer"), PANELS)
    assert suggestion.desk_id == "markets"


def test_severe_alert_raises_storm_and_names_the_alert() -> None:
    idle = rank(Snapshot(now=_at(22, 0)), PANELS)
    raised = rank(
        Snapshot(now=_at(22, 0), alert_severity="Severe", alert_headline="Severe thunderstorm warning"),
        PANELS,
    )
    assert idle.desk_id != "storm"
    assert raised.desk_id == "storm"
    assert raised.reason == "Severe thunderstorm warning"


def test_pinned_bay_beats_an_open_session() -> None:
    suggestion = rank(Snapshot(now=_at(15, 0), pinned_bay="wires"), PANELS)
    assert suggestion.desk_id == "wires"
    assert suggestion.reason == "wires is pinned"


def test_dismissal_skips_the_computed_desk() -> None:
    suggestion = rank(Snapshot(now=_at(15, 0), dismissed=("markets",)), PANELS)
    assert suggestion.desk_id != "markets"


def test_stale_desk_sinks_behind_a_follow() -> None:
    suggestion = rank(
        Snapshot(now=_at(15, 0), sports_follows=True, stale_desks=("markets",)),
        {**PANELS, "field": ("field",)},
    )
    assert suggestion.desk_id == "field"


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, 23, hour, minute, tzinfo=timezone.utc)
