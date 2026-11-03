# app-lifecycle Specification

## Purpose
Defines how the application owns its database connection over its lifetime: resources are created once at startup, every request runs in an isolated session, and everything is released in order at shutdown.

## Requirements

### Requirement: Startup creates shared resources once

The system SHALL create the database engine (configured with the pool size from settings), the session factory (`expire_on_commit=False`), and a precomputed dummy password hash (`bcrypt` at the configured cost) exactly once during application startup, storing all three in application state for the whole process lifetime.

#### Scenario: Single initialization

- **WHEN** the application starts
- **THEN** exactly one engine, one session factory, and one dummy password hash exist in application state and remain available until shutdown

#### Scenario: Dummy hash is valid bcrypt at configured cost

- **WHEN** the application starts with a configured `BCRYPT_ROUNDS` cost
- **THEN** `app.state.dummy_password_hash` holds a valid `bcrypt` hash generated once at startup so login checks against nonexistent accounts take constant time

### Requirement: One isolated session per request

The system SHALL serve every HTTP request with its own isolated database session, closed when the response is sent, so requests never share uncommitted state.

#### Scenario: Request isolation

- **WHEN** two requests run (sequentially or concurrently)
- **THEN** neither observes the other's uncommitted writes

#### Scenario: Session cleanup

- **WHEN** a response has been sent
- **THEN** its session is closed and its connection returned to the pool

### Requirement: Ordered shutdown releases resources

The system SHALL close the database engine during application shutdown, after in-flight responses complete.

#### Scenario: Clean shutdown

- **WHEN** the application stops
- **THEN** no database connection remains open afterwards

### Requirement: Connection configured from the environment

The system SHALL build the asynchronous PostgreSQL connection URL (`DATABASE_URL`) from `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, and `POSTGRES_PORT` environment variables, and SHALL require `POSTGRES_PASSWORD` and `JWT_SECRET` with no default values in code. It SHALL NOT embed real credentials in versioned files (`env.example` documents all variables without real secrets).

#### Scenario: Missing configuration

- **WHEN** `POSTGRES_PASSWORD` or `JWT_SECRET` is absent from the environment when loading settings
- **THEN** settings validation fails immediately and the application refuses to start without exposing internal details

#### Scenario: Database URL computed from POSTGRES variables

- **WHEN** `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, and `POSTGRES_PORT` are provided
- **THEN** the settings expose a computed `postgresql+asyncpg://` `DATABASE_URL` formed from those components

#### Scenario: No secrets in the repo

- **WHEN** the repository is inspected
- **THEN** it contains no file with real database credentials or real JWT secrets

### Requirement: Two route groups separate open and protected endpoints

The system SHALL organize HTTP routes into two top-level route groups in the application entry point: an open group (for health probes, authentication endpoints, and public catalog reads) and a protected group where the mandatory password-change guard (`debe_cambiar_password`) is mounted once for all protected endpoints.

#### Scenario: Open and protected route groups registered at startup

- **WHEN** the application initializes its routing table
- **THEN** open endpoints are mounted under the open route group and protected endpoints are mounted under the protected route group without duplicating the mandatory password-change dependency per endpoint
