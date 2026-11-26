
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.request_context import (
    get_request_id
)


pytestmark = pytest.mark.api


def test_request_id_header(client: TestClient):

    response = client.get(
        "/api/v1/health"
    )

    assert response.status_code == 200

    assert "X-Request-ID" in response.headers


def test_request_id_is_valid_uuid(
    client: TestClient
):

    response = client.get(
        "/api/v1/health"
    )

    request_id = response.headers[
        "X-Request-ID"
    ]

    parsed_uuid = UUID(request_id)

    assert parsed_uuid.version == 4


def test_unique_request_ids(client: TestClient):

    first_response = client.get(
        "/api/v1/health"
    )

    second_response = client.get(
        "/api/v1/health"
    )

    first_request_id = first_response.headers[
        "X-Request-ID"
    ]

    second_request_id = second_response.headers[
        "X-Request-ID"
    ]

    assert first_request_id != second_request_id


def test_client_request_id_not_trusted(
    client: TestClient
):

    response = client.get(
        "/api/v1/health",
        headers={
            "X-Request-ID": "untrusted-client-id"
        }
    )

    assert response.headers[
        "X-Request-ID"
    ] != "untrusted-client-id"


def test_error_request_id_correlation(
    client: TestClient
):

    response = client.get(
        "/unknown-endpoint"
    )

    header_request_id = response.headers[
        "X-Request-ID"
    ]

    body_request_id = response.json()[
        "error"
    ]["request_id"]

    assert header_request_id == body_request_id


def test_default_request_context():

    assert get_request_id() == "-"
