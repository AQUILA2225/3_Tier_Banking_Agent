
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.error_handlers import (
    register_exception_handlers
)

from app.core.exceptions import (
    BadRequestException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ConflictException,
    ServiceUnavailableException
)

from app.middleware.request_logging import (
    RequestLoggingMiddleware
)


pytestmark = pytest.mark.api


@pytest.fixture
def error_client():

    test_app = FastAPI(debug=False)

    test_app.add_middleware(
        RequestLoggingMiddleware
    )

    register_exception_handlers(test_app)

    @test_app.get("/bad-request")
    def bad_request():
        raise BadRequestException()

    @test_app.get("/unauthorized")
    def unauthorized():
        raise UnauthorizedException()

    @test_app.get("/forbidden")
    def forbidden():
        raise ForbiddenException()

    @test_app.get("/not-found")
    def not_found():
        raise NotFoundException()

    @test_app.get("/conflict")
    def conflict():
        raise ConflictException()

    @test_app.get("/unavailable")
    def unavailable():
        raise ServiceUnavailableException()

    @test_app.get("/validation")
    def validation(amount: int):
        return {"amount": amount}

    @test_app.get("/internal-error")
    def internal_error():
        raise RuntimeError(
            "Simulated internal failure"
        )

    with TestClient(
        test_app,
        raise_server_exceptions=False
    ) as test_client:

        yield test_client


@pytest.mark.parametrize(
    "endpoint,status_code,error_code",
    [
        ("/bad-request", 400, "BAD_REQUEST"),
        ("/unauthorized", 401, "UNAUTHORIZED"),
        ("/forbidden", 403, "FORBIDDEN"),
        ("/not-found", 404, "NOT_FOUND"),
        ("/conflict", 409, "CONFLICT"),
        (
            "/unavailable",
            503,
            "SERVICE_UNAVAILABLE"
        )
    ]
)
def test_custom_exceptions(
    error_client,
    endpoint,
    status_code,
    error_code
):

    response = error_client.get(endpoint)

    assert response.status_code == status_code

    data = response.json()

    assert data["success"] is False

    assert data["error"]["code"] == error_code

    assert data["error"]["request_id"] == (
        response.headers["X-Request-ID"]
    )


def test_unauthorized_header(error_client):

    response = error_client.get(
        "/unauthorized"
    )

    assert response.status_code == 401

    assert response.headers[
        "WWW-Authenticate"
    ] == "Bearer"


def test_unknown_endpoint(client: TestClient):

    response = client.get(
        "/unknown-endpoint"
    )

    assert response.status_code == 404

    data = response.json()

    assert data["success"] is False

    assert data["error"]["code"] == "NOT_FOUND"


def test_method_not_allowed(client: TestClient):

    response = client.post(
        "/api/v1/health"
    )

    assert response.status_code == 405

    assert response.json()["error"]["code"] == (
    "METHOD_NOT_ALLOWED"
    )


def test_validation_error(error_client):

    response = error_client.get(
        "/validation?amount=invalid"
    )

    assert response.status_code == 422

    data = response.json()

    assert data["success"] is False

    assert data["error"]["code"] == (
        "VALIDATION_ERROR"
    )

    assert data["error"]["details"][0][
        "field"
    ] == "query.amount"


def test_valid_request(error_client):

    response = error_client.get(
        "/validation?amount=100"
    )

    assert response.status_code == 200

    assert response.json() == {
        "amount": 100
    }


def test_internal_server_error(error_client):

    response = error_client.get(
        "/internal-error"
    )

    assert response.status_code == 500

    data = response.json()

    assert data["success"] is False

    assert data["error"]["code"] == (
        "INTERNAL_SERVER_ERROR"
    )

    assert data["error"]["message"] == (
        "An unexpected error occurred."
    )

    assert data["error"]["request_id"] == (
        response.headers["X-Request-ID"]
    )

    assert "Simulated internal failure" not in (
        response.text
    )
