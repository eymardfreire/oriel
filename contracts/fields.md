# Panel fields

A panel payload matches `panel.schema.json`. `fields` is domain data. The client picks a row renderer from `domain` plus `row`. Payloads do not carry colors, theme ids, or hex values.

`stale_reason` is an empty string when `stale` is false. A fixture sets `fixture` to true and is sample data, not a fetch.

The domain id `situation` is reserved and is not a panel domain in this version.

## Row hints

| `row` | Used by | `fields` |
| --- | --- | --- |
| `headline` | `wires`, `trade`, `weather-news` | `desk` (string, optional) for wires. `family` (string, optional) for trade: `policy`, `freight`, or `supply-chain`. The headline is `title`. For wires, `source` is the outlet name and `desk` is `world`, `regional`, `business`, `politics`, `technology`, or `science`. For trade, `source` is the feed name. A trade row is not a quote. |
| `quote` | `markets` | `symbol` (string), `price` (number), `change` (number, omit when unknown), `delayed` (boolean) |
| `observation` | `weather` | `place` (string), `temperature_c` (number, omit when unknown), `condition` (string, omit when unknown). `configured` (boolean) is true only when the place has coordinates. `home` (boolean) is true for a home place. Brief shows home rows only. |
| `score` | `sports` | `home`, `away` (strings), `score` (string, omit when unknown), `state` (string), `tier` (`live`, `delayed`, `results`, `schedule`, or `far`). A `schedule` row has no `score`. A Far Desk result sets `factual` true and may set `factual_line`. A report sets `excerpt` and is shown as a quotation. |
| `forecast` | `weather` | `period` (string), `temperature_high_c` and `temperature_low_c` (numbers, omit when unknown), `condition` (string, omit when unknown) |
| `alert` | `weather` | `severity` (string, omit on the empty state), `headline` (string). `severe` and `extreme` use the `down` role. Other severities use `warn`. |
| `clock` | brief | `time` (string) |
| `fantasy` | `sports` | `player`, `position`, `team`, `slot` (strings). `points` (number) and `week` only when a source supplied them for the scoring setting. `pinned` is true when that roster player is also pinned. Omit `points` when the source has none. The field bay does not use this row. |

A missing `change`, `temperature_c`, `score`, or `points` stays missing. The client does not render a fabricated zero.

`observation` is the weather row. The other row names are the renderers the client ships.
