from fastapi import Request

from app.core.config import settings
from app.core.exceptions import ForbiddenException


def require_trusted_origin(
    request: Request
) -> None:

    origin = request.headers.get("origin")

    if origin not in settings.cors_allowed_origins:

        raise ForbiddenException(
            "Untrusted request origin."
        )

    if request.headers.get("x-csrf-protection") != "1":

        raise ForbiddenException(
            "Missing CSRF protection header."
        )