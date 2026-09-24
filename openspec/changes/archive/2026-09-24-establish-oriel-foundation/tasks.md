## 1. Section 2 — walking skeleton

Section 2 stops at the gate in task 1.8. Do not add live upstream feeds in this group.

- [x] 1.1 Add `server/` as a Python 3.12 FastAPI app with a `/health` endpoint and a config file for bind address and home place. No upstream calls.
- [x] 1.2 Add `contracts/` JSON schemas for a panel payload, a bay, and a desk, matching `design.md`.
- [x] 1.3 Add catalog files for the six themes and the nine shipped desks, including `fantasy`. Themes use the palette roles and hex values in `design.md`.
- [x] 1.4 Add fixture panel JSON for one wire headline, one quote, one weather observation, one sports row, and one fantasy lineup row, all marked as fixtures.
- [x] 1.5 Add `client/` as a Go Bubble Tea app that opens one bay, loads a theme, and renders fixture panels with hairline chrome.
- [x] 1.6 Default the bay to the `night` theme. Accept a theme id and a bay name as arguments.
- [x] 1.7 Document how to run the server and one client in the README, including that fixtures are not live data.
- [x] 1.8 Gate: stop. Write the next handoff. Do not start wires, markets, weather, or sports pollers.

## 2. Later — wires

- [x] 2.1 Add an outlet catalog format and a first set of public RSS outlets, each verified alive before it is committed.
- [x] 2.2 Poll enabled outlets on the server, map them into panel payloads, and label stale failures.
- [x] 2.3 Render a wires bay from the live payload. Keep the fixture path for offline use.

## 3. Later — markets

- [x] 3.1 Choose and document one delayed source per family that is actually available without scraping a logged-in site.
- [x] 3.2 Implement operator selection for families and instruments.
- [x] 3.3 Render quote rows with delayed markers and `up` / `down` / `muted` roles.

## 4. Later — trade

- [x] 4.1 Add policy, freight, and supply-chain sources separately from market quotes.
- [x] 4.2 Render the trade desk from those payloads.

## 5. Later — weather and weather news

- [x] 5.1 Add home place and watched places, with Open-Meteo or a national weather service for observations, forecasts, and alerts.
- [x] 5.2 Add weather-news outlets and keep them off the brief desk.
- [x] 5.3 Render the storm desk with observation, forecast, alerts, and weather news as separate panels.

## 6. Later — sports and Far Desk

- [x] 6.1 Build the sports catalog with a coverage tier on every entry. Omit competitions with no verified source.
- [x] 6.2 Implement follows and the field bay for `live`, `delayed`, and recent `results` only.
- [x] 6.3 Implement Far Desk templates over sourced facts. No generated commentary.
- [x] 6.4 Implement the `fantasy` bay: pin strip, lineup slots, bench, select, pin, and explicit FLEX assignment.
- [x] 6.5 Attach weekly points only from a documented public NFL feed for the selected scoring setting. If that feed is unavailable, leave point cells empty. Do not scrape a fantasy host and do not import an outside league.

## 7. Later — recommendations and the multi-bay launcher

- [x] 7.1 Implement the ranker from session, follows, severity, freshness, bay pins, dismissals, and in-progress games for selected or pinned fantasy players.
- [x] 7.2 Show a suggestion with a reason and apply it only on an explicit command.
- [x] 7.3 Add a launcher that starts one process per bay for a named desk and prints the arrangement.
