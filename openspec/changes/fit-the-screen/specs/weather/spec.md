## ADDED Requirements

### Requirement: Storm fills the cell with the global picture
The storm bay SHALL use its cell for fetched observations, forecasts, and alerts, grouped by region. A measure nobody reported MUST stay off the row. The bay MUST NOT leave a blank remainder while a fetched place is waiting on a later page.

#### Scenario: Tall storm cell
- **GIVEN** more fetched places than the first screen
- **WHEN** the storm bay renders in a tall cell
- **THEN** later places from those regions fill the remaining lines
- **AND** a place with no temperature omits the temperature

### Requirement: Uncovered alerts collapse by region
Places with no public alert source SHALL share one row per region naming that region. A place with an active alert MUST keep its own row. A covered place with no active alert MUST still say that no alerts are active.

#### Scenario: Several uncovered cities in one region
- **GIVEN** Oceania places with no public alert source
- **WHEN** the alert panel renders
- **THEN** those places are one row for the region
- **AND** they are not one row per city
