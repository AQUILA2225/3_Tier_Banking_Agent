
import pytest
from pydantic import ValidationError
from app.core.config import Settings

pytestmark = pytest.mark.unit

def test_valid_application_environment():
    settings = Settings(
        app_env="testing"
    )

    assert settings.app_env == "testing"

def test_invalid_application_environment():
    with pytest.raises(ValidationError):
        Settings(
            app_env="invalid"
        )

def test_valid_cors_origins():
    origins = [
        "http://localhost:5173",
        "https://banking.example.com"
    ]
    settings = Settings(
        cors_allowed_origins=origins
    )
    assert settings.cors_allowed_origins == origins

def test_duplicate_cors_origins():
    settings = Settings(
        cors_allowed_origins=[
            "http://localhost:5173",
            "http://localhost:5173"
        ]
    )
    assert settings.cors_allowed_origins == [
        "http://localhost:5173"
    ]

@pytest.mark.parametrize(
    "invalid_origin",
    [
        "*",
        "localhost:5173",
        "http://localhost:5173/",
        "http://localhost:5173/login",
        "http://localhost:5173?name=test",
        "http://localhost:5173#section",
        "http://localhost:99999"
    ]
)
def test_invalid_cors_origins(invalid_origin):
    with pytest.raises(ValidationError):
        Settings(
            cors_allowed_origins=[
                invalid_origin
            ]
        )

@pytest.mark.parametrize(
    "invalid_max_age",
    [-1, 86401]
)
def test_invalid_cors_max_age(invalid_max_age):
    with pytest.raises(ValidationError):
        Settings(
            cors_max_age=invalid_max_age
        )

def test_valid_cors_max_age():
    settings = Settings(
        cors_max_age=600
    )
    assert settings.cors_max_age == 600

def test_invalid_api_prefix():
    with pytest.raises(ValidationError):
        Settings(
            api_v1_prefix="api/v1"
        )
