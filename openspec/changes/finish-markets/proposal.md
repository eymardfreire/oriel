## Why

A markets bay docked on its own still pages while most of the cell is empty, and the change bar sits on the box rules. The shipped families are also too short to fill a large cell, and two ordinary market categories are missing. This is the markets finishing pass. The board grid stays as it is.

## What Changes

- A markets cell spends its width and height on fetched quotes. Leftover lines in a column go to a family that still has rows. A later page exists only for rows that did not fit. A short cell shows fewer families at once and cycles the rest.
- The change bar is a short block with a gap inside the box, so it does not meet the row above or the panel rule.
- Indices, equities, FX, rates, and commodities grow on sources already in the catalog, after a live check on 25 September 2026. A symbol that did not answer is left out.
- Two families are added, both on the existing Yahoo chart source: sectors (US sector ETFs) and bonds (Treasury and credit ETFs). Crypto stays the market-cap list. No new source kind and no API key.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `markets`: The cell fills with fetched quotes, the change bar stays off the rules, and the shipped families include sectors and bonds plus a wider verified list.

## Impact

- `client/render.go` lays out the markets cell. Other bays keep their current layout.
- `catalog/markets/`, `server/oriel_server/markets/catalog.py`, and the market contracts gain `sectors` and `bonds`.
- Server tests and the README record the 25 September 2026 check. Restart the server after the catalog change. Do not reset `client/state/board.json`.
