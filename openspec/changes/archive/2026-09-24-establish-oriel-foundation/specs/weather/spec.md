## Purpose

Defines numeric weather for places the operator watches: the latest observation, the forecast, and alerts, each as its own panel.

## ADDED Requirements

### Requirement: Watched places
The operator SHALL configure one or more watched places. The service MUST also accept one home place for the brief desk. Weather panels MUST use only those places.

#### Scenario: Home place on the brief desk
- **GIVEN** a configured home place
- **AND** no extra watched places
- **WHEN** the brief desk renders weather
- **THEN** the observation is for the home place

#### Scenario: Added place
- **GIVEN** the operator adds a second place
- **WHEN** a weather bay refreshes
- **THEN** both places are available as panels or rows
- **AND** no unconfigured place is shown

### Requirement: Observation, forecast, and alerts are distinct
The weather domain SHALL provide separate observation, forecast, and alert panels. An observation panel MUST show the latest conditions and the observation time. A forecast panel MUST show the upcoming periods the source provides. An alert panel MUST show active alerts, or an explicit empty state when none are active.

#### Scenario: No active alerts
- **GIVEN** a watched place with no active alerts
- **WHEN** the alert panel renders
- **THEN** the panel states that no alerts are active
- **AND** it does not copy forecast text into the alert panel

### Requirement: Alert severity is visible
An alert row SHALL show the source severity and MUST color that severity with the theme `warn` or `down` role according to the source severity mapping. The row MUST include the issuing source.

#### Scenario: Severe alert
- **GIVEN** an alert the source marks severe
- **WHEN** the alert panel renders it
- **THEN** the row shows the severity, the issuing source, and the headline
- **AND** the severity uses the `down` role

### Requirement: Missing weather is not estimated
When a place has no observation, the panel SHALL say the observation is unavailable. The service MUST NOT invent a temperature or a condition.

#### Scenario: Source unavailable
- **GIVEN** a watched place whose observation fetch failed and has no last good value
- **WHEN** the observation panel renders
- **THEN** the place is named
- **AND** no temperature is shown
