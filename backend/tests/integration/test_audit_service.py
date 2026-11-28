from contextlib import contextmanager
from unittest.mock import Mock
from uuid import uuid4

import pytest

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import AuditLog, User

from app.services import audit_service

from app.services.audit_service import (
    AuditService,
    AuthAuditEvent
)


pytestmark = pytest.mark.integration


@pytest.fixture
def audit_db(db_session, monkeypatch):

    @contextmanager
    def begin_session():

        with db_session.begin():

            yield db_session

    session_factory = Mock()

    session_factory.begin.side_effect = (
        begin_session
    )

    monkeypatch.setattr(
        audit_service,
        "SessionLocal",
        session_factory
    )

    return db_session


def test_auth_event_persisted(audit_db):

    request_id = uuid4()

    result = AuditService.record_auth_event(
        AuthAuditEvent.LOGIN_FAILURE,
        request_id=request_id
    )

    assert result is True

    with audit_db.begin():

        record = audit_db.scalar(
            select(AuditLog).where(
                AuditLog.request_id == request_id
            )
        )

        assert record is not None
        assert record.action == "AUTH_LOGIN_FAILURE"
        assert record.entity_type == "AUTHENTICATION"
        assert record.user_id is None
        assert record.created_at is not None


def test_authenticated_user_association(audit_db):

    user_id = uuid4()
    request_id = uuid4()

    with audit_db.begin():

        user = User(
            id=user_id,
            full_name="Audit Test Customer",
            email=f"{uuid4()}@example.com",
            password_hash="!LOGIN_DISABLED",
            role="CUSTOMER",
            is_active=True
        )

        audit_db.add(user)

    assert AuditService.record_auth_event(
        AuthAuditEvent.LOGIN_SUCCESS,
        user_id=user_id,
        request_id=request_id
    )

    with audit_db.begin():

        record = audit_db.scalar(
            select(AuditLog).where(
                AuditLog.request_id == request_id
            )
        )

        assert record.user_id == user_id
        assert record.entity_id == user_id


def test_request_id_string_normalized(audit_db):

    request_id = uuid4()

    assert AuditService.record_auth_event(
        AuthAuditEvent.REFRESH_SUCCESS,
        request_id=str(request_id)
    )

    with audit_db.begin():

        record = audit_db.scalar(
            select(AuditLog).where(
                AuditLog.request_id == request_id
            )
        )

        assert record.request_id == request_id


def test_invalid_request_id_handled(audit_db):

    assert AuditService.record_auth_event(
        AuthAuditEvent.CSRF_REJECTED,
        request_id="invalid-uuid"
    )

    with audit_db.begin():

        record = audit_db.scalar(
            select(AuditLog).where(
                AuditLog.action == "AUTH_CSRF_REJECTED",
                AuditLog.request_id.is_(None)
            )
        )

        assert record is not None
        assert record.request_id is None


def test_audit_details_contain_no_credentials(audit_db):

    request_id = uuid4()

    assert AuditService.record_auth_event(
        AuthAuditEvent.LOGIN_FAILURE,
        request_id=request_id
    )

    with audit_db.begin():

        record = audit_db.scalar(
            select(AuditLog).where(
                AuditLog.request_id == request_id
            )
        )

        assert record.event_details == {
            "category": "AUTHENTICATION"
        }


def test_invalid_event_rejected(audit_db):

    with pytest.raises(ValueError):

        AuditService.record_auth_event(
            "INVALID_EVENT"
        )


def test_database_failure_handled(
    audit_db,
    monkeypatch,
    caplog
):

    factory = Mock()

    factory.begin.side_effect = SQLAlchemyError(
        "Simulated database failure"
    )

    monkeypatch.setattr(
        audit_service,
        "SessionLocal",
        factory
    )

    result = AuditService.record_auth_event(
        AuthAuditEvent.LOGIN_FAILURE
    )

    assert result is False

    assert "Authentication audit persistence failed" in (
        caplog.text
    )

    assert "Simulated database failure" not in caplog.text