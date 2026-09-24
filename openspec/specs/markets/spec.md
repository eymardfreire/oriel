# markets Specification

## Purpose
TBD - created by archiving change establish-oriel-foundation. Update Purpose after archive.
## Requirements
### Requirement: Instrument families
The markets domain SHALL support the families indices, equities, fx, rates, commodities, and crypto. The operator MUST be able to hide a family. A hidden family MUST NOT be fetched.

#### Scenario: Hide crypto
- **GIVEN** the crypto family is hidden
- **WHEN** a markets bay refreshes
- **THEN** no crypto row is shown
- **AND** no crypto source is called

### Requirement: Watchlists
The operator SHALL be able to choose the instruments shown for equities, FX pairs, and crypto. An index, rate, or commodity row MUST come from the operator's selected set for that family. The panel MUST NOT add instruments the operator did not select.

#### Scenario: Two FX pairs
- **GIVEN** the operator selected EURUSD and USDJPY
- **WHEN** the FX panel renders
- **THEN** only those pairs appear

### Requirement: Delayed quotes are labeled
When a source is delayed, the row SHALL include a delayed marker and MUST still show the source name. The row MUST NOT be presented as real-time.

#### Scenario: Delayed index
- **GIVEN** an index quote flagged delayed by its source
- **WHEN** the markets bay renders that row
- **THEN** the row shows the price, the change, the source name, and a delayed marker

### Requirement: Direction uses theme roles
A positive change SHALL render with the theme `up` role and a negative change SHALL render with the theme `down` role. A missing change MUST render with the `muted` role and MUST NOT show a fabricated zero.

#### Scenario: Missing change
- **GIVEN** a quote with a price and no change value
- **WHEN** the row renders
- **THEN** the price is shown
- **AND** the change cell is muted and empty of a number

