# Oriel — foundation change is complete

Read this first. Do not reopen product decisions that this file marks as locked unless the operator asks.

## Where we are

Tasks 1.1 through 7.3 are done. This change is ready to archive when the operator asks. Do not start a new change from this file.

- Folder: `F:\MaxMax\DB\Oriel`
- Git: initialized. Do not commit unless the operator asks.
- Active change: `establish-oriel-foundation`
- Next step, if asked: archive the change. Do not add outlets, feeds, or a new domain.

Verified in this session:

- `python -m pytest` in `server/` passed (51 tests).
- The Go client compiled. Windows application control still blocks running the test executable, so the client tests were not executed here.

## What the last section added

- `GET /suggestions` ranks a desk on the server from the cash-session clock, follows, alert severity, stale panels, a bay pin, a dismissal, and an in-progress game for a selected or pinned fantasy player. No third-party ranker.
- An open New York, London, or Asia session lifts markets. A severe or extreme alert lifts storm above that and the reason names the alert. A fantasy game lifts fantasy only when no cash session is open. The shipped feeds do not set `game_state`, so that lift stays off until a source provides it.
- Pin a bay with `POST /suggestions/pin` and `{"bay_id":"wires"}`. Dismiss a desk with `POST /suggestions/dismiss`. `POST /suggestions/clear` removes both. A fantasy player pin is not a bay pin.
- The client prints `suggestion`, the desk id, and the reason under the current panels. Those panels stay put. Press `a` to start the suggested desk.
- `go run . -desk three` starts one process per bay and prints each role. It does not tile windows. `three` starts wires, markets, and field. `fantasy` starts one fantasy bay.

## Locked decisions

- Name is Oriel. One OS window is a bay. A named set of bays is a desk.
- Server runs on the Omarch machine: Python 3.12, FastAPI. It is the only process that calls upstream sources.
- Client is Go, Bubble Tea, Lip Gloss. One process per window. Static binary, no Python on the viewing machine.
- Contracts in `contracts/` are the Second Brain boundary. Domain code must not import the TUI.
- Domains: `markets`, `trade`, `wires`, `weather`, `weather-news`, `sports`. `situation` is reserved and not built.
- Sports coverage tiers: `live`, `delayed`, `results`, `schedule`, `far`. Far Desk is factual templates and attributed excerpts only.
- NFL fantasy is the `fantasy` desk, one window. Default scoring is PPR. Points only when a public source has them. No ESPN, Yahoo, or Sleeper login, and no league import.
- Three different pins: a fantasy player pin, a bay pin for recommendations, and a follow. Do not merge them.
- Themes: `night` (default), `day`, `wire`, `paper`, `fog`, `signal`.
- Shipped desks: `brief`, `wires`, `markets`, `field`, `storm`, `trade`, `far`, `fantasy`, `three`.
- Recommendations are computed by Oriel. Applying one is explicit.
- Do not copy World Monitor. Do not call `api.worldmonitor.app`. Do not import Patch Notes Live.
- The trade desk does not show commodity or FX quotes.
- The test home is Tampa, Florida. Do not replace it unless the operator asks.

## Operator notes still open

- The test home is Tampa. Change it in `server/config.toml`. Add another home in `catalog/weather/places.json` with `"home": true`.
- No license file yet. Ask before the repository is published.
- A multi-sport API key is still unused. Ask before enabling one.
- Fantasy commands take a Sleeper player id.
- This Windows machine did not get a `py -3.12` launcher registration. `server/.venv` is already CPython 3.12.14.
- Go is 1.27.1 at `%LOCALAPPDATA%\Programs\go\bin`.

## How to continue

Archive only if the operator asks. The archive command is the OpenSpec archive for `establish-oriel-foundation`.
