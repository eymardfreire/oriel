## Purpose

Defines the news wire catalog: many outlets, grouped into desks, each headline attributed, and each outlet under operator control.

## ADDED Requirements

### Requirement: Outlets live in a catalog
The system SHALL keep news outlets in a catalog. Each entry MUST include a name, a fetch target, a language, a region, and one or more desks. A headline MUST show the outlet name and the observed time.

#### Scenario: Headline row
- **GIVEN** a fresh item from an enabled outlet
- **WHEN** a wires bay renders it
- **THEN** the row shows the headline, the outlet name, and the observed time

### Requirement: Operator controls outlets
The operator SHALL be able to enable or disable any catalog outlet. A disabled outlet MUST NOT be fetched and MUST NOT appear in a panel.

#### Scenario: Disable an outlet
- **GIVEN** an outlet that is currently enabled
- **WHEN** the operator disables it
- **THEN** later wire refreshes omit that outlet
- **AND** existing rows from that outlet are removed on the next successful refresh

### Requirement: Desks group headlines
The wires domain SHALL be able to group items into world, regional, business, politics, technology, and science desks. An item MUST appear only in the desks listed on its outlet or on the item. The wires domain MUST NOT place weather warnings or sports results in these desks.

#### Scenario: Technology desk
- **GIVEN** a technology desk panel
- **WHEN** the bay renders it
- **THEN** every row is tagged for the technology desk
- **AND** no row is a weather alert or a sports result

### Requirement: Empty wires stay empty
When no outlet is enabled, or none returned items, the wires panel SHALL render an empty state that names the wires domain. The panel MUST NOT fill the space with placeholder headlines.

#### Scenario: No outlets enabled
- **GIVEN** every news outlet is disabled
- **WHEN** a wires bay refreshes
- **THEN** the panel has no headline rows
- **AND** the empty state names the wires domain
