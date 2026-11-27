from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

import jwt

from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel, ConfigDict, ValidationError

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from argon2.exceptions import VerificationError, InvalidHashError

from app.core.config import settings


password_hasher = PasswordHash(
    (
        Argon2Hasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16
        ),
    )
)


DISABLED_PASSWORD_HASH = "!LOGIN_DISABLED"


def validate_password(password: str) -> None:

    if len(password) < settings.password_min_length:
        raise ValueError(
            f"Password must contain at least "
            f"{settings.password_min_length} characters."
        )

    if len(password) > settings.password_max_length:
        raise ValueError(
            f"Password must not exceed "
            f"{settings.password_max_length} characters."
        )

    if not password.strip():
        raise ValueError(
            "Password cannot contain only whitespace."
        )


def hash_password(password: str) -> str:

    validate_password(password)

    return password_hasher.hash(password)


def verify_password(
    password: str,
    hashed_password: str
) -> bool:

    if not password or len(password) > 128:
        return False

    if not hashed_password:
        return False

    if hashed_password == DISABLED_PASSWORD_HASH:
        return False

    try:
        return password_hasher.verify(
            password,
            hashed_password
        )

    except (
        UnknownHashError,
        VerificationError,
        InvalidHashError,
        ValueError
    ):
        return False


def verify_and_update_password(
    password: str,
    hashed_password: str
) -> tuple[bool, str | None]:

    if not password or len(password) > 128:
        return False, None

    if not hashed_password:
        return False, None

    if hashed_password == DISABLED_PASSWORD_HASH:
        return False, None

    try:
        return password_hasher.verify_and_update(
            password,
            hashed_password
        )

    except (
        UnknownHashError,
        VerificationError,
        InvalidHashError,
        ValueError
    ):
        return False, None
    
# JWT Token Security

TokenType = Literal["access", "refresh"]


class TokenClaims(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True
    )

    sub: str
    jti: str
    iss: str
    aud: str
    iat: int
    nbf: int
    exp: int
    token_type: TokenType


class TokenValidationError(ValueError):
    """Raised when a JWT is invalid or expired."""


def _create_token(
    user_id: UUID,
    token_type: TokenType,
    expires_delta: timedelta
) -> str:

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "jti": str(uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(
            (now + expires_delta).timestamp()
        ),
        "token_type": token_type
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )


def create_access_token(user_id: UUID) -> str:

    return _create_token(
        user_id=user_id,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.access_token_expire_minutes
        )
    )


def create_refresh_token(user_id: UUID) -> str:

    return _create_token(
        user_id=user_id,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.refresh_token_expire_days
        )
    )


def decode_token(
    token: str,
    expected_type: TokenType
) -> TokenClaims:

    if expected_type not in ("access", "refresh"):
        raise TokenValidationError(
            "Invalid expected token type."
        )

    if not token or len(token) > 4096:
        raise TokenValidationError(
            "Invalid or expired token."
        )

    try:

        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "require": [
                    "sub",
                    "jti",
                    "iss",
                    "aud",
                    "iat",
                    "nbf",
                    "exp",
                    "token_type"
                ],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_aud": True,
                "strict_aud": True
            }
        )

        claims = TokenClaims.model_validate(payload)

        # Validate canonical UUID identifiers.

        if str(UUID(claims.sub)) != claims.sub:
            raise ValueError("Invalid subject UUID.")

        if str(UUID(claims.jti)) != claims.jti:
            raise ValueError("Invalid token UUID.")

        # Prevent access and refresh token substitution.

        if claims.token_type != expected_type:
            raise ValueError("Incorrect token type.")

        # Validate timestamp consistency.

        if not claims.iat <= claims.nbf < claims.exp:
            raise ValueError("Invalid token timestamps.")

        # Enforce the configured maximum token lifetime.

        if expected_type == "access":

            max_lifetime = (
                settings.access_token_expire_minutes * 60
            )

        else:

            max_lifetime = (
                settings.refresh_token_expire_days * 86400
            )

        if claims.exp - claims.iat > max_lifetime:
            raise ValueError("Invalid token lifetime.")

        return claims

    except (
        InvalidTokenError,
        ValidationError,
        ValueError,
        TypeError,
        OverflowError
    ):
        raise TokenValidationError(
            "Invalid or expired token."
        ) from None


def decode_access_token(token: str) -> TokenClaims:

    return decode_token(
        token,
        expected_type="access"
    )


def decode_refresh_token(token: str) -> TokenClaims:

    return decode_token(
        token,
        expected_type="refresh"
    )