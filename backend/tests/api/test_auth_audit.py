from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from fastapi.testclient import TestClient

from app.main import app, fastapi_app
from app.db.session import get_db

from app.core.config import settings
from app.core.security import create_access_token
from app.core.auth_cookies import REFRESH_COOKIE_NAME

from app.core.exceptions import (
    ConflictException,
    UnauthorizedException
)

from app.schemas.auth import UserResponse

from app.services.audit_service import AuthAuditEvent
from app.services.auth_service import AuthService

from app.services.refresh_session_service import (
    RefreshSessionService,
    RefreshSessionError,
    RefreshTokenReuseError,
    TokenPair
)


pytestmark = pytest.mark.api

BASE_URL = "/api/v1/auth"

HEADERS = {
    "Origin": "http://localhost:5173",
    "X-CSRF-Protection": "1"
}

LOGIN_DATA = {
    "email": "customer@example.com",
    "password": "DemoPassword@123"
}

REGISTER_DATA = {
    **LOGIN_DATA,
    "full_name": "Audit Test Customer"
}


@pytest.fixture
def auth_client():

    fastapi_app.dependency_overrides[get_db] = (
        lambda: Mock()
    )

    try:

        with TestClient(
            app,
            raise_server_exceptions=False
        ) as client:

            yield client

    finally:

        fastapi_app.dependency_overrides.pop(
            get_db,
            None
        )


@pytest.mark.parametrize(
    "action, outcome, expected_event, expected_status",
    [
        (
            "register", "success",
            AuthAuditEvent.REGISTER_SUCCESS, 201
        ),
        (
            "register", "failure",
            AuthAuditEvent.REGISTER_FAILURE, 409
        ),
        (
            "login", "success",
            AuthAuditEvent.LOGIN_SUCCESS, 200
        ),
        (
            "login", "failure",
            AuthAuditEvent.LOGIN_FAILURE, 401
        ),
        (
            "refresh", "success",
            AuthAuditEvent.REFRESH_SUCCESS, 200
        ),
        (
            "refresh", "failure",
            AuthAuditEvent.REFRESH_FAILURE, 401
        ),
        (
            "refresh", "reuse",
            AuthAuditEvent.REFRESH_REUSE, 401
        ),
        (
            "refresh", "missing",
            AuthAuditEvent.REFRESH_FAILURE, 401
        ),
        (
            "logout", "success",
            AuthAuditEvent.LOGOUT_SUCCESS, 200
        ),
        (
            "logout", "failure",
            AuthAuditEvent.LOGOUT_NO_SESSION, 200
        ),
        (
            "logout", "missing",
            AuthAuditEvent.LOGOUT_NO_SESSION, 200
        )
    ]
)
def test_authentication_audit_events(
    auth_client,
    audit_mock,
    monkeypatch,
    action,
    outcome,
    expected_event,
    expected_status
):

    user_id = uuid4()

    user = UserResponse(
        id=user_id,
        full_name="Audit Test Customer",
        email="customer@example.com",
        role="CUSTOMER",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    tokens = TokenPair(
        access_token=create_access_token(user_id),
        refresh_token="test-refresh-token"
    )

    kwargs = {"headers": HEADERS}

    if action == "register":

        service_mock = Mock(return_value=user)

        if outcome == "failure":

            service_mock.side_effect = ConflictException(
                "Email address is already registered."
            )

        monkeypatch.setattr(
            AuthService,
            "register",
            service_mock
        )

        kwargs["json"] = REGISTER_DATA

    elif action == "login":

        service_mock = Mock(return_value=tokens)

        if outcome == "failure":

            service_mock.side_effect = UnauthorizedException(
                "Invalid email or password."
            )

        monkeypatch.setattr(
            AuthService,
            "login",
            service_mock
        )

        kwargs["json"] = LOGIN_DATA

    elif action == "refresh":

        service_mock = Mock(return_value=tokens)

        if outcome == "failure":

            service_mock.side_effect = RefreshSessionError(
                "Invalid refresh session."
            )

        elif outcome == "reuse":

            service_mock.side_effect = RefreshTokenReuseError(
                "Refresh token reuse detected."
            )

        monkeypatch.setattr(
            RefreshSessionService,
            "rotate_session",
            service_mock
        )

    elif action == "logout":

        service_mock = Mock()

        if outcome == "failure":

            service_mock.side_effect = RefreshSessionError(
                "Invalid refresh session."
            )

        monkeypatch.setattr(
            RefreshSessionService,
            "revoke_session",
            service_mock
        )

    if (
        action in ("refresh", "logout")
        and outcome != "missing"
    ):

        auth_client.cookies.set(
            REFRESH_COOKIE_NAME,
            "test-refresh-token"
        )

    response = auth_client.post(
        f"{BASE_URL}/{action}",
        **kwargs
    )

    assert response.status_code == expected_status

    audit_mock.assert_called_once()

    args, event_kwargs = audit_mock.call_args

    assert args[0] == expected_event

    expected_user_id = (
        user_id
        if outcome == "success"
        and action in ("register", "login", "refresh")
        else None
    )

    assert event_kwargs["user_id"] == expected_user_id

    assert UUID(
        str(event_kwargs["request_id"])
    ) == UUID(response.headers["x-request-id"])

    assert set(event_kwargs) == {
        "user_id",
        "request_id"
    }


def test_rate_limit_event_recorded(
    auth_client,
    audit_mock,
    monkeypatch
):

    monkeypatch.setattr(
        AuthService,
        "login",
        Mock(
            side_effect=UnauthorizedException(
                "Invalid email or password."
            )
        )
    )

    for _ in range(settings.auth_login_rate_limit):

        response = auth_client.post(
            f"{BASE_URL}/login",
            json=LOGIN_DATA,
            headers=HEADERS
        )

        assert response.status_code == 401

    audit_mock.reset_mock()

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=HEADERS
    )

    assert response.status_code == 429

    audit_mock.assert_called_once()

    assert audit_mock.call_args.args[0] == (
        AuthAuditEvent.RATE_LIMIT_EXCEEDED
    )


@pytest.mark.parametrize(
    "headers",
    [
        {
            "Origin": "https://untrusted.example.com",
            "X-CSRF-Protection": "1"
        },
        {
            "Origin": "http://localhost:5173"
        }
    ]
)
def test_csrf_rejection_event_recorded(
    auth_client,
    audit_mock,
    headers
):

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=headers
    )

    assert response.status_code == 403

    audit_mock.assert_called_once()

    assert audit_mock.call_args.args[0] == (
        AuthAuditEvent.CSRF_REJECTED
    )


def test_audit_failure_does_not_break_login(
    auth_client,
    audit_mock,
    monkeypatch
):

    audit_mock.return_value = False

    tokens = TokenPair(
        access_token=create_access_token(uuid4()),
        refresh_token="test-refresh-token"
    )

    monkeypatch.setattr(
        AuthService,
        "login",
        Mock(return_value=tokens)
    )

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=HEADERS
    )

    assert response.status_code == 200

    assert response.json()["access_token"] == (
        tokens.access_token
    )