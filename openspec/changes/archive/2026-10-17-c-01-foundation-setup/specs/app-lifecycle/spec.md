# Spec Delta — app-lifecycle

## Purpose

Defines how the application owns its database connection over its lifetime: resources are created once at startup, every request runs in an isolated session, and everything is released in order at shutdown.

## ADDED Requirements

### Requirement: Startup creates shared resources once

The system SHALL create the database engine and the session factory exactly once during application startup and hold them for the whole process lifetime.

#### Scenario: Single initialization

- **WHEN** the application starts
- **THEN** exactly one engine and one session factory exist and remain available until shutdown

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

The system SHALL take the database address exclusively from the `DATABASE_URL` environment variable, and SHALL NOT embed real credentials in versioned files (an `env.example` documents the shape with no secrets).

#### Scenario: Missing configuration

- **WHEN** `DATABASE_URL` is absent or the database is unreachable
- **THEN** the readiness probe reports failure without exposing internal details

#### Scenario: No secrets in the repo

- **WHEN** the repository is inspected
- **THEN** it contains no file with real database credentials
