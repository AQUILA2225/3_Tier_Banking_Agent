from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.user import User


class RevocationReason(str, Enum):

    ROTATED = "ROTATED"
    LOGOUT = "LOGOUT"
    REUSE_DETECTED = "REUSE_DETECTED"
    ADMIN_REVOKED = "ADMIN_REVOKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"


class RefreshSession(Base):

    __tablename__ = "refresh_sessions"

    __table_args__ = (

        UniqueConstraint(
            "token_jti",
            name="uq_refresh_sessions_token_jti"
        ),

        UniqueConstraint(
            "token_digest",
            name="uq_refresh_sessions_token_digest"
        ),

        CheckConstraint(
            "token_digest ~ '^[0-9a-f]{64}$'",
            name="valid_token_digest"
        ),

        CheckConstraint(
            "expires_at > created_at",
            name="valid_expiration"
        ),

        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="valid_revocation_timestamp"
        ),

        CheckConstraint(
            """
            (revoked_at IS NULL AND revocation_reason IS NULL)
            OR
            (
                revoked_at IS NOT NULL
                AND revocation_reason IS NOT NULL
                AND revocation_reason IN (
                    'ROTATED',
                    'LOGOUT',
                    'REUSE_DETECTED',
                    'ADMIN_REVOKED',
                    'PASSWORD_CHANGED'
                )
            )
            """,
            name="valid_revocation"
        ),

        Index(
            "ix_refresh_sessions_user_revoked_at",
            "user_id",
            "revoked_at"
        ),

        Index(
            "ix_refresh_sessions_family_revoked_at",
            "family_id",
            "revoked_at"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    token_jti: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False
    )

    token_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )

    family_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    revocation_reason: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    user: Mapped["User"] = relationship(
        back_populates="refresh_sessions"
    )