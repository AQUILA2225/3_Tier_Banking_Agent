from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    User,
    Account,
    Beneficiary,
    Transaction,
    FraudAssessment,
    Review,
    AuditLog
)


pytestmark = pytest.mark.integration


def assert_constraint_violation(
    db_session: Session,
    constraint_name: str
):
    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    db_session.rollback()

    assert (
        exc_info.value.orig.diag.constraint_name
        == constraint_name
    )


# Test data helpers

def create_user(db_session: Session) -> User:

    user = User(
        full_name="Test Customer",
        email=f"{uuid4()}@example.com",
        password_hash="test-only-placeholder",
        role="CUSTOMER"
    )

    db_session.add(user)
    db_session.flush()

    return user


def create_account(
    db_session: Session,
    user: User
) -> Account:

    account = Account(
        user_id=user.id,
        account_number=uuid4().hex[:20],
        account_type="SAVINGS",
        balance=Decimal("10000.00")
    )

    db_session.add(account)
    db_session.flush()

    return account


def create_transaction(
    db_session: Session
) -> Transaction:

    sender = create_user(db_session)
    recipient = create_user(db_session)

    source = create_account(db_session, sender)
    destination = create_account(db_session, recipient)

    beneficiary = Beneficiary(
        user_id=sender.id,
        account_id=destination.id,
        nickname="Test Recipient"
    )

    db_session.add(beneficiary)
    db_session.flush()

    transaction = Transaction(
        initiated_by=sender.id,
        source_account_id=source.id,
        destination_account_id=destination.id,
        beneficiary_id=beneficiary.id,
        amount=Decimal("5000.00"),
        idempotency_key=uuid4()
    )

    db_session.add(transaction)
    db_session.flush()

    return transaction


def create_assessment(
    db_session: Session
) -> FraudAssessment:

    transaction = create_transaction(db_session)

    assessment = FraudAssessment(
        transaction_id=transaction.id,
        risk_score=85,
        risk_level="HIGH",
        risk_factors=[],
        rule_version="1.0.0"
    )

    db_session.add(assessment)
    db_session.flush()

    return assessment


# User constraint tests

def test_duplicate_email_rejected(db_session):

    user = create_user(db_session)

    duplicate = User(
        full_name="Duplicate User",
        email=user.email,
        password_hash="test-only-placeholder"
    )

    db_session.add(duplicate)

    assert_constraint_violation(
        db_session,
        "uq_users_email"
    )


def test_invalid_user_role_rejected(db_session):

    user = create_user(db_session)
    user.role = "INVALID"

    assert_constraint_violation(
        db_session,
        "ck_users_valid_role"
    )


# Account constraint tests

def test_negative_balance_rejected(db_session):

    user = create_user(db_session)
    account = create_account(db_session, user)

    account.balance = Decimal("-100.00")

    assert_constraint_violation(
        db_session,
        "ck_accounts_non_negative_balance"
    )


def test_invalid_account_type_rejected(db_session):

    user = create_user(db_session)
    account = create_account(db_session, user)

    account.account_type = "INVALID"

    assert_constraint_violation(
        db_session,
        "ck_accounts_valid_account_type"
    )


def test_invalid_account_status_rejected(db_session):

    user = create_user(db_session)
    account = create_account(db_session, user)

    account.status = "INVALID"

    assert_constraint_violation(
        db_session,
        "ck_accounts_valid_status"
    )


def test_invalid_currency_rejected(db_session):

    user = create_user(db_session)
    account = create_account(db_session, user)

    account.currency = "USD"

    assert_constraint_violation(
        db_session,
        "ck_accounts_valid_currency"
    )


def test_duplicate_account_number_rejected(db_session):

    user = create_user(db_session)
    account = create_account(db_session, user)

    duplicate = Account(
        user_id=user.id,
        account_number=account.account_number,
        account_type="SAVINGS"
    )

    db_session.add(duplicate)

    assert_constraint_violation(
        db_session,
        "uq_accounts_account_number"
    )


def test_invalid_account_owner_rejected(db_session):

    account = Account(
        user_id=uuid4(),
        account_number=uuid4().hex[:20],
        account_type="SAVINGS"
    )

    db_session.add(account)

    assert_constraint_violation(
        db_session,
        "fk_accounts_user_id_users"
    )


# Beneficiary constraint tests

def test_duplicate_beneficiary_rejected(db_session):

    transaction = create_transaction(db_session)

    duplicate = Beneficiary(
        user_id=transaction.initiated_by,
        account_id=transaction.destination_account_id,
        nickname="Duplicate Recipient"
    )

    db_session.add(duplicate)

    assert_constraint_violation(
        db_session,
        "uq_beneficiaries_user_id_account_id"
    )


# Transaction constraint tests

@pytest.mark.parametrize("amount", ["0.00", "-500.00"])
def test_invalid_transfer_amount_rejected(
    db_session,
    amount
):

    transaction = create_transaction(db_session)
    transaction.amount = Decimal(amount)

    assert_constraint_violation(
        db_session,
        "ck_transactions_positive_amount"
    )


