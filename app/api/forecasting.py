"""API endpoints for forecasting."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.services.forecasting_service import ForecastingService

router = APIRouter()


@router.get("/trends")
async def get_historical_trends(
    months: int = Query(12, ge=3, le=36),
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical trend analysis.

    Returns:
    - Monthly revenue/expense data
    - Growth rates
    - Seasonality patterns
    - Trend direction (growing/stable/declining)
    """
    service = ForecastingService(db)
    return await service.get_historical_trends(months=months)


@router.get("/forecast")
async def get_forecast(
    projection_months: int = Query(6, ge=1, le=24),
    scenario: str = Query("baseline", regex="^(baseline|optimistic|pessimistic)$"),
    use_seasonality: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a forecast based on historical trends.

    Scenarios:
    - baseline: Continue current trends
    - optimistic: +2% monthly growth adjustment
    - pessimistic: -2% monthly growth adjustment

    Returns monthly projections with revenue, expenses, profit, and margin.
    """
    service = ForecastingService(db)
    return await service.generate_forecast(
        projection_months=projection_months,
        scenario=scenario,
        use_seasonality=use_seasonality,
    )


@router.get("/compare-scenarios")
async def compare_forecast_scenarios(
    projection_months: int = Query(6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare all three forecast scenarios side by side.

    Returns baseline, optimistic, and pessimistic forecasts
    with comparison metrics.
    """
    service = ForecastingService(db)
    return await service.compare_forecast_scenarios(
        projection_months=projection_months,
    )


class AIForecastRequest(BaseModel):
    """Request for AI-powered forecast."""
    projection_months: int = 6
    custom_prompt: Optional[str] = None


@router.post("/ai-forecast")
async def get_ai_forecast(
    request: AIForecastRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a forecast using AI scenario simulator.

    Optionally provide a custom prompt for specific scenario modeling.

    Examples of custom prompts:
    - "Forecast assuming we hire 2 new developers"
    - "Project revenue if we lose our biggest client"
    - "Model growth with 30% more marketing spend"
    """
    service = ForecastingService(db)
    return await service.forecast_with_ai(
        projection_months=request.projection_months,
        custom_prompt=request.custom_prompt,
    )
