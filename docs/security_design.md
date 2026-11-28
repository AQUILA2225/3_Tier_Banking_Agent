# Banking Agent Security Architecture

## Authentication

- Password hashing using Argon2id and pwdlib.
- JWT signing and verification using PyJWT.
- HS256 signing algorithm.
- Access token lifetime: 15 minutes.
- Refresh token lifetime: 7 days.
- Server-side refresh session tracking.
- Refresh token rotation and revocation.
- Reject disabled users and invalid credentials.

## Password Policy

- Minimum length: 12 characters.
- Maximum length: 128 characters.
- Never store plaintext passwords.
- Never expose password hashes through API responses.
- Reject the temporary !LOGIN_DISABLED password marker.

## Authorization

The application supports three roles:

- CUSTOMER
- REVIEWER
- ADMIN

Public registration creates CUSTOMER accounts only.
Privileged roles require controlled provisioning.

Authorization is enforced by the backend.
Customers can access only their authorized resources.
Reviewers cannot approve their own transactions.
Administrators cannot bypass financial security policies.

## Token Security

- Use cryptographically random signing secrets.
- Store secrets in environment variables.
- Validate token signature, expiration, issuer,
  audience, subject and token type.
- Reject revoked or reused refresh tokens.
- Store refresh token digests rather than raw tokens.
- Never expose tokens in application logs.

## Frontend Security

- Keep access tokens in memory.
- Store refresh tokens in HttpOnly cookies.
- Use Secure cookies in HTTPS deployments.
- Apply appropriate SameSite and CSRF protections.
- Configure explicit credentialed CORS origins.

## Banking Agent Security

- The LLM cannot directly modify database balances.
- All operations require authenticated user context.
- Financial operations require backend authorization.
- Transfers require explicit user confirmation.
- High-risk transfers require human review.
- Sensitive information must not appear in prompts
  or audit logs.

## Additional Security Controls

- Authentication rate limiting.
- Generic invalid-credential error responses.
- Security event auditing.
- Input validation.
- HTTPS for deployed environments.
- Automated security testing.

## Password Security Implementation

Module: backend/app/core/security.py

### Argon2id Parameters

- Time cost: 3
- Memory cost: 65536 KiB
- Parallelism: 4
- Hash length: 32 bytes
- Salt length: 16 bytes

### Implemented Functions

- validate_password()
- hash_password()
- verify_password()
- verify_and_update_password()

### Security Controls

- Configurable password length validation.
- Random salt for each password hash.
- Rejection of malformed and disabled password hashes.
- Support for upgrading outdated password hashes.
- No plaintext password storage.
- No silent password truncation.
- 24 automated password security tests.

## JWT Token Security Implementation

Module: backend/app/core/security.py

### Implemented Functions

- create_access_token()
- create_refresh_token()
- decode_token()
- decode_access_token()
- decode_refresh_token()

### Token Configuration

- Signing algorithm: HS256
- Access token lifetime: 15 minutes
- Refresh token lifetime: 7 days
- Unique UUID-based token identifiers
- UTC-based token timestamps

### Security Controls

- Cryptographic signature verification.
- Explicit signing algorithm restriction.
- Required JWT claim validation.
- Issuer and audience verification.
- Expiration and not-before validation.
- Strict access and refresh token separation.
- UUID validation for subject and token identifiers.
- Maximum token lifetime enforcement.
- Generic token validation errors.
- No sensitive banking information in token payloads.
- 30 automated JWT security tests.

### Pending Implementation

- Refresh session database model.
- Refresh token digest storage.
- Refresh token rotation and revocation.
- User authentication endpoints.
- Role-based access control.
- HttpOnly cookie and CSRF protection.

## Refresh Session Lifecycle Management

### Modules

- app/repositories/refresh_session_repository.py
- app/services/refresh_session_service.py

### Implemented Features

- SHA-256 refresh token digest generation.
- Timing-resistant digest comparison.
- Server-side session creation.
- Atomic refresh token rotation.
- User-level database row locking.
- Refresh token family reuse detection.
- Session family revocation.
- Global user session revocation.
- Inactive user validation.
- Transaction rollback on rotation failure.
- 15 lifecycle integration tests.

### Transaction Rules

Public refresh session service methods own their
database transactions.

All session-changing operations must follow the same
user-row locking protocol.

Token reuse errors are raised after committing
family revocation.

Session creation requires a trusted caller that has
already verified user credentials.

### Pending Security Controls

- Authentication and authorization endpoints.
- HttpOnly refresh cookies and CSRF protection.
- Authentication rate limiting.
- Concurrent refresh request testing.
- Session retention and cleanup policy.
- Security event auditing.

## Authentication Schemas and User Repository

### Modules

- app/schemas/auth.py
- app/repositories/user_repository.py

### Implemented Features

- Email validation and normalization.
- Full name normalization.
- Registration password policy enforcement.
- Password masking using SecretStr.
- Registration role injection prevention.
- Safe user response schemas.
- Access token response schema.
- User lookup by UUID and email.
- Customer-only user creation.
- Password hash updates.
- Optional database row locking.
- Service-controlled database transactions.

### Automated Tests

