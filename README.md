# Oriel

Oriel is a modular terminal desk for the world. One server gathers markets, trade, news, weather, and sports. Each terminal window is a bay, and you decide what that bay shows.

The name comes from an oriel window: a bay that projects outward so you can look in more than one direction at once.

## Status

The server answers `/health` and polls wires, markets, trade, weather, and sports. The client opens one bay. The wires, markets, trade, storm, field, far, and fantasy bays read live panels from the server. Brief keeps its fixture wire and quote. It swaps in the home observation only after that place has coordinates. Weather news stays on the storm desk.

- Change: `openspec/changes/establish-oriel-foundation/`
- Handoff: `openspec/HANDOFF.md`

## Shape

| Piece | Where it runs | Role |
| --- | --- | --- |
| Server | Omarch machine | Fetch, cache, and serve every domain. Today it serves health, wires, markets, trade, weather, and sports. |
| Client | Any terminal | One process, one window, one bay |
| Contracts | `contracts/` | Panel, bay, desk, wire-outlet, market, and trade JSON schemas |
| Catalog | `catalog/` | Themes, shipped desks, wire outlets, market sources, trade sources, and sports |
| Fixtures | `fixtures/` | Sample panels marked `fixture: true` |

## Run the server

From `server/`, with Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m oriel_server
```

The process binds to `bind_host` and `bind_port` in `server/config.toml` (default `127.0.0.1:8787`). On startup it polls enabled wire outlets, the selected market instruments, and the enabled trade families. Check it:

```powershell
Invoke-RestMethod http://127.0.0.1:8787/health
Invoke-RestMethod http://127.0.0.1:8787/bays/wires
Invoke-RestMethod http://127.0.0.1:8787/bays/markets
Invoke-RestMethod http://127.0.0.1:8787/bays/trade
Invoke-RestMethod http://127.0.0.1:8787/bays/storm
Invoke-RestMethod http://127.0.0.1:8787/bays/field
Invoke-RestMethod http://127.0.0.1:8787/bays/far
Invoke-RestMethod http://127.0.0.1:8787/bays/fantasy
```

`home_place` is the primary home. The shipped place is Tampa, Florida (`27.94752`, `-82.45843`), from the Open-Meteo geocoder. Edit that block to move it. Add more homes, or a place you watch that is not a home, in `catalog/weather/places.json`. A row with `"home": true` is another home. `"home": false` is watched on the storm desk only. Brief shows every home and leaves the others off that window.

`[wires]` sets `enabled`, `refresh_seconds` (default 120), and `stale_after_seconds` (default 900). A failed refresh keeps the last good headlines and marks the panel stale. Each outlet's last successful fetch is recorded in `server/state/wires.json`, which is local state, not part of the catalog.

`[markets]` uses the same shape, with `refresh_seconds` defaulting to 60. Last good quotes are recorded in `server/state/markets.json`. That directory is gitignored. There is no FRED key and no other market key in this file.

`[trade]` uses the same shape, with `refresh_seconds` defaulting to 300 and `stale_after_seconds` defaulting to 3600. Last good headlines are recorded in `server/state/trade.json`. Trade does not fetch quotes, and markets does not fetch trade headlines.

`[weather]` uses that same interval. Observations and forecasts come from Open-Meteo. Alerts come from the National Weather Service when a place has coordinates. A place with no coordinates is not fetched, and the server does not invent a temperature. Last good weather is recorded in `server/state/weather.json`.

`[sports]` uses `refresh_seconds` 60 and `stale_after_seconds` 900. With an empty follow list the field bay does not call a score feed. Fantasy points are read from Sleeper only when the roster or the pin list has a player. Last good fantasy points are recorded in `server/state/sports.json`.

On the Omarch machine the same entry point is `python3.12 -m oriel_server` from `server/` after the venv is installed.

## Run one client

From `client/`, with Go 1.24 or newer:

```powershell
go run . -bay brief
go run . -bay wires
go run . -bay wires -fixture
go run . -bay markets
go run . -bay markets -fixture
go run . -bay markets -theme wire
go run . -bay trade
go run . -bay trade -fixture
go run . -bay storm
go run . -bay storm -fixture
go run . -bay field
go run . -bay field -fixture
go run . -bay far
go run . -bay fantasy
go run . -bay fantasy -fixture
go run . -board
```

`-bay` defaults to `brief`. `-board` opens on home: wires, markets, storm, and trade. Press `h` to come back to that set. One bay uses the whole window. Two to four bays sit in full-height columns, and more bays wrap into rows. The column count still follows the width bands: one under 100 columns, two from 100, three from 160, four from 240. A bay that cannot show its whole set pages through it every 16 seconds and prints the page as `2/5`, with a dot that moves from green to red as that page runs out. A wide bay puts its panels in columns and fills each column. `j` and `k` pause that paging on the focused bay. `-theme` defaults to the bay's theme (`night` for every shipped bay). Themes: `night`, `day`, `wire`, `paper`, `fog`, `signal`. Press `q` to quit. `j` and `k` move the accent border between panels. `t` cycles the theme for this window. `?` opens settings. On a board, the number keys there show or hide a bay. Outside settings, `s` then a digit saves the current bays and theme into one of nine slots, a digit loads that slot, and `[` `]` cycle the occupied ones. An empty slot stays as it is and the status line says it is empty. On a board, `a` replaces the shown bays with the suggested desk. A single-bay window still starts that desk in new windows.

A wider terminal shows more columns: one under 100 columns, two from 100, three from 160, four from 240. Extra rows show more items. That is how a fullscreen 4K window carries more than a 1080p window. The client does not read the monitor's pixel size.

`wires` asks `http://127.0.0.1:8787` for live desk panels, one panel per desk, eight newest headlines each. `markets` asks the same server for one quote panel per enabled family. `trade` asks for one headline panel per enabled family. `storm` asks for observation, forecast, alerts, and weather news as separate panels. Pass `-server` if the aggregation service is on another host. If that server cannot be reached, the bay shows its fixture instead and prints a line on stderr. `-fixture` skips the server. A reachable server that returns no rows stays empty; it does not fill in fixture text. The client never calls an outlet, a market source, a trade feed, a weather service, or a sports feed.

