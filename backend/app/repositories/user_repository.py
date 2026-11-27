from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.schemas.auth import normalize_email


class UserRepository:

    def __init__(self, db: Session):

        self.db = db

    def get_by_id(
        self,
        user_id: UUID,
        *,
        for_update: bool = False
    ) -> User | None:

        statement = select(User).where(
            User.id == user_id
        )

        if for_update:

            statement = statement.with_for_update()

        statement = statement.execution_options(
            populate_existing=True
        )

        return self.db.scalar(statement)

    def get_by_email(
        self,
        email: str,
        *,
        for_update: bool = False
    ) -> User | None:

        statement = select(User).where(
            User.email == normalize_email(email)
        )

        if for_update:

            statement = statement.with_for_update()

        statement = statement.execution_options(
            populate_existing=True
        )

        return self.db.scalar(statement)

    def create_customer(
        self,
        full_name: str,
        email: str,
        password_hash: str
    ) -> User:

        user = User(
            full_name=full_name,
            email=normalize_email(email),
            password_hash=password_hash,
            role=UserRole.CUSTOMER.value,
            is_active=True
        )

        self.db.add(user)
        self.db.flush()

        return user

    def update_password_hash(
        self,
        user: User,
        password_hash: str
    ) -> None:

        user.password_hash = password_hash

        self.db.flush()