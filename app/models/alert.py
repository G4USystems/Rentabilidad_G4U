"""Alert model for automatic notifications."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Text, Numeric, Boolean, Enum, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AlertType(str, enum.Enum):
    """Types of alerts."""
    LOW_MARGIN = "low_margin"
    BUDGET_EXCEEDED = "budget_exceeded"
    NEGATIVE_PROFIT = "negative_profit"
    UNUSUAL_EXPENSE = "unusual_expense"
    MISSING_ALLOCATION = "missing_allocation"
    PENDING_REVIEW = "pending_review"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Alert(Base):
    """Model for system alerts."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Alert type and severity
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), index=True)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity),
        default=AlertSeverity.WARNING
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus),
        default=AlertStatus.ACTIVE,
        index=True
    )

    # Alert content
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)

    # Related entities (optional)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True
    )
    transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True
    )
    client_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Threshold values that triggered the alert
    threshold_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True
    )
    actual_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    acknowledged_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    # Relationships
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="alerts"
    )
    transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction",
        back_populates="alerts"
    )

    def __repr__(self) -> str:
        return f"<Alert {self.id}: {self.alert_type.value} - {self.severity.value}>"