Bays: `brief`, `wires`, `markets`, `field`, `storm`, `trade`, `far`, `fantasy`. `three` is a desk of three bays, not a bay. This client opens one window. It does not start the other bays. The wires, markets, trade, and storm bays call the server. Brief asks only for the home observation, and only uses it when that place is configured. The others render fixtures and do not call upstream sources.

`brief` shows one observation, one headline, and one quote. With nothing chosen, that is the home place, the first live headline, and the first live quote. Press `f` on the brief bay to choose a place, a wire outlet, or a market family. The choice is `catalog/brief/selection.json`. A chosen place is not marked home. A place with no observation keeps the previous weather row, and a missing price stays blank. `field`, `far`, and `fantasy` read the server. `-fixture`, or a server that cannot be reached, keeps the field and fantasy fixtures. `far` has no fixture panels, so that fallback shows an empty state that names the domain. `storm` falls back to sample observation, forecast, alert, and weather-news panels when the server is down.

## Outlets

Wire outlets live in `catalog/outlets/`, one JSON file per outlet. Each file has an id, a name, a public `fetch` URL, a language, a region, one or more desks (`world`, `regional`, `business`, `politics`, `technology`, `science`), and `enabled`. The format is `contracts/outlet.schema.json`.

Set `"enabled": false` to stop fetching an outlet. The next successful refresh drops its rows. A disabled outlet is not fetched.

The first set was checked live on 23 September 2026: BBC News (world, UK, business, politics, technology, science), The Guardian (world, business, science), The New York Times (U.S.), NPR (politics), and Ars Technica. Checked on 24 September 2026 and added: Al Jazeera (world), DW (Europe), France 24 (Europe), ABC News (Oceania), and CBC News (Americas). Reuters, AP, and NHK World did not answer from this machine, so they were not added. A headline includes the feed's description as a summary, with markup removed, and only when the bay is at full detail.

