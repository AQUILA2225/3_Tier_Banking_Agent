from fastapi import Request

from app.core.config import settings
from app.core.exceptions import ForbiddenException

from app.services.audit_service import (
    AuditService,
    AuthAuditEvent
)


def require_trusted_origin(
    request: Request
) -> None:

    origin = request.headers.get("origin")

    if origin not in settings.cors_allowed_origins:

        AuditService.record_auth_event(
            AuthAuditEvent.CSRF_REJECTED,
            request_id=getattr(
                request.state,
                "request_id",
                None
            )
        )

        raise ForbiddenException(
            "Untrusted request origin."
        )

    if request.headers.get("x-csrf-protection") != "1":

        AuditService.record_auth_event(
            AuthAuditEvent.CSRF_REJECTED,
            request_id=getattr(
                request.state,
                "request_id",
                None
            )
        )

        raise ForbiddenException(
            "Missing CSRF protection header."
        )