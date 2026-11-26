# Database Design

## Database Configuration

- Database engine: PostgreSQL 18.7
- Database name: banking_agent_db
- Database user: banking_app
- Host: localhost
- Port: 5432

## Security

- Dedicated database user.
- No superuser privileges.
- Public database access revoked.
- Database passwords must not be committed to Git.


## Database Schema

### Design Standards

- PostgreSQL is the primary relational database.
- UUID primary keys for all core tables.
- NUMERIC(18,2) for monetary values.
- Python Decimal for monetary calculations.
- Timezone-aware timestamps stored in UTC.
- Explicit foreign keys and named constraints.
- No plaintext passwords.
- Financial records must not be physically deleted.
- INR is the supported currency for the initial version.

### 1. users

| Column | Data Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| full_name | VARCHAR(100) | Not null |
| email | VARCHAR(255) | Unique, not null |
| password_hash | VARCHAR(255) | Not null |
| role | VARCHAR(20) | Not null |
| is_active | BOOLEAN | Default true |
| created_at | TIMESTAMPTZ | Not null |
| updated_at | TIMESTAMPTZ | Not null |

Roles: CUSTOMER, REVIEWER, ADMIN.

Emails must be normalized before storage.

### 2. accounts

| Column | Data Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | FK users.id, not null |
| account_number | VARCHAR(20) | Unique, not null |
| account_type | VARCHAR(20) | Not null |
| balance | NUMERIC(18,2) | Non-negative |
| currency | VARCHAR(3) | Default INR |
| status | VARCHAR(20) | Not null |
| created_at | TIMESTAMPTZ | Not null |
| updated_at | TIMESTAMPTZ | Not null |

Account types: SAVINGS, CURRENT.
Statuses: ACTIVE, FROZEN, CLOSED.

### 3. beneficiaries

| Column | Data Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | FK users.id, not null |
| account_id | UUID | FK accounts.id, not null |
| nickname | VARCHAR(100) | Not null |
| is_active | BOOLEAN | Default true |
| created_at | TIMESTAMPTZ | Not null |

Unique constraint: (user_id, account_id).

Beneficiaries reference simulated internal bank accounts.

### 4. transactions

| Column | Data Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| initiated_by | UUID | FK users.id, not null |
| source_account_id | UUID | FK accounts.id, not null |
| destination_account_id | UUID | FK accounts.id, not null |
| beneficiary_id | UUID | FK beneficiaries.id, not null |
| amount | NUMERIC(18,2) | Greater than zero |
| currency | VARCHAR(3) | Not null |
| status | VARCHAR(30) | Not null |
| idempotency_key | UUID | Not null |
| description | VARCHAR(255) | Nullable |
| failure_code | VARCHAR(50) | Nullable |
| created_at | TIMESTAMPTZ | Not null |
| updated_at | TIMESTAMPTZ | Not null |
| completed_at | TIMESTAMPTZ | Nullable |

Unique constraint: (initiated_by, idempotency_key).

Source and destination accounts must be different.

Transaction statuses:
- PENDING
- PENDING_REVIEW
- APPROVED
- REJECTED
- COMPLETED
- FAILED

### 5. fraud_assessments

| Column | Data Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| transaction_id | UUID | FK transactions.id, not null |
| risk_score | INTEGER | Between 0 and 100 |
| risk_level | VARCHAR(10) | Not null |
| risk_factors | JSONB | Not null |
| rule_version | VARCHAR(30) | Not null |
| created_at | TIMESTAMPTZ | Not null |

Risk levels: LOW, MEDIUM, HIGH.

Multiple assessments are permitted to support
risk reassessment before execution.

### 6. reviews

| Column | Data Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| transaction_id | UUID | FK transactions.id, not null |
| fraud_assessment_id | UUID | FK fraud_assessments.id |
| reviewer_id | UUID | FK users.id, nullable |
| status | VARCHAR(20) | Not null |
| decision_reason | TEXT | Nullable |
| created_at | TIMESTAMPTZ | Not null |
| reviewed_at | TIMESTAMPTZ | Nullable |

Review statuses: PENDING, APPROVED, REJECTED.

Only authorized reviewers can make decisions.
Only one pending review per transaction is permitted.

### 7. audit_logs

| Column | Data Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | FK users.id, nullable |
| transaction_id | UUID | FK transactions.id, nullable |
| request_id | UUID | Nullable |
| action | VARCHAR(100) | Not null |
| entity_type | VARCHAR(50) | Not null |
| entity_id | UUID | Nullable |
| event_details | JSONB | Not null |
| created_at | TIMESTAMPTZ | Not null |

Audit logs are append-only at the application level.
Passwords, tokens and sensitive credentials must
never be stored in audit logs.

## Transaction Integrity

- Validate account ownership and beneficiary ownership.
- Require explicit user confirmation before transfer.
- Validate account status, currency and available balance.
- Evaluate fraud risk before transferring funds.
- Route high-risk transactions to human review.
- Revalidate transaction conditions after approval.
- Lock affected account rows in consistent order.
- Debit and credit balances in one atomic transaction.
- Prevent duplicate transfers using idempotency keys.
- Record transaction state changes and audit events.
- Never allow the LLM to directly modify balances.

## Indexing Strategy

- accounts: user_id
- beneficiaries: account_id
- transactions: source_account_id, created_at
- transactions: destination_account_id, created_at
- transactions: status, created_at
- fraud_assessments: transaction_id, created_at
- reviews: status, created_at
- reviews: transaction_id
- audit_logs: user_id, created_at
- audit_logs: transaction_id, created_at
- audit_logs: request_id

Primary keys and unique constraints already
provide indexes for their respective columns.

## Transaction State Transitions

- PENDING -> COMPLETED
- PENDING -> PENDING_REVIEW
- PENDING -> FAILED
- PENDING_REVIEW -> APPROVED
- PENDING_REVIEW -> REJECTED
- APPROVED -> COMPLETED
- APPROVED -> PENDING_REVIEW
- APPROVED -> FAILED

COMPLETED, REJECTED and FAILED are terminal states.

## Additional Integrity Rules

- A beneficiary must belong to the initiating user.
- A beneficiary account must match the destination account.
- A fraud assessment must belong to the reviewed transaction.
- A completed transaction must have a completion timestamp.
- Reusing an idempotency key with different transfer
  details must be rejected.
- Reviewers cannot approve their own transactions.
- Enforce allowed roles, statuses and currency using
  named database check constraints.
- Enforce one pending review per transaction using
  a partial unique index.
