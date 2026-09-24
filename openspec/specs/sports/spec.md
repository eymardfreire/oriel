# sports Specification

## Purpose
TBD - created by archiving change establish-oriel-foundation. Update Purpose after archive.
## Requirements
### Requirement: Coverage tiers
Each sports catalog entry SHALL have one coverage tier: `live`, `delayed`, `results`, `schedule`, or `far`. The field bay MUST show `live` and `delayed` entries that the operator follows, and recent finals for `results` entries the operator follows. The field bay MUST NOT present a `schedule` or `far` entry as a live score.

#### Scenario: Live follow
- **GIVEN** a followed competition tiered `live` with an in-progress score
- **WHEN** the field bay renders
- **THEN** the row shows the competitors, the score, and the in-progress state
- **AND** the row names the source

#### Scenario: Schedule-only follow
- **GIVEN** a followed competition tiered `schedule`
- **WHEN** the field bay renders
- **THEN** the row shows the fixture time and the competitors
- **AND** the row has no score

### Requirement: Operator follows
The operator SHALL choose sports, competitions, or competitors to follow. A sports panel MUST be limited to those follows. If the operator has no follows, the field bay SHALL show an empty state that tells the operator to choose follows.

#### Scenario: No follows
- **GIVEN** an empty follow list
- **WHEN** the field bay renders
- **THEN** no score rows are shown
- **AND** the empty state tells the operator to choose follows

### Requirement: Delayed scores are labeled
A `delayed` score SHALL show a delayed marker. The client MUST NOT present it as live.

#### Scenario: Delayed match
- **GIVEN** a followed competition tiered `delayed` with a score
- **WHEN** the row renders
- **THEN** the score is shown with a delayed marker and the source name

### Requirement: Missing scores stay missing
If a `live` source misses a refresh and there is no last good score, the row SHALL name the competition and MUST NOT invent a score. If a last good score exists, the row SHALL keep it and MUST set the stale flag.

#### Scenario: First fetch fails
- **GIVEN** a live follow with no prior score
- **WHEN** the fetch fails
- **THEN** the row names the competition
- **AND** no score digits are shown

### Requirement: Far Desk uses sourced facts only
The `far` desk SHALL list catalog entries tiered `far`. A Far Desk item MUST contain only a schedule, a result, or a report excerpt, each with a source. A one-line factual sentence MUST be a template filled from those facts and MUST be labeled as a factual line. The system MUST NOT add events, quotes, or color commentary that the source does not contain. A competition with no verified public source MUST be absent from the catalog.

#### Scenario: Sourced result
- **GIVEN** a far-tier competition with a final result and a source
- **WHEN** the far desk renders it
- **THEN** the row shows the competitors, the result, the source, and a factual-line label

#### Scenario: Report excerpt
- **GIVEN** a far-tier item whose source is a report excerpt
- **WHEN** the far desk renders it
- **THEN** the excerpt is shown as a quotation with the source name
- **AND** no sentence adds an event beyond the excerpt

#### Scenario: No public source
- **GIVEN** a competition with no verified public schedule, result, or report
- **WHEN** the catalog is built
- **THEN** that competition is not listed

### Requirement: Fantasy football is its own bay
The sports domain SHALL provide an NFL fantasy bay named `fantasy`. That bay MUST be organized as a pin strip, then a lineup, then a bench. The lineup slots MUST be QB, RB, RB, WR, WR, TE, FLEX, K, and DST, in that order. Empty slots MUST remain visible. The field bay MUST NOT list fantasy points or fantasy slots.

#### Scenario: Empty fantasy bay
- **GIVEN** no pinned players and no selected players
- **WHEN** the fantasy bay renders
- **THEN** the pin strip is empty
- **AND** every lineup slot is visible and empty
- **AND** the field bay has no fantasy rows

### Requirement: Selecting a player fills the roster
The operator SHALL be able to select a player from the NFL fantasy catalog onto the roster. A selected player MUST occupy the first open starting slot for that player's position. When those slots are full, the player MUST go to the bench. A flex-eligible player MUST move into the FLEX slot only when the operator assigns FLEX. The same player MUST NOT be selected twice.

#### Scenario: First running back
- **GIVEN** both RB slots are empty
- **WHEN** the operator selects a running back
- **THEN** that player occupies the first RB slot
- **AND** the second RB slot stays empty

#### Scenario: Running backs already filled
- **GIVEN** both RB slots are filled
- **AND** the FLEX slot is empty
- **WHEN** the operator selects another running back
- **THEN** that player is placed on the bench
- **AND** the FLEX slot stays empty

#### Scenario: Assign flex
- **GIVEN** a running back on the bench
- **AND** an empty FLEX slot
- **WHEN** the operator assigns that player to FLEX
- **THEN** the player occupies the FLEX slot
- **AND** the player is no longer on the bench

#### Scenario: Select the same player again
- **GIVEN** a player already on the roster
- **WHEN** the operator selects that player again
- **THEN** the roster is unchanged

### Requirement: Pinning a player builds a watch strip
The operator SHALL be able to pin any catalog player, whether or not that player is selected. Pinned players MUST appear in the pin strip, most recently pinned first. A pin MUST NOT add the player to the lineup. Removing a player from the roster MUST NOT unpin that player. Unpinning a player MUST NOT remove that player from the roster. A selected player who is also pinned MUST show a pin marker on the lineup or bench row.

#### Scenario: Pin a player who is not selected
- **GIVEN** a catalog player who is not on the roster
- **WHEN** the operator pins that player
- **THEN** the player appears at the top of the pin strip
- **AND** the lineup slots are unchanged

#### Scenario: Unpin keeps the roster spot
- **GIVEN** a selected player who is also pinned
- **WHEN** the operator unpins that player
- **THEN** the player leaves the pin strip
- **AND** the player remains in the same roster slot

### Requirement: Fantasy figures come from a source
A fantasy row SHALL show the player name, position, and NFL team from the catalog. Opponent, game state, bye week, injury designation, and fantasy points MUST appear only when a source provided them for the operator's scoring setting. The scoring setting MUST be one of `ppr`, `half-ppr`, or `standard`, and the default MUST be `ppr`. The row MUST name the source of any points. The system MUST NOT invent points, projections, or injury tags.

#### Scenario: Points available
- **GIVEN** a selected player
- **AND** the scoring setting is `ppr`
- **AND** the source has PPR points for the current NFL week
- **WHEN** the fantasy bay renders that row
- **THEN** the row shows those points, the week, and the source name

#### Scenario: Points missing
- **GIVEN** a pinned player with no points from the source
- **WHEN** the pin strip renders that player
- **THEN** the row shows the name, position, and team
- **AND** the points cell is empty

### Requirement: Fantasy roster is Oriel's
The roster and the pin list SHALL be stored by Oriel for the operator. The system MUST NOT require an ESPN, Yahoo, or Sleeper login to select or pin a player. The system MUST NOT import an outside league roster in this change.

#### Scenario: Select without a league login
- **GIVEN** no fantasy-host account is configured
- **WHEN** the operator selects a catalog player
- **THEN** the player is added to the Oriel roster

