"""API endpoints for alerts management."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.models.alert import AlertType, AlertSeverity, AlertStatus
from app.services.alert_service import AlertService

router = APIRouter()


class AlertResponse(BaseModel):
    """Alert response model."""
    id: int
    alert_type: str
    severity: str
    status: str
    title: str
    message: str
    project_id: Optional[int] = None
    transaction_id: Optional[int] = None
    client_name: Optional[str] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    created_at: str
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None

    class Config:
        from_attributes = True


class AlertSummaryResponse(BaseModel):
    """Alert summary response."""
    total_active: int
    by_severity: dict
    critical: int
    warning: int
    info: int


@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    alert_type: Optional[AlertType] = None,
    severity: Optional[AlertSeverity] = None,
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get active alerts with optional filters."""
    service = AlertService(db)
    alerts = await service.get_active_alerts(
        alert_type=alert_type,
        severity=severity,
        project_id=project_id,
    )

    return [
        AlertResponse(
            id=a.id,
            alert_type=a.alert_type.value,
            severity=a.severity.value,
            status=a.status.value,
            title=a.title,
            message=a.message,
            project_id=a.project_id,
            transaction_id=a.transaction_id,
            client_name=a.client_name,
            threshold_value=float(a.threshold_value) if a.threshold_value else None,
            actual_value=float(a.actual_value) if a.actual_value else None,
            created_at=a.created_at.isoformat() if a.created_at else "",
            acknowledged_at=a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            acknowledged_by=a.acknowledged_by,
        )
        for a in alerts
    ]


@router.get("/summary", response_model=AlertSummaryResponse)
async def get_alert_summary(
    db: AsyncSession = Depends(get_db),
):
    """Get summary of current alerts."""
    service = AlertService(db)
    summary = await service.get_alert_summary()
    return AlertSummaryResponse(**summary)


@router.post("/check")
async def check_alerts(
    db: AsyncSession = Depends(get_db),
):
    """Run all alert checks and create new alerts."""
    service = AlertService(db)
    alerts = await service.check_all_alerts()

    return {
        "checked": True,
        "new_alerts_created": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "type": a.alert_type.value,
                "severity": a.severity.value,
                "title": a.title,
            }
            for a in alerts
        ],
    }


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge an alert."""
    service = AlertService(db)
    alert = await service.acknowledge_alert(alert_id, user_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"status": "acknowledged", "alert_id": alert_id}


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Mark an alert as resolved."""
    service = AlertService(db)
    alert = await service.resolve_alert(alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"status": "resolved", "alert_id": alert_id}


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Dismiss an alert."""
    service = AlertService(db)
    alert = await service.dismiss_alert(alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"status": "dismissed", "alert_id": alert_id}
