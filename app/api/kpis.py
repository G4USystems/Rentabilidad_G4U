"""API endpoints for KPIs."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.reports import (
    KPIResponse,
    ProjectKPIResponse,
    ProjectsKPISummary,
    TrendResponse,
    ReportPeriod,
)
from app.services.kpi_service import KPIService

router = APIRouter()


@router.get("/global", response_model=KPIResponse)
async def get_global_kpis(
    start_date: date,
    end_date: date,
    currency: str = "EUR",
    db: AsyncSession = Depends(get_db),
):
    """
    Get global KPIs for the organization.

    Includes:
    - Revenue metrics (total, daily average, growth)
    - Profitability metrics (gross margin, net margin, EBITDA)
    - Expense metrics (total, ratios, burn rate)
    - Activity metrics (transaction counts)
    - Category breakdowns
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date"
        )

    service = KPIService(db)
    kpis = await service.get_global_kpis(start_date, end_date, currency)

    return kpis


@router.get("/projects", response_model=ProjectsKPISummary)
async def get_all_projects_kpis(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Get KPIs for all projects.

    Returns summary with totals and individual project KPIs.
    Includes best/worst performers.
    """
    service = KPIService(db)
    summary = await service.get_all_projects_kpis(
        start_date=start_date,
        end_date=end_date,
        include_inactive=include_inactive,
    )

    return summary


@router.get("/projects/{project_id}", response_model=ProjectKPIResponse)
async def get_project_kpis(
    project_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get KPIs for a specific project.

    Includes:
    - Financial metrics (revenue, expenses, profit, margin)
    - ROI and contribution margin
    - Budget metrics (used, remaining, variance)
    - Contract metrics (actual vs contract value)
    - Activity metrics
    """
    service = KPIService(db)
    kpis = await service.get_project_kpis(project_id, start_date, end_date)

    if not kpis:
        raise HTTPException(status_code=404, detail="Project not found")

    return kpis


@router.get("/trends/{metric}", response_model=TrendResponse)
async def get_kpi_trends(
    metric: str,
    period_type: ReportPeriod = ReportPeriod.MONTHLY,
    periods: int = Query(12, ge=1, le=60),
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get trend data for a specific metric.

    Available metrics:
    - revenue
    - expenses
    - net_profit
    - gross_margin
    - net_margin

    Args:
        metric: Metric to analyze
        period_type: monthly, quarterly, or yearly
        periods: Number of periods to include
        end_date: End date for analysis
    """
    valid_metrics = ["revenue", "expenses", "net_profit", "gross_margin", "net_margin"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric. Must be one of: {valid_metrics}"
        )

    service = KPIService(db)
    trends = await service.get_trends(
        metric=metric,
        period_type=period_type,
        periods=periods,
        end_date=end_date,
    )

    return trends


@router.get("/dashboard")
async def get_dashboard_kpis(
    db: AsyncSession = Depends(get_db),
):
    """
    Get KPIs optimized for dashboard display.

    Returns current month, previous month, and YTD metrics.
    """
    from datetime import date
    from calendar import monthrange

    today = date.today()

    # Current month
    current_month_start = today.replace(day=1)
    _, last_day = monthrange(today.year, today.month)
    current_month_end = today.replace(day=last_day)

    # Previous month
    if today.month == 1:
        prev_month_start = date(today.year - 1, 12, 1)
        prev_month_end = date(today.year - 1, 12, 31)
    else:
        prev_month_start = date(today.year, today.month - 1, 1)
        _, last_day = monthrange(today.year, today.month - 1)
        prev_month_end = date(today.year, today.month - 1, last_day)

    # Year to date
    ytd_start = date(today.year, 1, 1)
    ytd_end = today

    service = KPIService(db)

    current_month = await service.get_global_kpis(current_month_start, current_month_end)
    previous_month = await service.get_global_kpis(prev_month_start, prev_month_end)
    year_to_date = await service.get_global_kpis(ytd_start, ytd_end)

    # Calculate MoM changes
    revenue_change = None
    if previous_month.total_revenue > 0:
        revenue_change = (
            (current_month.total_revenue - previous_month.total_revenue)
            / previous_month.total_revenue
            * 100
        )

    expense_change = None
    if previous_month.total_expenses > 0:
        expense_change = (
            (current_month.total_expenses - previous_month.total_expenses)
            / previous_month.total_expenses
            * 100
        )

    return {
        "current_month": {
            "period": f"{current_month_start} - {current_month_end}",
            "revenue": float(current_month.total_revenue),
            "expenses": float(current_month.total_expenses),
            "net_profit": float(current_month.net_profit),
            "net_margin": float(current_month.net_margin),
            "gross_margin": float(current_month.gross_margin),
            "ebitda": float(current_month.ebitda),
            "transactions": current_month.total_transactions,
        },
        "previous_month": {
            "period": f"{prev_month_start} - {prev_month_end}",
            "revenue": float(previous_month.total_revenue),
            "expenses": float(previous_month.total_expenses),
            "net_profit": float(previous_month.net_profit),
            "net_margin": float(previous_month.net_margin),
        },
        "month_over_month": {
            "revenue_change": float(revenue_change) if revenue_change else None,
            "expense_change": float(expense_change) if expense_change else None,
        },
        "year_to_date": {
            "period": f"{ytd_start} - {ytd_end}",
            "revenue": float(year_to_date.total_revenue),
            "expenses": float(year_to_date.total_expenses),
            "net_profit": float(year_to_date.net_profit),
            "net_margin": float(year_to_date.net_margin),
            "gross_margin": float(year_to_date.gross_margin),
            "burn_rate": float(year_to_date.burn_rate),
        },
        "top_expenses": current_month.top_expense_categories[:5],
        "top_revenue": current_month.top_revenue_sources[:5],
    }


@router.get("/comparison")
async def compare_periods(
    period1_start: date,
    period1_end: date,
    period2_start: date,
    period2_end: date,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare KPIs between two periods.

    Useful for year-over-year or month-over-month analysis.
    """
    service = KPIService(db)

    period1 = await service.get_global_kpis(period1_start, period1_end)
    period2 = await service.get_global_kpis(period2_start, period2_end)

    def calc_change(new, old):
        if old == 0:
            return None
        return float((new - old) / abs(old) * 100)

    return {
        "period1": {
            "dates": f"{period1_start} - {period1_end}",
            "revenue": float(period1.total_revenue),
            "expenses": float(period1.total_expenses),
            "net_profit": float(period1.net_profit),
            "net_margin": float(period1.net_margin),
            "gross_margin": float(period1.gross_margin),
        },
        "period2": {
            "dates": f"{period2_start} - {period2_end}",
            "revenue": float(period2.total_revenue),
            "expenses": float(period2.total_expenses),
            "net_profit": float(period2.net_profit),
            "net_margin": float(period2.net_margin),
            "gross_margin": float(period2.gross_margin),
        },
        "changes": {
            "revenue": calc_change(period1.total_revenue, period2.total_revenue),
            "expenses": calc_change(period1.total_expenses, period2.total_expenses),
            "net_profit": calc_change(period1.net_profit, period2.net_profit),
            "net_margin_diff": float(period1.net_margin - period2.net_margin),
            "gross_margin_diff": float(period1.gross_margin - period2.gross_margin),
        },
    }
