# Oriel — handoff

Read this first. Do not reopen product decisions that this file marks as locked unless the operator asks. Do not re-archive the foundation change.

## Next agent — start here

The operator is staying on this Windows machine for now. A Linux move is later. Do not port, repackage, or rewrite paths for Linux. Do not commit or push. Do not archive anything until the operator agrees. Archive `live-board` first, then `bay-universes`, then `fit-the-screen`.

`go run . -board` is the way they launch, and they said on 25 September 2026 that it is already right. Do not change that command or the board grid. A window whose status line has no `h home` and whose settings screen has no bay numbers is a single bay (`-bay`), not a broken board. Close that window. The board status line shows `h home` and the current slot.

On the night of 25 September 2026 the operator asked to finish navigation. `refine-the-bay` is implemented and uncommitted. Do not archive it until they agree. Do not redo the passes below. They had just looked at the eight-bay board and accepted the middle-cell fix. The screenshot they sent with the note is Brief beside Far Desk.

`f` refines the focused bay. Field opens follows, Sideline opens sports, and Brief opens place, outlet, and market family. The status hint names that action and omits `f` when the bay has nothing to choose. Pressing `f` on Far Desk, Wires, Markets, Storm, Trade, or Fantasy says that bay has nothing to choose. Brief's choice is `catalog/brief/selection.json`. Empty means Tampa, the first live headline, and the first live quote. A chosen place is not marked home.

Far Desk now has two competitions, checked 2026-09-26: 3. Liga on OpenLigaDB, and the Nippon Baseball League on TheSportsDB. Australian football returned no recent result. German ice hockey answered, and was left out because a tie would have been written as a win. A catalog with no `far` entry still says no far-coverage competition is configured. Restart the server, then the client, before the next live look.

These bays still have no in-client choice. Do not add pickers for them in this change:

- Fantasy roster and pins stay in `catalog/sports/roster.json`. The server has select and pin routes. The client has no key for them.
- Market instruments stay in `catalog/markets/selection.json`.
- Trade families stay in `catalog/trade/selection.json`.
- Wire outlets stay in `catalog/outlets/`, one file each, with `enabled`.
- Storm places stay in `catalog/weather/places.json`, plus the home block in `server/config.toml`.

What is on screen, uncommitted:

- The board list in `client/state/board.json` is trade, wires, storm, sideline, markets, field, brief, far. Theme `wire`, slot 2. Do not reset that file. `h` still restores wires, markets, storm, and trade. `catalog/sports/follows.json` is their follow list. Do not clear it.
- Markets grew on the existing Yahoo chart source, checked live that evening. Equities stays the US tape. It is not split into NYSE and Nasdaq. AMD, Netflix, Oracle, the TSMC ADR, and Goldman Sachs were added. The exchange benchmarks stay in Indices, including Ibovespa and the Shanghai Composite. New families: London, Europe, Tokyo, Hong Kong, China, India, Brazil, Canada, Korea, Taiwan, Australia, and Funds. China is the mainland stocks, Shanghai plus the Shenzhen names that move (CATL, BYD). Funds are the US-listed ETFs, and each title records the venue. The quote line still prints the symbol. `ROG.SW` for Roche returned 404 and is not shipped. London prices are in pence, as the source sent them. A wide cell pages once the families no longer fit. The page mark stays off a cell that still fits on one page.
- The bottoms of both rows were clipping. A line wider than the inside of its box wrapped, the cell drew past its height, and the cut hid the last rows and the panel border. Text now fits the inside of the box. A line stays one line. Rows that do not fit wait on the next page. A cell too short for one full row in every panel shows one panel at a time, so the seam between rows stays closed.
- The middle cell was Brief. In a quarter-width cell its three columns cut the weather line, and the wire and the quote were still the fixtures (`Fixture headline`, `FIX 100`). A narrow strip now stacks. On a wide cell the strip stays. With no brief selection, Brief takes the home observation, the first live wire, and the first live quote when the server is up, and keeps the fixtures when it is not. A saved choice in `catalog/brief/selection.json` replaces that slot.

Verified that night: `pytest tests/test_markets.py` passed (10). The full server suite was not re-run. `go test` in `client/` passed after the layout fixes. The server did not change for those fixes. Restart the client after a client change. Restart the server, then the client, after a server change.

