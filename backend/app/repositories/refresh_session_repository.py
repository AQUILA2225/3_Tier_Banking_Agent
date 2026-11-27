from datetime import datetime
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.models import RefreshSession, RevocationReason


class RefreshSessionRepository:
    def __init__(self, db: Session):
        self.db = db
        
    def create(
        self,
        session: RefreshSession
    ) -> RefreshSession:

        self.db.add(session)
        self.db.flush()
        return session

    def get_by_jti(
        self,
        token_jti: UUID
    ) -> RefreshSession | None:

        statement = (
            select(RefreshSession)
            .where(
                RefreshSession.token_jti == token_jti
            )
            .execution_options(populate_existing=True)
        )
        return self.db.scalar(statement)

    def revoke_family(
        self,
        user_id: UUID,
        family_id: UUID,
        revoked_at: datetime,
        reason: RevocationReason
    ) -> None:

        statement = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.family_id == family_id,
                RefreshSession.revoked_at.is_(None)
            )
            .values(
                revoked_at=revoked_at,
                revocation_reason=reason.value
            )
        )
        self.db.execute(statement)

    def revoke_all_for_user(
        self,
        user_id: UUID,
        revoked_at: datetime,
        reason: RevocationReason
    ) -> None:

        statement = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None)
            )
            .values(
                revoked_at=revoked_at,
                revocation_reason=reason.value
            )
        )
        self.db.execute(statement)