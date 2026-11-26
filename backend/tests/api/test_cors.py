
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.error_handlers import (
    register_exception_handlers
)

from app.middleware.cors import configure_cors

from app.middleware.request_logging import (
    RequestLoggingMiddleware
)


pytestmark = pytest.mark.api


ALLOWED_ORIGIN = "http://localhost:5173"

UNAUTHORIZED_ORIGIN = (
    "http://unauthorized.example"
)


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]
)
def test_allowed_origins(
    client: TestClient,
    origin
):

    response = client.get(
        "/api/v1/health",
        headers={"Origin": origin}
    )

    assert response.status_code == 200

    assert response.headers[
        "Access-Control-Allow-Origin"
    ] == origin


def test_unauthorized_origin(
    client: TestClient
):

    response = client.get(
        "/api/v1/health",
        headers={
            "Origin": UNAUTHORIZED_ORIGIN
        }
    )

    assert response.status_code == 200

    assert "Access-Control-Allow-Origin" not in (
        response.headers
    )


def test_allowed_preflight(
    client: TestClient
):

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": (
                "Authorization,Content-Type"
            )
        }
    )

    assert response.status_code == 200

    assert response.headers[
        "Access-Control-Allow-Origin"
    ] == ALLOWED_ORIGIN

    assert response.headers[
        "Access-Control-Max-Age"
    ] == "600"


def test_unauthorized_preflight(
    client: TestClient
):

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": UNAUTHORIZED_ORIGIN,
            "Access-Control-Request-Method": "GET"
        }
    )

    assert response.status_code == 400

    assert "Disallowed CORS origin" in (
        response.text
    )


def test_disallowed_method(
    client: TestClient
):

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "TRACE"
        }
    )

    assert response.status_code == 400

    assert "Disallowed CORS method" in (
        response.text
    )


def test_disallowed_request_header(
    client: TestClient
):

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": (
                "X-Unauthorized-Header"
            )
        }
    )

    assert response.status_code == 400

    assert "Disallowed CORS headers" in (
        response.text
    )


def test_exposed_request_id(
    client: TestClient
):

    response = client.get(
        "/api/v1/health",
        headers={
            "Origin": ALLOWED_ORIGIN
        }
    )

    exposed_headers = response.headers[
        "Access-Control-Expose-Headers"
    ].lower()

    assert "x-request-id" in exposed_headers


def test_cors_credentials_disabled(
    client: TestClient
):

    response = client.get(
        "/api/v1/health",
        headers={
            "Origin": ALLOWED_ORIGIN
        }
    )

    assert (
        "Access-Control-Allow-Credentials"
        not in response.headers
    )


def test_cors_on_not_found(
    client: TestClient
):

    response = client.get(
        "/unknown-endpoint",
        headers={
            "Origin": ALLOWED_ORIGIN
        }
    )

    assert response.status_code == 404

    assert response.headers[
        "Access-Control-Allow-Origin"
    ] == ALLOWED_ORIGIN


def test_cors_on_internal_server_error():

    test_app = FastAPI(debug=False)

    test_app.add_middleware(
        RequestLoggingMiddleware
    )

    register_exception_handlers(test_app)

    @test_app.get("/internal-error")
    def internal_error():

        raise RuntimeError(
            "Simulated internal failure"
        )

    cors_app = configure_cors(test_app)

    with TestClient(
        cors_app,
        raise_server_exceptions=False
    ) as test_client:

        response = test_client.get(
            "/internal-error",
            headers={
                "Origin": ALLOWED_ORIGIN
            }
        )

        assert response.status_code == 500

        assert response.headers[
            "Access-Control-Allow-Origin"
        ] == ALLOWED_ORIGIN

        assert response.json()["error"][
            "request_id"
        ] == response.headers[
            "X-Request-ID"
        ]
