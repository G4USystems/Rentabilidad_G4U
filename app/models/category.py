"""Category model for transaction classification."""

import enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, Text, Enum, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class CategoryType(str, enum.Enum):
    """Type of category for P&L classification."""

    # Income categories
    REVENUE = "revenue"  # Ingresos por ventas/servicios
    OTHER_INCOME = "other_income"  # Otros ingresos

    # Expense categories
    COGS = "cogs"  # Cost of Goods Sold / Costos directos
    OPERATING_EXPENSE = "operating_expense"  # Gastos operativos
    PAYROLL = "payroll"  # Nómina y salarios
    MARKETING = "marketing"  # Marketing y publicidad
    ADMIN = "admin"  # Gastos administrativos
    RENT = "rent"  # Alquiler y servicios
    PROFESSIONAL_SERVICES = "professional_services"  # Servicios profesionales
    SOFTWARE = "software"  # Software y suscripciones
    TRAVEL = "travel"  # Viajes y representación
    TAXES = "taxes"  # Impuestos
    INTEREST = "interest"  # Intereses financieros
    DEPRECIATION = "depreciation"  # Depreciación
    OTHER_EXPENSE = "other_expense"  # Otros gastos

    # Non-P&L categories
    TRANSFER = "transfer"  # Transferencias internas
    INVESTMENT = "investment"  # Inversiones
    LOAN = "loan"  # Préstamos
    EQUITY = "equity"  # Capital
    UNCATEGORIZED = "uncategorized"  # Sin categorizar


class Category(Base):
    """Category model for classifying transactions."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType),
        default=CategoryType.UNCATEGORIZED,
        nullable=False
    )

    # Hierarchical structure
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"),
        nullable=True
    )

    # Matching rules (for auto-categorization)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Comma-separated

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # System categories can't be deleted

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
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side=[id],
        backref="children"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="category"
    )

    @property
    def is_income(self) -> bool:
        """Check if category is an income type."""
        return self.type in [CategoryType.REVENUE, CategoryType.OTHER_INCOME]

    @property
    def is_expense(self) -> bool:
        """Check if category is an expense type."""
        return self.type in [
            CategoryType.COGS,
            CategoryType.OPERATING_EXPENSE,
            CategoryType.PAYROLL,
            CategoryType.MARKETING,
            CategoryType.ADMIN,
            CategoryType.RENT,
            CategoryType.PROFESSIONAL_SERVICES,
            CategoryType.SOFTWARE,
            CategoryType.TRAVEL,
            CategoryType.TAXES,
            CategoryType.INTEREST,
            CategoryType.DEPRECIATION,
            CategoryType.OTHER_EXPENSE,
        ]

    @property
    def affects_pl(self) -> bool:
        """Check if category affects P&L statement."""
        return self.is_income or self.is_expense

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', type={self.type})>"
