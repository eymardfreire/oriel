# recommendations Specification

## Purpose
TBD - created by archiving change establish-oriel-foundation. Update Purpose after archive.
## Requirements
### Requirement: Suggestions are computed by Oriel
The service SHALL compute desk and panel suggestions on the server. The suggestion MUST be derived from market-session time, operator follows, alert severity, freshness, and in-progress NFL games for players on the fantasy roster or pin list. The service MUST NOT present a third-party ranking as Oriel's suggestion.

#### Scenario: New York session
- **GIVEN** the New York market session is open
- **AND** no weather alert is active
- **WHEN** the operator asks for a suggestion
- **THEN** the suggestion favors the markets bay
- **AND** the reason text mentions the market session

#### Scenario: Fantasy player in progress on a closed market day
- **GIVEN** the New York market session is closed
- **AND** a selected fantasy player's NFL game is in progress
- **WHEN** the operator asks for a suggestion
- **THEN** the suggestion favors the fantasy desk
- **AND** the reason text names that player

#### Scenario: Active weather alert
- **GIVEN** a severe weather alert for a watched place
- **WHEN** the operator asks for a suggestion
- **THEN** the suggestion raises the storm bay above its idle rank
- **AND** the reason text names the alert

### Requirement: Pins and dismissals outrank the ranker
The operator SHALL be able to pin a bay and dismiss a suggestion. A pin or a dismissal MUST outrank the computed suggestion until the operator clears it.

#### Scenario: Pinned wires during a market session
- **GIVEN** the wires bay is pinned
- **AND** a market session is open
- **WHEN** the operator asks for a suggestion
- **THEN** the wires bay remains the leading suggestion
- **AND** the reason text says the bay is pinned

### Requirement: Applying a suggestion is explicit
The client SHALL show a suggestion as a suggestion, including the desk id and a one-line reason. The client MUST NOT change the running bays until the operator applies the suggestion.

#### Scenario: Suggestion shown
- **GIVEN** a suggestion for the `three` desk
- **WHEN** the bay displays it
- **THEN** the current panels stay as they are
- **AND** the suggestion shows the desk id and the reason

#### Scenario: Operator applies it
- **GIVEN** a suggestion is visible
- **WHEN** the operator applies it
- **THEN** the launcher starts the suggested desk

