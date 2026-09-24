## Purpose

Defines how Oriel splits aggregation from display, and how domains stay detachable so a later Second Brain can adopt the same contracts.

## ADDED Requirements

### Requirement: Server owns upstream access
The aggregation service SHALL perform every upstream fetch. A terminal client MUST NOT call an upstream source, and MUST NOT hold an upstream API key.

#### Scenario: Client renders a panel
- **GIVEN** a running aggregation service with a fresh markets payload
- **WHEN** a terminal bay requests that panel
- **THEN** the bay renders the service payload
- **AND** the bay makes no request to the markets source

#### Scenario: Client has no key
- **GIVEN** a terminal bay configuration
- **WHEN** the bay starts
- **THEN** the configuration contains no upstream API key

### Requirement: Domains are independent modules
The service SHALL expose each domain as a module that can be enabled or disabled. A disabled domain MUST NOT be fetched and MUST NOT appear as a panel.

#### Scenario: Disabled sports domain
- **GIVEN** the sports domain is disabled
- **WHEN** the service builds a desk
- **THEN** no sports panel is included
- **AND** the service does not call a sports source

### Requirement: Contracts are the integration surface
The service SHALL publish panel payloads that match the shared contract. A domain module MUST NOT depend on terminal rendering code. A later consumer MUST be able to read the same payload without the terminal client.

#### Scenario: Payload stands alone
- **GIVEN** a weather panel payload
- **WHEN** a consumer other than the terminal client reads it
- **THEN** the payload includes its domain, update time, stale flag, source names, and items

### Requirement: Stale data stays visible and labeled
When a refresh fails or a payload is older than its domain budget, the service SHALL keep the last good payload and MUST set the stale flag. The client SHALL show a stale marker. The service MUST NOT replace missing numbers with invented values.

#### Scenario: Upstream timeout
- **GIVEN** a markets panel with a last good quote
- **WHEN** the next fetch times out
- **THEN** the panel still contains that quote
- **AND** the stale flag is true
- **AND** the quote value is unchanged

#### Scenario: No last good payload
- **GIVEN** a domain that has never fetched successfully
- **WHEN** a bay requests that panel
- **THEN** the panel has no fabricated items
- **AND** the empty state names the domain
