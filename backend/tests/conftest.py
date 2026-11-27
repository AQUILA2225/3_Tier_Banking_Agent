
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


from app.main import app

@pytest.fixture
def client() -> Generator[TestClient, None, None]:

    with TestClient(
        app,
        raise_server_exceptions=False
    ) as test_client:

        yield test_client
