from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from fastapi.testclient import TestClient

from app.main import app, fastapi_app
from app.db.session import get_db

from app.core.config import settings
from app.core.auth_cookies import REFRESH_COOKIE_NAME

from app.core.exceptions import UnauthorizedException

from app.schemas.auth import UserResponse

from app.services.auth_service import AuthService

from app.services.refresh_session_service import (
    RefreshSessionService,
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
    "full_name": "Test Customer"
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


@pytest.fixture
def mocked_services(monkeypatch):

    tokens = TokenPair(
        access_token="test-access-token",
        refresh_token="test-refresh-token"
    )

    user = UserResponse(
        id=uuid4(),
        full_name="Test Customer",
        email="customer@example.com",
        role="CUSTOMER",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    services = {
        "register": Mock(return_value=user),
        "login": Mock(return_value=tokens),
        "refresh": Mock(return_value=tokens),
        "logout": Mock()
    }

    monkeypatch.setattr(
        AuthService,
        "register",
        services["register"]
    )

    monkeypatch.setattr(
        AuthService,
        "login",
        services["login"]
    )

    monkeypatch.setattr(
        RefreshSessionService,
        "rotate_session",
        services["refresh"]
    )

    monkeypatch.setattr(
        RefreshSessionService,
        "revoke_session",
        services["logout"]
    )

    return services


@pytest.mark.parametrize(
    "action, limit_field, expected_status",
    [
        (
            "register",
            "auth_register_rate_limit",
            201
        ),
        (
            "login",
            "auth_login_rate_limit",
            200
        ),
        (
            "refresh",
            "auth_refresh_rate_limit",
            200
        ),
        (
            "logout",
            "auth_logout_rate_limit",
            200
        )
    ]
)
def test_endpoint_rate_limit(
    auth_client,
    mocked_services,
    action,
    limit_field,
    expected_status
):

    limit = getattr(settings, limit_field)

    def send_request():

        kwargs = {
            "headers": HEADERS
        }

        if action == "register":

            kwargs["json"] = REGISTER_DATA

        elif action == "login":

            kwargs["json"] = LOGIN_DATA

        elif action in ("refresh", "logout"):

            auth_client.cookies.set(
                REFRESH_COOKIE_NAME,
                "test-refresh-token",
                domain="testserver.local",
                path="/api/v1/auth"
            )

        return auth_client.post(
            f"{BASE_URL}/{action}",
            **kwargs
        )

    for _ in range(limit):

        response = send_request()

        assert response.status_code == expected_status

    response = send_request()

    assert response.status_code == 429

    assert int(
        response.headers["retry-after"]
    ) > 0

    assert response.headers[
        "cache-control"
    ] == "no-store"

    assert mocked_services[action].call_count == limit


def test_failed_login_attempts_are_counted(
    auth_client,
    mocked_services
):

    mocked_services["login"].side_effect = (
        UnauthorizedException(
            "Invalid email or password."
        )
    )

    limit = settings.auth_login_rate_limit

    for _ in range(limit):

        response = auth_client.post(
            f"{BASE_URL}/login",
            json=LOGIN_DATA,
            headers=HEADERS
        )

        assert response.status_code == 401

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=HEADERS
    )

    assert response.status_code == 429

    assert mocked_services["login"].call_count == limit


def test_endpoint_limits_are_independent(
    auth_client,
    mocked_services
):

    for _ in range(settings.auth_login_rate_limit):

        response = auth_client.post(
            f"{BASE_URL}/login",
            json=LOGIN_DATA,
            headers=HEADERS
        )

        assert response.status_code == 200

    blocked = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=HEADERS
    )

    assert blocked.status_code == 429

    response = auth_client.post(
        f"{BASE_URL}/register",
        json=REGISTER_DATA,
        headers=HEADERS
    )

    assert response.status_code == 201


def test_forwarded_header_cannot_bypass_limit(
    auth_client,
    mocked_services
):

    for i in range(settings.auth_login_rate_limit):

        response = auth_client.post(
            f"{BASE_URL}/login",
            json=LOGIN_DATA,
            headers={
                **HEADERS,
                "X-Forwarded-For": f"192.0.2.{i + 1}"
            }
        )

        assert response.status_code == 200

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers={
            **HEADERS,
            "X-Forwarded-For": "198.51.100.1"
        }
    )

    assert response.status_code == 429


def test_untrusted_origin_does_not_consume_limit(
    auth_client,
    mocked_services
):

    limit = settings.auth_login_rate_limit

    for _ in range(limit):

        response = auth_client.post(
            f"{BASE_URL}/login",
            json=LOGIN_DATA,
            headers={
                **HEADERS,
                "Origin": "https://untrusted.example.com"
            }
        )

        assert response.status_code == 403
        
    for _ in range(limit):
        response = auth_client.post(
            f"{BASE_URL}/login",
            json=LOGIN_DATA,
            headers=HEADERS
        )
        assert response.status_code == 200