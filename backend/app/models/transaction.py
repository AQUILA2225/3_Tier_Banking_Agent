from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    ForeignKeyConstraint,
    Uuid,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.account import Account
    from app.models.beneficiary import Beneficiary
    from app.models.fraud_assessment import FraudAssessment
    from app.models.review import Review
    from app.models.audit_log import AuditLog
class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Transaction(Base):

    __tablename__ = "transactions"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="positive_amount"
        ),
        CheckConstraint(
            "source_account_id <> destination_account_id",
            name="different_accounts"
        ),
        CheckConstraint(
            "currency = 'INR'",
            name="valid_currency"
        ),
        CheckConstraint(
            "status in ('PENDING', 'PENDING_REVIEW', "
            "'APPROVED', 'REJECTED', 'COMPLETED', 'FAILED')",
            name="valid_status"
        ),
        CheckConstraint(
            "(status = 'COMPLETED' AND completed_at IS NOT NULL) "
            "OR (status <> 'COMPLETED' AND completed_at IS NULL)",
            name="valid_completion_timestamp"
        ),
        UniqueConstraint(
            "initiated_by",
            "idempotency_key",
            name="uq_transactions_initiator_idempotency"
        ),
        Index(
            "ix_transactions_source_account_created_at",
            "source_account_id",
            "created_at"
        ),
        Index(
            "ix_transactions_destination_account_created_at",
            "destination_account_id",
            "created_at"
        ),
        Index(
            "ix_transactions_status_created_at",
            "status",
            "created_at"
        ),
            CheckConstraint(
            "amount <> 'NaN'::numeric",
            name="finite_amount"
        ),
        ForeignKeyConstraint(
            ["source_account_id", "initiated_by"],
            ["accounts.id", "accounts.user_id"],
            name="fk_transactions_source_account_owner",
            ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            [
                "beneficiary_id",
                "initiated_by",
                "destination_account_id"
            ],
            [
                "beneficiaries.id",
                "beneficiaries.user_id",
                "beneficiaries.account_id"
            ],
            name="fk_transactions_beneficiary_consistency",
            ondelete="RESTRICT"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    initiated_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    source_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False
    )

    destination_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False
    )

    beneficiary_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("beneficiaries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR"
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=TransactionStatus.PENDING.value,
        server_default=TransactionStatus.PENDING.value
    )

    idempotency_key: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
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

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
        # ORM Relationships

    initiator: Mapped["User"] = relationship(
        back_populates="initiated_transactions",
        foreign_keys=[initiated_by]
    )

    source_account: Mapped["Account"] = relationship(
        back_populates="outgoing_transactions",
        foreign_keys=[source_account_id]
    )

    destination_account: Mapped["Account"] = relationship(
        back_populates="incoming_transactions",
        foreign_keys=[destination_account_id]
    )

    beneficiary: Mapped["Beneficiary"] = relationship(
        back_populates="transactions",
        foreign_keys=[beneficiary_id]
    )

    fraud_assessments: Mapped[list["FraudAssessment"]] = relationship(
        back_populates="transaction",
        passive_deletes="all"
    )

    reviews: Mapped[list["Review"]] = relationship(
        back_populates="transaction",
        passive_deletes="all"
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="transaction",
        passive_deletes="all"
    )