Markets, earlier that evening, uncommitted:

- `finish-markets` is done. Do not redo it. A markets cell packs families down its columns and spends leftover lines on rows that are still waiting. A short cell shows fewer families and cycles. The change bar is `▬`, with a column of padding so it does not sit on the box rule. A paging bay shows `1/2` and the countdown dot on its header. The fraction stays in the text color when that bay is focused, on every bay. The dot runs from the up color to the down color over the 16-second cycle, and every paging bay shares that dot. Sectors and bonds were added on the existing Yahoo chart source. The wider lists were checked live that day; `^SSEC` returned 404, so Shanghai is `000001.SS`. Crypto stays the top 48. The board grid was not changed.
- The page mark is absent when the cell has one page. The operator's wide board showed Trade `1/2` and Wires `1/3` with the dot, and Markets as a title only, because every quote fit. They confirmed that reading. Do not add a mark to a one-page markets cell.
- The same evening they asked to fill the cell. Sectors now adds the industry ETFs checked that afternoon on the Yahoo chart source: XBI, XHB, XRT, XME, XOP, KRE, KBE, XSD, XAR, XPH, XTN, XSW, XHE, XHS, KIE, and XES. No new family and no new source. A wide markets cell that already fits every row uses the extra columns, so a solo bay does not leave a blank side. A cell that still overflows keeps the taller columns. A quote line turns its symbol and price to the accent color for two seconds when the printed price changes. The first print does not flash. An unchanged price does not flash again. The change and the bar stay on the up and down colors. The flash appears on a later refresh.

`client/state/board.json` is theirs. Do not reset it. See the start of this file for the eight-bay list at handoff. Earlier that day the window was also markets only, a two-row board, and a three-column board.

Do not redo `bay-universes` or `fit-the-screen`. Do not redo the field picker, Sideline, or the standings split below.

Later on 24 September 2026, after those passes:

- The follow picker uses `j`/`k` to move and enter to toggle. A number jumps to that row. When `1` could still grow into 10 or above, it waits, and enter toggles the row it already names.
- League names are the full name. Each sport row carries that sport's ball.
- A followed competition with a public table gets its own standings panel, titled with the league. Checked live that day: Major League Baseball and 2. Bundesliga. The National Football League, the National Basketball Association, and the National Rugby League returned no table, so they have none. Do not invent one.
- Sideline is the sports-news bay. The client must fetch it (`shouldLive` includes `sideline`). `f` on that bay refines the sport. With nothing chosen, it shows the newest headline from each sport. Cricket and rugby union score feeds did not answer, so they are headlines only.
- `client/state/board.json` is the operator's board. Do not reset it. See the start of this file for what it showed at the end of 25 September 2026. `h` still restores wires, markets, storm, and trade. `catalog/sports/follows.json` is their follow list. Do not clear it.

Verified after Sideline and the standings split: `go test ./...` in `client/` passed. `pytest tests/test_sports.py` passed (17). The full server suite last passed at 65, before the per-league standings panels. Restart the server after server changes, then the client.

## Where we are

- Folder: `F:\MaxMax\DB\Oriel`
- Remote: `https://github.com/eymardfreire/oriel` (public)
- Branch: `main`. Last pushed commit: `1a57843` (foundation). `bay-universes`, `fit-the-screen`, the field expansion, Sideline, per-league standings, `finish-markets`, the 25 September markets fill, and the same-night layout fixes are implemented and uncommitted. Do not commit or push unless the operator asks.
- Git config has no `user.name` or `user.email`. Do not update git config.
- Foundation archive: `openspec/changes/archive/2026-09-24-establish-oriel-foundation/`

### Change `live-board` — implemented, not archived

`openspec/changes/live-board/`. All tasks checked. It added:

