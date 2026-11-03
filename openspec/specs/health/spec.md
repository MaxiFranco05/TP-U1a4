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

The system SHALL expose `GET /health/ready` that executes `SELECT 1` against the database and responds HTTP 200 when the check succeeds or HTTP 503 when the database does not respond, without leaking internal details.

#### Scenario: Ready with database

- **WHEN** a client calls `GET /health/ready` while the database responds to `SELECT 1`
- **THEN** it responds HTTP 200 with `{"estado": "listo"}`

#### Scenario: Not ready without database

- **WHEN** a client calls `GET /health/ready` while the database is unreachable or fails `SELECT 1`
- **THEN** it responds HTTP 503 without exposing table names, constraint names, connection strings, or tracebacks

### Requirement: Health module contains only router.py

The system SHALL implement the `health` module exclusively within `app/modules/health/router.py` (aside from package initialization if needed), without separate `models.py`, `schemas.py`, or `service.py` files in `app/modules/health/`.

#### Scenario: Inspecting the health module layout

- **WHEN** the `app/modules/health/` directory is inspected
- **THEN** `router.py` is the only module implementation file and `models.py`, `schemas.py`, and `service.py` do not exist in `app/modules/health/`
