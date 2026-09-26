## ADDED Requirements

### Requirement: Follows are chosen in the client
The field bay SHALL let the operator pick followed competitions from the shipped competition catalog. The choice MUST be written through the server and MUST reject an id that is not in the catalog. After a follow is saved, the next field refresh MUST fetch that competition.

#### Scenario: Follow MLB
- **GIVEN** an empty follows file
- **WHEN** the operator follows `mlb` from the field bay
- **THEN** the follows file lists `mlb`
- **AND** the field bay shows MLB games or an empty state that names MLB

#### Scenario: Unknown id
- **WHEN** the client posts a follow for an id not in the catalog
- **THEN** the server rejects it
- **AND** the follows file is unchanged

### Requirement: Far Desk says why it is empty
When no competition has the `far` tier, the Far Desk SHALL say that no far-coverage competition is configured. It MUST NOT show fabricated rows.

#### Scenario: Shipped catalog
- **GIVEN** a competition catalog with no `far` entry
- **WHEN** the Far Desk renders
- **THEN** it says no far-coverage competition is configured
