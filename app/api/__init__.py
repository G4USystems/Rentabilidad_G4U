"""API routes module."""

from fastapi import APIRouter

from app.api import transactions, categories, projects, reports, kpis, sync

api_router = APIRouter()

api_router.include_router(
    sync.router,
    prefix="/sync",
    tags=["sync"],
)
api_router.include_router(
    transactions.router,
    prefix="/transactions",
    tags=["transactions"],
)
api_router.include_router(
    categories.router,
    prefix="/categories",
    tags=["categories"],
)
api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["projects"],
)
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["reports"],
)
api_router.include_router(
    kpis.router,
    prefix="/kpis",
    tags=["kpis"],
)
