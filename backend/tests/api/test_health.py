
import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.api


def test_home_endpoint(client: TestClient):

    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == (
        "Welcome to the 3-Tier Banking Agent API"
    )

    assert data["status"] == "running"

    assert data["environment"] == "testing"


def test_health_endpoint(client: TestClient):

    response = client.get("/api/v1/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
        "service": "banking-agent-backend"
    }


def test_swagger_documentation(client: TestClient):

    response = client.get("/docs")

    assert response.status_code == 200

    assert "text/html" in response.headers[
        "content-type"
    ]


def test_openapi_schema(client: TestClient):

    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    assert "/" in schema["paths"]

    assert "/api/v1/health" in schema["paths"]


def test_temporary_endpoint_removed(
    client: TestClient
):

    response = client.get(
        "/test-internal-error"
    )

    assert response.status_code == 404
