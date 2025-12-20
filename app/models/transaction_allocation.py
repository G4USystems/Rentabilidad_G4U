"""Transaction allocation model for partial project/client assignments."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.project import Project


class TransactionAllocation(Base):
    """
    Model for storing partial allocations of transactions to projects and/or clients.

    A single transaction can be split across multiple projects and/or clients,
    allowing for more granular profitability tracking. Project and client are
    independent - an allocation can have one, the other, or both.
    """

    __tablename__ = "transaction_allocations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Parent transaction
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False
    )

    # Optional project allocation (independent from client)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True
    )

    # Optional client allocation (independent from project)
    # Using string to allow flexibility - clients aren't a separate table
    client_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Allocation amount - either percentage or absolute amount
    percentage: Mapped[Decimal] = mapped_column(
        Numeric(7, 4),  # Allows up to 100.0000%
        nullable=False,
        default=Decimal("100")
    )

    # Calculated amount based on percentage * transaction.amount
    amount_allocated: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="allocations"
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="allocations"
    )

    # Indexes for efficient queries
    __table_args__ = (
        Index('ix_allocations_transaction', 'transaction_id'),
        Index('ix_allocations_project', 'project_id'),
        Index('ix_allocations_client', 'client_name'),
    )

    def __repr__(self) -> str:
        return (
            f"<TransactionAllocation(id={self.id}, "
            f"transaction_id={self.transaction_id}, "
            f"project_id={self.project_id}, "
            f"client_name='{self.client_name}', "
            f"percentage={self.percentage}%)>"
        )
