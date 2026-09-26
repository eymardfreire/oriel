## Context

The board already clips each bay to its cell, pages on a 16-second timer, and pauses with `p`. A large cell still shows a short page and a blank remainder. Quote rows use two lines (price, then source and age). Storm repeats one "no public alert source" row per city outside the United States. Weather news stores the headline and drops the feed description (`server/oriel_server/weather/poller.py` builds the item with empty `fields`).

The client is the only place that knows the cell size. The server already returns the fetched rows. This change spends those rows. It does not add a source.

## Goals / Non-Goals

**Goals:**

- One density rule for every bay: leftover lines show more fetched rows.
- Markets and storm use the whole cell they are given.
- Weather news shows feed text when the feed has it, and nothing when it does not.
- The same spacing, live mark, page timer, and pause behavior on every bay.

**Non-Goals:**

- A new upstream source, an API key, or a new domain.
- Situation, a second application, or moving contracts into Second Brain.
- Changing pause, the page timer, themes, or the suggestion ranker.
- Inventing quotes, weather values, or story text.

## Decisions

### The client decides how many rows fit

The server keeps sending the fetched set. The client measures the cell and raises the row budget until the next row would cross the status line. A later page exists only for rows that do not fit.

Alternative: the server picks a count. It cannot see the window, so a 4K board and a half-screen board would get the same page.

### A quote is one line

Symbol, price, change bar, delayed mark, source, and age share one line. If the line is wider than the column, the age drops first, then the source. The price and the symbol stay. A missing price or change stays blank.

Alternative: keep the two-line quote and show fewer tickers. That leaves the cell empty, which is the current failure.

### Uncovered alerts collapse by region

Places with a real alert stay one row each. Places that have no public alert source become one row per region, naming the region, not every city. A region where alerts were checked and none are active still says no alerts are active.

Alternative: hide the uncovered state. The operator would not know the gap is coverage, not a failed fetch.

### Weather news reuses the wire summary

The RSS or Atom description, with markup removed and trimmed, is `summary` on the headline. No description means the field is absent. The client shows it only at full detail. The first pass of that work checks the shipped outlets live and records the date. An outlet whose entries have no description ships without summaries.

Alternative: fetch article pages. That is a new source path and is out of scope.

### Five passes, then stop

Each pass is a handoff gate. The agent does not start the next pass in the same turn.

1. Density rule and one-line quotes.
2. Markets fills its cell with fetched tickers.
3. Storm fills its cell and collapses uncovered alerts.
4. Weather news summaries, checked live.
5. The same rules on wires, trade, field, far, and fantasy, then tests and the handoff.

## Risks / Trade-offs

- [A one-line quote hides the source on a narrow column] → Age and source drop first. Symbol and price remain. The full row returns when the column is wider.
- [Collapsed alert lines hide which cities are uncovered] → The row names the region. The catalog still lists the cities.
- [A feed description is boilerplate or empty] → Omit it. Do not draft a substitute.
- [Showing more rows makes the page timer rare] → The timer stays. It only advances when a row did not fit.

## Migration Plan

Restart the client after passes 1, 2, 3, and 5. Restart the server after pass 4, because the weather-news payload grows a field. No catalog rewrite except the check date on the weather-news outlets.

## Open Questions

None. The pass count above is the plan.
