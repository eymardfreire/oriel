# themes Specification

## Purpose
TBD - created by archiving change establish-oriel-foundation. Update Purpose after archive.
## Requirements
### Requirement: Themes are semantic palettes
A theme SHALL define the roles `bg`, `surface`, `border`, `text`, `muted`, `accent`, `up`, `down`, `warn`, `info`, and `stale`. Domain payloads MUST NOT contain color values. The client MUST color numbers and alerts only through these roles.

#### Scenario: Quote direction
- **GIVEN** a markets row whose change is positive
- **WHEN** the bay renders that row
- **THEN** the change uses the theme `up` role
- **AND** the headline text uses the theme `text` role

#### Scenario: Payload has no color
- **GIVEN** any panel payload
- **WHEN** a client reads it
- **THEN** the payload contains no color or theme instruction

### Requirement: Shipped themes
The system SHALL ship the themes `night`, `day`, `wire`, `paper`, `fog`, and `signal`. The default theme MUST be `night`. `day` and `paper` MUST be light themes. `night`, `wire`, `fog`, and `signal` MUST be dark themes.

#### Scenario: First launch
- **GIVEN** a bay with no theme selected
- **WHEN** the bay starts
- **THEN** it renders with the `night` theme

#### Scenario: Light bay
- **GIVEN** a bay whose theme is `day`
- **WHEN** the bay renders
- **THEN** the ground is the light palette
- **AND** the text uses the light palette ink role

### Requirement: Theme is per bay
The operator SHALL be able to set a theme on one bay without changing other bays.

#### Scenario: Mixed monitor
- **GIVEN** a wires bay on `paper` and a markets bay on `wire`
- **WHEN** both are visible
- **THEN** each bay uses only its own palette

### Requirement: Chrome stays minimal
The client SHALL render panels with hairline borders and no decorative frames. A panel header MUST show the panel title and, when stale, the stale marker. The client MUST NOT add a second chrome bar that repeats the terminal title.

#### Scenario: Fresh panel
- **GIVEN** a fresh headlines panel
- **WHEN** the bay renders it
- **THEN** the header shows the panel title
- **AND** no stale marker is shown