- `go run . -board`: one window of chosen bays. Default wires, markets, storm, trade. Selection and theme saved in `client/state/board.json` (gitignored).
- Width bands: 1 column under 100, 2 from 100, 3 from 160, 4 from 240. Extra rows show more items.
- Status line: clock, focused panel, live/stale/fixture, suggestion, key hints. `j`/`k` focus (accent border), `t` theme, `?` settings (digits toggle bays on a board), `a` apply, `q` quit.
- Retuned `night` palette. Weather glyphs. Observation adds feels-like, humidity, wind from the same Open-Meteo request. Quote change bar. Ages tick every second.
- Verified: `go test ./...` passed in `client/` (it runs on this machine now). `pytest tests/test_weather.py` passed in `server/`. The full server suite was not re-run after this change.

Archive `live-board` when the operator agrees, before archiving `bay-universes`. Its `board` spec is new, and `bay-universes` adds to it.

### Change `bay-universes` — passes 1–7 done. Not archived.

`openspec/changes/bay-universes/`. It validates with `--strict`. Work it in the order of `tasks.md`. Each numbered section after section 1 is a handoff gate. Stop at a gate, run the tests, and update this file.

Pass 1 (tasks 1.1–1.4) is implemented and uncommitted:

- Panel payloads include `refresh_seconds` from the server poll interval. The live mark stays filled for that interval plus 10 seconds, and falls back to the bay refresh when the field is absent.
- A suggestion is hidden when every bay of that desk is already in the window.
- On a board, `a` replaces the shown bays with the suggested desk. A single-bay window still launches processes. Launched processes do not write into the current window.
- Far Desk says "No far-coverage competition is configured" when the catalog has no `far` tier.

Verified after pass 1: `go test ./...` in `client/` passed. `pytest tests -q` in `server/` passed (53). Restart the server before the next live look, because panel payloads changed.

Pass 2 (tasks 2.1–2.4) is implemented and uncommitted:

- Each bay has its own rectangle. One bay fills the window. Two to four share full-height columns. Five to eight use up to four columns and two rows. Nine to twelve use up to four columns and three rows. Columns never exceed the width band, so a narrow window wraps sooner.
- A large rectangle is `full`, a tighter one is `compact` (fewer items per panel), and a short one is `summary` (one panel at a time).
- Compact and summary bays advance every 8 seconds and show `2/5` in the bay header. `j` and `k` pause the focused bay for that interval.

Verified after pass 2: `go test ./...` in `client/` passed. `pytest tests -q` in `server/` passed.

Pass 3 (tasks 3.1–3.3) is implemented and uncommitted:

- `client/state/board.json` stores up to nine layouts. Each slot keeps the bay list, order, and theme.
- On a board, outside settings, `s` then a digit saves, a digit loads, and `[` `]` cycle occupied slots. The status line shows the slot. An empty slot leaves the board as it is and says the slot is empty.
- Loading a slot does not replace the other saved slots.

Verified after pass 3: `pytest tests -q` in `server/` passed (53). `go test` compiled the client, then Windows Application Control blocked the test executable, so the Go suite did not run.

Pass 4 (tasks 4.1–4.4) is implemented and uncommitted:

- An RSS or Atom description is stored as `summary` on the headline, with markup removed. A feed with no description leaves the summary off.
- Wires added on 24 September 2026, after a live fetch: Al Jazeera (world), DW (Europe), France 24 (Europe), ABC News (Oceania), CBC News (Americas). Reuters, AP, and NHK World did not answer and were not added.
- Trade added the same day: U.S. Customs and Border Protection on policy, gCaptain on freight, The Loadstar on supply chain. Each family can now list more than one feed.
- The client shows a summary only when the bay is at full detail.

Verified after pass 4: `go test ./...` in `client/` passed. `pytest tests -q` in `server/` passed (53).

Pass 5 (tasks 5.1–5.3) is implemented and uncommitted:

- The shipped market list grew on the existing sources, checked live on 24 September 2026. No new source was added. Indices add FTSE 100, DAX, Nikkei 225, and Hang Seng. Equities add NVIDIA, Amazon, Alphabet, and Meta. FX adds sterling, Swiss franc, Australian dollar, and Canadian dollar. Rates add the US 3-month, 5-year, and 30-year. Commodities add silver and natural gas. Crypto adds Solana and XRP.
- A symbol the source did not price is still shown, with no price and no change bar.

Verified after pass 5: `go test ./...` in `client/` passed. `pytest tests -q` in `server/` passed (53).

