## Purpose

Defines bays as independent terminal windows and desks as named sets of those windows, including the layouts Oriel ships.

## ADDED Requirements

### Requirement: One bay is one terminal window
The system SHALL run each bay as its own client process so the operator can place it in its own OS window. A bay MUST keep its own layout, theme, and panel list.

#### Scenario: Two windows
- **GIVEN** a desk with a wires bay and a markets bay
- **WHEN** the operator starts that desk
- **THEN** two client processes are running
- **AND** each process renders only its own bay

#### Scenario: Independent configuration
- **GIVEN** a wires bay on the night theme and a markets bay on the wire theme
- **WHEN** both bays are running
- **THEN** changing the wires theme does not change the markets theme

### Requirement: A layout places panels and does not fetch
A bay layout SHALL be one of `strip`, `stack`, `split`, or `dense`. The layout MUST only place panels the bay already has. Switching layout MUST NOT change which sources are fetched.

#### Scenario: Dense markets
- **GIVEN** a markets bay with four quote panels
- **WHEN** the operator selects the dense layout
- **THEN** those four panels are placed in the dense grid
- **AND** the fetched sources stay the same

### Requirement: Shipped desks
The system SHALL ship these desks: `brief`, `wires`, `markets`, `field`, `storm`, `trade`, `far`, `fantasy`, and `three`. The `three` desk SHALL contain the wires, markets, and field bays. The `fantasy` desk SHALL contain one fantasy bay. The operator MUST be able to start any shipped desk by name.

#### Scenario: Start the three desk
- **GIVEN** the shipped desk catalog
- **WHEN** the operator starts `three`
- **THEN** the wires, markets, and field bays start
- **AND** the fantasy bay does not start

#### Scenario: Start the fantasy desk
- **GIVEN** the shipped desk catalog
- **WHEN** the operator starts `fantasy`
- **THEN** one fantasy bay starts
- **AND** the field bay does not start

### Requirement: Window placement stays with the operator
The launcher SHALL start one terminal process per bay and MUST report the intended arrangement. The launcher MUST NOT claim to tile or position OS windows.

#### Scenario: Desk launch
- **GIVEN** the operator starts the `three` desk
- **WHEN** the launcher finishes
- **THEN** three processes are running
- **AND** the launcher output names each bay and its intended role
