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