Pass 6 (tasks 6.1–6.4) is implemented and uncommitted:

- `catalog/weather/places.json` now has 40 watched cities, all `"home": false`, across North America, South America, Europe, Africa, the Middle East, Asia, and Oceania.
- Open-Meteo is one request for every configured place. The National Weather Service is asked only for places marked `nws`. Other places say no public alert source covers them.
- The storm observation panel groups by region at full detail and leads with hottest, coldest, wettest, and windiest watched places. A measure nobody reported is left off.

Verified after pass 6: `go test ./...` in `client/` passed. `pytest tests -q` in `server/` passed (55). Restart the server before the next live look. Weather, markets, wires, and trade payloads all changed in this uncommitted work.

Pass 7 (tasks 7.1–7.3) is implemented and uncommitted:

- `POST /bays/field/follows` writes `catalog/sports/follows.json`. An id missing from `catalog/sports/competitions.json` is rejected and the follows file stays unchanged. Sports families and competitor names already in the file stay put. The roster file is not touched.
- On the field bay, `f` opens a picker of shipped competitions. A number follows or unfollows that one. An empty follows file still shows "Choose follows" and does not invent scores. After a follow is saved, the field refresh fetches that competition.
- A follow is not a fantasy player pin and not a bay pin.

The field catalog was expanded on 24 September 2026, after pass 7, then corrected the same day after the operator looked at it.

- Score rows name the league. In progress uses the up color, a final is muted, and a scheduled game uses warn. A minute clock is appended only when the source sent one.
- OpenLigaDB added 2. Bundesliga, the Premier League, La Liga, and the Champions League. Scheduled rows are limited to the next 14 days. Bundesliga stays finals only, with season dates 2026-08-28 through 2027-05-22.
- TheSportsDB's free feed is the nearest past event and the nearest upcoming event, not a full slate. It added Serie A, Ligue 1, Brazilian Serie A, the NFL, the NBA, the CFL, and the NRL.
- ESPN's scoreboard returned 403. Argentine football and rugby union were left out after a 429. OpenLigaDB's NFL feed was empty.
- The follow picker accepts every shipped competition. With more than nine, `1` waits for a second digit and enter confirms it. `2` through `9` still select immediately when they cannot start a larger number.
- A league that is not followed says `not followed`. `active` and `off season` are the season flag, not the follow state.
- A flag uses a published start and end when both exist. MLB is 2026-03-25 through 2026-10-31 (regular season through the postseason). The NHL is 2026-09-19 through 2027-06-10 (preseason through the playoffs; the regular season starts 2026-09-29). Formula 1 is 2026-03-08 through 2026-12-06. Without a published end, a game in the last 28 days is active, and a future next game after a longer gap is off season. The NBA's last game was 2026-06-14 and its next is 2026-10-03, so it is off season.
- The NFL flag follows Sleeper's `season_type` on each sports refresh when the NFL is in the catalog. Checked 2026-09-24: season 2026, week 3, regular, `season_start_date` 2026-09-09, last game 2026-09-22, next game 2026-09-25. No end date was published, so none is stored.

Verified after the field correction: `go test ./...` in `client/` passed. `pytest tests -q` in `server/` passed (63). Restart the server and the client before the next live look.

### Change `fit-the-screen` — passes 1–5 done. Not archived.

`openspec/changes/fit-the-screen/`. Work it in the order of `tasks.md`. Each numbered section is a handoff gate.

Pass 1 (tasks 1.1–1.4) is implemented and uncommitted:

- A bay spends the lines in its cell. Leftover lines show more fetched rows. A later page holds only rows that did not fit.
- A quote is one line: symbol, price, change, and the delayed mark. Age drops first, then source, when the column is narrow. A missing price stays blank.
- Headlines keep one blank line between them. A summary stays on one line and shows only at full detail.

Pass 2 (tasks 2.1–2.2) is implemented and uncommitted:

- Markets shows every fetched ticker that fits, family by family. A short family does not leave a blank block above a long crypto list.

Pass 3 (tasks 3.1–3.3) is implemented and uncommitted:

- The storm cell fills with fetched places, still grouped by region. A place with no temperature omits the temperature.
- Places with no public alert source share one row per region. A place with an active alert keeps its own row. A covered place with no active alert still says no alerts are active.

