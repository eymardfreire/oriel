"""Oriel's NFL roster. Select, pin, and flex are separate actions."""

from __future__ import annotations

from oriel_server.sports.catalog import FLEX_POSITIONS, LINEUP_SLOTS, SCORING, Player, Roster


def select_player(roster: Roster, player: Player) -> Roster:
    if _on_roster(roster, player.id):
        return roster
    slot = _open_slot(roster, player.position)
    if slot is None:
        roster.bench.append(player)
        return roster
    roster.starters[slot] = player
    return roster


def assign_flex(roster: Roster, player_id: str) -> Roster:
    flex = LINEUP_SLOTS.index("FLEX")
    if roster.starters[flex] is not None:
        return roster
    player = next((item for item in roster.bench if item.id == player_id), None)
    if player is None or player.position not in FLEX_POSITIONS:
        return roster
    roster.bench = [item for item in roster.bench if item.id != player_id]
    roster.starters[flex] = player
    return roster


def pin_player(roster: Roster, player: Player) -> Roster:
    roster.pins = [player, *[item for item in roster.pins if item.id != player.id]]
    return roster


def unpin_player(roster: Roster, player_id: str) -> Roster:
    roster.pins = [item for item in roster.pins if item.id != player_id]
    return roster


def drop_player(roster: Roster, player_id: str) -> Roster:
    roster.starters = [None if player is not None and player.id == player_id else player for player in roster.starters]
    roster.bench = [item for item in roster.bench if item.id != player_id]
    return roster


def set_scoring(roster: Roster, scoring: str) -> Roster:
    if scoring not in SCORING:
        raise ValueError("scoring must be ppr, half-ppr, or standard")
    roster.scoring = scoring
    return roster


def _on_roster(roster: Roster, player_id: str) -> bool:
    if any(player is not None and player.id == player_id for player in roster.starters):
        return True
    return any(player.id == player_id for player in roster.bench)


def _open_slot(roster: Roster, position: str) -> int | None:
    for index, slot in enumerate(LINEUP_SLOTS):
        if slot == "FLEX" or slot != position:
            continue
        if roster.starters[index] is None:
            return index
    return None
