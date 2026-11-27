import pytest
from pydantic import ValidationError

from app.core.config import Settings

pytestmark = pytest.mark.unit
def test_valid_security_configuration():

    settings = Settings()

    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_issuer == "banking-agent-api"
    assert settings.jwt_audience == "banking-agent-client"
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 7
    assert settings.password_min_length == 12
    assert settings.password_max_length == 128

    assert len(
        settings.jwt_secret_key.get_secret_value()
    ) == 64
    assert str(settings.jwt_secret_key) == "**********"

@pytest.mark.parametrize(
    "secret",
    ["", "short-secret", "z" * 64]
)
def test_invalid_jwt_secret_rejected(secret):
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key=secret)

def test_unsupported_jwt_algorithm_rejected():
    with pytest.raises(ValidationError):
        Settings(jwt_algorithm="none")

@pytest.mark.parametrize("minutes", [0, 61])
def test_invalid_access_token_expiration(minutes):
    with pytest.raises(ValidationError):
        Settings(
            access_token_expire_minutes=minutes
        )

@pytest.mark.parametrize("days", [0, 31])
def test_invalid_refresh_token_expiration(days):
    with pytest.raises(ValidationError):
        Settings(
            refresh_token_expire_days=days
        )

@pytest.mark.parametrize(
    "field_name",
    ["jwt_issuer", "jwt_audience"]
)
def test_invalid_jwt_identifier(field_name):
    with pytest.raises(ValidationError):
        Settings(
            **{field_name: "invalid identifier"}
        )

def test_invalid_password_policy():
    with pytest.raises(ValidationError):
        Settings(
            password_min_length=20,
            password_max_length=12
        )