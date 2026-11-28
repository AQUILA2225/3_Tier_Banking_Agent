from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from fastapi.testclient import TestClient

from app.main import app, fastapi_app
from app.db.session import get_db

from app.core.security import (
    DISABLED_PASSWORD_HASH,
    create_access_token,
    create_refresh_token
)

from app.models import User, UserRole
from app.repositories.user_repository import UserRepository


pytestmark = pytest.mark.api

ME_URL = "/api/v1/auth/me"


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
def user():

    return User(
        id=uuid4(),
        full_name="Test Customer",
        email="customer@example.com",
        password_hash="test-only-password-hash",
        role=UserRole.CUSTOMER.value,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def user_lookup(monkeypatch, user):

    lookup = Mock(return_value=user)

    monkeypatch.setattr(
        UserRepository,
        "get_by_id",
        lookup
    )

    return lookup


def authorization_headers(token):

    return {
        "Authorization": f"Bearer {token}"
    }


def test_get_current_user_success(
    auth_client,
    user,
    user_lookup
):

    token = create_access_token(user.id)

    response = auth_client.get(
        ME_URL,
        headers=authorization_headers(token)
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(user.id)
    assert data["email"] == user.email
    assert data["full_name"] == user.full_name
    assert data["role"] == "CUSTOMER"
    assert data["is_active"] is True

    user_lookup.assert_called_once_with(user.id)


def test_missing_authorization_header(
    auth_client
):

    response = auth_client.get(ME_URL)

    assert response.status_code == 401


def test_invalid_authorization_scheme(
    auth_client
):

    response = auth_client.get(
        ME_URL,
        headers={
            "Authorization": "Basic invalid-token"
        }
    )

    assert response.status_code == 401


def test_empty_bearer_token(auth_client):

    response = auth_client.get(
        ME_URL,
        headers={
            "Authorization": "Bearer"
        }
    )

    assert response.status_code == 401


def test_invalid_access_token(auth_client):

    response = auth_client.get(
        ME_URL,
        headers=authorization_headers(
            "invalid-access-token"
        )
    )

    assert response.status_code == 401


def test_refresh_token_cannot_authenticate(
    auth_client,
    user
):

    token = create_refresh_token(user.id)

    response = auth_client.get(
        ME_URL,
        headers=authorization_headers(token)
    )

    assert response.status_code == 401


def test_nonexistent_user_rejected(
    auth_client,
    user,
    user_lookup
):

    user_lookup.return_value = None

    token = create_access_token(user.id)

    response = auth_client.get(
        ME_URL,
        headers=authorization_headers(token)
    )

    assert response.status_code == 401


def test_inactive_user_rejected(
    auth_client,
    user,
    user_lookup
):

    user.is_active = False

    token = create_access_token(user.id)

    response = auth_client.get(
        ME_URL,
        headers=authorization_headers(token)
    )

    assert response.status_code == 401


def test_disabled_password_user_rejected(
    auth_client,
    user,
    user_lookup
):

    user.password_hash = DISABLED_PASSWORD_HASH

    token = create_access_token(user.id)

    response = auth_client.get(
        ME_URL,
        headers=authorization_headers(token)
    )

    assert response.status_code == 401


def test_sensitive_fields_not_exposed(
    auth_client,
    user,
    user_lookup
):

    token = create_access_token(user.id)

    response = auth_client.get(
        ME_URL,
        headers=authorization_headers(token)
    )

    assert response.status_code == 200

    data = response.json()

    assert "password_hash" not in data
    assert "password" not in data
    assert "access_token" not in data
    assert "refresh_token" not in data


def test_authentication_challenge_header(
    auth_client
):

    response = auth_client.get(ME_URL)

    assert response.status_code == 401

    assert response.headers[
        "www-authenticate"
    ] == "Bearer"


def test_current_user_response_not_cached(
    auth_client,
    user,
    user_lookup
):

    token = create_access_token(user.id)

    response = auth_client.get(
        ME_URL,
        headers=authorization_headers(token)
    )

    assert response.status_code == 200

    assert response.headers[
        "cache-control"
    ] == "no-store"


def test_invalid_token_skips_user_lookup(
    auth_client,
    user_lookup
):

    response = auth_client.get(
        ME_URL,
        headers=authorization_headers(
            "invalid-token"
        )
    )

    assert response.status_code == 401

    user_lookup.assert_not_called()


@pytest.mark.parametrize(
    "role",
    ["CUSTOMER", "REVIEWER", "ADMIN"]
)
def test_current_user_returns_database_role(
    auth_client,
    user,
    user_lookup,
    role
):

    user.role = role

    token = create_access_token(user.id)

    response = auth_client.get(
        ME_URL,
        headers=authorization_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["role"] == role