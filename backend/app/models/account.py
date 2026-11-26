from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Uuid,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.beneficiary import Beneficiary
    from app.models.transaction import Transaction
class AccountType(str, Enum):
    SAVINGS = "SAVINGS"
    CURRENT = "CURRENT"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class Account(Base):

    __tablename__ = "accounts"

    __table_args__ = (
        CheckConstraint(
            "balance >= 0",
            name="non_negative_balance"
        ),
        CheckConstraint(
            "account_type in ('SAVINGS', 'CURRENT')",
            name="valid_account_type"
        ),
        CheckConstraint(
            "status in ('ACTIVE', 'FROZEN', 'CLOSED')",
            name="valid_status"
        ),
        CheckConstraint(
            "currency = 'INR'",
            name="valid_currency"
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
        nullable=False,
        index=True
    )

    account_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False
    )

    account_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00"
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AccountStatus.ACTIVE.value,
        server_default=AccountStatus.ACTIVE.value
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
        # ORM Relationships

    owner: Mapped["User"] = relationship(
        back_populates="accounts"
    )

    beneficiaries: Mapped[list["Beneficiary"]] = relationship(
        back_populates="account",
        passive_deletes="all"
    )

    outgoing_transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="source_account",
        foreign_keys="Transaction.source_account_id",
        passive_deletes="all"
    )

    incoming_transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="destination_account",
        foreign_keys="Transaction.destination_account_id",
        passive_deletes="all"
    )