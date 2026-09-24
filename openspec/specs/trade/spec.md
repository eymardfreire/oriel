# trade Specification

## Purpose
TBD - created by archiving change establish-oriel-foundation. Update Purpose after archive.
## Requirements
### Requirement: Trade is its own domain
The trade domain SHALL serve policy, freight, and supply-chain items. A trade panel MUST NOT be the markets quote board. A markets panel MUST NOT be filled with trade policy headlines.

#### Scenario: Trade bay
- **GIVEN** the trade desk
- **WHEN** its bay renders
- **THEN** the bay includes policy, freight, and supply-chain panels
- **AND** those panels are not the markets quote rows

### Requirement: Operator can hide a trade family
The operator SHALL be able to hide policy, freight, or supply chain independently. A hidden family MUST NOT be fetched.

#### Scenario: Hide freight
- **GIVEN** freight is hidden
- **WHEN** the trade bay refreshes
- **THEN** no freight item is shown
- **AND** policy items still refresh

### Requirement: Trade items are attributed
Each trade item SHALL show its source name and observed time. The panel MUST NOT show an item with no source.

#### Scenario: Policy item
- **GIVEN** a policy item from an enabled source
- **WHEN** the policy panel renders it
- **THEN** the row shows the title, the source name, and the observed time

