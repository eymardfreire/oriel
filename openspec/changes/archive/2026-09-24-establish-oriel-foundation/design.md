## Context

Oriel replaces the unfinished "Pi terminal world monitor" proposal that still sits inside Patch Notes Live (`add-pi-terminal-world-monitor-client`). That proposal assumed a Raspberry Pi 3B display and a VPS aggregator. The operator now has a dedicated Omarch machine (about an i7-8700K, 32 GB RAM, RTX 2080) and wants the client to be the terminal, with several windows on one monitor.

World Monitor (https://github.com/koala73/worldmonitor) is the feature overlap: news, markets, geopolitics, climate, infrastructure. Oriel does not embed it. We keep the categories that match this desk and leave the map, the browser, and their feed compilation behind.

Patch Notes Live remains the broadcast overlay. Oriel may copy operational lessons (cache first, the client never calls third parties, label delayed data) and must not import that codebase.

Second Brain is a future home. Oriel stays modular by keeping each domain behind a JSON contract the TUI does not own.

## Goals / Non-Goals

**Goals:**

- A constitution for domains, bays, themes, and recommendations.
- A server on the Omarch machine and a thin terminal client.
- Operator control of what each window shows.
- Honest coverage labels, especially for sports and delayed quotes.
- A section gate so the next agent ships a walking skeleton and stops.

**Non-Goals:**

- Graphical maps, video, or a browser dashboard.
- Calling `api.worldmonitor.app` or vendoring World Monitor source.
- Live play-by-play for sports that have no public live source.
- Model-written color commentary. The RTX 2080 is spare capacity, not a v1 dependency.
- Situation monitoring (conflict, disaster, cables, chokepoints-as-a-map). The domain id `situation` is reserved in the catalog and has no panels in this change.
- Account system, multi-user hosting, and a public deploy. One operator, one server.
- Choosing an open-source license. That waits until the repo is published.

## Decisions

### Name

Oriel. An oriel window projects from the wall and looks out in several directions. Each terminal window is a bay.

### Process split

The Omarch machine runs one aggregation service. It fetches, caches, and normalizes. A terminal runs one client process per OS window. The client polls the service on the LAN (or localhost when both are on that machine). API keys never ship to the client.

Python 3.12 and FastAPI on the server, because the work is I/O, RSS, and JSON, and it matches the operator's other service. Go with Bubble Tea and Lip Gloss on the client, because one static binary runs in Windows Terminal, a Linux tty, or Cursor's terminal without a runtime install. Charm's styling is the closest match to a minimal, high-signal terminal.

Alternative considered: a single Python Textual app. Rejected for the client because every viewing machine would need Python. The server can stay Python.

### Contracts before widgets

`contracts/` will hold JSON schemas for panel payloads, bay config, and desks. Domain code returns those payloads. The client renders them. Second Brain later calls the same HTTP API or reads the same schemas. A domain package must not import the TUI.

Panel payload, v1:

- `id`, `domain`, `title`
- `updated_at`, `stale` (boolean), `stale_reason` (empty when fresh)
- `items[]` of `{ id, title, source, source_url, observed_at, fields }`

`fields` is domain-specific and documented beside the schema. The client has a small set of row renderers (quote, headline, score, alert, clock, fantasy) selected by `domain` plus a `row` hint, not by parsing upstream formats.

### Domain catalog

Domains are data plus a poller. Disabled domains produce no panels and no upstream calls.

| Domain | What it is | What it is not |
| --- | --- | --- |
| `markets` | Indices, equities the operator watches, FX, rates, commodities, crypto | Trade policy or shipping news |
| `trade` | Tariff and policy items, freight, supply-chain notices | A price board |
| `wires` | Headlines from an outlet catalog, grouped by desk | Weather warnings or match reports |
| `weather` | Observation, forecast, alerts for watched places | Narrative storm coverage |
| `weather-news` | Agency and outlet stories about weather | The numeric forecast |
| `sports` | Scores and results for follows, plus an NFL fantasy bay | Invented commentary or a hosted-league import |
| `situation` | Reserved | Not built in v1 |

Inside sports, a catalog entry has a coverage tier:

| Tier | Meaning | UI |
| --- | --- | --- |
| `live` | A public source updates during play | Score line, in-progress state |
| `delayed` | Score exists, with a known lag | Score line plus a delayed badge |
| `results` | Finals and schedules, not in-play | Result when final, schedule before |
| `schedule` | Fixtures only | Date, competitors, competition |
| `far` | Long-tail competition with a public result, schedule, or report | Far Desk only |

Far Desk is a bay preset, not a separate product. A line on Far Desk is a template over sourced facts ("A defeated B 2-1") with the source named. If the source has a report excerpt, the excerpt is quoted and attributed. Nothing is added.

### Fantasy football

NFL only. The `fantasy` desk is one window, kept off the field scoreboard so a lineup does not sit in the middle of other sports.

The bay is three bands, top to bottom: pin strip, lineup, bench. Lineup slots are QB, RB, RB, WR, WR, TE, FLEX, K, DST. Empty slots stay on screen so the shape of the roster is always visible.

Select puts a catalog player into the first open starting slot for that position. Extra players go to the bench. FLEX is an explicit assignment of a benched RB, WR, or TE. Selecting someone already on the roster does nothing.

Pin is a watch list, not a roster move. The newest pin sorts to the top. You can pin a player you have not selected, and you can unpin a starter without dropping them. A starter who is also pinned keeps a pin marker on the lineup row.

There are three different "pins" in Oriel. A fantasy player pin lives only in this bay. A bay pin is the recommendation override. A follow is a sport, competition, or place. Do not treat them as one list.

Scoring display is `ppr` by default, switchable to `half-ppr` or `standard`. Points, opponent, game state, bye, and injury show only when the source has them, and points name that source. No projections in this version.

The roster is stored by Oriel. The operator does not connect ESPN, Yahoo, or a Sleeper league. The player directory and weekly points should come from a documented public NFL feed, verified when the sports section starts. Sleeper's public player and stats endpoints are the candidate, because they expose standard, half-PPR, and PPR points without an account. Reject a source that requires scraping a logged-in fantasy host. If that public feed is gone by then, ship the lineup and pins with blank point cells rather than a scraper.

Starter sports families to register, each entry stamped with the best tier we can actually source: football, American football, basketball, baseball, ice hockey, tennis, cricket, rugby union, rugby league, golf, motorsport, combat sports, cycling, athletics, volleyball, handball, badminton, table tennis, Aussie rules, Gaelic games, hurling, lacrosse, curling, bandy, pesäpallo, kabaddi, sepak takraw, and esports as its own family. A family with no verified source is omitted from the catalog. It is not listed as live.

Candidate source classes, to be verified when that section starts, not frozen here: league-official public APIs where they exist (MLB Stats API and the NHL API are the known-good examples), a keyed multi-sport API the operator chooses to enable, Open-Meteo and national weather services for weather, ECB Frankfurter for FX reference rates, FRED for economy series if a key is present, CoinGecko for crypto, and RSS for wires and weather news. Stooq or an equivalent delayed board for indices. Reject a source that requires scraping a logged-in site.

### Bays, desks, and windows

A bay is one client process: theme, layout, panel list, refresh. A desk is a named list of bays. The launcher starts one terminal per bay. Oriel does not tile the window manager. On Omarch the operator can pin windows with the compositor; the launcher only starts the processes and prints the intended arrangement.

Shipped desks:

| Desk | Bays | Use |
| --- | --- | --- |
| `brief` | one | Clock, home weather, a short wire, a market strip |
| `wires` | one | Headlines by region and topic |
| `markets` | one | Dense quotes |
| `field` | one | Followed sports that are live or recently final |
| `storm` | one | Alerts, forecast, weather news |
| `trade` | one | Policy, freight, related commodities and FX |
| `far` | one | Far Desk |
| `fantasy` | one | NFL pin strip, lineup, and bench |
| `three` | wires, markets, field | Default multi-window recommendation |

Layouts inside a bay are named grids: `strip`, `stack`, `split`, `dense`. A layout places panels. It does not fetch data.

### Themes

Themes are JSON palettes of semantic roles: `bg`, `surface`, `border`, `text`, `muted`, `accent`, `up`, `down`, `warn`, `info`, `stale`. The client maps roles through Lip Gloss. Domain code never picks a color.

Shipped palettes, tuned toward a Cursor-like terminal: little chrome, hairline borders, one accent, semantic color only on numbers and alerts.

| Id | Mode | Notes |
| --- | --- | --- |
| `night` | dark | Default. Near-black `#141414`, text `#e6e6e6`, muted `#8a8a8a`, accent `#7aa2f7`, up `#7dcea0`, down `#e07a7a` |
| `day` | light | Paper `#f7f6f3`, ink `#1c1c1c`, accent `#2f5d9f` |
| `wire` | dark | Denser market board. Amber figures `#f0c14a` on `#0c0c0c` |
| `paper` | light | Newsroom. Warm ground `#f3efe6`, accent `#8c3a2f` |
| `fog` | dark | Lower contrast for long sessions. Ground `#1a1d21`, text `#c5c8ce` |
| `signal` | dark | High contrast. Black ground, white text, accent `#4da3ff` |

`night` is the default because it matches the terminal the operator already likes: dark, quiet, minimal.

### Recommendations are ours

A small ranker on the server scores panels:

- Market session: Asia, London, New York. The open session lifts `markets`.
- Follows: sports and places the operator follows.
- Fantasy: an in-progress NFL game for a selected or pinned player lifts the fantasy desk. It does not demote an open market session.
- Severity: weather alerts and explicit source severity lift that panel.
- Freshness: stale panels sink.
- Bay pins and dismissals beat the ranker until cleared. A fantasy player pin does not pin the bay.

The output is a suggested desk id plus an ordered panel list, with a one-line reason ("New York session is open"). The client shows it as a suggestion. Applying it is explicit.

### Failure

Every poller keeps the last good payload. The payload's `stale` flag goes true when the refresh fails or the item is older than its domain budget. The row shows a stale marker in the `stale` color. A domain with no sources configured renders an empty state that names the domain, not a fabricated row.

### Section gate

Section 1 is this spec. Section 2 builds the skeleton: server health, contracts, theme and desk files, a client that opens one bay on fixture JSON. Section 2 does not add live upstream feeds. Later sections take one domain at a time, wires first.

## Risks / Trade-offs

- Live sports coverage is uneven and often licensed. The catalog's tier is the product. A wide menu of honest tiers beats a short menu of unofficial scrapers.
- Fantasy points depend on a public stats feed. A lineup with empty point cells is acceptable. A scraped league host is not.
- Index quotes from free boards are delayed. The row says so.
- Two languages (Python and Go) cost context for agents. Contracts and the section gate keep the work separable.
- RSS feeds die. The catalog records the last successful fetch and a section task drops or replaces dead outlets.
- Multi-window placement depends on the terminal host and the compositor. We start processes; we do not pretend to be a window manager.

## Migration Plan

Greenfield. When Second Brain is ready, it should consume `contracts/` and the HTTP API. Domains can move one package at a time. The TUI stays behind.

## Open Questions

- Home coordinates for the `brief` desk, set in server config during section 2.
- Which multi-sport API key, if any, the operator wants for football and the long tail. Section for sports asks before enabling a keyed source.
- License at publish time.
