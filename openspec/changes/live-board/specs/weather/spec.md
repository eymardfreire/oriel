## ADDED Requirements

### Requirement: Observation detail comes only from the source
An observation row SHALL show a glyph for the condition word when that word is present. The row MUST show apparent temperature, humidity, and wind speed only when the payload includes those numbers. A missing number MUST be omitted. The client MUST NOT invent a condition or a measurement.

#### Scenario: Known condition
- **GIVEN** an observation whose condition is rain and whose humidity is present
- **WHEN** the row renders
- **THEN** the row shows a rain glyph, the humidity, and the temperature
- **AND** it does not show a wind speed

#### Scenario: Condition missing
- **GIVEN** an observation with a temperature and no condition
- **WHEN** the row renders
- **THEN** the temperature is shown
- **AND** no weather glyph is shown
