## ADDED Requirements

### Requirement: Headlines carry the feed summary
A headline row SHALL include the summary text the feed provides, with markup removed. When the feed provides no summary, the row MUST show the headline alone and MUST NOT generate one.

#### Scenario: Feed with description
- **GIVEN** an RSS item with a title and a description
- **WHEN** a wires bay renders it at full detail
- **THEN** the row shows the title and the description text

#### Scenario: Feed without description
- **GIVEN** an RSS item with only a title
- **WHEN** it renders
- **THEN** only the title and its source line are shown

### Requirement: Outlets are verified before they ship
Each added outlet SHALL be fetched live before it is enabled. An outlet that does not answer MUST be left out of the catalog.

#### Scenario: Outlet down on check
- **GIVEN** a candidate outlet whose feed times out on the check
- **WHEN** the catalog is updated
- **THEN** that outlet is not added
