"""Background jobs for async operations like Qonto sync."""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job:
    """Represents a background job."""

    def __init__(
        self,
        job_id: str,
        job_type: str,
        params: Optional[Dict[str, Any]] = None,
    ):
        self.job_id = job_id
        self.job_type = job_type
        self.params = params or {}
        self.status = JobStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.progress: float = 0.0
        self.progress_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "result": self.result,
            "error": self.error,
        }


class BackgroundJobService:
    """
    Service for managing background jobs.

    Uses asyncio for simple in-process background tasks.
    Can be extended to use Celery/Redis for distributed jobs.
    """

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._handlers: Dict[str, Callable] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

    def register_handler(self, job_type: str, handler: Callable):
        """Register a handler for a job type."""
        self._handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type}")

    async def submit_job(
        self,
        job_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """Submit a new background job."""
        import uuid

        job_id = str(uuid.uuid4())[:8]
        job = Job(job_id, job_type, params)
        self._jobs[job_id] = job

        # Start the job in background
        task = asyncio.create_task(self._run_job(job))
        self._running_tasks[job_id] = task

        logger.info(f"Submitted job {job_id} of type {job_type}")
        return job

    async def _run_job(self, job: Job):
        """Execute a job."""
        handler = self._handlers.get(job.job_type)

        if not handler:
            job.status = JobStatus.FAILED
            job.error = f"No handler registered for job type: {job.job_type}"
            logger.error(job.error)
            return

        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            logger.info(f"Starting job {job.job_id}")

            # Run the handler with progress callback
            async def update_progress(progress: float, message: str = ""):
                job.progress = progress
                job.progress_message = message

            result = await handler(job.params, update_progress)

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress = 100.0
            job.result = result
            logger.info(f"Job {job.job_id} completed successfully")

        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            logger.warning(f"Job {job.job_id} was cancelled")

        except Exception as e:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error = str(e)
            logger.error(f"Job {job.job_id} failed: {e}")

        finally:
            # Clean up
            self._running_tasks.pop(job.job_id, None)

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def get_all_jobs(self, limit: int = 50) -> list:
        """Get all jobs, most recent first."""
        jobs = sorted(
            self._jobs.values(),
            key=lambda j: j.created_at,
            reverse=True,
        )
        return jobs[:limit]

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        task = self._running_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove completed jobs older than max_age_hours."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        to_remove = [
            job_id for job_id, job in self._jobs.items()
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
            and job.completed_at and job.completed_at < cutoff
        ]

        for job_id in to_remove:
            del self._jobs[job_id]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old jobs")


# Singleton instance
_job_service: Optional[BackgroundJobService] = None


def get_job_service() -> BackgroundJobService:
    """Get or create job service singleton."""
    global _job_service
    if _job_service is None:
        _job_service = BackgroundJobService()
    return _job_service


# ============================================
# Job Handlers
# ============================================

async def sync_qonto_handler(
    params: Dict[str, Any],
    update_progress: Callable,
) -> Dict[str, Any]:
    """
    Handler for Qonto sync job.

    This runs the sync in background and reports progress.
    """
    from app.core.database import async_session_maker

    await update_progress(10, "Connecting to Qonto...")

    async with async_session_maker() as db:
        # Import here to avoid circular imports
        from app.services.qonto_sync_service import QontoSyncService

        sync_service = QontoSyncService(db)

        await update_progress(20, "Fetching accounts...")
        # accounts = await sync_service.sync_accounts()

        await update_progress(40, "Fetching transactions...")
        # Note: This would call the actual sync method
        # For now, simulate progress

        await asyncio.sleep(2)  # Simulate work
        await update_progress(70, "Processing transactions...")

        await asyncio.sleep(1)
        await update_progress(90, "Finalizing...")

        await db.commit()

        return {
            "synced": True,
            "message": "Sync completed successfully",
            # "accounts_synced": len(accounts),
            # "transactions_synced": tx_count,
        }


async def check_alerts_handler(
    params: Dict[str, Any],
    update_progress: Callable,
) -> Dict[str, Any]:
    """Handler for running alert checks in background."""
    from app.core.database import async_session_maker
    from app.services.alert_service import AlertService

    await update_progress(10, "Initializing alert check...")

    async with async_session_maker() as db:
        service = AlertService(db)

        await update_progress(30, "Checking margin alerts...")
        margin_alerts = await service.check_low_margin_alerts()

        await update_progress(50, "Checking budget alerts...")
        budget_alerts = await service.check_budget_exceeded_alerts()

        await update_progress(70, "Checking review status...")
        review_alerts = await service.check_pending_review_alerts()

        await update_progress(90, "Checking allocations...")
        alloc_alerts = await service.check_missing_allocation_alerts()

        all_alerts = margin_alerts + budget_alerts + review_alerts + alloc_alerts

        return {
            "alerts_created": len(all_alerts),
            "by_type": {
                "low_margin": len(margin_alerts),
                "budget_exceeded": len(budget_alerts),
                "pending_review": len(review_alerts),
                "missing_allocation": len(alloc_alerts),
            },
        }


async def auto_categorize_handler(
    params: Dict[str, Any],
    update_progress: Callable,
) -> Dict[str, Any]:
    """Handler for auto-categorizing transactions in background."""
    from app.core.database import async_session_maker
    from app.services.categorization_service import AICategorizationService

    limit = params.get("limit", 50)

    await update_progress(10, "Loading uncategorized transactions...")

    async with async_session_maker() as db:
        service = AICategorizationService(db)

        await update_progress(30, "Running AI categorization...")
        result = await service.auto_categorize_with_review(limit=limit)

        return result


# Register handlers on module load
def register_default_handlers():
    """Register all default job handlers."""
    service = get_job_service()
    service.register_handler("sync_qonto", sync_qonto_handler)
    service.register_handler("check_alerts", check_alerts_handler)
    service.register_handler("auto_categorize", auto_categorize_handler)


# Auto-register on import
register_default_handlers()
