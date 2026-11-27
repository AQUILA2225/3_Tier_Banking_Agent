from uuid import UUID, uuid4
import pytest
from sqlalchemy import select, func
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from app.core.exceptions import (
    ConflictException,
    UnauthorizedException
)
from app.core.security import (
    verify_password,
    decode_access_token,
    decode_refresh_token
)
from app.models import User, RefreshSession
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest
)
from app.services.auth_service import AuthService
from app.services.refresh_session_service import (
    RefreshSessionService,
    digest_refresh_token
)

pytestmark = pytest.mark.integration
VALID_PASSWORD = "DemoPassword@123"

@pytest.fixture
def service(db_session):
    return AuthService(db_session)

@pytest.fixture
def registration():
    return RegisterRequest(
        full_name="Test Customer",
        email=f"{uuid4()}@example.com",
        password=VALID_PASSWORD
    )

@pytest.fixture
def customer(service, registration):
    return service.register(registration)

def test_register_customer(
    db_session,
    service,
    registration
):
    response = service.register(registration)

    assert response.id is not None
    assert response.role.value == "CUSTOMER"
    assert response.is_active is True

    assert "password_hash" not in response.model_dump()
    with db_session.begin():

        user = db_session.get(User, response.id)

        assert user.password_hash != VALID_PASSWORD

        assert verify_password(
            VALID_PASSWORD,
            user.password_hash
        )


def test_duplicate_registration_rejected(
    service,
    registration
):

    service.register(registration)

    with pytest.raises(ConflictException):

        service.register(registration)


def test_duplicate_normalized_email_rejected(
    service,
    registration
):

    service.register(registration)

    duplicate = RegisterRequest(
        full_name="Duplicate Customer",
        email=str(registration.email).upper(),
        password=VALID_PASSWORD
    )

    with pytest.raises(ConflictException):

        service.register(duplicate)


def test_successful_login(
    db_session,
    service,
    customer
):

    tokens = service.login(
        LoginRequest(
            email=customer.email,
            password=VALID_PASSWORD
        )
    )

    access_claims = decode_access_token(
        tokens.access_token
    )

    refresh_claims = decode_refresh_token(
        tokens.refresh_token
    )

    assert access_claims.sub == str(customer.id)
    assert refresh_claims.sub == str(customer.id)
    assert tokens.token_type == "bearer"

    with db_session.begin():

        session = db_session.scalar(
            select(RefreshSession).where(
                RefreshSession.token_jti
                == UUID(refresh_claims.jti)
            )
        )

        assert session is not None
        assert session.user_id == customer.id
        assert session.revoked_at is None

        assert session.token_digest == (
            digest_refresh_token(tokens.refresh_token)
        )


def test_login_with_normalized_email(
    service,
    customer
):

    tokens = service.login(
        LoginRequest(
            email=f" {customer.email.upper()} ",
            password=VALID_PASSWORD
        )
    )

    claims = decode_access_token(
        tokens.access_token
    )

    assert claims.sub == str(customer.id)


def test_wrong_password_rejected(
    service,
    customer
):

    with pytest.raises(UnauthorizedException):

        service.login(
            LoginRequest(
                email=customer.email,
                password="WrongPassword@123"
            )
        )


def test_unknown_email_rejected(service):

    with pytest.raises(UnauthorizedException):

        service.login(
            LoginRequest(
                email=f"{uuid4()}@example.com",
                password=VALID_PASSWORD
            )
        )


def test_inactive_user_rejected(
    db_session,
    service,
    customer
):

    with db_session.begin():

        user = db_session.get(User, customer.id)
        user.is_active = False

    with pytest.raises(UnauthorizedException):

        service.login(
            LoginRequest(
                email=customer.email,
                password=VALID_PASSWORD
            )
        )


def test_disabled_password_rejected(
    db_session,
    service,
    customer
):

    with db_session.begin():

        user = db_session.get(User, customer.id)
        user.password_hash = "!LOGIN_DISABLED"

    with pytest.raises(UnauthorizedException):

        service.login(
            LoginRequest(
                email=customer.email,
                password=VALID_PASSWORD
            )
        )


def test_failed_login_creates_no_session(
    db_session,
    service,
    customer
):

    with pytest.raises(UnauthorizedException):

        service.login(
            LoginRequest(
                email=customer.email,
                password="WrongPassword@123"
            )
        )

    with db_session.begin():

        count = db_session.scalar(
            select(func.count())
            .select_from(RefreshSession)
            .where(
                RefreshSession.user_id == customer.id
            )
        )

        assert count == 0


def test_registration_creates_no_session(
    db_session,
    customer
):

    with db_session.begin():

        count = db_session.scalar(
            select(func.count())
            .select_from(RefreshSession)
            .where(
                RefreshSession.user_id == customer.id
            )
        )

        assert count == 0


def test_outdated_password_hash_upgraded(
    db_session,
    service,
    customer
):

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

    with db_session.begin():

        user = db_session.get(User, customer.id)
        user.password_hash = old_hash

    service.login(
        LoginRequest(
            email=customer.email,
            password=VALID_PASSWORD
        )
    )

    with db_session.begin():

        user = db_session.get(User, customer.id)

        assert user.password_hash != old_hash

        assert verify_password(
            VALID_PASSWORD,
            user.password_hash
        )


def test_login_failure_rolls_back_hash_upgrade(
    db_session,
    service,
    customer,
    monkeypatch
):

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

    with db_session.begin():

        user = db_session.get(User, customer.id)
        user.password_hash = old_hash

    def fail_session_creation(*args, **kwargs):

        raise RuntimeError(
            "Simulated session creation failure"
        )

    monkeypatch.setattr(
        service.sessions,
        "create_session_in_transaction",
        fail_session_creation
    )

    with pytest.raises(RuntimeError):

        service.login(
            LoginRequest(
                email=customer.email,
                password=VALID_PASSWORD
            )
        )

    with db_session.begin():

        user = db_session.get(User, customer.id)

        assert user.password_hash == old_hash

        count = db_session.scalar(
            select(func.count())
            .select_from(RefreshSession)
            .where(
                RefreshSession.user_id == customer.id
            )
        )

        assert count == 0


def test_session_creation_requires_transaction(
    db_session,
    customer
):

    session_service = RefreshSessionService(db_session)

    with pytest.raises(RuntimeError):

        session_service.create_session_in_transaction(
            customer.id
        )