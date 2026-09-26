## 1. Pass 1: density rule (handoff gate)

- [x] 1.1 Raise the row budget from the cell height so leftover lines show more fetched rows
- [x] 1.2 Render a quote as one line, dropping age and then source before the symbol or the price
- [x] 1.3 Keep one blank line between headlines and keep each summary on one line
- [x] 1.4 Tests for a tall cell, a short cell, and a narrow quote

## 2. Pass 2: markets fill (handoff gate)

- [x] 2.1 Show every fetched ticker that fits, family by family, with no blank remainder
- [x] 2.2 Tests for a short family beside a long crypto list, and for a symbol with no price

## 3. Pass 3: storm picture (handoff gate)

- [x] 3.1 Fill the storm cell with fetched places grouped by region
- [x] 3.2 Collapse places with no public alert source into one row per region
- [x] 3.3 Tests for a tall storm cell and for several uncovered cities in one region

## 4. Pass 4: weather news text (handoff gate)

- [x] 4.1 Carry a feed description as `summary` when the entry has one, and omit it when it does not
- [x] 4.2 Check the shipped weather-news outlets live and record the date in the catalog and README
- [x] 4.3 Show `summary` only at full detail

## 5. Pass 5: the other bays (handoff gate)

- [x] 5.1 Apply the same tightness rules to wires, trade, field, far, and fantasy
- [x] 5.2 Confirm pause, the page timer, and the status line still hold

## 6. Check

- [x] 6.1 Run the server tests and the Go client tests after each pass
- [x] 6.2 Update README and `openspec/HANDOFF.md` at each gate
