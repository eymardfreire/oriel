## Context

The client paints one bay per process. Markets, wires, trade, and storm use `stack`, so a wide terminal is a short column and a dark field. Theme and layout are flags. The suggestion line is three tokens. Weather observations carry temperature and a condition word from Open-Meteo. The client never calls upstream sources.

The terminal reports columns and rows, not pixels. A fullscreen 16:9 window has more cells as the monitor and the font allow it. That cell grid is the density signal.

## Goals / Non-Goals

**Goals:**

- One board process can show several existing bays and let the operator turn bays on and off.
- Wider and taller terminals show more columns and more rows.
- The screen moves: clock, relative ages, a live mark, a change bar drawn from the quote change already in the payload.
- Night is easier to read. Theme and board membership are choosable inside the window.
- Weather glyphs and extra observation numbers come only from fields the payload already has.

**Non-Goals:**

- Tiling OS windows. Named desks still launch one process per bay.
- New outlets, market sources, sports competitions, or a situation domain.
- Historical sparklines. The bar is the current change, not a series we do not have.
- Detecting physical resolution or DPI.

## Decisions

### Board is a client composition, not a new domain

`-board` loads the shipped bay catalog and fetches each selected bay from the existing `/bays/{id}` routes. The default selection is wires, markets, storm, and trade. Preferences live in `client/state/board.json`, gitignored. If that file is missing or unreadable, the default selection is used and the board still opens.

Failure mode: a bay the server cannot serve keeps its fixture or empty state for that bay only. The other bays stay.

### Density is a cell-grid table

| Columns | Band | Columns of panels |
| --- | --- | --- |
| under 100 | narrow, including a small 1080p window | 1 |
| 100–159 | 1080p fullscreen at a typical font | 2 |
| 160–239 | 1440p 16:9, and most 16:10 widths | 3 |
| 240 and up | 4K fullscreen, and a future 21:9 band | 4 |

Rows left after the status line are split across the panel rows. Extra height, which 16:10 has relative to 16:9 at the same width, shows more items. `strip` stays one horizontal row. A single bay uses the same bands so `go run . -bay markets` fills a wide window.

### Status line and settings overlay

One line, always: local clock, live or stale, focused title, suggestion sentence, key hints. It does not repeat the OS window title. `?` toggles an overlay listing shipped themes and, on a board, the bays with a mark for the ones shown. `t` cycles theme for this window only. `j` and `k` move the focused panel. `a` still applies the suggestion by launching that desk.

### Night palette

`catalog/themes/night.json` keeps the same roles. Ground goes blue-black, text brighter, up and down further apart, accent used for the focused border and the status line. Other shipped themes are unchanged.

### Weather payload

The weather domain still owns the payload. The same Open-Meteo forecast URL adds `apparent_temperature`, `relative_humidity_2m`, and `wind_speed_10m` on `current`. The observation item gains `apparent_temperature_c`, `humidity_pct`, and `wind_speed_kmh` only when the parser reads a number. The client maps the existing condition word to a glyph. A missing condition has no glyph. A missing extra field is omitted.

### Quote bar

The markets row already has `change`. The client draws up to eight block characters from the absolute change, capped so a large move does not overflow the row. No change, or a missing change, draws no bar. The signed number and the `up` or `down` role stay.

### Live mark

A one-second tick rewrites relative ages from `updated_at` and `observed_at`. A panel updated within its bay refresh interval shows a filled mark. Older than that, still not stale, shows an open mark. Stale keeps the existing stale marker.

## Risks / Trade-offs

- [Cell counts depend on the terminal font] → Bands are documented as typical fullscreen sizes, not as a promise about a monitor model.
- [Board preferences on disk] → Unreadable file falls back to the default selection. The file is local state, not catalog.
- [Emoji width in Windows terminals] → Glyphs are a prefix. If a terminal draws one as two cells, the row wraps inside the panel rather than shifting other panels.
- [Richer night breaks the old hex test] → The test is updated to the new night roles. Role names do not change.

## Migration Plan

No server migration. Old clients ignore the new observation fields. Rollback is reverting the client and the night palette. Board state can be deleted.

## Open Questions

None. 21:9 uses the 240-column band until a later change adds a fifth column.
