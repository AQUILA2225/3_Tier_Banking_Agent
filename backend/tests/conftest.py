
import os
from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient


# Configure the application for testing
os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "INFO"

os.environ["CORS_ALLOWED_ORIGINS"] = (
    '["http://localhost:5173",'
    '"http://127.0.0.1:5173"]'
)

os.environ["CORS_ALLOW_CREDENTIALS"] = "false"
os.environ["CORS_MAX_AGE"] = "600"
os.environ["DB_PASSWORD"] = "test-only-password"

os.environ["JWT_SECRET_KEY"] = "ab" * 32
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ISSUER"] = "banking-agent-api"
os.environ["JWT_AUDIENCE"] = "banking-agent-client"

os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"

os.environ["PASSWORD_MIN_LENGTH"] = "12"
os.environ["PASSWORD_MAX_LENGTH"] = "128"
os.environ["AUTH_COOKIE_SECURE"] = "false"

os.environ["AUTH_RATE_LIMIT_WINDOW_SECONDS"] = "60"
os.environ["AUTH_REGISTER_RATE_LIMIT"] = "5"
os.environ["AUTH_LOGIN_RATE_LIMIT"] = "10"
os.environ["AUTH_REFRESH_RATE_LIMIT"] = "30"
os.environ["AUTH_LOGOUT_RATE_LIMIT"] = "30"
os.environ["AUTH_RATE_LIMIT_MAX_KEYS"] = "10000"


from app.main import app
from app.core.auth_rate_limit import auth_rate_limiter

@pytest.fixture
def client() -> Generator[TestClient, None, None]:

    with TestClient(
        app,
        raise_server_exceptions=False
    ) as test_client:

        yield test_client

@pytest.fixture(autouse=True)
def reset_auth_rate_limiter():

    auth_rate_limiter.reset()

    yield

    auth_rate_limiter.reset()