## Markets

Market sources are recorded in `catalog/markets/sources.json`. One delayed source per family, checked on 23 September 2026:

| Family | Source | What it is |
| --- | --- | --- |
| Indices, sectors, equities, exchange boards, funds, bonds, commodities | Yahoo Finance chart | Public delayed quotes. Stooq did not return a quote feed. |
| FX | Frankfurter | ECB reference rates, not a live dealing price. |
| Rates | US Treasury | Daily par yield curve. FRED is not enabled; it needs an API key. |
| Crypto | CoinGecko | Public simple price, labeled delayed because it is not an exchange feed. |

The operator's list is `catalog/markets/selection.json`. Set a family's `"enabled"` to false to hide it. A hidden family is not fetched and does not appear. Edit `instruments` to change the symbols. Other families do not add a symbol that is absent from that list. Crypto also requests CoinGecko's market-cap list, `top` 48, checked on 24 September 2026 (Bitcoin through Aave). If that list does not answer, the named crypto instruments are the fallback. No new source was added on 24 September 2026. The wider list was checked that day on the sources above: FTSE 100, DAX, Nikkei 225, Hang Seng, NVIDIA, Amazon, Alphabet, Meta, sterling, Swiss franc, Australian dollar, Canadian dollar, the US 3-month, 5-year, and 30-year, silver, natural gas, Solana, and XRP, plus the original names.

Checked on 25 September 2026, still on those sources: Russell 2000, CBOE VIX, CAC 40, Euro Stoxx 50, S&P/TSX, ASX 200, KOSPI, Shanghai Composite (`000001.SS`; `^SSEC` returned 404 and was left out), BSE Sensex, Ibovespa, the eleven SPDR sector ETFs plus the industry ETFs XBI, XHB, XRT, XME, XOP, KRE, KBE, XSD, XAR, XPH, XTN, XSW, XHE, XHS, KIE, and XES, Broadcom, Tesla, Berkshire Hathaway, Eli Lilly, JPMorgan, Visa, UnitedHealth, Exxon Mobil, Mastercard, Johnson & Johnson, Costco, Home Depot, Procter & Gamble, Bank of America, Walmart, the New Zealand dollar, krona, yuan, Hong Kong dollar, Singapore dollar, rupee, won, Mexican peso, real, rand, euro/sterling, euro/yen, the US 1-month, 6-month, 1-year, 3-year, 7-year, and 20-year, SHY, IEF, TLT, LQD, HYG, EMB, TIP, platinum, palladium, copper, Brent, heating oil, gasoline, wheat, corn, soybeans, coffee, sugar, and cotton. Sectors and bonds are families on the same Yahoo chart source. Rates stay the Treasury yield curve. Bonds are the tradable prices beside that curve.

Later on 25 September 2026 the same chart endpoint added the leading listings on the other major boards, and a funds section. Equities stays the US tape and now also includes AMD, Netflix, Oracle, the TSMC ADR, and Goldman Sachs. It is not split into a NYSE list and a Nasdaq list. The exchange index stays in Indices: Ibovespa, the Shanghai Composite, the FTSE 100, and the rest were already there. London is Shell, AstraZeneca, HSBC, Unilever, BP, Rio Tinto, GSK, and RELX, in pence. Europe is LVMH, L'Oreal, TotalEnergies, Airbus, SAP, Siemens, Allianz, ASML, Nestle, and Novartis. Roche (`ROG.SW`) returned 404 and was left out. Tokyo is Toyota, Sony, SoftBank, Keyence, Mitsubishi UFJ, Tokyo Electron, and Fast Retailing. Hong Kong is Tencent, Alibaba, Meituan, Xiaomi, AIA, China Construction Bank, and HSBC. China is the mainland cash names: Kweichow Moutai, Ping An, China Merchants Bank, and ICBC in Shanghai, plus CATL and BYD in Shenzhen. India is Reliance, Tata Consultancy Services, HDFC Bank, Infosys, ICICI Bank, and Bharti Airtel. Brazil is Petrobras, Vale, Itau, Bradesco, Ambev, and WEG. Canada is Royal Bank of Canada, Toronto-Dominion, Shopify, and Enbridge. Korea is Samsung Electronics, SK Hynix, and Hyundai Motor. Taiwan is the local TSMC line, Hon Hai, and MediaTek. Australia is BHP, Commonwealth Bank, and CSL. Funds are the US-listed ETFs SPY, QQQ, IWM, DIA, VTI, EFA, EEM, EWJ, FXI, EWZ, INDA, VGK, GLD, and IBIT. Each fund title records the venue. The quote line still prints the symbol.

