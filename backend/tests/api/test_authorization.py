from datetime import datetime, timezone
from typing import Annotated
from unittest.mock import Mock
from uuid import uuid4

import pytest

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.api.deps import (
    CustomerUser,
    ReviewerUser,
    AdminUser,
    require_roles,
    require_permissions
)

from app.core.permissions import Permission
from app.core.security import create_access_token

from app.db.session import get_db

from app.models import User, UserRole

from app.repositories.user_repository import (
    UserRepository
)


pytestmark = pytest.mark.api


test_app = FastAPI()


@test_app.get("/customer")
def customer_endpoint(user: CustomerUser):

    return {"role": user.role}


@test_app.get("/reviewer")
def reviewer_endpoint(user: ReviewerUser):

    return {"role": user.role}


@test_app.get("/admin")
def admin_endpoint(user: AdminUser):

    return {"role": user.role}


@test_app.get("/transfer")
def transfer_endpoint(
    user: Annotated[
        User,
        Depends(
            require_permissions(
                Permission.TRANSFER_INITIATE
            )
        )
    ]
):

    return {"allowed": True}


@test_app.get("/review")
def review_endpoint(
    user: Annotated[
        User,
        Depends(
            require_permissions(
                Permission.REVIEW_READ,
                Permission.REVIEW_DECIDE
            )
        )
    ]
):

    return {"allowed": True}


@test_app.get("/staff")
def staff_endpoint(
    user: Annotated[
        User,
        Depends(
            require_roles(
                UserRole.REVIEWER,
                UserRole.ADMIN
            )
        )
    ]
):

    return {"role": user.role}


@pytest.fixture
def user():

    return User(
        id=uuid4(),
        full_name="Authorization Test User",
        email="authorization@example.com",
        password_hash="test-only-password-hash",
        role=UserRole.CUSTOMER.value,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def client(monkeypatch, user):

    test_app.dependency_overrides[get_db] = (
        lambda: Mock()
    )

    monkeypatch.setattr(
        UserRepository,
        "get_by_id",
        Mock(return_value=user)
    )

    try:

        with TestClient(test_app) as test_client:

            yield test_client

    finally:

        test_app.dependency_overrides.clear()


def auth_headers(user):

    token = create_access_token(user.id)

    return {
        "Authorization": f"Bearer {token}"
    }


@pytest.mark.parametrize(
    "role, endpoint, expected_status",
    [
        ("CUSTOMER", "/customer", 200),
        ("CUSTOMER", "/reviewer", 403),
        ("CUSTOMER", "/admin", 403),

        ("REVIEWER", "/customer", 403),
        ("REVIEWER", "/reviewer", 200),
        ("REVIEWER", "/admin", 403),

        ("ADMIN", "/customer", 403),
        ("ADMIN", "/reviewer", 403),
        ("ADMIN", "/admin", 200)
    ]
)
def test_role_access_matrix(
    client,
    user,
    role,
    endpoint,
    expected_status
):

    user.role = role

    response = client.get(
        endpoint,
        headers=auth_headers(user)
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "role, expected_status",
    [
        ("CUSTOMER", 200),
        ("REVIEWER", 403),
        ("ADMIN", 403)
    ]
)
def test_transfer_permission(
    client,
    user,
    role,
    expected_status
):

    user.role = role

    response = client.get(
        "/transfer",
        headers=auth_headers(user)
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "role, expected_status",
    [
        ("CUSTOMER", 403),
        ("REVIEWER", 200),
        ("ADMIN", 403)
    ]
)
def test_multiple_required_permissions(
    client,
    user,
    role,
    expected_status
):

    user.role = role

    response = client.get(
        "/review",
        headers=auth_headers(user)
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "role, expected_status",
    [
        ("CUSTOMER", 403),
        ("REVIEWER", 200),
        ("ADMIN", 200)
    ]
)
def test_multiple_allowed_roles(
    client,
    user,
    role,
    expected_status
):

    user.role = role

    response = client.get(
        "/staff",
        headers=auth_headers(user)
    )

    assert response.status_code == expected_status


def test_unauthenticated_request_rejected(client):

    response = client.get("/customer")

    assert response.status_code == 401


def test_inactive_user_rejected(client, user):

    user.is_active = False

    response = client.get(
        "/customer",
        headers=auth_headers(user)
    )

    assert response.status_code == 401


def test_unknown_role_rejected(client, user):

    user.role = "UNKNOWN"

    response = client.get(
        "/customer",
        headers=auth_headers(user)
    )

    assert response.status_code == 403


def test_forbidden_response_not_cached(
    client,
    user
):

    user.role = "CUSTOMER"

    response = client.get(
        "/admin",
        headers=auth_headers(user)
    )

    assert response.status_code == 403

    assert response.headers[
        "cache-control"
    ] == "no-store"


def test_database_role_change_takes_effect(
    client,
    user
):

    headers = auth_headers(user)

    response = client.get(
        "/customer",
        headers=headers
    )

    assert response.status_code == 200

    user.role = "REVIEWER"

    response = client.get(
        "/customer",
        headers=headers
    )

    assert response.status_code == 403

    response = client.get(
        "/reviewer",
        headers=headers
    )

    assert response.status_code == 200