from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from fastapi.testclient import TestClient

from app.main import app, fastapi_app
from app.db.session import get_db

from app.core.auth_cookies import REFRESH_COOKIE_NAME

from app.core.exceptions import (
    ConflictException,
    UnauthorizedException
)

from app.schemas.auth import UserResponse

from app.services.auth_service import AuthService

from app.services.refresh_session_service import (
    RefreshSessionService,
    RefreshSessionError,
    TokenPair
)


pytestmark = pytest.mark.api

BASE_URL = "/api/v1/auth"

HEADERS = {
    "Origin": "http://localhost:5173",
    "X-CSRF-Protection": "1"
}

PASSWORD = "DemoPassword@123"

REGISTER_DATA = {
    "full_name": "Test Customer",
    "email": "customer@example.com",
    "password": PASSWORD
}

LOGIN_DATA = {
    "email": "customer@example.com",
    "password": PASSWORD
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
def token_pair():

    return TokenPair(
        access_token="test-access-token",
        refresh_token="test-refresh-token"
    )


def test_register_success(
    auth_client,
    monkeypatch
):

    user = UserResponse(
        id=uuid4(),
        full_name="Test Customer",
        email="customer@example.com",
        role="CUSTOMER",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    monkeypatch.setattr(
        AuthService,
        "register",
        lambda self, request: user
    )

    response = auth_client.post(
        f"{BASE_URL}/register",
        json=REGISTER_DATA,
        headers=HEADERS
    )

    assert response.status_code == 201
    assert response.json()["role"] == "CUSTOMER"
    assert "password_hash" not in response.json()


def test_duplicate_registration(
    auth_client,
    monkeypatch
):

    def fail_register(self, request):

        raise ConflictException(
            "Email address is already registered."
        )

    monkeypatch.setattr(
        AuthService,
        "register",
        fail_register
    )

    response = auth_client.post(
        f"{BASE_URL}/register",
        json=REGISTER_DATA,
        headers=HEADERS
    )

    assert response.status_code == 409


def test_login_success(
    auth_client,
    monkeypatch,
    token_pair
):

    monkeypatch.setattr(
        AuthService,
        "login",
        lambda self, request: token_pair
    )

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=HEADERS
    )

    assert response.status_code == 200

    assert response.json()["access_token"] == (
        token_pair.access_token
    )

    assert response.json()["expires_in"] == 900
    assert "refresh_token" not in response.json()

    assert response.cookies.get(
        REFRESH_COOKIE_NAME
    ) == token_pair.refresh_token

    cookie = response.headers["set-cookie"].lower()

    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api/v1/auth" in cookie

    assert response.headers["cache-control"] == (
        "no-store"
    )


def test_invalid_credentials(
    auth_client,
    monkeypatch
):

    def fail_login(self, request):

        raise UnauthorizedException(
            "Invalid email or password."
        )

    monkeypatch.setattr(
        AuthService,
        "login",
        fail_login
    )

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=HEADERS
    )

    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_refresh_success(
    auth_client,
    monkeypatch,
    token_pair
):

    rotate = Mock(return_value=token_pair)

    monkeypatch.setattr(
        RefreshSessionService,
        "rotate_session",
        rotate
    )

    auth_client.cookies.set(
        REFRESH_COOKIE_NAME,
        "old-refresh-token"
    )

    response = auth_client.post(
        f"{BASE_URL}/refresh",
        headers=HEADERS
    )

    assert response.status_code == 200

    rotate.assert_called_once_with(
        "old-refresh-token"
    )

    assert response.cookies.get(
        REFRESH_COOKIE_NAME
    ) == token_pair.refresh_token


def test_refresh_without_cookie(auth_client):

    response = auth_client.post(
        f"{BASE_URL}/refresh",
        headers=HEADERS
    )

    assert response.status_code == 401


def test_invalid_refresh_token(
    auth_client,
    monkeypatch
):

    def fail_refresh(self, token):

        raise RefreshSessionError(
            "Invalid refresh session."
        )

    monkeypatch.setattr(
        RefreshSessionService,
        "rotate_session",
        fail_refresh
    )

    auth_client.cookies.set(
        REFRESH_COOKIE_NAME,
        "invalid-token"
    )

    response = auth_client.post(
        f"{BASE_URL}/refresh",
        headers=HEADERS
    )

    assert response.status_code == 401


def test_logout_success(
    auth_client,
    monkeypatch
):

    revoke = Mock()

    monkeypatch.setattr(
        RefreshSessionService,
        "revoke_session",
        revoke
    )

    auth_client.cookies.set(
        REFRESH_COOKIE_NAME,
        "test-refresh-token"
    )

    response = auth_client.post(
        f"{BASE_URL}/logout",
        headers=HEADERS
    )

    assert response.status_code == 200

    revoke.assert_called_once_with(
        "test-refresh-token"
    )

    assert "max-age=0" in (
        response.headers["set-cookie"].lower()
    )


def test_logout_without_cookie(auth_client):

    response = auth_client.post(
        f"{BASE_URL}/logout",
        headers=HEADERS
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {
            "Origin": "https://untrusted.example.com",
            "X-CSRF-Protection": "1"
        },
        {
            "Origin": "http://localhost:5173"
        },
        {
            "Origin": "http://localhost:5173",
            "X-CSRF-Protection": "invalid"
        }
    ]
)
def test_csrf_protection(
    auth_client,
    headers
):

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=headers
    )

    assert response.status_code == 403


def test_password_not_exposed_in_validation_error(
    auth_client
):

    password = "SecretPassword@" * 20

    response = auth_client.post(
        f"{BASE_URL}/register",
        json={
            **REGISTER_DATA,
            "password": password
        },
        headers=HEADERS
    )

    assert response.status_code == 422
    assert password not in response.text
    assert "input" not in response.json()["error"]

def test_role_injection_rejected(auth_client):

    response = auth_client.post(
        f"{BASE_URL}/register",
        json={
            **REGISTER_DATA,
            "role": "ADMIN"
        },
        headers=HEADERS
    )

    assert response.status_code == 422