## Context

`live-board` added `-board`, width bands, a status line, settings, weather detail, and quote bars. It places every panel of every bay into one flat grid, so a bay has no area of its own. The mark in a panel header compares `updated_at` with the client bay refresh. Markets refreshes every 30 seconds in the client and the server polls every 60, so the mark alternates. `a` calls the desk launcher, which starts new console windows and pipes their stdout into the board.

## Goals / Non-Goals

**Goals:**

- Each bay owns a rectangle. The rectangle decides how much of that bay is drawn.
- Summarized bays rotate through all of their items, so nothing is permanently hidden.
- Up to nine saved layouts.
- More data per domain from verified public sources.
- A global weather view.

**Non-Goals:**

- Tiling OS windows.
- The `situation` domain.
- Paid sources or logins. A key is used only if the operator supplies one.
- Maps drawn from tiles. The weather view is a region grid, not a raster map.

## Decisions

### Bay rectangles

| Bays shown | Arrangement |
| --- | --- |
| 1 | full screen |
| 2–4 | one column each, full height |
| 5–8 | four columns, two rows |
| 9–12 | four columns, three rows |

The band rule from `live-board` still caps columns by terminal width. A half-screen window at 1080p gets two columns, so four bays become two by two. Inside its rectangle a bay lays out its own panels with the same width bands.

### Detail levels

A bay renders at `full`, `compact`, or `summary` from its rectangle size. `full` shows every panel and every item that fits. `compact` shows every panel with fewer items. `summary` shows one panel at a time. A summarized or compact bay rotates: every 8 seconds it advances to the next page of items, or the next panel in `summary`. The page position is shown as `2/5` in the bay header. Rotation pauses on the focused bay while `j` and `k` are in use.

### Saved layouts

`client/state/board.json` gains `layouts`, an array of up to nine entries with `bays` and `theme`. `s` then a digit saves the current board to that slot. A digit on the board, outside settings, loads that slot. `[` and `]` cycle occupied slots. An empty slot does nothing and the status line says it is empty. The selected slot number is shown in the status line.

### Suggestion and `a`

The suggestion is hidden when every bay in the suggested desk is already on the board, or when a single-bay window is that bay. On a board, `a` replaces the board bays with the desk bays and leaves the saved layouts alone. A single-bay window keeps the launcher. The launcher detaches child stdout and stderr so nothing prints into an alt-screen view.

### Live mark

Each panel payload gains `refresh_seconds`, the server poll interval for its domain. The mark is filled when the age is within that interval plus a 10-second margin. An older mark is hollow, and stale stays stale. When the field is absent the client falls back to the bay refresh.

### New data

Every new source follows the foundation rule: fetch it live, record the date and what it is in the catalog and README, and omit it if it does not answer. Candidates, checked in the first pass of each domain:

- Wires: Al Jazeera, DW, France 24, Reuters-hosted public RSS where it exists, AP where it exists, NHK World, ABC Australia, CBC. RSS `description` becomes `summary` on a headline row, stripped of HTML and trimmed.
- Markets: more indices (FTSE, DAX, Nikkei, Hang Seng), more large caps, more FX pairs from Frankfurter, more Treasury tenors, silver and natural gas, a few more coins.
- Trade: public port, shipping, and customs feeds that answer without a key.
- Weather: about 40 world cities across North America, South America, Europe, Africa, the Middle East, Asia, and Oceania, as `"home": false` rows in `catalog/weather/places.json`. Open-Meteo accepts multiple coordinates in one request. NWS alerts only cover the United States; other regions show "no public alert source" rather than "no alerts". The weather bay groups by region and adds a hottest, coldest, wettest, and windiest strip computed from the fetched values only.
- Sports: follows written by the client through a new `POST /bays/field/follows` route to `catalog/sports/follows.json`. More competitions only if a public source is verified.

Failure mode for all of it is unchanged: a failed source keeps its last good payload and marks the panel stale, and a source that never answered produces no rows.

## Risks / Trade-offs

- [Upstream rate limits with many cities] → One Open-Meteo request per batch of places, and the existing 300-second weather poll.
- [Feeds without summaries] → Summary is omitted, not synthesized.
- [Rotation hides the item you were reading] → The focused bay pauses rotation.
- [Catalog writes from the client] → Only the follows file, only through the server route, validated against the competition catalog.

## Open Questions

- Which of the wire candidates answer from the Omarch machine. Resolved in the wires pass.
