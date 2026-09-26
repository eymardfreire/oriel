## 1. Pass 1: fixes from operator testing

- [x] 1.1 Add `refresh_seconds` to panel payloads from the server poll interval and use it for the live mark
- [x] 1.2 Hide a suggestion whose desk is already shown
- [x] 1.3 On a board, make `a` swap the board to the suggested desk; detach launcher stdout and stderr
- [x] 1.4 Far Desk empty state names the reason

## 2. Pass 2: bay rectangles and rotation (handoff gate)

- [x] 2.1 Allocate one rectangle per bay by bay count and width band
- [x] 2.2 Render each bay at full, compact, or summary detail inside its rectangle
- [x] 2.3 Rotate pages in compact and summary bays, show the page position, pause on the focused bay
- [x] 2.4 Tests for 1, 2, 4, 6, and 9 bays at 80, 120, 180, and 260 columns

## 3. Pass 3: saved layouts (handoff gate)

- [x] 3.1 Store up to nine layouts in `client/state/board.json`
- [x] 3.2 `s` plus a digit saves, a digit loads, `[` and `]` cycle, the status line shows the slot
- [x] 3.3 Tests for save, load, empty slot, and restart

## 4. Pass 4: wires and trade data (handoff gate)

- [x] 4.1 Carry RSS description as `summary` on headline rows, stripped and trimmed
- [x] 4.2 Check wire candidates live, add the ones that answer, record date and region in the catalog and README
- [x] 4.3 Check trade candidates live, add the ones that answer
- [x] 4.4 Render summaries at full detail only

## 5. Pass 5: markets data (handoff gate)

- [x] 5.1 Expand the shipped instrument selection from existing sources
- [x] 5.2 Verify any added source live; record it in the catalog and README
- [x] 5.3 Missing quote renders symbol only

## 6. Pass 6: global weather (handoff gate)

- [x] 6.1 Add about 40 watched cities grouped by region to `catalog/weather/places.json`
- [x] 6.2 Batch Open-Meteo requests for many places
- [x] 6.3 Name alert coverage per place; outside the United States say no public alert source covers it
- [x] 6.4 Region-grouped storm bay and an extremes strip from fetched values only

## 7. Pass 7: sports follows (handoff gate)

- [x] 7.1 Add `POST /bays/field/follows` that validates ids against the competition catalog
- [x] 7.2 Add a follows picker in the field bay
- [x] 7.3 Tests for follow, unfollow, and unknown id

## 8. Check

- [x] 8.1 Run the server tests and the Go client tests after each pass
- [x] 8.2 Update README and `openspec/HANDOFF.md` at each gate
