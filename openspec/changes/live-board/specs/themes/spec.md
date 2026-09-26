## MODIFIED Requirements

### Requirement: Chrome stays minimal
The client SHALL render panels with hairline borders and no decorative frames. A panel header MUST show the panel title and, when stale, the stale marker. The client MAY show one status line with the clock, a live mark, the focused title, the suggestion, and key hints. That line MUST NOT repeat the OS window title. A settings overlay MAY cover the panels while it is open and MUST leave when the operator closes it.

#### Scenario: Fresh panel
- **GIVEN** a fresh headlines panel
- **WHEN** the bay renders it
- **THEN** the header shows the panel title
- **AND** no stale marker is shown

#### Scenario: Status line
- **WHEN** a bay renders
- **THEN** one status line shows the clock and the keys that move, open settings, and apply a suggestion
- **AND** the line does not repeat the window title

## ADDED Requirements

### Requirement: Night is the readable default
The `night` theme MUST use a dark blue-black ground, a text role brighter than the muted role, an `up` role distinct from a `down` role, and an accent role. The focused panel border MUST use the accent role.

#### Scenario: Focused panel
- **GIVEN** a bay on the night theme with more than one panel
- **WHEN** the operator moves the focus
- **THEN** the focused panel border uses the accent role
- **AND** the other panel borders use the border role
