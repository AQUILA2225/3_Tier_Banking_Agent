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
from app.api.deps import require_permissions
from app.core.permissions import Permission
from app.models import User

from app.core.auth_rate_limit import (
    AuthAction,
    require_auth_rate_limit
)

from uuid import UUID

from app.core.security import decode_access_token
from app.core.exceptions import ConflictException
from app.services.audit_service import (
    AuditService,
    AuthAuditEvent
)

from app.services.refresh_session_service import (
    RefreshTokenReuseError
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

def audit_auth_event(
    request: Request,
    event: AuthAuditEvent,
    user_id: UUID | None = None
) -> None:

    AuditService.record_auth_event(
        event,
        user_id=user_id,
        request_id=getattr(
            request.state,
            "request_id",
            None
        )
    )

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_trusted_origin),
        Depends(require_auth_rate_limit(AuthAction.REGISTER)
        )
    ]
)
def register(
    request: RegisterRequest,
    http_request: Request,
    db: DatabaseSession
) -> UserResponse:

    try:

        user = AuthService(db).register(request)

    except ConflictException:

        audit_auth_event(
            http_request,
            AuthAuditEvent.REGISTER_FAILURE
        )

        raise

    audit_auth_event(
        http_request,
        AuthAuditEvent.REGISTER_SUCCESS,
        user_id=user.id
    )

    return user

@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[
        Depends(require_trusted_origin),
        Depends(require_auth_rate_limit(AuthAction.LOGIN)
        )
    ]
)
def login(
    request: LoginRequest,
    http_request: Request,
    response: Response,
    db: DatabaseSession
) -> TokenResponse:

    try:

        tokens = AuthService(db).login(request)

    except UnauthorizedException:

        audit_auth_event(
            http_request,
            AuthAuditEvent.LOGIN_FAILURE
        )

        raise

    claims = decode_access_token(
        tokens.access_token
    )

    audit_auth_event(
        http_request,
        AuthAuditEvent.LOGIN_SUCCESS,
        user_id=UUID(claims.sub)
    )

    return build_token_response(
        response,
        tokens
    )
    
@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[
        Depends(require_trusted_origin),
        Depends(require_auth_rate_limit(AuthAction.REFRESH)
        )
    ]
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

        audit_auth_event(
            request,
            AuthAuditEvent.REFRESH_FAILURE
        )

        raise UnauthorizedException(
            "Invalid or expired refresh session."
        )

    try:

        tokens = RefreshSessionService(db).rotate_session(
            refresh_token
        )

    except RefreshTokenReuseError:

        audit_auth_event(
            request,
            AuthAuditEvent.REFRESH_REUSE
        )

        raise UnauthorizedException(
            "Invalid or expired refresh session."
        ) from None

    except RefreshSessionError:

        audit_auth_event(
            request,
            AuthAuditEvent.REFRESH_FAILURE
        )

        raise UnauthorizedException(
            "Invalid or expired refresh session."
        ) from None

    claims = decode_access_token(
        tokens.access_token
    )

    audit_auth_event(
        request,
        AuthAuditEvent.REFRESH_SUCCESS,
        user_id=UUID(claims.sub)
    )

    return build_token_response(
        response,
        tokens
    )

@router.post(
    "/logout",
    response_model=MessageResponse,
    dependencies=[
        Depends(require_trusted_origin),
        Depends(require_auth_rate_limit(AuthAction.LOGOUT)
        )
    ]
)
def logout(
    request: Request,
    response: Response,
    db: DatabaseSession
) -> MessageResponse:

    refresh_token = request.cookies.get(
        REFRESH_COOKIE_NAME
    )

    event = AuthAuditEvent.LOGOUT_NO_SESSION

    if refresh_token:

        try:

            RefreshSessionService(db).revoke_session(
                refresh_token
            )

            event = AuthAuditEvent.LOGOUT_SUCCESS

        except RefreshSessionError:

            pass

    audit_auth_event(
        request,
        event
    )

    clear_refresh_cookie(response)

    return MessageResponse(
        message="Logged out successfully."
    )
    
@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: Annotated[
        User,
        Depends(
            require_permissions(
                Permission.PROFILE_READ
            )
        )
    ]
) -> UserResponse:

    return UserResponse.model_validate(
        current_user
    )