## ADDED Requirements

### Requirement: Global watch
The shipped places catalog SHALL include watched cities across every inhabited continent, grouped by region. The storm bay MUST group observations by region. Homes MUST stay on brief, and watched places MUST stay off brief.

#### Scenario: Region groups
- **GIVEN** the shipped places catalog
- **WHEN** the storm bay renders at full detail
- **THEN** observations are grouped under region headings

### Requirement: Extremes come only from fetched values
The storm bay SHALL show the hottest, coldest, wettest, and windiest watched places, computed only from places with a fetched value for that measure. A measure no place reported MUST be omitted.

#### Scenario: No wind values
- **GIVEN** no watched place reported wind
- **WHEN** the extremes strip renders
- **THEN** it has no windiest entry

### Requirement: Alert coverage is named
A place outside the coverage of any configured alert source SHALL say that no public alert source covers it. It MUST NOT say that no alerts are active.

#### Scenario: Tokyo
- **GIVEN** Tokyo is watched and only the National Weather Service is configured
- **WHEN** alerts render for Tokyo
- **THEN** the row says no public alert source covers Tokyo
