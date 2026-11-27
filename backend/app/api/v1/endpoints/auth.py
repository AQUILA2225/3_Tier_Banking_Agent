from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    status
)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from sqlalchemy.orm import Session

from app.core.config import settings

from app.core.auth_cookies import (
    REFRESH_COOKIE_NAME,
    set_refresh_cookie,
    clear_refresh_cookie,
    disable_auth_caching
)

from app.core.csrf import require_trusted_origin
from app.core.exceptions import UnauthorizedException
from app.db.session import get_db

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse,
    MessageResponse
)

from app.services.auth_service import AuthService

from app.services.refresh_session_service import (
    RefreshSessionService,
    RefreshSessionError,
    TokenPair
)


class AuthRoute(APIRoute):

    def get_route_handler(self):

        original_handler = super().get_route_handler()

        async def safe_handler(request: Request):

            try:

                response = await original_handler(request)

            except RequestValidationError:

                response = JSONResponse(
                    status_code=422,
                    content={
                        "success": False,
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Invalid authentication request.",
                            "details": [],
                            "request_id": getattr(
                                request.state,
                                "request_id",
                                None
                            )
                        }
                    }
                )

            disable_auth_caching(response)

            return response

        return safe_handler


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    dependencies=[Depends(require_trusted_origin)],
    route_class=AuthRoute
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db)
]


def build_token_response(
    response: Response,
    tokens: TokenPair
) -> TokenResponse:

    set_refresh_cookie(
        response,
        tokens.refresh_token
    )

    return TokenResponse(
        access_token=tokens.access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    request: RegisterRequest,
    db: DatabaseSession
) -> UserResponse:

    return AuthService(db).register(request)


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    request: LoginRequest,
    response: Response,
    db: DatabaseSession
) -> TokenResponse:

    tokens = AuthService(db).login(request)

    return build_token_response(response, tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse
)
def refresh(
    request: Request,
    response: Response,
    db: DatabaseSession
) -> TokenResponse:

    refresh_token = request.cookies.get(
        REFRESH_COOKIE_NAME
    )

    if not refresh_token:

        raise UnauthorizedException(
            "Invalid or expired refresh session."
        )

    try:

        tokens = RefreshSessionService(db).rotate_session(
            refresh_token
        )

    except RefreshSessionError:

        raise UnauthorizedException(
            "Invalid or expired refresh session."
        ) from None

    return build_token_response(response, tokens)


@router.post(
    "/logout",
    response_model=MessageResponse
)
def logout(
    request: Request,
    response: Response,
    db: DatabaseSession
) -> MessageResponse:

    refresh_token = request.cookies.get(
        REFRESH_COOKIE_NAME
    )

    if refresh_token:

        try:

            RefreshSessionService(db).revoke_session(
                refresh_token
            )

        except RefreshSessionError:

            pass

    clear_refresh_cookie(response)

    return MessageResponse(
        message="Logged out successfully."
    )