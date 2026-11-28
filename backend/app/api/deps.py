from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from sqlalchemy.orm import Session

from app.core.security import (
    DISABLED_PASSWORD_HASH,
    TokenValidationError,
    decode_access_token
)

from app.db.session import get_db
from app.models import User
from app.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="AccessToken",
    description="Enter your JWT access token."
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db)
]


BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme)
]


def authentication_error() -> HTTPException:

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token.",
        headers={
            "WWW-Authenticate": "Bearer",
            "Cache-Control": "no-store"
        }
    )


def get_current_user(
    credentials: BearerCredentials,
    db: DatabaseSession
) -> User:

    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
    ):
        raise authentication_error()

    try:

        claims = decode_access_token(
            credentials.credentials
        )

        user_id = UUID(claims.sub)

    except (TokenValidationError, ValueError):

        raise authentication_error() from None

    repository = UserRepository(db)

    user = repository.get_by_id(user_id)

    if (
        user is None
        or not user.is_active
        or user.password_hash == DISABLED_PASSWORD_HASH
    ):
        raise authentication_error()

    return user


CurrentUser = Annotated[
    User,
    Depends(get_current_user)
]