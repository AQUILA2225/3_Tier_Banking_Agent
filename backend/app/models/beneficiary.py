from datetime import datetime
from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
    true
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.account import Account
    from app.models.transaction import Transaction
class Beneficiary(Base):

    __tablename__ = "beneficiaries"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "account_id",
            name="uq_beneficiaries_user_id_account_id"
        ),
        UniqueConstraint(
            "id",
            "user_id",
            "account_id",
            name="uq_beneficiaries_id_user_account"
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

    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    nickname: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true()
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
        # ORM Relationships

    owner: Mapped["User"] = relationship(
        back_populates="beneficiaries"
    )

    account: Mapped["Account"] = relationship(
        back_populates="beneficiaries"
    )

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="beneficiary",
        foreign_keys="Transaction.beneficiary_id",
        passive_deletes="all"
    )