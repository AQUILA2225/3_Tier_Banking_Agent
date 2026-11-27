from datetime import datetime, timezone
from uuid import uuid4

import pytest

from pydantic import ValidationError

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse
)


pytestmark = pytest.mark.unit


def registration_data(**overrides):

    data = {
        "full_name": "Demo Customer",
        "email": "customer@example.com",
        "password": "DemoPassword@123"
    }

    data.update(overrides)

    return data


def test_valid_registration():

    request = RegisterRequest(
        **registration_data()
    )

    assert request.full_name == "Demo Customer"
    assert request.email == "customer@example.com"

    assert request.password.get_secret_value() == (
        "DemoPassword@123"
    )


def test_email_normalization():

    request = RegisterRequest(
        **registration_data(
            email=" CUSTOMER@EXAMPLE.COM "
        )
    )

    assert request.email == "customer@example.com"


def test_full_name_normalization():

    request = RegisterRequest(
        **registration_data(
            full_name="  Demo   Customer  "
        )
    )

    assert request.full_name == "Demo Customer"


@pytest.mark.parametrize(
    "email",
    ["", "invalid-email", "customer@"]
)
def test_invalid_registration_email(email):

    with pytest.raises(ValidationError):

        RegisterRequest(
            **registration_data(email=email)
        )


@pytest.mark.parametrize(
    "full_name",
    ["", "A", "   ", "a" * 101]
)
def test_invalid_full_name(full_name):

    with pytest.raises(ValidationError):

        RegisterRequest(
            **registration_data(full_name=full_name)
        )


@pytest.mark.parametrize(
    "password",
    ["", "short", "a" * 129, " " * 12]
)
def test_invalid_registration_password(password):

    with pytest.raises(ValidationError):

        RegisterRequest(
            **registration_data(password=password)
        )


@pytest.mark.parametrize(
    "role",
    ["CUSTOMER", "REVIEWER", "ADMIN"]
)
def test_registration_role_injection_rejected(role):

    with pytest.raises(ValidationError):

        RegisterRequest(
            **registration_data(role=role)
        )


def test_registration_password_masked():

    request = RegisterRequest(
        **registration_data()
    )

    assert "DemoPassword@123" not in repr(request)

    assert str(request.password) == "**********"


def test_valid_login():

    request = LoginRequest(
        email="CUSTOMER@EXAMPLE.COM",
        password="DemoPassword@123"
    )

    assert request.email == "customer@example.com"


def test_login_accepts_legacy_short_password():

    request = LoginRequest(
        email="customer@example.com",
        password="oldpass"
    )

    assert request.password.get_secret_value() == "oldpass"


@pytest.mark.parametrize("password", ["", "a" * 129])
def test_invalid_login_password(password):

    with pytest.raises(ValidationError):

        LoginRequest(
            email="customer@example.com",
            password=password
        )


def test_user_response_excludes_password_hash():
    response = UserResponse.model_validate({
        "id": uuid4(),
        "full_name": "Demo Customer",
        "email": "customer@example.com",
        "role": "CUSTOMER",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "password_hash": "secret-password-hash"
    })
    assert "password_hash" not in response.model_dump()


def test_valid_token_response():
    response = TokenResponse(
        access_token="test-access-token",
        expires_in=900
    )

    assert response.token_type == "bearer"
    assert response.expires_in == 900

    assert "refresh_token" not in response.model_dump()
    assert "test-access-token" not in repr(response)

@pytest.mark.parametrize("expires_in", [0, -1])
def test_invalid_token_expiration(expires_in):

    with pytest.raises(ValidationError):

        TokenResponse(
            access_token="test-access-token",
            expires_in=expires_in
        )