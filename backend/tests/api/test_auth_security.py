from unittest.mock import Mock

import pytest

from fastapi.testclient import TestClient

from app.main import app, fastapi_app
from app.db.session import get_db

from app.core.config import settings

from app.core.exceptions import (
    ConflictException,
    UnauthorizedException
)

from app.services.auth_service import AuthService


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
    "full_name": "Security Test Customer"
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


def assert_no_cache(response):

    assert response.headers["cache-control"] == "no-store"

    assert response.headers["pragma"] == "no-cache"


def test_login_failure_not_cached(
    auth_client,
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

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=HEADERS
    )

    assert response.status_code == 401

    assert_no_cache(response)


def test_duplicate_registration_not_cached(
    auth_client,
    monkeypatch
):

    monkeypatch.setattr(
        AuthService,
        "register",
        Mock(
            side_effect=ConflictException(
                "Email address is already registered."
            )
        )
    )

    response = auth_client.post(
        f"{BASE_URL}/register",
        json=REGISTER_DATA,
        headers=HEADERS
    )

    assert response.status_code == 409

    assert_no_cache(response)


def test_csrf_rejection_not_cached(auth_client):

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA
    )

    assert response.status_code == 403

    assert_no_cache(response)


def test_missing_refresh_cookie_not_cached(
    auth_client
):

    response = auth_client.post(
        f"{BASE_URL}/refresh",
        headers=HEADERS
    )

    assert response.status_code == 401

    assert_no_cache(response)


def test_missing_access_token_not_cached(
    auth_client
):

    response = auth_client.get(
        f"{BASE_URL}/me"
    )

    assert response.status_code == 401

    assert response.headers[
        "www-authenticate"
    ] == "Bearer"

    assert_no_cache(response)


def test_validation_error_not_cached(
    auth_client
):

    response = auth_client.post(
        f"{BASE_URL}/register",
        json={},
        headers=HEADERS
    )

    assert response.status_code == 422

    assert_no_cache(response)


def test_rate_limit_error_not_cached(
    auth_client,
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

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=HEADERS
    )

    assert response.status_code == 429

    assert int(
        response.headers["retry-after"]
    ) > 0

    assert_no_cache(response)


def test_unexpected_auth_error_not_cached(
    auth_client,
    monkeypatch
):

    sensitive_message = "InternalSecretTestValue"

    monkeypatch.setattr(
        AuthService,
        "login",
        Mock(
            side_effect=RuntimeError(
                sensitive_message
            )
        )
    )

    response = auth_client.post(
        f"{BASE_URL}/login",
        json=LOGIN_DATA,
        headers=HEADERS
    )

    assert response.status_code == 500

    assert sensitive_message not in response.text

    assert_no_cache(response)


def test_non_auth_error_cache_policy_unchanged(
    auth_client
):

    response = auth_client.get(
        "/nonexistent-security-test-path"
    )

    assert response.status_code == 404

    assert "no-store" not in response.headers.get(
        "cache-control",
        ""
    )