- 26 authentication schema unit tests.
- 12 user repository integration tests.
- 38 new automated tests.

## Authentication Service Implementation

### Module

- app/services/auth_service.py

### Implemented Features

- Customer-only registration.
- Secure Argon2id password hashing.
- Duplicate email conflict handling.
- Email-based user authentication.
- Generic invalid credential errors.
- Dummy password hash verification.
- Inactive user login prevention.
- Disabled password login prevention.
- Automatic password hash upgrading.
- JWT access and refresh token issuance.
- Server-side refresh session creation.
- Atomic login transaction management.
- 14 authentication service integration tests.

### Transaction Rules

The authentication service owns the registration
and login transactions.

Credential verification, password hash upgrading
and refresh session creation occur within the
same login transaction.

The refresh session service supports token issuance
within an existing transaction.

### Pending Security Controls

- Authentication REST API endpoints.
- Secure refresh cookies and CSRF protection.
- Authentication dependencies.
- Role-based access control.
- Authentication rate limiting.
- Authentication security event auditing.

## Authentication REST API Implementation

### Endpoints

- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout

### Security Controls

- HttpOnly refresh token cookies.
- SameSite Strict cookie protection.
- HTTPS-only cookies in production.
- Trusted origin validation.
- Required custom CSRF protection header.
- Explicit credentialed CORS configuration.
- Sanitized authentication validation errors.
- Access tokens returned through JSON.
- Refresh token rotation and family revocation.
- No-store caching policy on successful authentication
  responses and sanitized validation responses.

### Deployment Requirements

- Production must use HTTPS.
- Frontend and backend must use compatible same-site
  deployment origins for SameSite Strict cookies.
- Frontend requests must include credentials and
  the X-CSRF-Protection header.

### Automated Tests

- 15 authentication API tests.

### Pending Controls

- Access token authentication dependencies.
- Current user endpoint.
- Role-based access control.
- Authentication rate limiting.
- Security event auditing.
- Browser-based cookie and CORS integration testing.

## Access Token Authentication Dependencies

### Modules

- app/api/deps.py
- app/api/v1/endpoints/auth.py

### Protected Endpoint

GET /api/v1/auth/me

### Implemented Features

- HTTP bearer token extraction.
- JWT access token validation.
- Refresh token substitution prevention.
- Database-backed current user retrieval.
- Inactive and disabled user rejection.
- Reusable CurrentUser dependency.
- Safe user profile response.
- WWW-Authenticate bearer challenge.
- Authentication response cache protection.
- Swagger bearer authentication integration.
- 16 authentication dependency API tests.

### Security Rules

- Never trust user identity without JWT validation.
- Retrieve current user status and role from PostgreSQL.
- Never return password hashes in API responses.
- Apply CSRF protection to authentication POST endpoints.
- Use bearer authentication for the read-only current
  user endpoint.

### Pending Controls

- Role-based access control.
- Resource ownership authorization.
- Authentication rate limiting.
- Security event auditing.
- Immediate access token revocation, if required.

## Role-Based Access Control

### Modules

- app/core/permissions.py
- app/api/deps.py

### Implemented Features

- Centralized permission definitions.
- Immutable role-to-permission mapping.
- Customer, reviewer and administrator roles.
- Default-deny authorization policy.
- Principle of least privilege.
- Reusable role-based dependencies.
- Reusable permission-based dependencies.
- Multiple required permission checks.
- Multiple allowed role checks.
- HTTP 403 authorization errors.
- Database-backed role validation.
- Profile endpoint permission enforcement.

### Authorization Rules

- Customers can perform permitted customer operations.
- Reviewers can access and decide assigned reviews.
- Administrators can perform permitted user
  administration and audit operations.
- Administrators do not inherit customer or
  reviewer permissions.
- Unknown roles are denied access.
- Permissions do not replace resource ownership checks.
- Reviewers must not approve their own transactions.
- Financial operations require additional business
  policy and transaction state validation.

### Automated Tests

- 20 permission management unit tests.
- 23 authorization API tests.
- 43 new automated tests.

## Authentication Rate Limiting

### Modules

- app/core/rate_limiter.py
- app/core/auth_rate_limit.py

### Implemented Features

- Sliding-window rate limiting.
- Configurable authentication request limits.
- Endpoint-specific and IP-based request tracking.
- Thread-safe request counters.
- Monotonic time measurement.
- Expired request cleanup.
- Bounded identity tracking.
- HTTP 429 Too Many Requests responses.
- Retry-After response header.
- Failed login attempt counting.
- Automated test isolation.

### Default Policies

Window: 60 seconds

- Registration: 5 requests per IP.
- Login: 10 requests per IP.
- Refresh: 30 requests per IP.
- Logout: 30 requests per IP.

### Automated Tests

- 20 rate limiter unit tests.
- 8 authentication rate-limiting API tests.
- 28 new automated tests.

### Deployment Limitations

The rate limiter stores request history in memory.

Request history is lost when the server restarts.
Multiple worker processes do not share counters.

Distributed deployments require shared rate-limit
storage and trusted reverse proxy configuration.

Account-based throttling and upstream request
protection are additional security requirements.