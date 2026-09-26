## ADDED Requirements

### Requirement: Refine follows the focused bay
On a board or a single bay, `f` SHALL open the refine list for the focused bay and MUST NOT open another bay's list. The status line MUST name that action for field, sideline, and brief, and MUST omit `f` for a bay that has no list. Pressing `f` on a bay with no list MUST leave every list closed and MUST say that bay has nothing to choose.

#### Scenario: Field is focused
- **GIVEN** the field bay is focused
- **WHEN** the operator presses `f`
- **THEN** the competition follow list opens
- **AND** the sideline sport list stays closed

#### Scenario: Sideline is focused
- **GIVEN** the sideline bay is focused
- **WHEN** the operator presses `f`
- **THEN** the sport list opens
- **AND** the field follow list stays closed

#### Scenario: Another bay is focused while field is open
- **GIVEN** the field bay is on the board
- **AND** the focused bay is not field, sideline, or brief
- **WHEN** the operator presses `f`
- **THEN** the field follow list stays closed
- **AND** the status line says that bay has nothing to choose

### Requirement: Brief chooses place, outlet, and family
The brief bay SHALL let the operator choose one place, one wire outlet, and one market family from the shipped catalogs. The choice MUST be written through the server. An id that is not in the matching catalog MUST be rejected and the selection file MUST stay unchanged. An empty choice for a slot MUST keep that slot on its default: the configured home, the first live headline, and the first live quote.

#### Scenario: Choose a place
- **GIVEN** an empty brief selection
- **WHEN** the operator selects a shipped place from the brief list
- **THEN** the selection file records that place
- **AND** the brief observation is for that place

#### Scenario: Unknown outlet
- **WHEN** the client posts an outlet id that is not an enabled wire outlet
- **THEN** the server rejects it
- **AND** the selection file is unchanged

#### Scenario: Defaults
- **GIVEN** an empty brief selection
- **AND** the server has a home observation, a wire headline, and a market quote
- **WHEN** the brief bay renders
- **THEN** the observation is the home place
- **AND** the headline is the first live headline
- **AND** the quote is the first live quote

### Requirement: A missing brief value stays missing
When the chosen place has no observation, the brief weather row MUST keep the fixture or the last good observation and MUST NOT invent a temperature. When the chosen outlet has no headline, the brief wire row MUST keep the previous headline and MUST NOT invent one. When the chosen family has no quote, the brief quote row MUST keep the last good quote if one exists, and a missing price MUST stay blank.

#### Scenario: Place has no observation
- **GIVEN** the operator has chosen a shipped place
- **AND** that place has no observation
- **WHEN** the brief bay renders weather
- **THEN** no temperature is invented for that place

#### Scenario: Family quote has no price
- **GIVEN** the operator has chosen a market family
- **AND** the lead instrument in that family has no price
- **WHEN** the brief bay renders the quote
- **THEN** the price is blank

### Requirement: Far Desk has no refine list
The far bay MUST NOT open a refine list. When the catalog has no `far` competition, `f` on that bay MUST say it has nothing to choose, and the bay MUST keep the sentence that no far-coverage competition is configured.

#### Scenario: Empty far catalog
- **GIVEN** no competition is tiered `far`
- **AND** the far bay is focused
- **WHEN** the operator presses `f`
- **THEN** no list opens
- **AND** the bay still says no far-coverage competition is configured
