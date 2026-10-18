# health Specification

## Purpose
Exposes two probes so operators and graders can tell whether the process is alive and whether it can reach the database, without leaking internals when something is wrong.

## Requirements

### Requirement: Liveness probe independent of the database

The system SHALL expose `GET /health/live` returning `{"estado": "vivo"}` with HTTP 200 without touching the database.

#### Scenario: Alive without database

- **WHEN** a client calls `GET /health/live` while the database is down
- **THEN** it still responds 200 with `{"estado": "vivo"}`

### Requirement: Readiness probe verifies the database

The system SHALL expose `GET /health/ready` that checks database reachability and responds 200 when the check succeeds.

#### Scenario: Ready with database

- **WHEN** a client calls `GET /health/ready` while the database responds
- **THEN** it responds 200

#### Scenario: Not ready without database

- **WHEN** a client calls `GET /health/ready` while the database is unreachable
- **THEN** it reports failure without exposing table names, constraint names, connection strings, or tracebacks