Each quote row shows the symbol, price, source, and a delayed marker. A positive change uses the theme `up` role and a negative change uses `down`. If the source did not send a price, the row shows the symbol only. If it sent a price and no change, the change cell stays empty.

## Trade

Trade sources are recorded in `catalog/trade/sources.json`. Public RSS feeds, checked on 23 September 2026, with more feeds checked on 24 September 2026:

| Family | Source | What it is |
| --- | --- | --- |
| Policy | WTO | Official news RSS. No login and no API key. |
| Policy | U.S. Customs and Border Protection | Customs news RSS, checked 24 September 2026. |
| Freight | FreightWaves | Public freight headlines. The Federal Maritime Commission feed was stale, so it is not used. |
| Freight | gCaptain | Maritime headlines, checked 24 September 2026. |
| Supply chain | Supply Chain Dive | Public supply-chain headlines. |
| Supply chain | The Loadstar | Shipping and supply-chain headlines, checked 24 September 2026. |

The operator's list is `catalog/trade/selection.json`. Set a family's `"enabled"` to false to hide it. A hidden family is not fetched and does not appear. Each row shows the title, the source name, and the observed time. These panels are not the markets quote board.

## Weather

Weather uses Open-Meteo for the observation and the forecast, and the National Weather Service for active alerts. Both are public and need no API key. A place is fetched only when it has coordinates.

The primary home is `[home_place]` in `server/config.toml`. Further places are a list in `catalog/weather/places.json`. Each one needs an id, a name, a latitude, a longitude, `"home"`, a region, and `alerts` (`nws` or `none`). Set `"home": true` for another home, or `false` for a place that belongs on the storm desk only. Brief shows every home. The shipped watch list, added 24 September 2026, is about 40 cities across North America, South America, Europe, Africa, the Middle East, Asia, and Oceania, all with `"home": false`. Open-Meteo is requested once for the whole list. The National Weather Service covers United States places only. Everywhere else the alert row says no public alert source covers that place. The storm bay groups observations by region and leads with the hottest, coldest, wettest, and windiest watched places that actually reported that measure.

Weather news is a separate feed in `catalog/weather-news/`. The shipped outlets, checked on 23 September 2026, are the National Hurricane Center Atlantic outlook and the Storm Prediction Center. Checked again on 24 September 2026: both feeds answered, and both include a description, which is stored as `summary` and shown only when the storm bay is at full detail. Set `"enabled": false` on an outlet to stop fetching it. Those stories appear on the storm desk only. Brief does not show them.

An alert marked severe or extreme uses the theme `down` role. Other severities use `warn`. When the alert source reports none, the panel says no alerts are active. It does not copy the forecast into that panel.

## Sports

Sports competitions are `catalog/sports/competitions.json`. Each entry has one coverage tier. A competition with no verified public source is omitted. European leagues below were checked on 24 September 2026. MLB, the NHL, and Formula 1 were checked on 23 September 2026. No multi-sport API key.

