"""Forecasting service based on historical trends."""

from datetime import date
from decimal import Decimal
from typing import Dict, Any, List, Optional
import logging

from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.financial_service import FinancialService
from app.services.scenario_service import ScenarioService

logger = logging.getLogger(__name__)


class ForecastingService:
    """Service for trend-based forecasting integrated with scenario simulator."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.financial = FinancialService(db)
        self.scenario_service = ScenarioService(db)

    async def get_historical_trends(
        self,
        months: int = 12,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Analyze historical trends for forecasting.

        Returns:
        - Monthly data for the period
        - Growth rates (revenue, expenses)
        - Seasonality patterns
        - Trend direction
        """
        if not end_date:
            end_date = date.today()

        start_date = end_date - relativedelta(months=months)

        # Get monthly data
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
                "margin": float((revenue - expenses) / revenue * 100) if revenue > 0 else 0,
            })

            current = current + relativedelta(months=1)

        # Calculate trends
        if len(monthly_data) >= 2:
            first_half = monthly_data[:len(monthly_data)//2]
            second_half = monthly_data[len(monthly_data)//2:]

            avg_first_revenue = sum(m["revenue"] for m in first_half) / len(first_half)
            avg_second_revenue = sum(m["revenue"] for m in second_half) / len(second_half)

            avg_first_expenses = sum(m["expenses"] for m in first_half) / len(first_half)
            avg_second_expenses = sum(m["expenses"] for m in second_half) / len(second_half)

            revenue_trend = "growing" if avg_second_revenue > avg_first_revenue * 1.05 else \
                           "declining" if avg_second_revenue < avg_first_revenue * 0.95 else "stable"
            expense_trend = "growing" if avg_second_expenses > avg_first_expenses * 1.05 else \
                           "declining" if avg_second_expenses < avg_first_expenses * 0.95 else "stable"
        else:
            revenue_trend = "insufficient_data"
            expense_trend = "insufficient_data"

        # Calculate seasonality (compare same month across years)
        seasonality = self._detect_seasonality(monthly_data)

        # Calculate compound monthly growth rate (CMGR)
        if len(monthly_data) >= 2 and monthly_data[0]["revenue"] > 0:
            months_diff = len(monthly_data) - 1
            end_val = monthly_data[-1]["revenue"]
            start_val = monthly_data[0]["revenue"]
            cmgr = ((end_val / start_val) ** (1 / months_diff) - 1) * 100
        else:
            cmgr = 0

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "months": months,
            },
            "monthly_data": monthly_data,
            "trends": {
                "revenue": revenue_trend,
                "expenses": expense_trend,
                "monthly_growth_rate": round(cmgr, 2),
            },
            "seasonality": seasonality,
            "averages": {
                "avg_monthly_revenue": sum(m["revenue"] for m in monthly_data) / len(monthly_data) if monthly_data else 0,
                "avg_monthly_expenses": sum(m["expenses"] for m in monthly_data) / len(monthly_data) if monthly_data else 0,
                "avg_monthly_profit": sum(m["profit"] for m in monthly_data) / len(monthly_data) if monthly_data else 0,
            },
        }

    def _detect_seasonality(self, monthly_data: List[Dict]) -> Dict[str, Any]:
        """Detect seasonality patterns in monthly data."""
        if len(monthly_data) < 12:
            return {"detected": False, "reason": "Need at least 12 months of data"}

        # Group by month of year
        by_month = {}
        for m in monthly_data:
            month_num = int(m["month"].split("-")[1])
            if month_num not in by_month:
                by_month[month_num] = []
            by_month[month_num].append(m["revenue"])

        # Calculate average for each month
        monthly_averages = {k: sum(v)/len(v) for k, v in by_month.items()}
        overall_avg = sum(monthly_averages.values()) / len(monthly_averages)

        # Find high and low months
        high_months = [k for k, v in monthly_averages.items() if v > overall_avg * 1.2]
        low_months = [k for k, v in monthly_averages.items() if v < overall_avg * 0.8]

        return {
            "detected": bool(high_months or low_months),
            "high_months": high_months,
            "low_months": low_months,
            "monthly_factors": {k: round(v / overall_avg, 2) for k, v in monthly_averages.items()},
        }

    async def generate_forecast(
        self,
        projection_months: int = 6,
        scenario: str = "baseline",
        use_seasonality: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate forecast based on historical trends.

        Scenarios:
        - baseline: Continue current trends
        - optimistic: +20% growth adjustment
        - pessimistic: -20% growth adjustment
        - custom: Use scenario simulator with AI
        """
        # Get historical trends
        trends = await self.get_historical_trends(months=12)

        base_revenue = trends["averages"]["avg_monthly_revenue"]
        base_expenses = trends["averages"]["avg_monthly_expenses"]
        monthly_growth = trends["trends"]["monthly_growth_rate"] / 100

        # Adjust for scenario
        if scenario == "optimistic":
            monthly_growth = monthly_growth + 0.02  # +2% per month extra
            expense_growth = monthly_growth * 0.5  # Expenses grow slower
        elif scenario == "pessimistic":
            monthly_growth = monthly_growth - 0.02  # -2% per month
            expense_growth = monthly_growth + 0.01  # Expenses still grow
        else:  # baseline
            expense_growth = monthly_growth * 0.8  # Expenses grow at 80% of revenue growth

        # Generate projections
        projections = []
        current_date = date.today().replace(day=1)
        current_revenue = base_revenue
        current_expenses = base_expenses

        seasonality = trends["seasonality"]

        for i in range(projection_months):
            month = current_date + relativedelta(months=i)
            month_num = month.month

            # Apply growth
            current_revenue = current_revenue * (1 + monthly_growth)
            current_expenses = current_expenses * (1 + expense_growth)

            # Apply seasonality if enabled and detected
            if use_seasonality and seasonality.get("detected"):
                factor = seasonality.get("monthly_factors", {}).get(month_num, 1.0)
                adjusted_revenue = current_revenue * factor
            else:
                adjusted_revenue = current_revenue

            projections.append({
                "month": month.strftime("%Y-%m"),
                "projected_revenue": round(adjusted_revenue, 2),
                "projected_expenses": round(current_expenses, 2),
                "projected_profit": round(adjusted_revenue - current_expenses, 2),
                "projected_margin": round((adjusted_revenue - current_expenses) / adjusted_revenue * 100, 1) if adjusted_revenue > 0 else 0,
            })

        # Summary
        total_revenue = sum(p["projected_revenue"] for p in projections)
        total_expenses = sum(p["projected_expenses"] for p in projections)
        total_profit = total_revenue - total_expenses

        return {
            "scenario": scenario,
            "projection_months": projection_months,
            "based_on_historical_months": 12,
            "assumptions": {
                "monthly_revenue_growth": round(monthly_growth * 100, 2),
                "monthly_expense_growth": round(expense_growth * 100, 2),
                "seasonality_applied": use_seasonality and seasonality.get("detected", False),
            },
            "projections": projections,
            "summary": {
                "total_projected_revenue": round(total_revenue, 2),
                "total_projected_expenses": round(total_expenses, 2),
                "total_projected_profit": round(total_profit, 2),
                "avg_monthly_profit": round(total_profit / projection_months, 2),
                "end_monthly_revenue": projections[-1]["projected_revenue"] if projections else 0,
            },
            "historical_context": trends,
        }

    async def compare_forecast_scenarios(
        self,
        projection_months: int = 6,
    ) -> Dict[str, Any]:
        """Compare all three scenarios side by side."""
        baseline = await self.generate_forecast(projection_months, "baseline")
        optimistic = await self.generate_forecast(projection_months, "optimistic")
        pessimistic = await self.generate_forecast(projection_months, "pessimistic")

        return {
            "projection_months": projection_months,
            "scenarios": {
                "baseline": baseline,
                "optimistic": optimistic,
                "pessimistic": pessimistic,
            },
            "comparison": {
                "profit_range": {
                    "min": pessimistic["summary"]["total_projected_profit"],
                    "max": optimistic["summary"]["total_projected_profit"],
                    "baseline": baseline["summary"]["total_projected_profit"],
                },
                "revenue_range": {
                    "min": pessimistic["summary"]["total_projected_revenue"],
                    "max": optimistic["summary"]["total_projected_revenue"],
                    "baseline": baseline["summary"]["total_projected_revenue"],
                },
            },
        }

    async def forecast_with_ai(
        self,
        projection_months: int = 6,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate forecast using AI scenario simulator.

        This integrates with the existing scenario service for
        more sophisticated projections.
        """
        prompt = custom_prompt or (
            f"Generate a realistic {projection_months}-month forecast based on "
            "historical trends. Consider seasonality and market conditions."
        )

        result = await self.scenario_service.simulate_scenario(
            user_prompt=prompt,
            projection_months=projection_months,
        )

        return {
            "type": "ai_forecast",
            "prompt": prompt,
            "result": result,
        }
