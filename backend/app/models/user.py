from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    String,
    Uuid,
    func,
    true
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.beneficiary import Beneficiary
    from app.models.transaction import Transaction
    from app.models.review import Review
    from app.models.audit_log import AuditLog

class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"


class User(Base):

    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "role in ('CUSTOMER', 'REVIEWER', 'ADMIN')",
            name="valid_role"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.CUSTOMER.value,
        server_default=UserRole.CUSTOMER.value
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
        # ORM Relationships

    accounts: Mapped[list["Account"]] = relationship(
        back_populates="owner",
        passive_deletes="all"
    )

    beneficiaries: Mapped[list["Beneficiary"]] = relationship(
        back_populates="owner",
        passive_deletes="all"
    )

    initiated_transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="initiator",
        passive_deletes="all"
    )

    reviews: Mapped[list["Review"]] = relationship(
        back_populates="reviewer",
        passive_deletes="all"
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user",
        passive_deletes="all"
    )