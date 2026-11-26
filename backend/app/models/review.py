from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    Uuid,
    func,
    text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.fraud_assessment import FraudAssessment
    from app.models.user import User
class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Review(Base):

    __tablename__ = "reviews"

    __table_args__ = (
        CheckConstraint(
            "status in ('PENDING', 'APPROVED', 'REJECTED')",
            name="valid_status"
        ),
        CheckConstraint(
            "(status = 'PENDING' AND reviewed_at IS NULL) "
            "OR (status in ('APPROVED', 'REJECTED') "
            "AND reviewed_at IS NOT NULL "
            "AND reviewer_id IS NOT NULL "
            "AND decision_reason IS NOT NULL "
            "AND length(trim(decision_reason)) > 0)",
            name="valid_review_decision"
        ),
        Index(
            "uq_reviews_pending_transaction",
            "transaction_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'")
        ),
        Index(
            "ix_reviews_status_created_at",
            "status",
            "created_at"
        ),
        ForeignKeyConstraint(
            ["fraud_assessment_id", "transaction_id"],
            [
                "fraud_assessments.id",
                "fraud_assessments.transaction_id"
            ],
            name="fk_reviews_assessment_transaction",
            ondelete="RESTRICT"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    transaction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("transactions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    fraud_assessment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("fraud_assessments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    reviewer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReviewStatus.PENDING.value,
        server_default=ReviewStatus.PENDING.value
    )

    decision_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
        # ORM Relationships

    transaction: Mapped["Transaction"] = relationship(
        back_populates="reviews"
    )
    
    fraud_assessment: Mapped["FraudAssessment"] = relationship(
        back_populates="reviews",
        foreign_keys=[fraud_assessment_id]
    )

    reviewer: Mapped["User | None"] = relationship(
        back_populates="reviews"
    )