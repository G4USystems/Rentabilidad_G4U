"""Audit log model for tracking all changes."""

import enum
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import String, Text, Enum, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditAction(str, enum.Enum):
    """Types of auditable actions."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ALLOCATE = "allocate"
    DEALLOCATE = "deallocate"
    CONFIRM = "confirm"
    CATEGORIZE = "categorize"
    SYNC = "sync"
    IMPORT = "import"
    EXPORT = "export"


class AuditLog(Base):
    """Model for audit trail of all system changes."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # What happened
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)  # transaction, project, etc.
    entity_id: Mapped[str] = mapped_column(String(100), index=True)  # ID of affected entity

    # Who did it
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    user_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # What changed
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    changes_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.id}: {self.action.value} {self.entity_type}:{self.entity_id}>"
