## ADDED Requirements

### Requirement: A board composes selected bays in one window
The client SHALL open a board as one process that renders more than one bay in a single terminal. The operator MUST be able to choose which shipped bays appear. A bay that is not chosen MUST NOT be fetched for that board. Starting a named desk MUST still start one process per bay.

#### Scenario: Default board
- **WHEN** the operator starts a board with no saved selection
- **THEN** the window shows the wires, markets, storm, and trade bays
- **AND** the field bay is not fetched

#### Scenario: Operator hides a bay
- **GIVEN** a board that is showing markets
- **WHEN** the operator turns markets off in settings
- **THEN** the markets panels leave the window
- **AND** the choice is still in effect the next time the board starts

### Requirement: Density follows the terminal cell grid
The client SHALL choose the number of panel columns from the terminal width. Fewer than 100 columns MUST use one column. At least 100 and fewer than 160 MUST use two. At least 160 and fewer than 240 MUST use three. 240 or more MUST use four. Extra rows MUST show more items in the panels that have them. The client MUST NOT read the monitor's pixel resolution.

#### Scenario: Wide terminal
- **GIVEN** a terminal that is 240 columns wide
- **WHEN** a markets bay with six panels renders
- **THEN** those panels occupy four columns

#### Scenario: Narrow terminal
- **GIVEN** a terminal that is 80 columns wide
- **WHEN** the same bay renders
- **THEN** the panels occupy one column

### Requirement: Settings are reachable from the bay
The client SHALL open a settings overlay on `?`. The overlay MUST list the shipped themes and, on a board, each shipped bay with whether it is shown. `t` MUST cycle the theme for that window only. Closing the overlay MUST leave the panels in place.

#### Scenario: Theme cycle
- **GIVEN** a window on the night theme
- **WHEN** the operator presses `t`
- **THEN** the window uses the next shipped theme
- **AND** no other window changes

#### Scenario: Help does not navigate away
- **GIVEN** a visible settings overlay
- **WHEN** the operator closes it
- **THEN** the same panels are still shown

### Requirement: The board looks live without inventing values
The client SHALL refresh relative ages and the clock every second. A panel header MUST show a live mark when the payload is within its refresh interval, an aging mark when it is older and not stale, and the stale marker when the payload is stale. A quote row MUST draw a short bar from the absolute change when a change number is present, and MUST omit the bar when the change is missing. The signed change MUST still use the theme `up` or `down` role.

#### Scenario: Fresh quote
- **GIVEN** a quote panel updated within its refresh interval and a negative change
- **WHEN** the row renders
- **THEN** the header shows a live mark
- **AND** the change uses the `down` role
- **AND** a bar is drawn from that change

#### Scenario: Missing change
- **GIVEN** a quote whose payload has no change
- **WHEN** the row renders
- **THEN** no bar is drawn
- **AND** the change cell is empty
