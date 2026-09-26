## ADDED Requirements

### Requirement: Nine saved layouts
The board SHALL store up to nine layouts. A layout MUST record the shown bays, their order, and the theme. The operator MUST be able to save the current board into a numbered slot, load a slot by number, and cycle through occupied slots. Loading an empty slot MUST leave the board unchanged and say the slot is empty.

#### Scenario: Save and load
- **GIVEN** a board showing wires and markets on the wire theme
- **WHEN** the operator saves slot 3, changes the board, and loads slot 3
- **THEN** the board shows wires and markets on the wire theme

#### Scenario: Empty slot
- **GIVEN** slot 7 is empty
- **WHEN** the operator loads slot 7
- **THEN** the board is unchanged
- **AND** the status line says slot 7 is empty

#### Scenario: Survives restart
- **GIVEN** a saved slot 2
- **WHEN** the board starts again
- **THEN** slot 2 can still be loaded
