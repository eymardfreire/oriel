## Purpose

Defines weather reporting as a news feed of its own, separate from observations, forecasts, and alerts.

## ADDED Requirements

### Requirement: Weather news is its own feed
The weather-news domain SHALL list stories from enabled weather outlets and agencies. A weather-news panel MUST NOT display temperatures, forecasts, or alert polygons as if they were the observation panel.

#### Scenario: Storm story
- **GIVEN** an enabled agency story about a storm
- **WHEN** the weather-news panel renders
- **THEN** the row shows the headline, the outlet, and the observed time
- **AND** the row does not replace the numeric forecast

### Requirement: Default desks keep the feeds apart
The storm desk SHALL include both weather panels and the weather-news panel. The brief desk MUST use the numeric weather panel and MUST NOT replace it with weather news.

#### Scenario: Brief desk
- **GIVEN** the brief desk
- **WHEN** it renders
- **THEN** a numeric weather panel is present
- **AND** the weather-news panel is absent

### Requirement: Operator can disable weather outlets
The operator SHALL be able to disable a weather-news outlet. A disabled outlet MUST NOT be fetched.

#### Scenario: Disable an agency feed
- **GIVEN** a weather agency outlet that is enabled
- **WHEN** the operator disables it
- **THEN** the next refresh omits that outlet

### Requirement: Alerts can raise weather news in suggestions
When a watched place has an active alert, the recommendation service SHALL be able to raise weather-news items about that alert. The items MUST still be sourced stories, not a restatement written by Oriel.

#### Scenario: Alert-linked story
- **GIVEN** an active alert and a sourced story that the catalog links to that alert
- **WHEN** a suggestion is computed
- **THEN** that story is eligible to rank above ordinary weather news
- **AND** the story row still names its outlet
