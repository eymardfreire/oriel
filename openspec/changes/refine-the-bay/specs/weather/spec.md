## MODIFIED Requirements

### Requirement: Watched places
The operator SHALL configure one or more watched places. The service MUST also accept one home place for the brief desk. Weather panels MUST use only those places. With no brief place chosen, the brief desk MUST show the home observation. A place chosen for the brief desk MUST be shown there and MUST NOT be marked home. Watched places that are not chosen MUST stay off the brief desk.

#### Scenario: Home place on the brief desk
- **GIVEN** a configured home place
- **AND** no brief place is chosen
- **WHEN** the brief desk renders weather
- **THEN** the observation is for the home place

#### Scenario: Added place
- **GIVEN** the operator adds a second place
- **WHEN** a weather bay refreshes
- **THEN** both places are available as panels or rows
- **AND** no unconfigured place is shown

#### Scenario: Chosen watched place on brief
- **GIVEN** a watched place that is not a home
- **WHEN** the operator chooses that place for the brief desk
- **THEN** the brief observation is for that place
- **AND** the place remains not a home
- **AND** the storm bay still lists it with the other watched places
