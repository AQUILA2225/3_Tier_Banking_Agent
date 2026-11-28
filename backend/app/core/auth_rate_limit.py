from collections.abc import Callable
from enum import Enum
from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.rate_limiter import (
    SlidingWindowRateLimiter
)

class AuthAction(str, Enum):

    REGISTER = "register"
    LOGIN = "login"
    REFRESH = "refresh"
    LOGOUT = "logout"

auth_rate_limiter = SlidingWindowRateLimiter(
    window_seconds=settings.auth_rate_limit_window_seconds,
    max_keys=settings.auth_rate_limit_max_keys
)

def get_auth_limit(action: AuthAction) -> int:
    limits = {
        AuthAction.REGISTER:
            settings.auth_register_rate_limit,

        AuthAction.LOGIN:
            settings.auth_login_rate_limit,

        AuthAction.REFRESH:
            settings.auth_refresh_rate_limit,

        AuthAction.LOGOUT:
            settings.auth_logout_rate_limit
    }

    return limits[action]

def require_auth_rate_limit(
    action: AuthAction
) -> Callable[..., None]:

    if not isinstance(action, AuthAction):

        raise ValueError(
            "Invalid authentication action."
        )

    def dependency(request: Request) -> None:

        client_ip = (
            request.client.host
            if request.client
            else "unknown"
        )

        key = f"{action.value}:{client_ip}"

        result = auth_rate_limiter.check(
            key=key,
            limit=get_auth_limit(action)
        )

        if not result.allowed:

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many authentication requests. "
                    "Please try again later."
                ),
                headers={
                    "Retry-After": str(
                        result.retry_after
                    ),
                    "Cache-Control": "no-store"
                }
            )

    return dependency