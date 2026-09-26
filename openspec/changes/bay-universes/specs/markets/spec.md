## ADDED Requirements

### Requirement: Wider shipped instrument list
The shipped selection SHALL include global indices, more large-cap equities, more FX pairs, more Treasury tenors, more commodities, and more crypto, each from a source already in the markets catalog or a newly verified public source. An instrument whose source returns no price MUST show the symbol with an empty price and no change bar.

#### Scenario: Missing quote
- **GIVEN** a shipped instrument the source did not return
- **WHEN** the markets bay renders
- **THEN** the symbol is shown with no price
- **AND** no change and no bar are drawn
