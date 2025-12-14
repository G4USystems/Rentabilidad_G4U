"""Service for calculating KPIs."""

from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from dateutil.relativedelta import relativedelta

from app.models.transaction import Transaction, TransactionSide
from app.models.category import Category, CategoryType
from app.models.project import Project, ProjectStatus
from app.schemas.reports import (
    KPIResponse,
    ProjectKPIResponse,
    ProjectsKPISummary,
    TrendDataPoint,
    TrendResponse,
    ReportPeriod,
)
from app.services.financial_service import FinancialService

logger = logging.getLogger(__name__)


class KPIService:
    """Service for calculating business KPIs."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.financial = FinancialService(db)

    async def get_global_kpis(
        self,
        start_date: date,
        end_date: date,
        currency: str = "EUR",
    ) -> KPIResponse:
        """
        Calculate global KPIs for the organization.

        Args:
            start_date: Period start
            end_date: Period end
            currency: Currency code

        Returns:
            Global KPIs
        """
        # Get financial calculations
        financials = await self.financial.calculate_net_income(start_date, end_date)
        counts = await self.financial.get_transaction_counts(start_date, end_date)

        # Calculate derived metrics
        total_revenue = financials["revenue"]
        total_expenses = (
            financials["cogs"]
            + financials["operating_expenses"]
            + financials["interest"]
            + financials["taxes"]
            + financials["other_expenses"]
        )

        # Days in period
        days = (end_date - start_date).days + 1
        revenue_per_day = total_revenue / days if days > 0 else Decimal("0")

        # Average transaction value
        avg_transaction = (
            total_revenue / counts["income"]
            if counts["income"] > 0
            else Decimal("0")
        )

        # Expense ratio
        expense_ratio = self._calculate_ratio(total_expenses, total_revenue)
        operating_expense_ratio = self._calculate_ratio(
            financials["operating_expenses"], total_revenue
        )

        # Burn rate (monthly)
        burn_rate = await self.financial.calculate_burn_rate(months=3, end_date=end_date)

        # Get category breakdowns
        expense_breakdown = await self.financial.get_breakdown_by_category(
            start_date, end_date, TransactionSide.DEBIT
        )
        revenue_breakdown = await self.financial.get_breakdown_by_category(
            start_date, end_date, TransactionSide.CREDIT
        )

        # Format breakdowns
        expense_by_category = {
            item["category_name"]: float(item["total"])
            for item in expense_breakdown
        }
        revenue_by_category = {
            item["category_name"]: float(item["total"])
            for item in revenue_breakdown
        }

        # Top 5 items
        top_expenses = sorted(expense_breakdown, key=lambda x: x["total"], reverse=True)[:5]
        top_revenue = sorted(revenue_breakdown, key=lambda x: x["total"], reverse=True)[:5]

        return KPIResponse(
            start_date=start_date,
            end_date=end_date,
            currency=currency,
            # Revenue metrics
            total_revenue=total_revenue,
            average_transaction_value=self._round(avg_transaction),
            revenue_per_day=self._round(revenue_per_day),
            # Profitability
            gross_profit=financials["gross_profit"],
            gross_margin=financials["gross_margin"],
            net_profit=financials["net_income"],
            net_margin=financials["net_margin"],
            operating_margin=financials["operating_margin"],
            # EBITDA
            ebitda=financials["ebitda"],
            ebitda_margin=financials["ebitda_margin"],
            # Expenses
            total_expenses=total_expenses,
            expense_ratio=expense_ratio,
            operating_expense_ratio=operating_expense_ratio,
            # Cash flow
            burn_rate=burn_rate,
            runway_months=None,  # Would need cash balance
            # Activity
            total_transactions=counts["total"],
            income_transactions=counts["income"],
            expense_transactions=counts["expense"],
            # Breakdowns
            expense_by_category=expense_by_category,
            revenue_by_category=revenue_by_category,
            top_expense_categories=top_expenses,
            top_revenue_sources=top_revenue,
        )

    async def get_project_kpis(
        self,
        project_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[ProjectKPIResponse]:
        """
        Calculate KPIs for a specific project.

        Args:
            project_id: Project ID
            start_date: Optional period start
            end_date: Optional period end

        Returns:
            Project KPIs or None if project not found
        """
        # Get project
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            return None

        # Use project dates if not specified
        if start_date is None:
            start_date = project.start_date or date(2020, 1, 1)
        if end_date is None:
            end_date = project.end_date or date.today()

        # Get financial data
        total_revenue = await self.financial.get_total_revenue(
            start_date, end_date, project_id
        )
        total_expenses = await self.financial.get_total_expenses(
            start_date, end_date, project_id
        )
        counts = await self.financial.get_transaction_counts(
            start_date, end_date, project_id
        )

        net_profit = total_revenue - total_expenses
        profit_margin = self._calculate_ratio(net_profit, total_revenue)

        # ROI
        roi = self._calculate_ratio(net_profit, total_expenses) if total_expenses > 0 else None

        # Budget metrics
        budget_used = total_expenses
        budget_remaining = None
        budget_used_percentage = None
        budget_variance = None

        if project.budget_amount:
            budget_remaining = project.budget_amount - total_expenses
            budget_used_percentage = self._calculate_ratio(
                total_expenses, project.budget_amount
            )
            budget_variance = project.budget_amount - total_expenses

        # Contract metrics
        revenue_vs_contract = None
        if project.contract_value:
            revenue_vs_contract = self._calculate_ratio(
                total_revenue, project.contract_value
            )

        # Duration
        project_duration = None
        revenue_per_day = None
        if project.start_date:
            end = project.end_date or date.today()
            project_duration = (end - project.start_date).days
            if project_duration > 0:
                revenue_per_day = total_revenue / project_duration

        # Average expense
        avg_expense = (
            total_expenses / counts["expense"]
            if counts["expense"] > 0
            else Decimal("0")
        )

        return ProjectKPIResponse(
            project_id=project.id,
            project_name=project.name,
            project_code=project.code,
            client_name=project.client_name,
            start_date=start_date,
            end_date=end_date,
            currency=project.budget_currency,
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            net_profit=net_profit,
            profit_margin=profit_margin,
            roi=roi,
            contribution_margin=net_profit,  # Simplified
            budget_amount=project.budget_amount,
            budget_used=budget_used,
            budget_remaining=budget_remaining,
            budget_used_percentage=budget_used_percentage,
            budget_variance=budget_variance,
            contract_value=project.contract_value,
            revenue_vs_contract=revenue_vs_contract,
            transaction_count=counts["total"],
            income_count=counts["income"],
            expense_count=counts["expense"],
            average_expense=self._round(avg_expense),
            project_duration_days=project_duration,
            revenue_per_day=self._round(revenue_per_day) if revenue_per_day else None,
        )

    async def get_all_projects_kpis(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_inactive: bool = False,
    ) -> ProjectsKPISummary:
        """
        Get KPIs for all projects.

        Args:
            start_date: Period start
            end_date: Period end
            include_inactive: Include inactive projects

        Returns:
            Summary with all project KPIs
        """
        # Get projects
        query = select(Project)
        if not include_inactive:
            query = query.where(Project.is_active == True)

        result = await self.db.execute(query)
        projects = result.scalars().all()

        # Calculate KPIs for each project
        project_kpis = []
        total_revenue = Decimal("0")
        total_expenses = Decimal("0")
        total_profit = Decimal("0")

        active_count = 0
        completed_count = 0

        for project in projects:
            kpi = await self.get_project_kpis(project.id, start_date, end_date)
            if kpi:
                project_kpis.append(kpi)
                total_revenue += kpi.total_revenue
                total_expenses += kpi.total_expenses
                total_profit += kpi.net_profit

                if project.status == ProjectStatus.ACTIVE:
                    active_count += 1
                elif project.status == ProjectStatus.COMPLETED:
                    completed_count += 1

        # Find best/worst performers
        if project_kpis:
            sorted_by_profit = sorted(
                project_kpis,
                key=lambda x: x.net_profit,
                reverse=True
            )
            most_profitable = sorted_by_profit[0] if sorted_by_profit else None
            least_profitable = sorted_by_profit[-1] if sorted_by_profit else None

            sorted_by_revenue = sorted(
                project_kpis,
                key=lambda x: x.total_revenue,
                reverse=True
            )
            highest_revenue = sorted_by_revenue[0] if sorted_by_revenue else None
        else:
            most_profitable = None
            least_profitable = None
            highest_revenue = None

        # Average margin
        avg_margin = Decimal("0")
        if project_kpis:
            margins = [p.profit_margin for p in project_kpis if p.profit_margin]
            if margins:
                avg_margin = sum(margins) / len(margins)

        return ProjectsKPISummary(
            total_projects=len(projects),
            active_projects=active_count,
            completed_projects=completed_count,
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            total_profit=total_profit,
            average_profit_margin=self._round(avg_margin),
            most_profitable_project=most_profitable,
            least_profitable_project=least_profitable,
            highest_revenue_project=highest_revenue,
            projects=project_kpis,
        )

    async def get_trends(
        self,
        metric: str,
        period_type: ReportPeriod,
        periods: int = 12,
        end_date: Optional[date] = None,
    ) -> TrendResponse:
        """
        Get trend data for a specific metric.

        Args:
            metric: Metric name (revenue, expenses, net_profit, etc.)
            period_type: Period granularity
            periods: Number of periods
            end_date: End date

        Returns:
            Trend data
        """
        if end_date is None:
            end_date = date.today()

        data_points = []

        for i in range(periods - 1, -1, -1):
            if period_type == ReportPeriod.MONTHLY:
                period_end = end_date - relativedelta(months=i)
                period_start = period_end.replace(day=1)
                period_end = (period_start + relativedelta(months=1)) - relativedelta(days=1)
                period_label = period_start.strftime("%Y-%m")
            elif period_type == ReportPeriod.QUARTERLY:
                period_end = end_date - relativedelta(months=i * 3)
                quarter = (period_end.month - 1) // 3
                period_start = date(period_end.year, quarter * 3 + 1, 1)
                period_end = period_start + relativedelta(months=3) - relativedelta(days=1)
                period_label = f"Q{quarter + 1} {period_start.year}"
            else:  # Yearly
                period_end = end_date - relativedelta(years=i)
                period_start = date(period_end.year, 1, 1)
                period_end = date(period_end.year, 12, 31)
                period_label = str(period_start.year)

            # Get data for period
            revenue = await self.financial.get_total_revenue(period_start, period_end)
            expenses = await self.financial.get_total_expenses(period_start, period_end)
            counts = await self.financial.get_transaction_counts(period_start, period_end)

            net_profit = revenue - expenses
            gross_margin = self._calculate_ratio(revenue - expenses, revenue)
            net_margin = self._calculate_ratio(net_profit, revenue)

            data_points.append(
                TrendDataPoint(
                    period=period_label,
                    start_date=period_start,
                    end_date=period_end,
                    revenue=revenue,
                    expenses=expenses,
                    net_profit=net_profit,
                    gross_margin=gross_margin,
                    net_margin=net_margin,
                    transaction_count=counts["total"],
                )
            )

        # Calculate trend statistics
        values = [
            getattr(dp, metric) if hasattr(dp, metric) else dp.net_profit
            for dp in data_points
        ]

        if values:
            avg_value = sum(values) / len(values)
            min_value = min(values)
            max_value = max(values)

            # Growth rate (first to last)
            if len(values) >= 2 and values[0] != 0:
                growth_rate = ((values[-1] - values[0]) / abs(values[0])) * 100
            else:
                growth_rate = None

            # Trend direction
            if len(values) >= 2:
                if values[-1] > values[-2]:
                    trend_direction = "up"
                elif values[-1] < values[-2]:
                    trend_direction = "down"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "stable"
        else:
            avg_value = Decimal("0")
            min_value = Decimal("0")
            max_value = Decimal("0")
            growth_rate = None
            trend_direction = "stable"

        return TrendResponse(
            metric=metric,
            period_type=period_type,
            data_points=data_points,
            trend_direction=trend_direction,
            average_value=self._round(avg_value),
            min_value=self._round(min_value),
            max_value=self._round(max_value),
            growth_rate=self._round(Decimal(str(growth_rate))) if growth_rate else None,
        )

    def _calculate_ratio(self, numerator: Decimal, denominator: Decimal) -> Decimal:
        """Calculate ratio as percentage."""
        if denominator == 0:
            return Decimal("0")
        return ((numerator / denominator) * 100).quantize(Decimal("0.01"))

    def _round(self, value: Optional[Decimal], places: int = 2) -> Decimal:
        """Round decimal value."""
        if value is None:
            return Decimal("0")
        return value.quantize(Decimal(10) ** -places)