def test_same_account_transfer_rejected(db_session):

    transaction = create_transaction(db_session)

    transaction.destination_account_id = (
        transaction.source_account_id
    )

    assert_constraint_violation(
        db_session,
        "ck_transactions_different_accounts"
    )


def test_duplicate_idempotency_key_rejected(db_session):

    transaction = create_transaction(db_session)

    duplicate = Transaction(
        initiated_by=transaction.initiated_by,
        source_account_id=transaction.source_account_id,
        destination_account_id=transaction.destination_account_id,
        beneficiary_id=transaction.beneficiary_id,
        amount=transaction.amount,
        idempotency_key=transaction.idempotency_key
    )

    db_session.add(duplicate)

    assert_constraint_violation(
        db_session,
        "uq_transactions_initiator_idempotency"
    )


def test_invalid_transaction_status_rejected(db_session):

    transaction = create_transaction(db_session)
    transaction.status = "INVALID"

    assert_constraint_violation(
        db_session,
        "ck_transactions_valid_status"
    )


def test_completed_without_timestamp_rejected(db_session):

    transaction = create_transaction(db_session)
    transaction.status = "COMPLETED"

    assert_constraint_violation(
        db_session,
        "ck_transactions_valid_completion_timestamp"
    )


def test_valid_completion_state_accepted(db_session):

    transaction = create_transaction(db_session)

    transaction.status = "COMPLETED"
    transaction.completed_at = datetime.now(timezone.utc)

    db_session.flush()

    assert transaction.status == "COMPLETED"
    assert transaction.completed_at is not None


# Fraud assessment constraint tests

@pytest.mark.parametrize("score", [-1, 101])
def test_invalid_risk_score_rejected(db_session, score):

    assessment = create_assessment(db_session)
    assessment.risk_score = score

    assert_constraint_violation(
        db_session,
        "ck_fraud_assessments_valid_risk_score"
    )


def test_invalid_risk_level_rejected(db_session):

    assessment = create_assessment(db_session)
    assessment.risk_level = "INVALID"

    assert_constraint_violation(
        db_session,
        "ck_fraud_assessments_valid_risk_level"
    )


def test_invalid_risk_factors_rejected(db_session):

    assessment = create_assessment(db_session)
    assessment.risk_factors = {"invalid": True}

    assert_constraint_violation(
        db_session,
        "ck_fraud_assessments_valid_risk_factors"
    )


# Human review constraint tests

def test_duplicate_pending_review_rejected(db_session):

    assessment = create_assessment(db_session)

    for _ in range(2):
        db_session.add(
            Review(
                transaction_id=assessment.transaction_id,
                fraud_assessment_id=assessment.id,
                status="PENDING"
            )
        )

    assert_constraint_violation(
        db_session,
        "uq_reviews_pending_transaction"
    )


@pytest.mark.parametrize(
    "status",
    ["APPROVED", "REJECTED"]
)
def test_incomplete_review_decision_rejected(
    db_session,
    status
):

    assessment = create_assessment(db_session)

    review = Review(
        transaction_id=assessment.transaction_id,
        fraud_assessment_id=assessment.id,
        status=status
    )

    db_session.add(review)

    assert_constraint_violation(
        db_session,
        "ck_reviews_valid_review_decision"
    )


def test_valid_review_decision_accepted(db_session):

    assessment = create_assessment(db_session)

    reviewer = create_user(db_session)
    reviewer.role = "REVIEWER"

    review = Review(
        transaction_id=assessment.transaction_id,
        fraud_assessment_id=assessment.id,
        reviewer_id=reviewer.id,
        status="APPROVED",
        decision_reason="Test verification completed",
        reviewed_at=datetime.now(timezone.utc)
    )

    db_session.add(review)
    db_session.flush()

    assert review.status == "APPROVED"
    assert review.id is not None


# Audit log constraint tests

def test_invalid_audit_details_rejected(db_session):

    audit = AuditLog(
        action="TRANSFER_REQUESTED",
        entity_type="TRANSACTION",
        event_details=["invalid"]
    )

    db_session.add(audit)

    assert_constraint_violation(
        db_session,
        "ck_audit_logs_valid_event_details"
    )


def test_empty_audit_action_rejected(db_session):

    audit = AuditLog(
        action="",
        entity_type="TRANSACTION",
        event_details={}
    )

    db_session.add(audit)

    assert_constraint_violation(
        db_session,
        "ck_audit_logs_valid_action"
    )

def test_empty_audit_entity_type_rejected(db_session):

    audit = AuditLog(
        action="TRANSFER_REQUESTED",
        entity_type="",
        event_details={}
    )
    db_session.add(audit)
    assert_constraint_violation(
        db_session,
        "ck_audit_logs_valid_entity_type"
    )