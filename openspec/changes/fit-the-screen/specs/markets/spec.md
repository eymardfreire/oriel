## ADDED Requirements

### Requirement: The markets cell shows the fetched tickers that fit
The markets bay SHALL render as many fetched instruments as the cell can hold, family by family. It MUST NOT leave a blank remainder while a fetched ticker for that family is waiting on a later page. It MUST NOT add an instrument that was not fetched. A missing price stays blank.

#### Scenario: Crypto beside a short family
- **GIVEN** a markets cell tall enough for the index list and part of the crypto list
- **WHEN** the bay renders
- **THEN** every fetched index is visible
- **AND** the visible crypto rows are the next fetched coins, with no blank block above the fold

#### Scenario: Missing price
- **GIVEN** a fetched symbol with no price
- **WHEN** the row renders
- **THEN** the symbol is shown
- **AND** the price cell is empty
