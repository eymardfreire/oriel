## ADDED Requirements

### Requirement: A board does not replace the desk launcher
The launcher SHALL still start one terminal process per bay when the operator starts a named desk, and MUST still report the arrangement without tiling OS windows. A board MUST be a separate start mode that keeps those bays inside one process.

#### Scenario: Three desk still opens three processes
- **WHEN** the operator starts the `three` desk
- **THEN** three client processes start
- **AND** the launcher output names wires, markets, and field

#### Scenario: Board is one process
- **WHEN** the operator starts a board
- **THEN** one client process renders the selected bays
- **AND** the desk launcher is not required
