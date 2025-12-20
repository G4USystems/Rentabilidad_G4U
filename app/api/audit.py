"""API endpoints for audit logs."""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.models.audit_log import AuditAction
from app.services.audit_service import AuditService

router = APIRouter()


class AuditLogResponse(BaseModel):
    """Audit log response model."""
    id: int
    action: str
    entity_type: str
    entity_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    changes_summary: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[AuditLogResponse])
async def get_audit_logs(
    entity_type: Optional[str] = None,
    action: Optional[AuditAction] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get recent audit logs with optional filters."""
    service = AuditService(db)
    logs = await service.get_recent_activity(
        entity_type=entity_type,
        action=action,
        limit=limit,
    )

    return [
        AuditLogResponse(
            id=log.id,
            action=log.action.value,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            user_id=log.user_id,
            user_email=log.user_email,
            user_name=log.user_name,
            old_values=log.old_values,
            new_values=log.new_values,
            changes_summary=log.changes_summary,
            ip_address=log.ip_address,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]


@router.get("/entity/{entity_type}/{entity_id}", response_model=List[AuditLogResponse])
async def get_entity_history(
    entity_type: str,
    entity_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get audit history for a specific entity."""
    service = AuditService(db)
    logs = await service.get_entity_history(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )

    return [
        AuditLogResponse(
            id=log.id,
            action=log.action.value,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            user_id=log.user_id,
            user_email=log.user_email,
            user_name=log.user_name,
            old_values=log.old_values,
            new_values=log.new_values,
            changes_summary=log.changes_summary,
            ip_address=log.ip_address,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]


@router.get("/user/{user_id}", response_model=List[AuditLogResponse])
async def get_user_activity(
    user_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get audit logs for a specific user."""
    service = AuditService(db)
    logs = await service.get_user_activity(
        user_id=user_id,
        limit=limit,
    )

    return [
        AuditLogResponse(
            id=log.id,
            action=log.action.value,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            user_id=log.user_id,
            user_email=log.user_email,
            user_name=log.user_name,
            old_values=log.old_values,
            new_values=log.new_values,
            changes_summary=log.changes_summary,
            ip_address=log.ip_address,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]
