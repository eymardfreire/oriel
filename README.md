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
```

`-bay` defaults to `brief`. `-theme` defaults to the bay's theme (`night` for every shipped bay). Themes: `night`, `day`, `wire`, `paper`, `fog`, `signal`. Press `q` to quit. `j` and `k` move down and up through panels.

`wires` asks `http://127.0.0.1:8787` for live desk panels, one panel per desk, eight newest headlines each. `markets` asks the same server for one quote panel per enabled family. `trade` asks for one headline panel per enabled family. `storm` asks for observation, forecast, alerts, and weather news as separate panels. Pass `-server` if the aggregation service is on another host. If that server cannot be reached, the bay shows its fixture instead and prints a line on stderr. `-fixture` skips the server. A reachable server that returns no rows stays empty; it does not fill in fixture text. The client never calls an outlet, a market source, a trade feed, a weather service, or a sports feed.

Bays: `brief`, `wires`, `markets`, `field`, `storm`, `trade`, `far`, `fantasy`. `three` is a desk of three bays, not a bay. This client opens one window. It does not start the other bays. The wires, markets, trade, and storm bays call the server. Brief asks only for the home observation, and only uses it when that place is configured. The others render fixtures and do not call upstream sources.

`brief` shows a live observation for every home once the server is up, and keeps the wire and quote fixtures. A place with `"home": false` stays off brief. `field`, `far`, and `fantasy` read the server. `-fixture`, or a server that cannot be reached, keeps the field and fantasy fixtures. `far` has no fixture panels, so that fallback shows an empty state that names the domain. `storm` falls back to sample observation, forecast, alert, and weather-news panels when the server is down.

## Outlets

Wire outlets live in `catalog/outlets/`, one JSON file per outlet. Each file has an id, a name, a public `fetch` URL, a language, a region, one or more desks (`world`, `regional`, `business`, `politics`, `technology`, `science`), and `enabled`. The format is `contracts/outlet.schema.json`.

Set `"enabled": false` to stop fetching an outlet. The next successful refresh drops its rows. A disabled outlet is not fetched.

The first set was checked live on 23 September 2026: BBC News (world, UK, business, politics, technology, science), The Guardian (world, business, science), The New York Times (U.S.), NPR (politics), and Ars Technica. Feeds that did not answer were not added.

## Markets

Market sources are recorded in `catalog/markets/sources.json`. One delayed source per family, checked on 23 September 2026:

| Family | Source | What it is |
| --- | --- | --- |
| Indices, equities, commodities | Yahoo Finance chart | Public delayed quotes. Stooq did not return a quote feed. |
| FX | Frankfurter | ECB reference rates, not a live dealing price. |
| Rates | US Treasury | Daily par yield curve. FRED is not enabled; it needs an API key. |
| Crypto | CoinGecko | Public simple price, labeled delayed because it is not an exchange feed. |

The operator's list is `catalog/markets/selection.json`. Set a family's `"enabled"` to false to hide it. A hidden family is not fetched and does not appear. Edit `instruments` to change the symbols. The panel does not add anything that is not in that list. The shipped list is S&P 500, Dow, Nasdaq 100, Apple, Microsoft, EURUSD, USDJPY, US 2-year, US 10-year, gold, WTI, Bitcoin, and Ethereum.

Each quote row shows the symbol, price, source, and a delayed marker. A positive change uses the theme `up` role and a negative change uses `down`. If the source did not send a change, the row leaves that cell empty.

## Trade

Trade sources are recorded in `catalog/trade/sources.json`. One public RSS feed per family, checked on 23 September 2026:

| Family | Source | What it is |
| --- | --- | --- |
| Policy | WTO | Official news RSS. No login and no API key. |
| Freight | FreightWaves | Public freight headlines. The Federal Maritime Commission feed was stale, so it is not used. |
| Supply chain | Supply Chain Dive | Public supply-chain headlines. |

The operator's list is `catalog/trade/selection.json`. Set a family's `"enabled"` to false to hide it. A hidden family is not fetched and does not appear. Each row shows the title, the source name, and the observed time. These panels are not the markets quote board.

## Weather

Weather uses Open-Meteo for the observation and the forecast, and the National Weather Service for active alerts. Both are public and need no API key. A place is fetched only when it has coordinates.

The primary home is `[home_place]` in `server/config.toml`. Further places are a list in `catalog/weather/places.json`. Each one needs an id, a name, a latitude, a longitude, and `"home"`. Set `"home": true` for another home, or `false` for a place that belongs on the storm desk only. Brief shows every home.

Weather news is a separate feed in `catalog/weather-news/`. The shipped outlets, checked on 23 September 2026, are the National Hurricane Center Atlantic outlook and the Storm Prediction Center. Set `"enabled": false` on an outlet to stop fetching it. Those stories appear on the storm desk only. Brief does not show them.

An alert marked severe or extreme uses the theme `down` role. Other severities use `warn`. When the alert source reports none, the panel says no alerts are active. It does not copy the forecast into that panel.

## Sports

Sports competitions are `catalog/sports/competitions.json`. Each entry has one coverage tier. A competition with no verified public source is omitted. Checked on 23 September 2026, with no multi-sport API key:

| Competition | Family | Tier | Source |
| --- | --- | --- | --- |
| Major League Baseball | baseball | `live` | MLB Stats API |
| National Hockey League | ice hockey | `live` | NHL |
| Bundesliga | football | `results` | OpenLigaDB finals, not in-play |
| Formula 1 | motorsport | `results` | Jolpica last-race classification, not live timing |

NBA's public scoreboard returned 403. OpenDota returned 522. NFL game scores are not in the catalog. Those families are absent, not labeled live.

Follows are `catalog/sports/follows.json`. Put a competition id in `competitions`, a family such as `baseball` in `sports`, or a competitor name in `competitors`. An empty file shows "Choose follows" and does not fetch scores. The field bay shows live and delayed follows, recent finals from the last 48 hours, and schedule follows as a time with no score. It does not show Far Desk rows or fantasy points. A failed first fetch names the competition and leaves the score blank. A later failure keeps the last score and marks the panel stale.

Far Desk lists only `far` entries. A result becomes one factual sentence, such as "North defeated South 2-1", labeled `factual line`. A report excerpt is shown as a quotation. Nothing is added. The shipped catalog has no `far` entry, so the bay is empty until one is verified.

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

The client prints the suggestion under the current panels. The panels stay as they are. Press `a` to start that desk. `applied` in the payload stays false until you do.

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