| Competition | Family | Tier | Source |
| --- | --- | --- | --- |
| Major League Baseball | baseball | `live` | MLB Stats API |
| National Hockey League | ice hockey | `live` | NHL |
| Bundesliga | football | `results` | OpenLigaDB finals, season 2026-08-28 to 2027-05-22 |
| 2. Bundesliga | football | `delayed` | OpenLigaDB, season 2026-08-07 to 2027-05-23 |
| Premier League | football | `delayed` | OpenLigaDB, season 2026-08-21 to 2027-05-30 |
| La Liga | football | `delayed` | OpenLigaDB, season 2026-08-15 to 2027-05-30 |
| UEFA Champions League | football | `delayed` | OpenLigaDB, season 2026-09-08 to 2027-01-27 |
| Serie A | football | `delayed` | TheSportsDB nearest past and next event |
| Ligue 1 | football | `delayed` | TheSportsDB nearest past and next event |
| Brazilian Serie A | football | `delayed` | TheSportsDB nearest past and next event |
| National Football League | american football | `delayed` | TheSportsDB nearest past and next event |
| National Basketball Association | basketball | `delayed` | TheSportsDB nearest past and next event |
| Canadian Football League | canadian football | `delayed` | TheSportsDB nearest past and next event |
| National Rugby League | rugby league | `delayed` | TheSportsDB nearest past and next event |
| 3. Liga | football | `far` | OpenLigaDB, season 2026-08-07 to 2027-05-22, checked 2026-09-26 |
| Nippon Baseball League | baseball | `far` | TheSportsDB nearest past and next event, checked 2026-09-26 |
| Formula 1 | motorsport | `results` | Jolpica last-race classification, not live timing |

ESPN's scoreboard returned 403. TheSportsDB's free feed is one past event and one upcoming event, not a full slate. Argentine football and rugby union were left out after a 429. OpenLigaDB scheduled rows are limited to the next 14 days so a 380-match season does not fill the bay. A minute clock is shown only when the source sent one.

Follows are `catalog/sports/follows.json`. Put a competition id in `competitions`, a family such as `baseball` in `sports`, or a competitor name in `competitors`. An empty file shows "Choose follows" and does not fetch scores. On the field bay, `f` opens a picker. `j` and `k` move the row, and enter toggles it. A number jumps to that row. When the number could still grow into 10 or above, it waits, and enter toggles the row it already names. League names are the full name, and each row carries that sport's ball. The follows file is not the fantasy roster and not a bay pin. After a follow is saved, the next field refresh fetches that competition and, when that source publishes a table, the season standings. An id that is not in the competition catalog is rejected and the follows file stays as it was. `f` follows the focused bay. The status hint says `f follows`, `f sports`, or `f brief`, and it omits `f` when that bay has nothing to choose.

Sideline is the sports-news bay. Turn it on from settings. `f` on that bay refines the sports. With nothing chosen, the bay shows the newest headline from each sport. Choosing a sport keeps only that sport. Cricket and rugby union are headlines here: their score feeds did not answer on 24 September 2026. The feeds that did are BBC Sport (football, cricket, rugby union, rugby league, Formula 1, tennis) and The Guardian (cricket, rugby union).

```powershell
Invoke-RestMethod http://127.0.0.1:8787/bays/field/follows -Method Post -ContentType application/json -Body '{"competition_id":"mlb","follow":true}'
```

The field bay shows live and delayed follows, recent finals from the last 48 hours, and schedule follows as a time with no score. Each score row names its league. Final, in progress, and scheduled use different colors. Each follow row shows the season dates from the catalog and an active or off-season flag when both dates exist. It does not show Far Desk rows or fantasy points. A failed first fetch names the competition and leaves the score blank. A later failure keeps the last score and marks the panel stale.

Far Desk lists only `far` entries. A result becomes one factual sentence, such as "North defeated South 2-1", labeled `factual line`. A report excerpt is shown as a quotation. Nothing is added. The shipped far entries are 3. Liga and the Nippon Baseball League, checked 2026-09-26. Australian football returned no recent result that day, and the German ice hockey feed was left out because a tied score would have been written as a win. A catalog with no `far` entry still says no far-coverage competition is configured. Press `f` on Far Desk and the status line says that bay has nothing to choose.

## Fantasy

The fantasy bay is NFL only, and it is not the field scoreboard. It is a pin strip, then the lineup slots QB, RB, RB, WR, WR, TE, FLEX, K, DST, then the bench. Empty slots stay visible. The roster is `catalog/sports/roster.json`. There is no ESPN, Yahoo, or Sleeper login and no league import.

