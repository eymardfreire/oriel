# Panel fields

A panel payload matches `panel.schema.json`. `fields` is domain data. The client picks a row renderer from `domain` plus `row`. Payloads do not carry colors, theme ids, or hex values.

`stale_reason` is an empty string when `stale` is false. A fixture sets `fixture` to true and is sample data, not a fetch.

`refresh_seconds` is the server poll interval for that panel's domain. The client fills the live mark while the payload age is within that interval plus 10 seconds. A fixture omits it, and the client then uses the bay refresh.

The domain id `situation` is reserved and is not a panel domain in this version.

## Row hints

| `row` | Used by | `fields` |
| --- | --- | --- |
| `headline` | `wires`, `trade`, `weather-news` | `desk` (string, optional) for wires. `family` (string, optional) for trade: `policy`, `freight`, or `supply-chain`. The headline is `title`. `summary` (string, optional) is the feed description with markup removed. Omit it when the feed has none. The client shows it only at full detail. For wires, `source` is the outlet name and `desk` is `world`, `regional`, `business`, `politics`, `technology`, or `science`. For trade, `source` is the feed name. A trade row is not a quote. |
| `quote` | `markets` | `symbol` (string), `price` (number), `change` (number, omit when unknown), `delayed` (boolean) |
| `observation` | `weather` | `place` (string), `temperature_c` (number, omit when unknown), `condition` (string, omit when unknown). `configured` (boolean) is true only when the place has coordinates. `home` (boolean) is true for a home place. Brief shows home rows only. |
| `score` | `sports` | `home`, `away` (strings), `league` (competition name), `score` (string, omit when unknown), `state` (string: `final`, `in progress`, or a scheduled time), `tier` (`live`, `delayed`, `results`, `schedule`, or `far`). A source clock is appended to `in progress` only when the feed gave one. A `schedule` row has no `score`. A Far Desk result sets `factual` true and may set `factual_line`. A report sets `excerpt` and is shown as a quotation. |
| `forecast` | `weather` | `period` (string), `temperature_high_c` and `temperature_low_c` (numbers, omit when unknown), `condition` (string, omit when unknown) |
| `alert` | `weather` | `severity` (string, omit on the empty state), `headline` (string). `severe` and `extreme` use the `down` role. Other severities use `warn`. |
| `clock` | brief | `time` (string) |
| `fantasy` | `sports` | `player`, `position`, `team`, `slot` (strings). `points` (number) and `week` only when a source supplied them for the scoring setting. `pinned` is true when that roster player is also pinned. Omit `points` when the source has none. The field bay does not use this row. |
| `follow` | `sports` | `competition_id` (string), `tier` (coverage tier), `followed` (boolean). When the catalog has them: `country`, `season`, `season_start`, `season_end`, `last_event`, `next_event` (`YYYY-MM-DD`), and `flag` (`active` or `off season`). The flag uses a start and end when both exist. Otherwise a game in the last 28 days is active, and a future next game after a longer gap is off season. The NFL flag follows Sleeper's `season_type` when that request answers. A follow row names a shipped competition. It is not a score, a fantasy pin, or a bay pin. |

A missing `change`, `temperature_c`, `score`, or `points` stays missing. The client does not render a fabricated zero.

`observation` is the weather row. The other row names are the renderers the client ships.
