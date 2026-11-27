from functools import lru_cache
from secrets import token_urlsafe

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_password,
    verify_and_update_password
)

from app.core.exceptions import (
    ConflictException,
    UnauthorizedException
)

from app.repositories.user_repository import UserRepository

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse
)

from app.services.refresh_session_service import (
    RefreshSessionService,
    TokenPair
)
from app.core.security import password_hasher

@lru_cache(maxsize=1)
def get_dummy_password_hash() -> str:

    return password_hasher.hash(token_urlsafe(32))


class AuthService:

    def __init__(self, db: Session):

        self.db = db
        self.users = UserRepository(db)
        self.sessions = RefreshSessionService(db)

    def register(
        self,
        request: RegisterRequest
    ) -> UserResponse:

        password_hash = hash_password(
            request.password.get_secret_value()
        )

        try:

            with self.db.begin():

                user = self.users.create_customer(
                    full_name=request.full_name,
                    email=str(request.email),
                    password_hash=password_hash
                )

                response = UserResponse.model_validate(
                    user
                )

        except IntegrityError as exc:

            constraint_name = getattr(
                getattr(exc.orig, "diag", None),
                "constraint_name",
                None
            )

            if constraint_name == "uq_users_email":

                raise ConflictException(
                    "Email address is already registered."
                ) from None

            raise

        return response

    def login(
        self,
        request: LoginRequest
    ) -> TokenPair:

        password = request.password.get_secret_value()

        dummy_hash = get_dummy_password_hash()

        with self.db.begin():

            user = self.users.get_by_email(
                str(request.email),
                for_update=True
            )

            if (
                user is None
                or not user.is_active
                or user.password_hash == "!LOGIN_DISABLED"
            ):

                verify_password(password, dummy_hash)

                raise UnauthorizedException(
                    "Invalid email or password."
                )

            verified, updated_hash = (
                verify_and_update_password(
                    password,
                    user.password_hash
                )
            )

            if not verified:

                raise UnauthorizedException(
                    "Invalid email or password."
                )

            if updated_hash is not None:

                self.users.update_password_hash(
                    user,
                    updated_hash
                )

            tokens = (
                self.sessions.create_session_in_transaction(
                    user.id
                )
            )

        return tokens