"""Assignment rule model for configurable transaction suggestions."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class AssignmentRule(Base):
    """
    Model for storing configurable rules to suggest project/client assignments.

    Rules are evaluated in order of priority (higher = more important).
    A transaction matches a rule if any of the keyword conditions match.
    """

    __tablename__ = "assignment_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Rule identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Match conditions (any non-null field is used for matching)
    # Comma-separated list of keywords to match in label/reference/note
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Match exact counterparty name
    counterparty: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Match pattern in counterparty (supports wildcards)
    counterparty_pattern: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Suggested assignment values
    client_name_suggested: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    project_id_suggested: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True
    )

    # Rule priority (higher = evaluated first)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    # Active flag
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        foreign_keys=[project_id_suggested]
    )

    @property
    def keyword_list(self) -> list:
        """Get keywords as a list."""
        if not self.keywords:
            return []
        return [k.strip().lower() for k in self.keywords.split(",") if k.strip()]

    def matches_transaction(self, label: str, counterparty_name: Optional[str] = None) -> bool:
        """
        Check if this rule matches a transaction.

        Returns True if any condition matches.
        """
        label_lower = label.lower() if label else ""
        counterparty_lower = counterparty_name.lower() if counterparty_name else ""

        # Check keywords
        for keyword in self.keyword_list:
            if keyword in label_lower:
                return True

        # Check exact counterparty match
        if self.counterparty and counterparty_lower == self.counterparty.lower():
            return True

        # Check counterparty pattern (simple wildcard support)
        if self.counterparty_pattern:
            pattern_lower = self.counterparty_pattern.lower()
            if pattern_lower.startswith("*") and pattern_lower.endswith("*"):
                if pattern_lower[1:-1] in counterparty_lower:
                    return True
            elif pattern_lower.startswith("*"):
                if counterparty_lower.endswith(pattern_lower[1:]):
                    return True
            elif pattern_lower.endswith("*"):
                if counterparty_lower.startswith(pattern_lower[:-1]):
                    return True
            elif pattern_lower == counterparty_lower:
                return True

        return False

    def __repr__(self) -> str:
        return f"<AssignmentRule(id={self.id}, name='{self.name}', priority={self.priority})>"
