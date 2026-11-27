from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import pytest

from sqlalchemy.exc import IntegrityError

from app.models import (
    User,
    RefreshSession,
    RevocationReason
)


pytestmark = pytest.mark.integration


def create_user(db_session):

    user = User(
        full_name="Test Session User",
        email=f"{uuid4()}@example.com",
        password_hash="!LOGIN_DISABLED",
        role="CUSTOMER"
    )

    db_session.add(user)
    db_session.flush()

    return user


def create_session(db_session, user, **overrides):

    now = datetime.now(timezone.utc)

    values = {
        "user_id": user.id,
        "token_jti": uuid4(),
        "token_digest": sha256(
            uuid4().bytes
        ).hexdigest(),
        "family_id": uuid4(),
        "created_at": now,
        "expires_at": now + timedelta(days=7)
    }

    values.update(overrides)

    session = RefreshSession(**values)

    db_session.add(session)

    return session


def assert_constraint_violation(
    db_session,
    constraint_name
):

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    db_session.rollback()

    assert (
        exc_info.value.orig.diag.constraint_name
        == constraint_name
    )


def test_refresh_session_creation(db_session):

    user = create_user(db_session)

    session = create_session(db_session, user)

    db_session.flush()

    assert session.id is not None
    assert session.user_id == user.id
    assert session.revoked_at is None
    assert session.revocation_reason is None
    assert session.expires_at > session.created_at


def test_refresh_session_relationship(db_session):

    user = create_user(db_session)

    session = create_session(db_session, user)

    db_session.flush()

    assert session.user == user
    assert session in user.refresh_sessions


def test_duplicate_token_jti_rejected(db_session):

    user = create_user(db_session)

    first = create_session(db_session, user)

    db_session.flush()

    create_session(
        db_session,
        user,
        token_jti=first.token_jti
    )

    assert_constraint_violation(
        db_session,
        "uq_refresh_sessions_token_jti"
    )


def test_duplicate_token_digest_rejected(db_session):

    user = create_user(db_session)

    first = create_session(db_session, user)

    db_session.flush()

    create_session(
        db_session,
        user,
        token_digest=first.token_digest
    )

    assert_constraint_violation(
        db_session,
        "uq_refresh_sessions_token_digest"
    )


def test_invalid_user_rejected(db_session):

    user = create_user(db_session)

    create_session(
        db_session,
        user,
        user_id=uuid4()
    )

    assert_constraint_violation(
        db_session,
        "fk_refresh_sessions_user_id_users"
    )


@pytest.mark.parametrize(
    "digest",
    ["invalid-digest", "z" * 64, "A" * 64]
)
def test_invalid_token_digest_rejected(
    db_session,
    digest
):

    user = create_user(db_session)

    create_session(
        db_session,
        user,
        token_digest=digest
    )

    assert_constraint_violation(
        db_session,
        "ck_refresh_sessions_valid_token_digest"
    )


def test_invalid_expiration_rejected(db_session):

    user = create_user(db_session)

    now = datetime.now(timezone.utc)

    create_session(
        db_session,
        user,
        created_at=now,
        expires_at=now
    )

    assert_constraint_violation(
        db_session,
        "ck_refresh_sessions_valid_expiration"
    )


def test_valid_session_revocation(db_session):

    user = create_user(db_session)

    session = create_session(db_session, user)

    db_session.flush()

    session.revoked_at = datetime.now(timezone.utc)
    session.revocation_reason = RevocationReason.LOGOUT.value

    db_session.flush()
    db_session.refresh(session)

    assert session.revoked_at is not None
    assert session.revocation_reason == "LOGOUT"


def test_invalid_revocation_timestamp(db_session):

    user = create_user(db_session)

    now = datetime.now(timezone.utc)

    create_session(
        db_session,
        user,
        created_at=now,
        revoked_at=now - timedelta(seconds=1),
        revocation_reason="LOGOUT"
    )

    assert_constraint_violation(
        db_session,
        "ck_refresh_sessions_valid_revocation_timestamp"
    )


@pytest.mark.parametrize(
    "has_timestamp, reason",
    [
        (True, None),
        (False, "LOGOUT"),
        (True, "INVALID_REASON")
    ]
)
def test_invalid_revocation_state(
    db_session,
    has_timestamp,
    reason
):

    user = create_user(db_session)

    now = datetime.now(timezone.utc)

    create_session(
        db_session,
        user,
        created_at=now,
        revoked_at=now if has_timestamp else None,
        revocation_reason=reason
    )

    assert_constraint_violation(
        db_session,
        "ck_refresh_sessions_valid_revocation"
    )