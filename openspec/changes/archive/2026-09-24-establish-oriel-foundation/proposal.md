## Why

Patch Notes Live proved a broadcast desk, and a later proposal sketched a Pi terminal that mirrored World Monitor. The hardware and the product have both moved. Aggregation now belongs on the Omarch machine, the viewer is any terminal, and the operator wants many windows on one monitor, each configured on its own. World Monitor overlaps the intelligence surface, but Oriel has to be a terminal-native desk with its own catalog, its own layouts, and a clean path into Second Brain.

## What Changes

- Establish Oriel as a new project, separate from Patch Notes Live.
- Specify the server/client split, the domain catalog, multi-window bays, themes, and Oriel's own recommendations.
- Cover markets, trade, news wires, weather, weather news, and sports, including a Far Desk for thinly covered sports and an NFL fantasy bay with a lineup and player pins.
- Leave implementation to later sections. This change is the constitution those sections build against.

## Capabilities

### New Capabilities

- `platform`: Server owns upstream access. Terminal bays render contracts. Domains stay detachable for Second Brain.
- `desks`: One OS window per bay. A desk is a named set of bays with shipped layouts.
- `themes`: Semantic color themes, including a minimal dark default and a light alternative.
- `recommendations`: Oriel-ranked desk and panel suggestions from session, follows, severity, and freshness.
- `wires`: News outlets the operator can enable, grouped into desks, always attributed.
- `markets`: Indices, FX, rates, commodities, and crypto, with delay and staleness labeled.
- `trade`: Policy, freight, and supply chain, kept apart from price quotes.
- `weather`: Observations, forecasts, and alerts for watched places.
- `weather-news`: Weather reporting as its own feed, separate from numeric observations.
- `sports`: A coverage-tiered sports catalog, operator follows, live scores only where a source supports them, Far Desk for the long tail, and an NFL fantasy bay where the operator selects a lineup and pins players to watch.

### Modified Capabilities

None.

## Impact

- New repository at `F:\MaxMax\DB\Oriel`. No Patch Notes Live code moves.
- Later sections add a Python aggregation server, a Go terminal client, and JSON contracts.
- Upstream sources are chosen per domain at implementation time from public or operator-keyed feeds. World Monitor is reference material only.
- No license file yet. Choose one before the repository is published.
