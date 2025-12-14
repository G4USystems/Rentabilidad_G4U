"""Transaction model for storing Qonto transactions."""

import enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, Date, Numeric, Enum, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.project import Project
    from app.models.account import QontoAccount


class TransactionSide(str, enum.Enum):
    """Transaction side (credit or debit)."""
    CREDIT = "credit"  # Money in (income)
    DEBIT = "debit"    # Money out (expense)


class TransactionStatus(str, enum.Enum):
    """Transaction status from Qonto."""
    PENDING = "pending"
    COMPLETED = "completed"
    DECLINED = "declined"
    REVERSED = "reversed"


class TransactionType(str, enum.Enum):
    """Type of transaction."""
    TRANSFER = "transfer"
    CARD = "card"
    DIRECT_DEBIT = "direct_debit"
    INCOME = "income"
    QONTO_FEE = "qonto_fee"
    CHECK = "check"
    SWIFT = "swift"
    OTHER = "other"


class Transaction(Base):
    """Transaction model storing financial movements from Qonto."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Qonto identifiers
    qonto_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Account relationship
    account_id: Mapped[int] = mapped_column(
        ForeignKey("qonto_accounts.id"),
        nullable=False
    )

    # Basic transaction info
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    amount_cents: Mapped[int] = mapped_column(nullable=False)  # Original amount in cents
    currency: Mapped[str] = mapped_column(String(3), default="EUR")

    # Local amount (if different currency)
    local_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    local_currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)

    # Transaction classification
    side: Mapped[TransactionSide] = mapped_column(Enum(TransactionSide), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus),
        default=TransactionStatus.COMPLETED
    )
    operation_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType),
        default=TransactionType.OTHER
    )

    # Dates
    emitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Description and notes
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Counterparty info
    counterparty_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    counterparty_iban: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Card info (if card transaction)
    card_last_digits: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)

    # VAT info
    vat_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    vat_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Attachment info
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_count: Mapped[int] = mapped_column(default=0)

    # Category relationship
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"),
        nullable=True
    )

    # Project relationship
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"),
        nullable=True
    )

    # Manual flags
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_excluded_from_reports: Mapped[bool] = mapped_column(Boolean, default=False)

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
    synced_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    account: Mapped["QontoAccount"] = relationship(
        "QontoAccount",
        back_populates="transactions"
    )
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="transactions"
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="transactions"
    )

    @property
    def is_income(self) -> bool:
        """Check if transaction is income (credit)."""
        return self.side == TransactionSide.CREDIT

    @property
    def is_expense(self) -> bool:
        """Check if transaction is expense (debit)."""
        return self.side == TransactionSide.DEBIT

    @property
    def signed_amount(self) -> Decimal:
        """Get amount with sign (positive for income, negative for expense)."""
        if self.is_income:
            return self.amount
        return -self.amount

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, "
            f"qonto_id='{self.qonto_id}', "
            f"amount={self.signed_amount}, "
            f"label='{self.label[:30]}...')>"
        )
