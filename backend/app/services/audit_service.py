import logging

from enum import Enum
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models import AuditLog


logger = logging.getLogger(__name__)


class AuthAuditEvent(str, Enum):

    REGISTER_SUCCESS = "AUTH_REGISTER_SUCCESS"
    REGISTER_FAILURE = "AUTH_REGISTER_FAILURE"

    LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    LOGIN_FAILURE = "AUTH_LOGIN_FAILURE"

    REFRESH_SUCCESS = "AUTH_REFRESH_SUCCESS"
    REFRESH_FAILURE = "AUTH_REFRESH_FAILURE"
    REFRESH_REUSE = "AUTH_REFRESH_REUSE"

    LOGOUT_SUCCESS = "AUTH_LOGOUT_SUCCESS"
    LOGOUT_NO_SESSION = "AUTH_LOGOUT_NO_SESSION"

    RATE_LIMIT_EXCEEDED = "AUTH_RATE_LIMIT_EXCEEDED"
    CSRF_REJECTED = "AUTH_CSRF_REJECTED"


class AuditService:

    @staticmethod
    def record_auth_event(
        event: AuthAuditEvent,
        *,
        user_id: UUID | None = None,
        request_id: UUID | str | None = None
    ) -> bool:

        if not isinstance(event, AuthAuditEvent):

            raise ValueError(
                "Invalid authentication audit event."
            )

        normalized_request_id = None

        if request_id is not None:

            try:

                normalized_request_id = UUID(
                    str(request_id)
                )

            except (ValueError, TypeError):

                normalized_request_id = None

        try:

            with SessionLocal.begin() as db:

                audit_log = AuditLog(
                    user_id=user_id,
                    transaction_id=None,
                    request_id=normalized_request_id,
                    action=event.value,
                    entity_type="AUTHENTICATION",
                    entity_id=user_id,
                    event_details={
                        "category": "AUTHENTICATION"
                    }
                )

                db.add(audit_log)

            return True

        except SQLAlchemyError:

            logger.error(
                "Authentication audit persistence failed: %s",
                event.value
            )

            return False