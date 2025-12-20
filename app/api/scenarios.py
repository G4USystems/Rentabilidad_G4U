"""API endpoints for AI-powered scenario simulation."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.scenario_service import ScenarioService
from app.schemas.scenario import (
    ScenarioRequest,
    ScenarioResponse,
    CompareRequest,
    CompareResponse,
    HistoricalContext,
)

router = APIRouter()


@router.post("/simulate", response_model=ScenarioResponse)
async def simulate_scenario(
    request: ScenarioRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an AI-powered scenario simulation.

    Uses historical financial data from the last 3-6 months combined with
    user's scenario description to generate projections.

    The LLM analyzes the context and generates:
    - Scenario assumptions (growth rates, churn, new clients, etc.)
    - Monthly projections for revenue, expenses, and profit
    - Summary KPIs
    - Reasoning explanation

    Supports multiple LLM providers:
    - 'openai': Uses GPT-4 (requires OPENAI_API_KEY)
    - 'anthropic': Uses Claude (requires ANTHROPIC_API_KEY)
    - 'mock': Uses rule-based mock provider (no API key needed)

    If no provider specified, auto-detects based on available API keys.
    """
    service = ScenarioService(db)

    try:
        result = await service.simulate_scenario(
            user_prompt=request.prompt,
            projection_months=request.projection_months,
            llm_provider_name=request.llm_provider,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating scenario: {str(e)}"
        )


@router.post("/compare", response_model=CompareResponse)
async def compare_scenarios(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare multiple scenarios side by side.

    Generates scenarios for each prompt and provides comparison metrics
    including best/worst performers and profit ranges.
    """
    service = ScenarioService(db)

    try:
        result = await service.compare_scenarios(
            prompts=request.prompts,
            projection_months=request.projection_months,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing scenarios: {str(e)}"
        )


@router.get("/context", response_model=HistoricalContext)
async def get_historical_context(
    months: int = 6,
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical context data used for scenario simulations.

    Returns the same metrics that are provided to the LLM for
    scenario generation, useful for understanding the baseline.
    """
    service = ScenarioService(db, months_history=months)

    try:
        result = await service.get_historical_metrics()
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting historical context: {str(e)}"
        )
