from datetime import datetime, timezone
from uuid import uuid4

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token
)


pytestmark = pytest.mark.unit

def build_payload(**overrides):
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "sub": str(uuid4()),
        "jti": str(uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + 900,
        "token_type": "access"
    }
    payload.update(overrides)
    return payload

def sign_payload(
    payload,
    secret=None,
    algorithm="HS256"
):
    if secret is None:
        secret = settings.jwt_secret_key.get_secret_value()
    return jwt.encode(
        payload,
        secret,
        algorithm=algorithm
    )

def test_create_and_decode_access_token():
    user_id = uuid4()
    token = create_access_token(user_id)
    claims = decode_access_token(token)
    
    assert claims.sub == str(user_id)
    assert claims.token_type == "access"
    assert claims.iss == settings.jwt_issuer
    assert claims.aud == settings.jwt_audience
    assert claims.exp - claims.iat == (
        settings.access_token_expire_minutes * 60
    )

def test_create_and_decode_refresh_token():
    user_id = uuid4()
    token = create_refresh_token(user_id)
    claims = decode_refresh_token(token)

    assert claims.sub == str(user_id)
    assert claims.token_type == "refresh"
    assert claims.exp - claims.iat == (
        settings.refresh_token_expire_days * 86400
    )

def test_tokens_have_unique_identifiers():
    user_id = uuid4()
    first = decode_access_token(
        create_access_token(user_id)
    )
    second = decode_access_token(
        create_access_token(user_id)
    )
    assert first.jti != second.jti

def test_refresh_token_rejected_as_access_token():
    token = create_refresh_token(uuid4())

    with pytest.raises(TokenValidationError):
        decode_access_token(token)

def test_access_token_rejected_as_refresh_token():
    token = create_access_token(uuid4())

    with pytest.raises(TokenValidationError):
        decode_refresh_token(token)

def test_expired_token_rejected():
    now = int(datetime.now(timezone.utc).timestamp())
    payload = build_payload(
        iat=now - 1000,
        nbf=now - 1000,
        exp=now - 100
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(sign_payload(payload))

def test_future_token_rejected():
    now = int(datetime.now(timezone.utc).timestamp())
    payload = build_payload(
        iat=now + 60,
        nbf=now + 60,
        exp=now + 960
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(sign_payload(payload))

def test_wrong_signature_rejected():
    token = sign_payload(
        build_payload(),
        secret="cd" * 32
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(token)

def test_unsupported_algorithm_rejected():
    token = sign_payload(
        build_payload(),
        algorithm="HS384"
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(token)

def test_unsigned_token_rejected():
    token = jwt.encode(
        build_payload(),
        key="",
        algorithm="none"
    )
    
    with pytest.raises(TokenValidationError):
        decode_access_token(token)

@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "unknown-issuer"},
        {"aud": "unknown-audience"},
        {"sub": "invalid-uuid"},
        {"jti": "invalid-uuid"},
        {"token_type": "unknown"},
        {"unexpected_claim": "unexpected"}
    ]
)
def test_invalid_claims_rejected(overrides):
    token = sign_payload(
        build_payload(**overrides)
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(token)

@pytest.mark.parametrize(
    "claim",
    [
        "sub",
        "jti",
        "iss",
        "aud",
        "iat",
        "nbf",
        "exp",
        "token_type"
    ]
)
def test_missing_required_claim_rejected(claim):
    payload = build_payload()
    del payload[claim]

    with pytest.raises(TokenValidationError):
        decode_access_token(sign_payload(payload))

@pytest.mark.parametrize(
    "token",
    [
        "",
        "invalid-token",
        "a" * 4097
    ]
)
def test_malformed_token_rejected(token):
    with pytest.raises(TokenValidationError):
        decode_access_token(token)

def test_excessive_token_lifetime_rejected():
    now = int(datetime.now(timezone.utc).timestamp())
    payload = build_payload(
        iat=now,
        nbf=now,
        exp=now + 86400
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(sign_payload(payload))

def test_invalid_timestamp_order_rejected():
    now = int(datetime.now(timezone.utc).timestamp())
    payload = build_payload(
        iat=now,
        nbf=now - 10,
        exp=now + 900
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(sign_payload(payload))

def test_modified_token_rejected():
    token = create_access_token(uuid4())
    header, payload, signature = token.split(".")
    replacement = "A" if signature[0] != "A" else "B"
    modified_signature = replacement + signature[1:]
    modified_token = (
        f"{header}.{payload}.{modified_signature}"
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(modified_token)