## ADDED Requirements

### Requirement: Each bay owns a share of the board
The board SHALL give each shown bay its own rectangle. One bay MUST fill the screen. Two to four bays MUST each get one full-height column. Five to eight MUST use four columns and two rows. Nine to twelve MUST use four columns and three rows. The column count MUST NOT exceed the width band for the terminal.

#### Scenario: One bay
- **GIVEN** a board that shows only wires
- **WHEN** it renders
- **THEN** wires uses the whole screen above the status line

#### Scenario: Six bays
- **GIVEN** a board that shows six bays on a 240-column terminal
- **WHEN** it renders
- **THEN** the bays occupy four columns and two rows

### Requirement: A summarized bay rotates through its full data set
When a bay's rectangle cannot show all of its items, the bay SHALL show a page and MUST advance to the next page on a fixed interval until every item has been shown, then start again. The bay header MUST show the page position. The focused bay MUST NOT advance while the operator is moving the focus.

#### Scenario: Rotation
- **GIVEN** a wires bay with 40 items and room for 10
- **WHEN** four rotation intervals pass
- **THEN** all 40 items have been shown
- **AND** the header showed 1/4 through 4/4

### Requirement: The live mark follows the source poll
A panel header SHALL show a filled mark while the payload age is within the server poll interval for that domain plus a margin, a hollow mark after that, and the stale marker when the payload is stale. The mark MUST NOT alternate while the payload is unchanged and within that interval.

#### Scenario: Markets poll
- **GIVEN** a markets panel the server polls every 60 seconds
- **WHEN** the client redraws every second for 60 seconds after an update
- **THEN** the mark stays filled

### Requirement: Applying a suggestion on a board swaps the board
On a board, applying a suggestion SHALL replace the shown bays with the suggested desk's bays in the same window. A single-bay window MUST keep starting the desk as separate processes. Launched processes MUST NOT write into the current window.

#### Scenario: Board apply
- **GIVEN** a board showing wires and storm, and a suggestion for markets
- **WHEN** the operator presses `a`
- **THEN** the board shows markets
- **AND** no new window opens
