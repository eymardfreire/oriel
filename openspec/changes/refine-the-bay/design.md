## Context

Field follows and Sideline sports already use `f`. The client opens Sideline only when that bay is focused, or when Field is absent and Sideline is on the board. Every other case opens Field, or reports that Field is not open. The status line always says `f follows`.

Brief is composed in the client from server payloads. Weather keeps items with `home: true` (Tampa, from `server/config.toml`). Wires and markets each contribute the first item of the first panel. There is no selection file. Far Desk reads competitions tiered `far`. The shipped catalog has none, so the panel title is "No far-coverage competition is configured".

The operator's board file and follow list stay put. The server remains the only process that calls upstream sources and the only process that writes catalog files.

## Goals / Non-Goals

**Goals:**

- One key, `f`, bound to the focused bay.
- Brief can choose a place, a wire outlet, and a market family, with today's strip as the default.
- Far Desk gains a competition only when a public source answers.
- A written sweep of bays that still have no in-client choice.

**Non-Goals:**

- A second refine key.
- A picker for fantasy, markets, trade, wires, or storm.
- Changing which competitions Field follows, or resetting `client/state/board.json`.
- Inventing a far result, a quote, or a temperature.
- Marking a watched place as home because Brief shows it.

## Decisions

### Same `f`, focused bay only

`f` looks at the focused bay:

| Focused bay | Overlay | Status hint |
| --- | --- | --- |
| field | shipped competitions, follow or drop | `f follows` |
| sideline | shipped sports, keep or drop, plus Most relevant | `f sports` |
| brief | place, outlet, and family | `f brief` |
| anything else | none | `f` is omitted |

Pressing `f` on a bay with no list sets a notice that the bay has nothing to choose and leaves every other picker closed. Field's list no longer opens from Brief, Far, or Wires.

Alternative considered: a different key per bay. Rejected. Field and Sideline already share `f`, and a second key would hide Sideline again.

### Brief selection is a catalog file

`catalog/brief/selection.json` holds three strings: `place`, `outlet`, and `family`. An empty string is the default for that slot.

| Slot | Empty means | Chosen means |
| --- | --- | --- |
| place | the configured home | that place's observation |
| outlet | the first live headline | the newest headline from that outlet |
| family | the first live quote | the first quote in that family |

The quote stays one line: symbol, price, change, delayed mark. The family choice does not pick a single symbol, because the market list is too long for this overlay. The printed symbol is whichever instrument leads that family.

`POST /bays/brief/selection` writes the file. The body names the slot and the id. An id that is not in the place catalog, the enabled wire outlets, or the market families is rejected and the file stays unchanged. The empty id selects the default for that slot.

The client still composes Brief from the weather, wires, and markets payloads. After a save it applies the selection to those payloads. It does not call Open-Meteo, RSS, or Yahoo.

Failure mode, per slot:

- Server rejects the id: notice, previous selection remains.
- Server unreachable: notice, the strip already on screen stays.
- Chosen place has no observation: the weather row stays on the fixture or the last good home row. No temperature is filled in.
- Chosen outlet has no headline: the wire row stays. No headline is written.
- Chosen family has no quote, or the quote has no price: the row is kept only when a last good quote exists; a missing price stays blank.

Choosing a place does not set `home` on that place. Storm still lists every watched place. Brief's weather panel stays the numeric observation. Weather news stays off Brief.

The overlay reuses the field picker: `j` and `k` move, a number jumps, enter selects. Each section is a radio. The first row of a section is its default.

### Far Desk stays a catalog, not a picker

The far panel already lists every `far` competition. This change does not add a follow file for it. The pass tries a few public result, schedule, or report sources that fit the existing far row (competitors and result, or a sourced excerpt). A source that returns a parseable fact is added to `catalog/sports/competitions.json` with tier `far`, the check date in the catalog note and the README. A source that fails, or that the current sports fetcher cannot read, is omitted. If none answer, the empty sentence stays, and that is the completed pass.

`f` on Far Desk says the bay has nothing to choose. Once a competition is in the catalog it shows without a picker, which is the existing far rule.

### Sweep is a note, not a build

After the three passes, record in the handoff which bays still cannot be refined from the client: fantasy roster and pins, market instrument selection, trade family selection, the wire outlet set, and the storm place list. Do not add keys for them in this change.

## Risks / Trade-offs

- [Pressing `f` on Brief used to open Field when Field was also on the board] → The status hint changes with focus, and the notice names the bay that has nothing to choose.
- [A long place list] → The same number-jump as the field picker. Enter confirms when a digit can still grow.
- [Brief shows a city storm also shows] → The strip is one observation. Storm's grouping is unchanged, and the place is not marked home.
- [A far source looks plausible but does not parse] → Leave it out. The empty sentence is the correct panel.
- [Catalog writes] → Only `catalog/brief/selection.json`, only through the server, validated against catalogs that already exist.

## Migration Plan

Ship an empty selection file so every existing Brief keeps Tampa, the first headline, and the first quote. No change to `client/state/board.json` or `catalog/sports/follows.json`. Rolling back is deleting the selection file and the route; Brief returns to the first-item composition.

## Open Questions

None. The quote slot is a family, not a symbol. Far sources are settled by the live check, not in advance.
