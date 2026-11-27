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