## ADDED Requirements

### Requirement: A suggestion for the current view is not shown
The client SHALL hide the suggestion when the suggested desk's bays are all already shown in that window. The client MUST show it again when the suggestion changes to a desk that is not shown.

#### Scenario: Markets already shown
- **GIVEN** a window showing the markets bay and a suggestion for the markets desk
- **WHEN** the status line renders
- **THEN** no suggestion is shown

#### Scenario: Different desk
- **GIVEN** a window showing wires and a suggestion for storm
- **WHEN** the status line renders
- **THEN** the suggestion names storm and the apply key
