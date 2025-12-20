"""API endpoints for background jobs."""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.background_jobs import get_job_service, JobStatus

router = APIRouter()


class JobResponse(BaseModel):
    """Job response model."""
    job_id: str
    job_type: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float
    progress_message: str
    result: Optional[dict] = None
    error: Optional[str] = None


class SubmitJobRequest(BaseModel):
    """Request to submit a new job."""
    job_type: str
    params: Optional[dict] = None


@router.post("/submit", response_model=JobResponse)
async def submit_job(request: SubmitJobRequest):
    """
    Submit a new background job.

    Available job types:
    - sync_qonto: Sync transactions from Qonto
    - check_alerts: Run all alert checks
    - auto_categorize: Auto-categorize pending transactions
    """
    service = get_job_service()

    job = await service.submit_job(
        job_type=request.job_type,
        params=request.params,
    )

    return JobResponse(**job.to_dict())


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    service = get_job_service()
    job = service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(**job.to_dict())


@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[JobStatus] = None,
):
    """List all jobs."""
    service = get_job_service()
    jobs = service.get_all_jobs(limit=limit)

    if status:
        jobs = [j for j in jobs if j.status == status]

    return [JobResponse(**job.to_dict()) for job in jobs]


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    service = get_job_service()

    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job in status: {job.status.value}"
        )

    cancelled = await service.cancel_job(job_id)

    if cancelled:
        return {"status": "cancelled", "job_id": job_id}
    else:
        raise HTTPException(status_code=400, detail="Failed to cancel job")


@router.post("/cleanup")
async def cleanup_old_jobs(max_age_hours: int = Query(24, ge=1)):
    """Remove old completed/failed jobs."""
    service = get_job_service()
    service.cleanup_old_jobs(max_age_hours=max_age_hours)

    return {"status": "cleaned_up", "max_age_hours": max_age_hours}


# Convenience endpoints for common jobs

@router.post("/sync-qonto", response_model=JobResponse)
async def start_qonto_sync():
    """Start a Qonto sync job."""
    service = get_job_service()
    job = await service.submit_job("sync_qonto", {})
    return JobResponse(**job.to_dict())


@router.post("/check-alerts", response_model=JobResponse)
async def start_alert_check():
    """Start an alert check job."""
    service = get_job_service()
    job = await service.submit_job("check_alerts", {})
    return JobResponse(**job.to_dict())


@router.post("/auto-categorize", response_model=JobResponse)
async def start_auto_categorize(
    limit: int = Query(50, ge=1, le=500),
):
    """Start an auto-categorization job."""
    service = get_job_service()
    job = await service.submit_job("auto_categorize", {"limit": limit})
    return JobResponse(**job.to_dict())
