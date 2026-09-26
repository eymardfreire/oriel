## MODIFIED Requirements

### Requirement: Instrument families
The markets domain SHALL support the families indices, sectors, equities, london, europe, tokyo, hongkong, china, india, brazil, canada, korea, taiwan, australia, funds, fx, rates, bonds, commodities, and crypto. The operator MUST be able to hide a family. A hidden family MUST NOT be fetched.

#### Scenario: Hide crypto
- **GIVEN** the crypto family is hidden
- **WHEN** a markets bay refreshes
- **THEN** no crypto row is shown
- **AND** no crypto source is called

#### Scenario: Hide sectors
- **GIVEN** the sectors family is hidden
- **WHEN** a markets bay refreshes
- **THEN** no sectors row is shown
- **AND** the sectors source is not called

## ADDED Requirements

### Requirement: The markets cell spends its lines on fetched quotes
A markets bay SHALL pack its families down the columns of its cell and SHALL give leftover lines to a family that still has fetched rows. It MUST NOT leave those rows on a later page while the cell still has room. A cell too short for every family SHALL show a smaller set and cycle the rest. The page label MUST count only rows or families that did not fit. That label and the countdown mark MUST use the same form on every bay, and MUST stay in the text color when the bay is focused. Other bays MUST keep their current layout.

#### Scenario: Tall cell beside a short family
- **GIVEN** a markets cell with a short family and a longer family that does not fit an equal split
- **WHEN** the bay renders
- **THEN** every row of the short family is visible
- **AND** the leftover lines show the next rows of the longer family

#### Scenario: Short cell
- **GIVEN** a markets cell too short to show every family with a few rows
- **WHEN** the bay renders
- **THEN** the families that do not fit wait on a later page
- **AND** the page label counts that overflow

#### Scenario: Focused bay
- **GIVEN** a markets bay that is paging and is the focused bay
- **WHEN** the bay renders
- **THEN** the page label and the countdown mark are shown
- **AND** the page label stays in the text color

### Requirement: The change bar stays off the rules
A quote with a change SHALL draw a bar shorter than the line box, on that same line, with a gap between the bar and the panel border. A quote with no change MUST NOT draw a bar. The row MUST NOT wrap onto a second line.

#### Scenario: Positive change
- **GIVEN** a quote with a positive change
- **WHEN** the row renders
- **THEN** the bar is drawn on the quote line
- **AND** the bar is not a full-cell block

#### Scenario: Missing change
- **GIVEN** a quote with a price and no change
- **WHEN** the row renders
- **THEN** no bar is drawn

### Requirement: Sectors and bonds use the recorded chart source
Sectors and bonds SHALL be fetched from the Yahoo chart source already recorded for indices. Each row MUST be an instrument in that family's selection. An instrument the source did not price MUST show the symbol with an empty price and no change bar. The shipped wider list MUST contain only symbols checked live on 25 September 2026. Shanghai MUST use the query that answered. The query that returned 404 MUST NOT be shipped.

#### Scenario: Unpriced symbol
- **GIVEN** a shipped sector or bond the source did not return
- **WHEN** the markets bay renders
- **THEN** the symbol is shown with no price
- **AND** no change and no bar are drawn

#### Scenario: Shanghai
- **GIVEN** the shipped index list
- **WHEN** the catalog is loaded
- **THEN** Shanghai's query is the symbol that returned a price
- **AND** the query that returned 404 is absent

### Requirement: Exchange boards and funds use the recorded chart source
London, Europe, Tokyo, Hong Kong, China, India, Brazil, Canada, Korea, Taiwan, Australia, and funds SHALL be fetched from the Yahoo chart source already recorded for indices. Equities SHALL stay the US tape and MUST NOT be split into a NYSE family and a Nasdaq family. An exchange index that is already in the indices family MUST stay there. Each shipped row MUST be an instrument checked live on 25 September 2026. A query that returned 404 MUST NOT be shipped. A fund title MUST name the venue where that fund trades. The quote line MUST still show the symbol.

#### Scenario: US tape
- **GIVEN** the shipped equities list
- **WHEN** the catalog is loaded
- **THEN** the US names stay in equities
- **AND** there is no NYSE family and no Nasdaq family

#### Scenario: Roche
- **GIVEN** the shipped Europe list
- **WHEN** the catalog is loaded
- **THEN** Roche's query is absent

#### Scenario: Fund venue
- **GIVEN** the shipped funds list
- **WHEN** the catalog is loaded
- **THEN** each fund title names its venue
- **AND** the row symbol is the fund ticker
