## MODIFIED Requirements

### Requirement: Weather news is its own feed
The weather-news domain SHALL list stories from enabled weather outlets and agencies. A weather-news panel MUST NOT display temperatures, forecasts, or alert polygons as if they were the observation panel. When a feed entry has a description, the row MUST carry it as `summary` with markup removed and the text trimmed. When the entry has no description, `summary` MUST be absent. The client MUST show `summary` only at full detail.

#### Scenario: Storm story
- **GIVEN** an enabled agency story about a storm
- **WHEN** the weather-news panel renders
- **THEN** the row shows the headline, the outlet, and the observed time
- **AND** the row does not replace the numeric forecast

#### Scenario: Description present
- **GIVEN** a feed entry whose description is non-empty after markup is removed
- **WHEN** the weather-news panel is built
- **THEN** the item fields include that text as `summary`
- **AND** the text is not written by Oriel

#### Scenario: Description absent
- **GIVEN** a feed entry with no description
- **WHEN** the weather-news panel is built
- **THEN** the item has no `summary` field
