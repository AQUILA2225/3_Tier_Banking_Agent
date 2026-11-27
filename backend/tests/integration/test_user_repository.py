from uuid import uuid4

import pytest

from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserResponse


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def password_hash():

    return hash_password("DemoPassword@123")


@pytest.fixture
def repository(db_session):

    return UserRepository(db_session)


@pytest.fixture
def customer(repository, password_hash):

    return repository.create_customer(
        full_name="Test Customer",
        email=f"{uuid4()}@example.com",
        password_hash=password_hash
    )


def test_create_customer(customer):

    assert customer.id is not None
    assert customer.role == "CUSTOMER"
    assert customer.is_active is True

    assert verify_password(
        "DemoPassword@123",
        customer.password_hash
    )


def test_get_user_by_id(repository, customer):

    user = repository.get_by_id(customer.id)

    assert user is not None
    assert user.id == customer.id


def test_get_user_by_email(repository, customer):

    user = repository.get_by_email(customer.email)

    assert user is not None
    assert user.id == customer.id


def test_email_lookup_normalization(
    repository,
    customer
):

    user = repository.get_by_email(
        f" {customer.email.upper()} "
    )

    assert user is not None
    assert user.id == customer.id


def test_email_normalized_during_creation(
    repository,
    password_hash
):

    email = f"{uuid4()}@example.com"

    user = repository.create_customer(
        full_name="Test Customer",
        email=f" {email.upper()} ",
        password_hash=password_hash
    )

    assert user.email == email


def test_missing_user_by_id(repository):

    assert repository.get_by_id(uuid4()) is None


def test_missing_user_by_email(repository):

    assert repository.get_by_email(
        f"{uuid4()}@example.com"
    ) is None


def test_duplicate_email_rejected(
    db_session,
    repository,
    customer,
    password_hash
):

    with pytest.raises(IntegrityError) as exc_info:

        repository.create_customer(
            full_name="Duplicate Customer",
            email=customer.email.upper(),
            password_hash=password_hash
        )

    db_session.rollback()

    assert (
        exc_info.value.orig.diag.constraint_name
        == "uq_users_email"
    )


def test_update_password_hash(
    db_session,
    repository,
    customer
):

    new_hash = hash_password(
        "UpdatedPassword@123"
    )

    repository.update_password_hash(
        customer,
        new_hash
    )

    db_session.refresh(customer)

    assert customer.password_hash == new_hash

    assert verify_password(
        "UpdatedPassword@123",
        customer.password_hash
    )

def test_get_user_with_row_lock(
    repository,
    customer
):

    user = repository.get_by_id(
        customer.id,
        for_update=True
    )

    assert user is not None
    assert user.id == customer.id

def test_user_response_from_orm(customer):

    response = UserResponse.model_validate(customer)

    assert response.id == customer.id
    assert response.role.value == "CUSTOMER"

    assert "password_hash" not in response.model_dump()

def test_repository_does_not_commit(
    db_session,
    repository,
    customer
):

    user_id = customer.id

    db_session.rollback()

    assert repository.get_by_id(user_id) is None