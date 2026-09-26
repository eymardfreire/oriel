## Why

A bay still leaves most of a large window empty, and the rows that do show spend lines on repetition instead of the data already fetched. Markets pages through tickers while the rest of the cell is blank. Storm lists a handful of cities and a stack of "no public alert source" lines. Weather news shows headlines only, even when the feed carried a description. The operator wants one tightness rule for the whole board before any later application is considered.

## What Changes

- A bay spends the lines it is given. If unread rows remain and the cell still has room, those rows are shown. Empty space inside a cell is not a resting state while fetched rows are waiting on a later page.
- Quote rows are one line: symbol, price, change, and the delayed mark. The source and the age stay on that line when they fit, and drop off before the row wraps onto a second line.
- Markets shows as many fetched tickers as the cell holds, family by family. Crypto keeps the top-48 list. No new market source is added in this change.
- Storm is a global picture in the space it has: regions, extremes, and the places that reported a value. Repeated "no public alert source" lines collapse into one line per region instead of one line per city. Missing values stay blank.
- Weather news carries the feed description as `summary` when the entry has one, checked live and left off when it does not. The client shows that summary only when the bay is at full detail, same as wires.
- The same tightness rules are applied to wires, trade, field, far, and fantasy: one gap between headlines, no row cut off by the status line, pause and the page timer unchanged.
- Other applications are out of scope. This change only records that the board rules should stay stable enough to reuse later.

## Capabilities

### New Capabilities

- `density`: How a bay spends the lines it is given, including one-line quotes, headline gaps, and the rule that leftover room shows more fetched rows.

### Modified Capabilities

- `markets`: The visible set is as many fetched instruments as the cell holds, not a short page with a blank remainder.
- `weather`: The storm bay fills with the global picture and collapses uncovered-alert lines by region.
- `weather-news`: A story row includes the feed description when the source provided one.

## Impact

- Client layout and row renderers in `client/`. The pause key, the page timer, and the status line stay.
- Server weather-news items gain an optional `summary`. Storm alert rows for places with no public source are grouped.
- No new upstream source. Weather-news descriptions are verified on the feeds already shipped. No API key.
