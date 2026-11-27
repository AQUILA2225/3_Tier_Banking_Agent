from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from hmac import compare_digest
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token
)

from app.models import (
    User,
    RefreshSession,
    RevocationReason
)

from app.repositories.refresh_session_repository import (
    RefreshSessionRepository
)


class RefreshSessionError(ValueError):
    """Raised when refresh session authentication fails."""


class RefreshTokenReuseError(RefreshSessionError):
    """Raised when a rotated refresh token is reused."""


@dataclass(frozen=True)
class TokenPair:

    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    token_type: str = "bearer"


def digest_refresh_token(token: str) -> str:

    return sha256(
        token.encode("utf-8")
    ).hexdigest()


class RefreshSessionService:

    def __init__(self, db: Session):

        self.db = db
        self.repository = RefreshSessionRepository(db)

    def _lock_user(
        self,
        user_id: UUID
    ) -> User | None:

        statement = (
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        return self.db.scalar(statement)

    def _issue_token_pair(
        self,
        user_id: UUID,
        family_id: UUID
    ) -> TokenPair:

        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)

        claims = decode_refresh_token(refresh_token)

        session = RefreshSession(
            user_id=user_id,
            token_jti=UUID(claims.jti),
            token_digest=digest_refresh_token(
                refresh_token
            ),
            family_id=family_id,
            created_at=datetime.fromtimestamp(
                claims.iat,
                tz=timezone.utc
            ),
            expires_at=datetime.fromtimestamp(
                claims.exp,
                tz=timezone.utc
            )
        )

        self.repository.create(session)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token
        )

    # Create a session inside an existing transaction
    def create_session_in_transaction(
        self,
        user_id: UUID
    ) -> TokenPair:

        if not self.db.in_transaction():

            raise RuntimeError(
                "An active database transaction is required."
            )

        user = self._lock_user(user_id)

        if (
            user is None
            or not user.is_active
            or user.password_hash == "!LOGIN_DISABLED"
        ):

            raise RefreshSessionError(
                "Unable to create session."
            )

        return self._issue_token_pair(
            user_id=user.id,
            family_id=uuid4()
        )

    # Create a session with its own transaction
    def create_session(
        self,
        user_id: UUID
    ) -> TokenPair:

        with self.db.begin():

            tokens = self.create_session_in_transaction(
                user_id
            )

        return tokens

    def _decode_refresh_token(self, token: str):

        try:

            return decode_refresh_token(token)

        except TokenValidationError:

            raise RefreshSessionError(
                "Invalid or expired refresh token."
            ) from None

    def _get_verified_session(
        self,
        token: str,
        claims
    ) -> RefreshSession:

        session = self.repository.get_by_jti(
            UUID(claims.jti)
        )

        if (
            session is None
            or session.user_id != UUID(claims.sub)
            or not compare_digest(
                session.token_digest,
                digest_refresh_token(token)
            )
        ):

            raise RefreshSessionError(
                "Invalid refresh session."
            )

        return session

    def rotate_session(
        self,
        refresh_token: str
    ) -> TokenPair:

        claims = self._decode_refresh_token(
            refresh_token
        )

        reuse_detected = False
        tokens = None

        with self.db.begin():

            user = self._lock_user(
                UUID(claims.sub)
            )

            if (
                user is None
                or not user.is_active
                or user.password_hash == "!LOGIN_DISABLED"
            ):

                raise RefreshSessionError(
                    "Invalid refresh session."
                )

            session = self._get_verified_session(
                refresh_token,
                claims
            )

            now = datetime.now(timezone.utc)

            if session.expires_at <= now:

                raise RefreshSessionError(
                    "Refresh session has expired."
                )

            if session.revoked_at is not None:

                if (
                    session.revocation_reason
                    == RevocationReason.ROTATED.value
                ):

                    self.repository.revoke_family(
                        user_id=user.id,
                        family_id=session.family_id,
                        revoked_at=now,
                        reason=RevocationReason.REUSE_DETECTED
                    )

                    reuse_detected = True

                else:

                    raise RefreshSessionError(
                        "Refresh session has been revoked."
                    )

            else:

                session.revoked_at = now

                session.revocation_reason = (
                    RevocationReason.ROTATED.value
                )

                tokens = self._issue_token_pair(
                    user_id=user.id,
                    family_id=session.family_id
                )

        # Raise only after the revocation transaction commits.
        if reuse_detected:

            raise RefreshTokenReuseError(
                "Refresh token reuse detected."
            )

        if tokens is None:

            raise RefreshSessionError(
                "Unable to refresh session."
            )

        return tokens

    def revoke_session(
        self,
        refresh_token: str
    ) -> None:

        claims = self._decode_refresh_token(
            refresh_token
        )

        with self.db.begin():

            user = self._lock_user(
                UUID(claims.sub)
            )

            if user is None:

                raise RefreshSessionError(
                    "Invalid refresh session."
                )

            session = self._get_verified_session(
                refresh_token,
                claims
            )

            self.repository.revoke_family(
                user_id=user.id,
                family_id=session.family_id,
                revoked_at=datetime.now(timezone.utc),
                reason=RevocationReason.LOGOUT
            )

    def revoke_all_sessions(
        self,
        user_id: UUID,
        reason: RevocationReason
    ) -> None:

        if reason not in (
            RevocationReason.LOGOUT,
            RevocationReason.ADMIN_REVOKED,
            RevocationReason.PASSWORD_CHANGED
        ):

            raise ValueError(
                "Invalid session revocation reason."
            )

        with self.db.begin():

            user = self._lock_user(user_id)

            if user is None:

                raise RefreshSessionError(
                    "User does not exist."
                )

            self.repository.revoke_all_for_user(
                user_id=user.id,
                revoked_at=datetime.now(timezone.utc),
                reason=reason
            )