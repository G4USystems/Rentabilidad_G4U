"""Service for AI-powered scenario simulation."""

from datetime import date
from decimal import Decimal
from typing import Dict, Any, Optional, List
import logging

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionSide
from app.models.project import Project
from app.models.transaction_allocation import TransactionAllocation
from app.services.financial_service import FinancialService
from app.services.llm_provider import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


SCENARIO_SYSTEM_PROMPT = """You are a financial analyst AI assistant specializing in business scenario modeling.
Your task is to create realistic financial projections based on historical data and user requirements.

When analyzing scenarios, consider:
1. Historical trends and seasonality
2. Industry benchmarks
3. The specific request from the user
4. Realistic growth/decline rates

Provide conservative, realistic estimates unless the user specifically requests optimistic or pessimistic scenarios.
Always explain your reasoning and key assumptions."""


class ScenarioService:
    """Service for generating AI-powered financial scenarios."""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: Optional[LLMProvider] = None,
        months_history: int = 6,
    ):
        self.db = db
        self.financial = FinancialService(db)
        self.llm = llm_provider or get_llm_provider()
        self.months_history = months_history

    async def get_historical_metrics(
        self,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Gather historical metrics for scenario context.

        Returns metrics from the last N months.
        """
        if not end_date:
            end_date = date.today()

        start_date = end_date - relativedelta(months=self.months_history)

        # Get monthly revenue and expenses
        monthly_data = []
        current = start_date.replace(day=1)

        while current <= end_date:
            month_end = (current + relativedelta(months=1)) - relativedelta(days=1)
            if month_end > end_date:
                month_end = end_date

            revenue = await self.financial.get_total_revenue(current, month_end)
            expenses = await self.financial.get_total_expenses(current, month_end)

            monthly_data.append({
                "month": current.strftime("%Y-%m"),
                "revenue": float(revenue),
                "expenses": float(expenses),
                "profit": float(revenue - expenses),
            })

            current = current + relativedelta(months=1)

        # Calculate averages
        if monthly_data:
            avg_revenue = sum(m["revenue"] for m in monthly_data) / len(monthly_data)
            avg_expenses = sum(m["expenses"] for m in monthly_data) / len(monthly_data)
            avg_profit = sum(m["profit"] for m in monthly_data) / len(monthly_data)

            # Calculate growth rates
            if len(monthly_data) >= 2:
                first_month = monthly_data[0]
                last_month = monthly_data[-1]
                months_diff = len(monthly_data) - 1

                if first_month["revenue"] > 0:
                    revenue_growth = (last_month["revenue"] / first_month["revenue"]) ** (1/months_diff) - 1
                else:
                    revenue_growth = 0

                if first_month["expenses"] > 0:
                    expense_growth = (last_month["expenses"] / first_month["expenses"]) ** (1/months_diff) - 1
                else:
                    expense_growth = 0
            else:
                revenue_growth = 0
                expense_growth = 0
        else:
            avg_revenue = 0
            avg_expenses = 0
            avg_profit = 0
            revenue_growth = 0
            expense_growth = 0

        # Get client count from allocations
        client_query = (
            select(func.count(func.distinct(TransactionAllocation.client_name)))
            .join(Transaction, TransactionAllocation.transaction_id == Transaction.id)
            .where(
                and_(
                    TransactionAllocation.client_name.isnot(None),
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                )
            )
        )
        result = await self.db.execute(client_query)
        client_count = result.scalar() or 0

        # Also count from projects
        project_client_query = (
            select(func.count(func.distinct(Project.client_name)))
            .where(Project.client_name.isnot(None))
        )
        result = await self.db.execute(project_client_query)
        project_clients = result.scalar() or 0

        total_clients = max(client_count, project_clients)

        # Get project count
        project_query = select(func.count(Project.id)).where(Project.is_active == True)
        result = await self.db.execute(project_query)
        active_projects = result.scalar() or 0

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "months": self.months_history,
            },
            "monthly_data": monthly_data,
            "averages": {
                "avg_monthly_revenue": round(avg_revenue, 2),
                "avg_monthly_expenses": round(avg_expenses, 2),
                "avg_monthly_profit": round(avg_profit, 2),
            },
            "growth_rates": {
                "revenue_growth_monthly": round(revenue_growth, 4),
                "expense_growth_monthly": round(expense_growth, 4),
            },
            "current_state": {
                "active_clients": total_clients,
                "active_projects": active_projects,
                "latest_month_revenue": monthly_data[-1]["revenue"] if monthly_data else 0,
                "latest_month_expenses": monthly_data[-1]["expenses"] if monthly_data else 0,
            },
        }

    async def simulate_scenario(
        self,
        user_prompt: str,
        projection_months: int = 6,
        llm_provider_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a scenario simulation based on user prompt and historical data.

        Args:
            user_prompt: User's description of the scenario to simulate
            projection_months: Number of months to project (default 6)
            llm_provider_name: Optional specific provider ('openai', 'anthropic', 'mock')

        Returns:
            Complete scenario with assumptions, projections, and simulated KPIs
        """
        # Get historical metrics
        historical = await self.get_historical_metrics()

        # Get LLM provider (override if specified)
        if llm_provider_name:
            llm = get_llm_provider(llm_provider_name)
        else:
            llm = self.llm

        # Prepare context
        context = {
            "historical_metrics": historical,
            "projection_months": projection_months,
        }

        # Generate scenario with LLM
        scenario = await llm.generate_scenario(
            system_prompt=SCENARIO_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            context=context,
        )

        # Calculate simulated KPIs from projections
        projections = scenario.get("projections", [])
        if projections:
            total_revenue = sum(p.get("projected_revenue", 0) for p in projections)
            total_expenses = sum(p.get("projected_expenses", 0) for p in projections)
            total_profit = total_revenue - total_expenses

            avg_monthly_revenue = total_revenue / len(projections)
            avg_monthly_profit = total_profit / len(projections)

            profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

            simulated_kpis = {
                "period_months": len(projections),
                "total_revenue": round(total_revenue, 2),
                "total_expenses": round(total_expenses, 2),
                "total_profit": round(total_profit, 2),
                "avg_monthly_revenue": round(avg_monthly_revenue, 2),
                "avg_monthly_profit": round(avg_monthly_profit, 2),
                "projected_profit_margin": round(profit_margin, 2),
                "revenue_growth_from_current": round(
                    ((projections[-1].get("projected_revenue", 0) /
                      max(1, historical["current_state"]["latest_month_revenue"])) - 1) * 100,
                    2
                ) if historical["current_state"]["latest_month_revenue"] > 0 else 0,
            }
        else:
            simulated_kpis = {}

        return {
            "user_prompt": user_prompt,
            "historical_context": historical,
            "scenario": scenario,
            "simulated_kpis": simulated_kpis,
        }

    async def compare_scenarios(
        self,
        prompts: List[str],
        projection_months: int = 6,
    ) -> Dict[str, Any]:
        """
        Generate and compare multiple scenarios.

        Args:
            prompts: List of scenario descriptions to compare
            projection_months: Projection period

        Returns:
            Comparison of all scenarios
        """
        scenarios = []
        for prompt in prompts:
            result = await self.simulate_scenario(prompt, projection_months)
            scenarios.append(result)

        # Find best/worst scenarios
        if scenarios:
            by_profit = sorted(
                scenarios,
                key=lambda s: s.get("simulated_kpis", {}).get("total_profit", 0),
                reverse=True
            )
            best = by_profit[0] if by_profit else None
            worst = by_profit[-1] if len(by_profit) > 1 else None
        else:
            best = None
            worst = None

        return {
            "scenarios": scenarios,
            "comparison": {
                "count": len(scenarios),
                "best_scenario": best["scenario"]["scenario_name"] if best else None,
                "worst_scenario": worst["scenario"]["scenario_name"] if worst and worst != best else None,
                "profit_range": {
                    "min": min(s.get("simulated_kpis", {}).get("total_profit", 0) for s in scenarios) if scenarios else 0,
                    "max": max(s.get("simulated_kpis", {}).get("total_profit", 0) for s in scenarios) if scenarios else 0,
                },
            },
        }
