## Context

The markets bay is one cell. The client already pages it every 16 seconds, but the line budget is split into equal panel rows and the panels stay as tall as their first slice. A solo markets window, which is the current board, therefore shows `1/4` while the rest of the cell is blank. The change bar is a full-cell block, so it meets the box rules. The shipped list was last widened on 24 September 2026 and still cannot fill a large cell.

The server is the only process that fetches. Families are a closed set in the catalog, the contracts, and `FAMILIES`. Crypto already uses CoinGecko's market-cap list. The board grid is unchanged.

## Goals / Non-Goals

**Goals:**

- Spend the markets cell on fetched quotes. A later page holds only rows that did not fit.
- Keep the change bar off the panel rules without giving quotes a second line.
- Grow indices, equities, FX, rates, and commodities on the sources already recorded.
- Add sectors and bonds as families on the existing Yahoo chart kind, after a live check.

**Non-Goals:**

- A new source kind, an API key, or a login.
- Changing the board grid, the 16-second timer, pause, or any other bay's layout.
- Rescaling the bar to a percent. The bar stays the source's change, capped as it is today.
- Inventing a price when a symbol does not answer.

## Decisions

### The markets cell packs families down columns

Only a markets bay uses this layout. The client counts the lines the fetched families need, then picks the fewest columns that can hold them, never more than the width band. Families pack down a column in catalog order. Leftover lines in a column go to the family that still has unseen rows. A short cell that cannot give every visible family a few rows shows a smaller window of families and cycles the rest. `bayPageCount` uses that same page list, so the header and the timer stay in step.

Alternative: keep the equal row split and stretch empty boxes. That fills the border and still hides fetched quotes on later pages.

### The bar is a short block inside padding

The bar character is `▬`, which sits inside the line instead of filling it. Market panels keep one column of padding, including when the bay has several columns, and the quote is fitted to that inner width so the bar does not run into the rule. A quote stays one line. A missing change still draws no bar.

Alternative: a blank line between quotes. That restores air by hiding half the rows.

### Sectors and bonds reuse the Yahoo chart kind

Both families are `yahoo-chart` entries in the existing sources file. The poller does not grow a new fetcher. `FAMILIES` becomes indices, sectors, equities, london, europe, tokyo, hongkong, china, india, brazil, canada, korea, taiwan, australia, funds, fx, rates, bonds, commodities, crypto. The boards and funds were added later on 25 September 2026, on that same kind. Equities stays one US tape. A hidden family is still not fetched. Crypto's `top` list is unchanged.

The 25 September 2026 check: the chart endpoint returned the added indices, equities, commodities, sector ETFs, and bond ETFs. `^SSEC` returned 404, so Shanghai is `000001.SS`. Frankfurter returned the added pairs. The Treasury curve returned the added tenors. A symbol that failed is not in the selection.

Alternative: a volatility family for VIX alone. VIX is an index row. A one-row family spends a header and still looks empty.

## Risks / Trade-offs

- [About seventy Yahoo calls per refresh] → The poller already fetches that source eight at a time. One missed symbol keeps a cached quote or a blank price. It does not drop the family.
- [A narrow cell cycles families instead of showing every header] → The overflow is the later page. A wide cell has the room to show the families together.
- [An ambiguous-width bar glyph] → The previous bar was already an ambiguous block. The short block is the same width class, with padding so it cannot sit on the rule.
- [Old market state has no sectors or bonds panels] → The next refresh replaces stored panels. Restart the server. Do not delete or rewrite `client/state/board.json`.

## Migration Plan

Restart the server, then the client. No board-grid change and no new process. Rolling back is reverting the catalog and the markets layout; saved layouts do not store quotes.

## Open Questions

None. The operator asked for more of the existing categories and left the new categories to this pass.
