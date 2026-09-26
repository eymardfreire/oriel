## Why

`f` already chooses field follows and, when Sideline is the focused bay, which sports to keep. On any other cell it still opens the field list, or it says the field bay is not open. Brief always takes the home observation, the first wire, and the first quote, with no way to change them. Far Desk is wired and live; the catalog simply has no `far` competition, so the bay says so. This change belongs to the client keys and the brief, sideline, and far desks.

## What Changes

- `f` refines the focused bay and only that bay. Field opens follows. Sideline opens sports. The status line names that action. A bay with nothing to choose does not advertise `f`, and pressing it does not open another bay's list.
- Brief gains the same kind of choice: a place, a wire outlet, and a market family. Unset stays today's strip: the configured home (Tampa), the first live headline, and the first live quote. A chosen place does not become a home, and storm still watches every place.
- Far Desk keeps the empty sentence until a public far-tier source answers a live check. One that answers is added under the existing far rules. One that does not answer is left out. Nothing is invented.
- A sweep records which other bays still have no in-client choice (fantasy roster, market selection, trade families, wire outlets, storm places). This change does not add those pickers.

## Capabilities

### New Capabilities

- `refine`: `f` refines the focused bay. Field, Sideline, and Brief each have a list. Other bays do not borrow Field's list.

### Modified Capabilities

- `weather`: Brief may show one chosen place from the shipped catalog. With no choice, it still shows the configured home. Watched places stay off Brief until chosen, and choosing one does not mark it home.

## Impact

- Client key handling and the status hint in `client/chrome.go` and `client/main.go`. Brief composition in `client/live.go`.
- A brief selection file and a small write route, on the same pattern as field follows and sideline focus. Weather, wires, and markets payloads are read, not redefined.
- Far catalog entries only after a live fetch, recorded in the catalog and the README.
- `client/state/board.json` and `catalog/sports/follows.json` stay as the operator left them.
