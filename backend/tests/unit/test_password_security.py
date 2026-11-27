import pytest

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.security import (
    validate_password,
    hash_password,
    verify_password,
    verify_and_update_password
)


pytestmark = pytest.mark.unit

VALID_PASSWORD = "DemoPassword@123"


def test_valid_password_accepted():

    validate_password(VALID_PASSWORD)


@pytest.mark.parametrize(
    "password",
    [
        "",
        "short",
        "a" * 129,
        " " * 12
    ]
)
def test_invalid_password_rejected(password):

    with pytest.raises(ValueError):
        hash_password(password)


@pytest.mark.parametrize("length", [12, 128])
def test_password_length_boundaries(length):

    validate_password("a" * length)


def test_password_hash_uses_argon2id():

    hashed = hash_password(VALID_PASSWORD)

    assert hashed.startswith("$argon2id$")
    assert hashed != VALID_PASSWORD
    assert len(hashed) <= 255


def test_same_password_generates_different_hashes():

    first_hash = hash_password(VALID_PASSWORD)
    second_hash = hash_password(VALID_PASSWORD)

    assert first_hash != second_hash

    assert verify_password(VALID_PASSWORD, first_hash)
    assert verify_password(VALID_PASSWORD, second_hash)


def test_correct_password_verified():

    hashed = hash_password(VALID_PASSWORD)

    assert verify_password(VALID_PASSWORD, hashed) is True


def test_incorrect_password_rejected():

    hashed = hash_password(VALID_PASSWORD)

    assert verify_password("WrongPassword@123", hashed) is False


@pytest.mark.parametrize(
    "hashed_password",
    [
        "",
        "!LOGIN_DISABLED",
        "invalid-hash",
        "$argon2id$invalid"
    ]
)
def test_invalid_hash_rejected(hashed_password):

    assert verify_password(
        VALID_PASSWORD,
        hashed_password
    ) is False


@pytest.mark.parametrize("password", ["", "a" * 129])
def test_invalid_verification_input(password):

    hashed = hash_password(VALID_PASSWORD)

    assert verify_password(password, hashed) is False


def test_current_hash_does_not_require_update():

    hashed = hash_password(VALID_PASSWORD)

    verified, updated_hash = verify_and_update_password(
        VALID_PASSWORD,
        hashed
    )

    assert verified is True
    assert updated_hash is None


def test_outdated_hash_is_upgraded():

    old_hasher = PasswordHash(
        (
            Argon2Hasher(
                time_cost=2,
                memory_cost=19456,
                parallelism=1
            ),
        )
    )

    old_hash = old_hasher.hash(VALID_PASSWORD)

    verified, updated_hash = verify_and_update_password(
        VALID_PASSWORD,
        old_hash
    )

    assert verified is True
    assert updated_hash is not None
    assert updated_hash != old_hash

    assert verify_password(
        VALID_PASSWORD,
        updated_hash
    ) is True


def test_incorrect_password_does_not_update_hash():

    hashed = hash_password(VALID_PASSWORD)

    result = verify_and_update_password(
        "WrongPassword@123",
        hashed
    )

    assert result == (False, None)


@pytest.mark.parametrize(
    "hashed_password",
    [
        "",
        "!LOGIN_DISABLED",
        "invalid-hash",
        "$argon2id$invalid"
    ]
)
def test_invalid_hash_cannot_be_upgraded(hashed_password):

    result = verify_and_update_password(
        VALID_PASSWORD,
        hashed_password
    )

    assert result == (False, None)