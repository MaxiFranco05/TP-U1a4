# Spec Delta

## Purpose

Provides cryptographic utilities and request dependencies for non-blocking bcrypt hashing, JWT issuance and verification, cookie-based authentication, real-time database role authorization, and mandatory password-change enforcement.

## ADDED Requirements

### Requirement: Asynchronous bcrypt password hashing and verification
The system SHALL hash and verify passwords using bcrypt outside the main asynchronous event loop via worker threads and SHALL restrict concurrent bcrypt executions with a global semaphore to prevent thread pool exhaustion and event loop latency spikes.

#### Scenario: Password hashing produces valid bcrypt hash
- **WHEN** a plain text password is provided to the hashing function
- **THEN** the system returns a valid bcrypt hash string generated with the configured cost factor without blocking the event loop

#### Scenario: Password verification validates correct password
- **WHEN** a plain text password and its corresponding bcrypt hash are verified
- **THEN** the system returns true

#### Scenario: Password verification rejects incorrect password
- **WHEN** an invalid plain text password is checked against a bcrypt hash
- **THEN** the system returns false

#### Scenario: Concurrent password operations are throttled by semaphore
- **WHEN** multiple concurrent password hashing or verification requests are processed
- **THEN** the system processes them respecting the maximum concurrency limit defined by the semaphore

### Requirement: UTF-8 72-byte password length validation
The system SHALL enforce that all password inputs intended for bcrypt processing do not exceed 72 bytes when encoded in UTF-8, rejecting invalid values with a validation error before any hashing execution.

#### Scenario: Password within 72 bytes is accepted
- **WHEN** a password whose UTF-8 byte count is less than or equal to 72 is validated
- **THEN** the validation succeeds and returns the password unchanged

#### Scenario: Password exceeding 72 bytes raises validation error
- **WHEN** a password whose UTF-8 byte count exceeds 72 bytes is submitted
- **THEN** the system raises a validation error resulting in an HTTP 422 Unprocessable Entity response

#### Scenario: Multi-byte characters count their actual byte length
- **WHEN** a password with non-ASCII multi-byte characters exceeds 72 UTF-8 bytes despite having fewer than 72 characters
- **THEN** the system counts byte length rather than character count and raises a validation error

### Requirement: JWT token issuance and verification
The system SHALL issue and verify signed JSON Web Tokens using HS256 with the configured secret key, embedding subject identifier, expiration timestamp, and an informational list of roles active at issuance time.

#### Scenario: Token issued with valid payload and signature
- **WHEN** an access token is created for a user with specific active roles and expiration time
- **THEN** the system returns a signed JWT containing subject, exp, and roles claims

#### Scenario: Expired token is rejected
- **WHEN** a decoded token has an expiration timestamp in the past
- **THEN** the verification fails indicating token expiration

#### Scenario: Corrupted or tampered token is rejected
- **WHEN** a token with an invalid signature or malformed structure is verified
- **THEN** the verification fails rejecting the token

### Requirement: Cookie-only current user resolution with shared session
The system SHALL resolve the authenticated user strictly from an `access_token` HTTP cookie using the request's shared database session, and SHALL NOT read credentials from the `Authorization: Bearer` header.

#### Scenario: Valid cookie resolves active user entity
- **WHEN** a request arrives with a valid `access_token` cookie for an existing active user
- **THEN** the system retrieves the `Usuario` instance from the database using the request's shared session

#### Scenario: Missing cookie returns 401 Unauthorized
- **WHEN** a request to an authenticated endpoint arrives without an `access_token` cookie
- **THEN** the system responds with HTTP 401 Unauthorized and an appropriate error message

#### Scenario: Authorization Bearer header is ignored
- **WHEN** a request provides credentials only in the `Authorization: Bearer` header without the `access_token` cookie
- **THEN** the system ignores the header and responds with HTTP 401 Unauthorized

#### Scenario: Inactive user account returns 401 Unauthorized
- **WHEN** a valid token references a user whose `activo` flag is false in the database
- **THEN** the system responds with HTTP 401 Unauthorized

#### Scenario: Non-existent user in token returns 401 Unauthorized
- **WHEN** a valid token references a user id that does not exist in the database
- **THEN** the system responds with HTTP 401 Unauthorized

### Requirement: Real-time database role authorization
The system SHALL verify user authorization against active assignments in the `asignacion_rol` database table for each request using the shared session, ignoring any roles listed inside the JWT token.

#### Scenario: User with active non-expired database role is authorized
- **WHEN** an authenticated user has an assignment in `asignacion_rol` with `revocada_en IS NULL` and `(vence_en IS NULL OR vence_en > now())` matching a required role
- **THEN** the system permits access to the endpoint

#### Scenario: User with revoked database role returns 403 Forbidden
- **WHEN** a user's role has `revocada_en IS NOT NULL` in the database, even if their token claims the role
- **THEN** the system responds with HTTP 403 Forbidden

#### Scenario: User with expired role assignment returns 403 Forbidden
- **WHEN** a user's role has `vence_en <= now()` and `revocada_en IS NULL` in the database
- **THEN** the system responds with HTTP 403 Forbidden

#### Scenario: User lacking required role returns 403 Forbidden
- **WHEN** a user has no active assignment matching any of the required roles
- **THEN** the system responds with HTTP 403 Forbidden

### Requirement: Mandatory password change gate on protected routes
The system SHALL prevent users with pending mandatory password changes from accessing any endpoint in the protected route group, while allowing access to open endpoints.

#### Scenario: User with password change pending is blocked on protected endpoint
- **WHEN** an authenticated user with `debe_cambiar_password = True` attempts to access an endpoint in the protected router
- **THEN** the system responds with HTTP 403 Forbidden and a message stating that password change is required

#### Scenario: User with password change pending accesses open endpoint
- **WHEN** an authenticated user with `debe_cambiar_password = True` accesses an endpoint in the open router
- **THEN** the system permits access without raising the password change block

#### Scenario: User without password change pending accesses protected endpoint
- **WHEN** an authenticated user with `debe_cambiar_password = False` accesses an endpoint in the protected router
- **THEN** the system processes the request normally
