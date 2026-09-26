## ADDED Requirements

### Requirement: More trade feeds
The trade catalog SHALL add public feeds for ports, shipping, and customs policy that answer without a key. Each added feed MUST be verified live and MUST NOT carry commodity or FX quotes.

#### Scenario: Added feed
- **GIVEN** a verified shipping feed in the trade catalog
- **WHEN** the trade bay renders
- **THEN** its headlines appear in the matching family panel
- **AND** no quote rows appear in the trade bay
