## MODIFIED Requirements

### Requirement: Applying a suggestion is explicit
The client SHALL show a suggestion as a suggestion. The line MUST name the desk, include the reason, and state that a keypress applies it. The client MUST NOT change the running panels until the operator applies the suggestion.

#### Scenario: Suggestion shown
- **GIVEN** a suggestion for the `three` desk because the New York session is open
- **WHEN** the bay displays it
- **THEN** the current panels stay as they are
- **AND** the line contains the desk id, the reason, and the apply key

#### Scenario: Operator applies it
- **GIVEN** a suggestion is visible
- **WHEN** the operator applies it
- **THEN** the launcher starts the suggested desk
