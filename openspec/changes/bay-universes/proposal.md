## Why

The live board works, but every bay is a few boxes of the same size, so one bay alone wastes the screen and many bays feel thin. The suggestion line says the same thing everywhere, and `a` only opens more windows. Field and Far Desk look broken because their catalogs are empty. This change belongs to the desk and domain sections: each bay becomes a complete view that grows or shrinks with the space it gets, and the board gains saved layouts.

## What Changes

- A bay is a "universe": alone on the board it fills the screen with its full data set. Each added bay splits the width, up to four columns. After four columns, rows split, and each bay shows a summary that rotates through its full set.
- The operator can save the current board as one of nine layouts and cycle or jump between them.
- Wires, markets, trade, and sports get more sources and richer rows: headline plus summary text when the feed has one, more instruments, more feeds. Each new source is checked live before it ships.
- Weather becomes a global monitor: a curated set of world cities, grouped by region, with current conditions, a forecast strip, and alerts where a public source exists.
- Field gets a follows picker in the client, so it stops saying "Choose follows" with no way to choose. Far Desk states why it is empty until a far-tier competition is verified.
- The suggestion is hidden when it names what is already on screen. On a board, `a` swaps the board to the suggested desk instead of opening new windows. Launched child processes no longer write into the board's screen.
- The live mark compares against the server poll interval for that domain, so it stops blinking between filled and open on every client refresh.

## Capabilities

### New Capabilities

- `layouts`: Saved board layouts, one to nine, with save, cycle, and jump.

### Modified Capabilities

- `board`: Space allocation by bay count, rotation of a bay's full data set when it is summarized, live-mark rule, `a` on a board.
- `wires`: More outlets and summary text on a headline row.
- `markets`: A larger shipped instrument list per family.
- `trade`: More public trade feeds.
- `weather`: Global watched places grouped by region.
- `sports`: Follows chosen from the client. Far Desk empty state names the reason.
- `recommendations`: Suggestion hidden when it matches the current view.

## Impact

- Client layout engine, key handling, prefs file (`client/state/board.json` grows a `layouts` list).
- Server: new catalog entries for outlets, instruments, trade feeds, weather places. A follows write endpoint for sports.
- New public sources, each verified with a live fetch and recorded in the catalog and README. No API key unless the operator supplies one.
