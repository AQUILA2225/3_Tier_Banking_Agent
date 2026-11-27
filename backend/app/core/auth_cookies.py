from fastapi import Response
from app.core.config import settings


REFRESH_COOKIE_NAME = "banking_refresh_token"
REFRESH_COOKIE_PATH = (
    f"{settings.api_v1_prefix}/auth"
)

def set_refresh_cookie(
    response: Response,
    refresh_token: str
) -> None:

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict",
        path=REFRESH_COOKIE_PATH
    )

def clear_refresh_cookie(
    response: Response
) -> None:

    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="strict"
    )

def disable_auth_caching(
    response: Response
) -> None:

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"