Pass 4 (tasks 4.1–4.3) is implemented and uncommitted:

- Weather news stores a feed description as `summary` when the entry has one, with markup removed, and omits the field when it does not.
- Checked live on 24 September 2026: National Hurricane Center Atlantic outlook and Storm Prediction Center both answered, and both include descriptions. Recorded in `catalog/weather-news/` and the README.
- The client shows `summary` only at full detail.

Pass 5 (tasks 5.1–5.2) is implemented and uncommitted:

- The same line budget covers wires, trade, field, far, and fantasy.
- Pause, the 16-second page timer, and the status line are unchanged.

Verified after the five passes: `go test ./...` in `client/` passed. `pytest tests -q` in `server/` passed (59). Restart the server and the client before the next live look.

Operator intent, in their words, condensed:

- One bay alone fills the screen as its own complete universe. Each added bay halves the space, up to four columns. After that, rows split and each bay shows less but rotates through its full data set.
- Save up to nine layouts and cycle through them.
- Much more data per bay. The agent picks the most relevant public sources. Headlines plus content where the feed has it.
- Weather: a real global monitor.
- The operator snaps the window to half a screen and likes how it reflows. Keep that.
- The operator has delegated design decisions. Keep feedback loops short and show results.

Operator-reported problems:

- Pass 1 fixed the suggestion showing on the desk it names, `a` opening extra windows and printing into the board, the live mark flipping because markets polls every 60 seconds, and Far Desk being empty with no reason.
- Pass 7 added the field follows picker. Press `f` on the field bay. `j`/`k` move, enter toggles, and a number jumps to that row. The season flag is separate from `not followed`.
- On 25 September 2026 a single markets window looked like the board had lost its bays. It was not the board. `go run . -board` still loads `client/state/board.json`. The operator then stayed on markets, filled the exchanges, fixed the clipped bottoms and the Brief cell, and stopped for the night. The current board is at the start of this file. Wait for their next note.

## Locked decisions

- Name is Oriel. One OS window is a bay. A named set of bays is a desk. A board is one window that shows several bays. Named desks still launch one process per bay and never tile OS windows.
- Server runs on the Omarch machine: Python 3.12, FastAPI. It is the only process that calls upstream sources.
- Client is Go, Bubble Tea, Lip Gloss. Static binary, no Python on the viewing machine.
- Contracts in `contracts/` are the Second Brain boundary. Domain code must not import the TUI.
- Domains: `markets`, `trade`, `wires`, `weather`, `weather-news`, `sports`. `situation` is reserved and not built.
- Sports coverage tiers: `live`, `delayed`, `results`, `schedule`, `far`.
- NFL fantasy is the `fantasy` desk. Default scoring is PPR. No ESPN, Yahoo, or Sleeper login, and no league import.
- Three different pins: fantasy player pin, bay pin, follow. Do not merge them.
- Themes: `night` (default), `day`, `wire`, `paper`, `fog`, `signal`.
- Recommendations are computed by Oriel. Applying one is explicit.
- Do not copy World Monitor. Do not call `api.worldmonitor.app`. Do not import Patch Notes Live.
- The trade desk does not show commodity or FX quotes.
- The test home is Tampa, Florida. Global cities go in as `"home": false`.
- No license file unless the operator asks.
- Never invent scores, quotes, weather values, or summaries. A missing value is blank.

## Adding sources

The operator has now asked for more data. `bay-universes` authorizes new wire outlets, market instruments, trade feeds, weather places, and a sports follows route. Every new source still has to be fetched live, recorded with the check date in its catalog file and the README, and left out if it does not answer. No API key unless the operator supplies one. No logged-in scraping.

## Running it

- Server: from `server/`, `.\.venv\Scripts\python -m oriel_server` (CPython 3.12.14 venv; no `py -3.12` launcher). Binds `127.0.0.1:8787`. Restart it after server changes.
- Client: add `%LOCALAPPDATA%\Programs\go\bin` to PATH (Go 1.27.1), then from `client/`, `go run . -board` or `go run . -bay markets`.
- PowerShell here is 5.1: chain commands with `;`, not `&&`.
