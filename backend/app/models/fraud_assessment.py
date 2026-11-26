from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
from typing import Any, TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.review import Review
class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FraudAssessment(Base):

    __tablename__ = "fraud_assessments"

    __table_args__ = (
        CheckConstraint(
            "risk_score BETWEEN 0 AND 100",
            name="valid_risk_score"
        ),
        CheckConstraint(
            "risk_level in ('LOW', 'MEDIUM', 'HIGH')",
            name="valid_risk_level"
        ),
        CheckConstraint(
            "jsonb_typeof(risk_factors) = 'array'",
            name="valid_risk_factors"
        ),
        Index(
            "ix_fraud_assessments_transaction_created_at",
            "transaction_id",
            "created_at"
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
        nullable=False
    )

    risk_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    risk_level: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    risk_factors: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list
    )

    rule_version: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
        # ORM Relationships

    transaction: Mapped["Transaction"] = relationship(
        back_populates="fraud_assessments"
    )

    reviews: Mapped[list["Review"]] = relationship(
        back_populates="fraud_assessment",
        passive_deletes="all"
    )