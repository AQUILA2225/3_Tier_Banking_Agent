from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import User, Account, Beneficiary
from scripts.seed_demo_data import seed_demo_data


pytestmark = pytest.mark.integration


def test_seed_creates_demo_records(db_session):

    counts = seed_demo_data(db_session)

    assert counts == {
        "users": 5,
        "accounts": 3,
        "beneficiaries": 3
    }

    assert db_session.scalar(
        select(func.count()).select_from(User)
    ) == 5

    assert db_session.scalar(
        select(func.count()).select_from(Account)
    ) == 3

    assert db_session.scalar(
        select(func.count()).select_from(Beneficiary)
    ) == 3


def test_seed_is_idempotent(db_session):

    seed_demo_data(db_session)

    counts = seed_demo_data(db_session)

    assert counts == {
        "users": 0,
        "accounts": 0,
        "beneficiaries": 0
    }


def test_seed_preserves_existing_balance(db_session):

    seed_demo_data(db_session)

    account = db_session.scalar(
        select(Account).where(
            Account.account_number == "100000000001"
        )
    )

    assert account is not None

    account.balance = Decimal("95000.00")

    db_session.flush()

    seed_demo_data(db_session)

    db_session.refresh(account)

    assert account.balance == Decimal("95000.00")


def test_seed_preserves_existing_password(db_session):

    seed_demo_data(db_session)

    user = db_session.scalar(
        select(User).where(
            User.email == "customer1@example.com"
        )
    )

    assert user is not None

    user.password_hash = "test-existing-password-hash"

    db_session.flush()

    seed_demo_data(db_session)

    db_session.refresh(user)

    assert user.password_hash == "test-existing-password-hash"


def test_seed_preserves_disabled_beneficiary(db_session):

    seed_demo_data(db_session)

    user = db_session.scalar(
        select(User).where(
            User.email == "customer1@example.com"
        )
    )

    assert user is not None

    beneficiary = db_session.scalar(
        select(Beneficiary).where(
            Beneficiary.user_id == user.id,
            Beneficiary.nickname == "Customer Two"
        )
    )

    assert beneficiary is not None

    beneficiary.is_active = False

    db_session.flush()

    seed_demo_data(db_session)

    db_session.refresh(beneficiary)

    assert beneficiary.is_active is False