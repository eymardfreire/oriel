## ADDED Requirements

### Requirement: A bay spends the lines it is given
A bay SHALL show fetched rows until the next row would cross the status line. A later page MUST contain only rows that did not fit. The page timer, the pause key, and the live mark MUST keep their current behavior.

#### Scenario: Tall markets cell
- **GIVEN** a markets cell with unread quotes below the first screen
- **WHEN** the bay renders
- **THEN** those quotes fill the remaining lines
- **AND** the status line stays on screen

#### Scenario: Short cell
- **GIVEN** a cell shorter than the fetched set
- **WHEN** the bay renders
- **THEN** the overflow waits on the next page
- **AND** the page label counts only that overflow

### Requirement: A quote is one line
A quote row SHALL render symbol, price, and change on one line. The delayed mark, source, and age MUST share that line when they fit. A missing price or a missing change MUST stay blank. The row MUST NOT wrap onto a second line.

#### Scenario: Narrow column
- **GIVEN** a quote column too narrow for the source and the age
- **WHEN** the row renders
- **THEN** the symbol and the price remain
- **AND** the row is still one line

### Requirement: Headlines keep a gap
A headline row SHALL be separated from the next headline by one blank line. A summary MUST be one line, cut to the column, and shown only at full detail.

#### Scenario: Two headlines
- **GIVEN** two headlines in one panel at full detail
- **WHEN** the panel renders
- **THEN** one blank line sits between them
- **AND** neither summary wraps onto a second line
