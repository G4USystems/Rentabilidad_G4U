"""Scenario simulation schemas for API validation."""

from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    """Request for scenario simulation."""

    prompt: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Description of the scenario to simulate",
        examples=[
            "What if we hire 2 new developers and increase marketing spend by 20%?",
            "Optimistic growth scenario with 3 new clients",
            "What happens if our biggest client churns?",
        ]
    )
    projection_months: int = Field(
        default=6,
        ge=1,
        le=24,
        description="Number of months to project"
    )
    llm_provider: Optional[str] = Field(
        default=None,
        description="LLM provider to use: 'openai', 'anthropic', or 'mock'"
    )


class MonthlyProjection(BaseModel):
    """Monthly projection data."""

    month: int
    projected_revenue: float
    projected_expenses: float
    projected_profit: float
    projected_clients: Optional[int] = None


class ScenarioAssumptions(BaseModel):
    """Scenario assumptions."""

    revenue_growth_rate: Optional[float] = None
    expense_growth_rate: Optional[float] = None
    new_clients_per_month: Optional[int] = None
    churn_rate: Optional[float] = None
    base_revenue: Optional[float] = None
    base_expenses: Optional[float] = None


class ScenarioSummary(BaseModel):
    """Summary of scenario projections."""

    total_projected_revenue: float
    total_projected_expenses: float
    total_projected_profit: float
    final_client_count: Optional[int] = None


class GeneratedScenario(BaseModel):
    """LLM-generated scenario."""

    scenario_name: str
    assumptions: Dict[str, Any]
    projections: List[Dict[str, Any]]
    summary: Dict[str, Any]
    reasoning: str
    provider: str
    error: Optional[str] = None


class SimulatedKPIs(BaseModel):
    """Simulated KPIs from scenario."""

    period_months: int
    total_revenue: float
    total_expenses: float
    total_profit: float
    avg_monthly_revenue: float
    avg_monthly_profit: float
    projected_profit_margin: float
    revenue_growth_from_current: float


class HistoricalContext(BaseModel):
    """Historical data context."""

    period: Dict[str, Any]
    monthly_data: List[Dict[str, Any]]
    averages: Dict[str, float]
    growth_rates: Dict[str, float]
    current_state: Dict[str, Any]


class ScenarioResponse(BaseModel):
    """Response from scenario simulation."""

    user_prompt: str
    historical_context: HistoricalContext
    scenario: GeneratedScenario
    simulated_kpis: SimulatedKPIs


class CompareRequest(BaseModel):
    """Request for comparing multiple scenarios."""

    prompts: List[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="List of scenario prompts to compare"
    )
    projection_months: int = Field(
        default=6,
        ge=1,
        le=24,
        description="Number of months to project"
    )


class ScenarioComparison(BaseModel):
    """Comparison summary."""

    count: int
    best_scenario: Optional[str] = None
    worst_scenario: Optional[str] = None
    profit_range: Dict[str, float]


class CompareResponse(BaseModel):
    """Response from scenario comparison."""

    scenarios: List[Dict[str, Any]]
    comparison: ScenarioComparison
