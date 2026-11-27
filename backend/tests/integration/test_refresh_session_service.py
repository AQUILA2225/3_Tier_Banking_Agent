from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from sqlalchemy import select

from app.core.security import (
    hash_password,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token
)

from app.models import (
    User,
    RefreshSession,
    RevocationReason
)

from app.services.refresh_session_service import (
    RefreshSessionService,
    RefreshSessionError,
    RefreshTokenReuseError,
    digest_refresh_token
)


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def password_hash():

    return hash_password("DemoPassword@123")


@pytest.fixture
def user_id(db_session, password_hash):

    with db_session.begin():

        user = User(
            full_name="Test Session User",
            email=f"{uuid4()}@example.com",
            password_hash=password_hash,
            role="CUSTOMER"
        )

        db_session.add(user)
        db_session.flush()

        uid = user.id

    return uid


def get_session(db_session, token):

    claims = decode_refresh_token(token)

    return db_session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_jti == UUID(claims.jti)
        )
    )


def test_create_session(db_session, user_id):

    service = RefreshSessionService(db_session)

    tokens = service.create_session(user_id)

    access_claims = decode_access_token(
        tokens.access_token
    )

    assert access_claims.sub == str(user_id)

    with db_session.begin():

        session = get_session(
            db_session,
            tokens.refresh_token
        )

        assert session is not None
        assert session.user_id == user_id
        assert session.revoked_at is None

        assert session.token_digest == (
            digest_refresh_token(tokens.refresh_token)
        )

        assert session.token_digest != tokens.refresh_token


def test_rotate_session(db_session, user_id):

    service = RefreshSessionService(db_session)

    original = service.create_session(user_id)

    replacement = service.rotate_session(
        original.refresh_token
    )

    assert (
        original.refresh_token
        != replacement.refresh_token
    )

    with db_session.begin():

        old = get_session(
            db_session,
            original.refresh_token
        )

        new = get_session(
            db_session,
            replacement.refresh_token
        )

        assert old.revoked_at is not None
        assert old.revocation_reason == "ROTATED"
        assert new.revoked_at is None
        assert old.family_id == new.family_id


def test_token_reuse_revokes_family(
    db_session,
    user_id
):

    service = RefreshSessionService(db_session)

    original = service.create_session(user_id)

    replacement = service.rotate_session(
        original.refresh_token
    )

    with pytest.raises(RefreshTokenReuseError):

        service.rotate_session(
            original.refresh_token
        )

    with db_session.begin():

        session = get_session(
            db_session,
            replacement.refresh_token
        )

        assert session.revoked_at is not None

        assert (
            session.revocation_reason
            == "REUSE_DETECTED"
        )

    with pytest.raises(RefreshSessionError):

        service.rotate_session(
            replacement.refresh_token
        )


def test_reuse_does_not_revoke_other_families(
    db_session,
    user_id
):

    service = RefreshSessionService(db_session)

    first = service.create_session(user_id)
    second = service.create_session(user_id)

    service.rotate_session(first.refresh_token)

    with pytest.raises(RefreshTokenReuseError):

        service.rotate_session(first.refresh_token)

    with db_session.begin():

        session = get_session(
            db_session,
            second.refresh_token
        )

        assert session.revoked_at is None


def test_logout_revokes_session(
    db_session,
    user_id
):

    service = RefreshSessionService(db_session)

    tokens = service.create_session(user_id)

    service.revoke_session(tokens.refresh_token)

    with db_session.begin():

        session = get_session(
            db_session,
            tokens.refresh_token
        )

        assert session.revoked_at is not None
        assert session.revocation_reason == "LOGOUT"

    with pytest.raises(RefreshSessionError):

        service.rotate_session(tokens.refresh_token)


def test_revoke_all_sessions(db_session, user_id):

    service = RefreshSessionService(db_session)

    service.create_session(user_id)
    service.create_session(user_id)

    service.revoke_all_sessions(
        user_id,
        RevocationReason.PASSWORD_CHANGED
    )

    with db_session.begin():

        sessions = db_session.scalars(
            select(RefreshSession).where(
                RefreshSession.user_id == user_id
            )
        ).all()

        assert len(sessions) == 2

        assert all(
            session.revoked_at is not None
            for session in sessions
        )

        assert all(
            session.revocation_reason == "PASSWORD_CHANGED"
            for session in sessions
        )


def test_inactive_user_cannot_create_session(
    db_session,
    user_id
):

    with db_session.begin():

        user = db_session.get(User, user_id)
        user.is_active = False

    service = RefreshSessionService(db_session)

    with pytest.raises(RefreshSessionError):

        service.create_session(user_id)


def test_inactive_user_cannot_refresh(
    db_session,
    user_id
):

    service = RefreshSessionService(db_session)

    tokens = service.create_session(user_id)

    with db_session.begin():

        user = db_session.get(User, user_id)
        user.is_active = False

    with pytest.raises(RefreshSessionError):

        service.rotate_session(tokens.refresh_token)


def test_unregistered_refresh_token_rejected(
    db_session,
    user_id
):

    service = RefreshSessionService(db_session)

    token = create_refresh_token(user_id)

    with pytest.raises(RefreshSessionError):

        service.rotate_session(token)


def test_invalid_refresh_token_rejected(db_session):

    service = RefreshSessionService(db_session)

    with pytest.raises(RefreshSessionError):

        service.rotate_session("invalid-token")


def test_access_token_cannot_refresh(
    db_session,
    user_id
):

    service = RefreshSessionService(db_session)

    tokens = service.create_session(user_id)

    with pytest.raises(RefreshSessionError):

        service.rotate_session(tokens.access_token)


def test_digest_mismatch_rejected(
    db_session,
    user_id
):

    service = RefreshSessionService(db_session)

    tokens = service.create_session(user_id)

    with db_session.begin():

        session = get_session(
            db_session,
            tokens.refresh_token
        )

        session.token_digest = "0" * 64

    with pytest.raises(RefreshSessionError):

        service.rotate_session(tokens.refresh_token)


def test_expired_database_session_rejected(
    db_session,
    user_id
):

    service = RefreshSessionService(db_session)

    tokens = service.create_session(user_id)

    with db_session.begin():

        session = get_session(
            db_session,
            tokens.refresh_token
        )

        now = datetime.now(timezone.utc)

        session.created_at = now - timedelta(days=2)
        session.expires_at = now - timedelta(days=1)

    with pytest.raises(RefreshSessionError):

        service.rotate_session(tokens.refresh_token)


def test_rotation_failure_rolls_back(
    db_session,
    user_id,
    monkeypatch
):

    service = RefreshSessionService(db_session)

    tokens = service.create_session(user_id)

    def fail_issue(*args, **kwargs):

        raise RuntimeError("Simulated token issue failure")

    monkeypatch.setattr(
        service,
        "_issue_token_pair",
        fail_issue
    )

    with pytest.raises(RuntimeError):

        service.rotate_session(tokens.refresh_token)

    with db_session.begin():

        session = get_session(
            db_session,
            tokens.refresh_token
        )

        assert session.revoked_at is None
        assert session.revocation_reason is None


def test_disabled_password_user_rejected(
    db_session,
    user_id
):

    with db_session.begin():

        user = db_session.get(User, user_id)

        user.password_hash = "!LOGIN_DISABLED"

    service = RefreshSessionService(db_session)

    with pytest.raises(RefreshSessionError):

        service.create_session(user_id)