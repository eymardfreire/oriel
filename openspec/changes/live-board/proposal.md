## Why

A bay today is a quiet stack of boxes in a mostly empty terminal. The operator cannot tell what is fresh, cannot change theme or layout without a flag, and cannot fill one monitor with the bays they care about. This change belongs to the client presentation of the existing desk: same sources, a live board.

## What Changes

- A board is one fullscreen terminal that places several bays the operator chooses. Starting a named desk still opens one process per bay.
- The client reads terminal columns and rows and shows more columns and more rows on a larger cell grid. 16:9 fullscreen is the target. 16:10 uses the extra rows. 21:9 is a later width band, not a separate product.
- The default `night` palette is retuned. The operator can cycle the shipped themes from the bay. Themes stay per window.
- A single status line shows the clock, a live mark, the focused bay, a plain-language suggestion, and the keys that do something. `?` opens settings for theme and, on a board, which bays are shown.
- Weather rows use a glyph for the condition the source already named, and show humidity, wind, and feels-like only when Open-Meteo sent them. Missing numbers stay blank.
- Quote rows keep the price and the signed change, and add a short magnitude bar drawn from that change. Ages update every second. Nothing new is fetched from a market source.

## Capabilities

### New Capabilities

- `board`: One window composes selected bays, scales with the terminal cell grid, and exposes theme and bay choices.

### Modified Capabilities

- `themes`: The default night palette changes. A window can switch among shipped themes without a new process. A status line and a settings overlay are allowed. Panels stay hairline and do not repeat the window title.
- `desks`: A board is an additional way to view bays. Named desks still start one process per bay and still do not tile OS windows.
- `recommendations`: The suggestion line states the desk, the reason, and that applying it is a keypress. Panels do not change until the operator applies it.
- `weather`: An observation may show humidity, wind, and apparent temperature when the existing Open-Meteo response includes them, plus a glyph for the condition word. Absent fields are omitted.

## Impact

- Client rendering, key handling, and a local preference file for the board. No new upstream source.
- Open-Meteo current-weather fields already on the same request: apparent temperature, humidity, wind.
- Theme catalog `night`. Server weather item fields. Existing desk launch behavior stays.
