from uuid import uuid4

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import User, UserRole


pytestmark = pytest.mark.integration


def test_database_connection(db_session: Session):

    result = db_session.execute(
        text("select 1")
    ).scalar_one()

    assert result == 1


def test_database_isolation(db_session: Session):

    database_name, database_user = db_session.execute(
        text("select current_database(), current_user")
    ).one()

    assert database_name == "banking_agent_test_db"
    assert database_user == "banking_test_app"


def test_database_tables(test_engine: Engine):

    expected_tables = {
        "users",
        "accounts",
        "beneficiaries",
        "transactions",
        "fraud_assessments",
        "reviews",
        "audit_logs",
        "refresh_sessions",
        "alembic_version"
    }

    actual_tables = set(
        inspect(test_engine).get_table_names()
    )

    assert expected_tables.issubset(actual_tables)


def test_user_persistence(
    db_session: Session,
    test_engine: Engine
):

    user = User(
        full_name="Integration Test User",
        email=f"{uuid4()}@example.com",
        password_hash="test-only-placeholder",
        role=UserRole.CUSTOMER.value
    )

    db_session.add(user)
    db_session.commit()

    user_id = user.id

    db_session.expire_all()

    saved_user = db_session.scalar(
        select(User).where(User.id == user_id)
    )

    assert saved_user is not None
    assert saved_user.full_name == "Integration Test User"
    assert saved_user.role == "CUSTOMER"
    assert saved_user.is_active is True
    assert saved_user.created_at is not None

    # Verify that the outer transaction prevents
    # other connections from seeing uncommitted test data.

    with test_engine.connect() as connection:

        result = connection.execute(
            select(User.id).where(User.id == user_id)
        ).scalar_one_or_none()

        assert result is None