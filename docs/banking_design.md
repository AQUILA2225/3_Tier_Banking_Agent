# Banking Account and Beneficiary Management

## Objective

Implement secure account retrieval, balance retrieval
and beneficiary management for authenticated customers.

## Technologies

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- JWT
- RBAC
- Decimal
- Pytest

## Architecture

API Endpoint
    -> Authentication
    -> Permission Validation
    -> Service Layer
    -> Resource Ownership Validation
    -> Repository Layer
    -> PostgreSQL

## Database Tables

- users
- accounts
- beneficiaries

Existing Phase 3 database models will be reused.

## Account Management

### Supported Account Types

- SAVINGS
- CURRENT

### Supported Account Statuses

- ACTIVE
- FROZEN
- CLOSED

### Business Rules

- Customers can access only their own accounts.
- Account balances are read-only in Phase 5.
- Monetary values use Decimal.
- Supported currency is INR.
- Customers cannot directly modify balances.
- Account provisioning is controlled.
- Frozen and closed accounts cannot participate
  in future fund transfers.

## Beneficiary Management

### Business Rules

- Customers can add existing active recipient accounts.
- Customers cannot add their own accounts.
- Duplicate active beneficiaries are rejected.
- Inactive beneficiaries may be reactivated.
- Customers can modify only their own beneficiaries.
- Beneficiary removal uses soft deletion.
- Recipient account numbers are masked in responses.
- Beneficiary operations do not modify balances.

## API Endpoints

### Accounts

- GET /api/v1/accounts
- GET /api/v1/accounts/{account_id}
- GET /api/v1/accounts/{account_id}/balance

### Beneficiaries

- POST /api/v1/beneficiaries
- GET /api/v1/beneficiaries
- GET /api/v1/beneficiaries/{beneficiary_id}
- PATCH /api/v1/beneficiaries/{beneficiary_id}
- DELETE /api/v1/beneficiaries/{beneficiary_id}

## Required Permissions

- ACCOUNT_READ
- BENEFICIARY_READ
- BENEFICIARY_MANAGE

## Security Requirements

- JWT authentication.
- Role-based access control.
- Resource ownership validation.
- Server-derived authenticated user identity.
- Protection against IDOR and BOLA.
- Request validation.
- Sensitive data masking.
- Database transaction isolation.
- Database uniqueness constraints.
- Safe error responses.
- Audit logging for beneficiary mutations.

## Transaction Management

Authentication database reads must not interfere
with service-owned database transactions.

Authentication session isolation will be addressed
before implementing banking write operations.

## Testing Strategy

- Schema validation unit tests.
- Repository integration tests.
- Service integration tests.
- Account API tests.
- Beneficiary API tests.
- Cross-customer access rejection tests.
- Duplicate beneficiary tests.
- Beneficiary reactivation tests.
- Transaction rollback tests.
- Concurrent operation tests.
- Authentication regression tests.

## Scope Limitations

Phase 5 does not implement:

- Fund transfers.
- Deposits or withdrawals.
- Real banking integrations.
- Fraud risk scoring.
- AI banking agent integration.
- Human review workflows.

This is a simulated banking application.