Select, pin, and flex are server commands:

```powershell
Invoke-RestMethod http://127.0.0.1:8787/bays/fantasy/select -Method Post -ContentType application/json -Body '{"player_id":"4046"}'
Invoke-RestMethod http://127.0.0.1:8787/bays/fantasy/pin -Method Post -ContentType application/json -Body '{"player_id":"4046"}'
Invoke-RestMethod http://127.0.0.1:8787/bays/fantasy/flex -Method Post -ContentType application/json -Body '{"player_id":"4046"}'
Invoke-RestMethod http://127.0.0.1:8787/bays/fantasy/unpin -Method Post -ContentType application/json -Body '{"player_id":"4046"}'
Invoke-RestMethod http://127.0.0.1:8787/bays/fantasy/drop -Method Post -ContentType application/json -Body '{"player_id":"4046"}'
Invoke-RestMethod http://127.0.0.1:8787/bays/fantasy/scoring -Method Post -ContentType application/json -Body '{"scoring":"half-ppr"}'
```

Select fills the first open starting slot for that position. Further players go to the bench. FLEX is only an explicit flex command, and only from the bench. Selecting someone already on the roster does nothing. Pin watches a player and does not add them to the lineup. Unpin leaves the roster spot. Drop leaves the pin.

Weekly points come from Sleeper's public stats (`pts_ppr`, `pts_half_ppr`, `pts_std`), checked on 23 September 2026. The default scoring is `ppr`. A row shows points only when that feed has a number for the current week, and it names Sleeper. If the feed has no number, the points cell stays empty.

## Suggestions

`GET /suggestions` is Oriel's own ranking. It uses the market-session clock, follows, weather-alert severity, stale panels, a pinned bay, a dismissed desk, and an in-progress game for a selected or pinned fantasy player. It does not call a third-party ranker. A fantasy player pin does not pin a bay.

An open New York, London, or Asia session lifts markets. A severe or extreme alert lifts storm above that and the reason names the alert. An in-progress fantasy game lifts the fantasy desk only when no cash session is open, and the reason names the player. The shipped feeds do not set `game_state`, so that lift stays off until a source provides it. A stale desk sinks. Pinning a bay, or dismissing a desk, beats the ranker until you clear it.

The client prints the suggestion under the current panels. It hides the line when every bay of that desk is already in the window. On a board, `a` replaces the shown bays with that desk. A single-bay window still starts the desk as separate processes, and those processes do not write into the current window. `applied` in the payload stays false until you do.

```powershell
Invoke-RestMethod http://127.0.0.1:8787/suggestions
Invoke-RestMethod http://127.0.0.1:8787/suggestions/pin -Method Post -ContentType application/json -Body '{"bay_id":"wires"}'
Invoke-RestMethod http://127.0.0.1:8787/suggestions/dismiss -Method Post -ContentType application/json -Body '{"desk_id":"markets"}'
Invoke-RestMethod http://127.0.0.1:8787/suggestions/clear -Method Post
```

## Launcher

`-desk` starts one client process per bay and prints each bay's role. It does not tile or position OS windows.

```powershell
go run . -desk three
go run . -desk fantasy
```

`three` starts wires, markets, and field. `fantasy` starts one fantasy bay and does not start field.

## Fixtures are not live data

Files in `fixtures/` are canned panels so a bay can render before a poller exists, and so the wires bay can still open while the server is down. Each one sets `fixture: true`, and the client prints `fixture` in the panel header. Fixture files are not a news feed, a quote board, a weather service, or a sports source.

## Domains

Markets, trade, wires (news), weather, weather news, and sports. Sports includes a Far Desk for competitions that only have public results or reports, and a separate NFL fantasy window where you select a lineup and pin players to watch. A situation domain is reserved and is not part of the first build.

## Work from the spec

```powershell
openspec show establish-oriel-foundation
openspec validate establish-oriel-foundation --strict
```
