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