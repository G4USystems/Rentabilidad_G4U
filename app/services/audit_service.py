"""Service for audit logging and change tracking."""

from datetime import datetime, date
from typing import Dict, Any, Optional, List
import logging
import json

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class AuditService:
    """Service for creating and querying audit logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        # Generate changes summary
        changes_summary = self._generate_changes_summary(
            action, entity_type, old_values, new_values
        )

        # Serialize values for JSON storage
        old_serialized = self._serialize_values(old_values) if old_values else None
        new_serialized = self._serialize_values(new_values) if new_values else None

        log_entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            old_values=old_serialized,
            new_values=new_serialized,
            changes_summary=changes_summary,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)

        logger.debug(f"Audit log created: {log_entry}")
        return log_entry

    async def log_create(
        self,
        entity_type: str,
        entity_id: str,
        values: Dict[str, Any],
        **kwargs,
    ) -> AuditLog:
        """Log a create action."""
        return await self.log(
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            new_values=values,
            **kwargs,
        )

    async def log_update(
        self,
        entity_type: str,
        entity_id: str,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        **kwargs,
    ) -> AuditLog:
        """Log an update action."""
        return await self.log(
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            **kwargs,
        )

    async def log_delete(
        self,
        entity_type: str,
        entity_id: str,
        old_values: Dict[str, Any],
        **kwargs,
    ) -> AuditLog:
        """Log a delete action."""
        return await self.log(
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            **kwargs,
        )

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50,
    ) -> List[AuditLog]:
        """Get audit history for a specific entity."""
        query = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.entity_type == entity_type,
                    AuditLog.entity_id == str(entity_id),
                )
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_activity(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs for a specific user."""
        query = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_recent_activity(
        self,
        entity_type: Optional[str] = None,
        action: Optional[AuditAction] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get recent audit logs with optional filters."""
        conditions = []

        if entity_type:
            conditions.append(AuditLog.entity_type == entity_type)
        if action:
            conditions.append(AuditLog.action == action)

        query = select(AuditLog)
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(AuditLog.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _generate_changes_summary(
        self,
        action: AuditAction,
        entity_type: str,
        old_values: Optional[Dict[str, Any]],
        new_values: Optional[Dict[str, Any]],
    ) -> str:
        """Generate a human-readable summary of changes."""
        if action == AuditAction.CREATE:
            return f"Created new {entity_type}"

        elif action == AuditAction.DELETE:
            return f"Deleted {entity_type}"

        elif action == AuditAction.UPDATE and old_values and new_values:
            changes = []
            all_keys = set(old_values.keys()) | set(new_values.keys())

            for key in all_keys:
                old_val = old_values.get(key)
                new_val = new_values.get(key)
                if old_val != new_val:
                    changes.append(f"{key}: {old_val} → {new_val}")

            if changes:
                return f"Updated {entity_type}: " + ", ".join(changes[:5])
            return f"Updated {entity_type} (no visible changes)"

        return f"{action.value} on {entity_type}"

    def _serialize_values(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize values for JSON storage."""
        serialized = {}
        for key, value in values.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, date):
                serialized[key] = value.isoformat()
            elif hasattr(value, "__dict__"):
                serialized[key] = str(value)
            else:
                try:
                    json.dumps(value)  # Test if serializable
                    serialized[key] = value
                except (TypeError, ValueError):
                    serialized[key] = str(value)
        return serialized


def get_audit_context_from_request(request) -> Dict[str, Any]:
    """Extract audit context from a FastAPI request."""
    context = {}

    # Get IP address
    if hasattr(request, "client") and request.client:
        context["ip_address"] = request.client.host

    # Get user agent
    user_agent = request.headers.get("user-agent")
    if user_agent:
        context["user_agent"] = user_agent[:500]  # Truncate if too long

    # Get request ID if available
    request_id = request.headers.get("x-request-id")
    if request_id:
        context["request_id"] = request_id

    return context
