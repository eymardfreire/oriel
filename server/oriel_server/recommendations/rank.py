"""Score desks from session, follows, alerts, freshness, and fantasy games."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

DESKS = ("brief", "wires", "markets", "field", "storm", "trade", "far", "fantasy", "three")
# Cash-session windows in UTC. New York is listed first so an overlap names New York.
SESSIONS = (
    ("New York", time(14, 30), time(21, 0)),
    ("London", time(8, 0), time(16, 30)),
    ("Asia", time(0, 0), time(6, 0)),
)


@dataclass(frozen=True)
class Snapshot:
    now: datetime
    sports_follows: bool = False
    alert_severity: str = ""
    alert_headline: str = ""
    stale_desks: tuple[str, ...] = ()
    fantasy_player: str = ""
    pinned_bay: str = ""
    dismissed: tuple[str, ...] = ()


@dataclass(frozen=True)
class Suggestion:
    desk_id: str
    reason: str
    panels: tuple[str, ...]


def open_session(now: datetime) -> str:
    clock = now.time()
    for name, start, end in SESSIONS:
        if start <= clock < end:
            return name
    return ""


def rank(snapshot: Snapshot, panels_for: dict[str, tuple[str, ...]]) -> Suggestion:
    scores = {desk: 0 for desk in DESKS}
    reasons: dict[str, str] = {}
    session = open_session(snapshot.now)
    if session:
        scores["markets"] += 50
        reasons["markets"] = f"{session} session is open"
    severity = snapshot.alert_severity.casefold()
    if snapshot.alert_headline and severity:
        if severity in {"severe", "extreme"}:
            scores["storm"] += 80
        else:
            scores["storm"] += 25
        reasons["storm"] = snapshot.alert_headline
    if snapshot.fantasy_player:
        scores["fantasy"] += 40 if session else 60
        reasons["fantasy"] = f"{snapshot.fantasy_player} is in progress"
    if snapshot.sports_follows:
        scores["field"] += 20
        reasons["field"] = "A follow is active"
    for desk in snapshot.stale_desks:
        if desk in scores:
            scores[desk] -= 70
    pinned = snapshot.pinned_bay
    if pinned in scores:
        scores[pinned] = 1000
        reasons[pinned] = f"{pinned} is pinned"
    for desk in snapshot.dismissed:
        if desk in scores and desk != pinned:
            scores[desk] = -1000
    desk_id = max(DESKS, key=lambda desk: (scores[desk], -DESKS.index(desk)))
    if scores[desk_id] <= 0 and not pinned:
        desk_id = "brief"
        reason = "No session, alert, or follow is active"
    else:
        reason = reasons.get(desk_id, "Oriel ranking")
    ordered = _order(panels_for.get(desk_id, (desk_id,)), snapshot.stale_desks)
    return Suggestion(desk_id=desk_id, reason=reason, panels=ordered)


def _order(panels: tuple[str, ...], stale: tuple[str, ...]) -> tuple[str, ...]:
    sunk = set(stale)
    fresh = tuple(panel for panel in panels if panel not in sunk)
    late = tuple(panel for panel in panels if panel in sunk)
    return fresh + late
