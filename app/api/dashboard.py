"""API endpoints for customizable dashboards."""

from typing import Optional, List, Dict, Any
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.services.financial_service import FinancialService
from app.services.alert_service import AlertService

router = APIRouter()


class WidgetConfig(BaseModel):
    """Widget configuration."""
    widget_type: str
    title: Optional[str] = None
    params: Optional[dict] = None


class DashboardConfig(BaseModel):
    """Dashboard configuration."""
    name: str
    widgets: List[WidgetConfig]


class KPIWidget(BaseModel):
    """KPI widget data."""
    label: str
    value: float
    formatted_value: str
    change_percent: Optional[float] = None
    trend: Optional[str] = None  # up, down, stable


class ChartDataPoint(BaseModel):
    """Chart data point."""
    label: str
    value: float


class ChartWidget(BaseModel):
    """Chart widget data."""
    title: str
    chart_type: str  # bar, line, pie
    data: List[ChartDataPoint]


class AlertWidget(BaseModel):
    """Alert widget data."""
    total: int
    critical: int
    warning: int
    info: int
    recent: List[dict]


class DashboardResponse(BaseModel):
    """Full dashboard response."""
    name: str
    generated_at: str
    widgets: Dict[str, Any]


@router.get("/overview")
async def get_dashboard_overview(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get default dashboard overview with key metrics.

    Returns a pre-configured dashboard with:
    - Revenue, Expenses, Profit KPIs
    - Monthly trend chart
    - Top projects by revenue
    - Active alerts summary
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - relativedelta(months=6)

    financial = FinancialService(db)
    alert_service = AlertService(db)

    # Calculate KPIs
    total_revenue = await financial.get_total_revenue(start_date, end_date)
    total_expenses = await financial.get_total_expenses(start_date, end_date)
    total_profit = total_revenue - total_expenses
    margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    # Get previous period for comparison
    prev_end = start_date - relativedelta(days=1)
    prev_start = prev_end - relativedelta(months=6)
    prev_revenue = await financial.get_total_revenue(prev_start, prev_end)
    prev_expenses = await financial.get_total_expenses(prev_start, prev_end)
    prev_profit = prev_revenue - prev_expenses

    revenue_change = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    expense_change = ((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
    profit_change = ((total_profit - prev_profit) / abs(prev_profit) * 100) if prev_profit != 0 else 0

    # Get alert summary
    alert_summary = await alert_service.get_alert_summary()

    # Get active alerts
    active_alerts = await alert_service.get_active_alerts()

    return {
        "name": "Overview Dashboard",
        "generated_at": datetime.utcnow().isoformat(),
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "kpis": {
            "revenue": {
                "label": "Total Revenue",
                "value": float(total_revenue),
                "formatted": f"€{total_revenue:,.2f}",
                "change_percent": round(float(revenue_change), 1),
                "trend": "up" if revenue_change > 0 else "down" if revenue_change < 0 else "stable",
            },
            "expenses": {
                "label": "Total Expenses",
                "value": float(total_expenses),
                "formatted": f"€{total_expenses:,.2f}",
                "change_percent": round(float(expense_change), 1),
                "trend": "up" if expense_change > 0 else "down" if expense_change < 0 else "stable",
            },
            "profit": {
                "label": "Net Profit",
                "value": float(total_profit),
                "formatted": f"€{total_profit:,.2f}",
                "change_percent": round(float(profit_change), 1),
                "trend": "up" if profit_change > 0 else "down" if profit_change < 0 else "stable",
            },
            "margin": {
                "label": "Profit Margin",
                "value": float(margin),
                "formatted": f"{margin:.1f}%",
            },
        },
        "alerts": {
            "summary": alert_summary,
            "recent": [
                {
                    "id": a.id,
                    "type": a.alert_type.value,
                    "severity": a.severity.value,
                    "title": a.title,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in active_alerts[:5]
            ],
        },
    }


@router.get("/projects")
async def get_projects_dashboard(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Get project-focused dashboard.

    Returns:
    - Top projects by revenue
    - Top projects by profitability
    - Projects at risk (low margin)
    - Budget utilization
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - relativedelta(months=3)

    financial = FinancialService(db)

    # Get all projects summary
    projects_summary = await financial.get_all_projects_summary(start_date, end_date)

    # Sort by different metrics
    by_revenue = sorted(
        projects_summary,
        key=lambda p: p.get('revenue', 0),
        reverse=True
    )[:limit]

    by_profit = sorted(
        projects_summary,
        key=lambda p: p.get('profit', 0),
        reverse=True
    )[:limit]

    at_risk = [
        p for p in projects_summary
        if p.get('revenue', 0) > 0 and p.get('margin', 0) < 15
    ]

    return {
        "name": "Projects Dashboard",
        "generated_at": datetime.utcnow().isoformat(),
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "total_projects": len(projects_summary),
        "top_by_revenue": by_revenue,
        "top_by_profit": by_profit,
        "at_risk": at_risk,
        "summary": {
            "total_revenue": sum(p.get('revenue', 0) for p in projects_summary),
            "total_expenses": sum(p.get('expenses', 0) for p in projects_summary),
            "total_profit": sum(p.get('profit', 0) for p in projects_summary),
        },
    }


@router.get("/clients")
async def get_clients_dashboard(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Get client-focused dashboard.

    Returns:
    - Top clients by revenue
    - Client concentration metrics
    - Client profitability ranking
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - relativedelta(months=6)

    financial = FinancialService(db)

    # Get all clients summary
    clients_summary = await financial.get_all_clients_summary(start_date, end_date)

    # Sort by revenue
    by_revenue = sorted(
        clients_summary,
        key=lambda c: c.get('revenue', 0),
        reverse=True
    )

    total_revenue = sum(c.get('revenue', 0) for c in clients_summary)

    # Calculate concentration (top client as % of total)
    top_client_percent = 0
    top_3_percent = 0
    if total_revenue > 0 and by_revenue:
        top_client_percent = by_revenue[0].get('revenue', 0) / total_revenue * 100
        top_3_percent = sum(c.get('revenue', 0) for c in by_revenue[:3]) / total_revenue * 100

    return {
        "name": "Clients Dashboard",
        "generated_at": datetime.utcnow().isoformat(),
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "total_clients": len(clients_summary),
        "top_by_revenue": by_revenue[:limit],
        "concentration": {
            "top_client_percent": round(top_client_percent, 1),
            "top_3_percent": round(top_3_percent, 1),
            "is_concentrated": top_client_percent > 40,  # Risk if > 40% from one client
        },
        "summary": {
            "total_revenue": total_revenue,
            "avg_revenue_per_client": total_revenue / len(clients_summary) if clients_summary else 0,
        },
    }


@router.post("/custom")
async def get_custom_dashboard(
    config: DashboardConfig,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a custom dashboard based on provided configuration.

    Available widget types:
    - kpi_revenue, kpi_expenses, kpi_profit, kpi_margin
    - chart_monthly_trend
    - chart_project_revenue
    - chart_expense_breakdown
    - list_top_projects
    - list_active_alerts
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - relativedelta(months=6)

    financial = FinancialService(db)
    alert_service = AlertService(db)

    widgets_data = {}

    for widget in config.widgets:
        widget_id = widget.title or widget.widget_type

        if widget.widget_type.startswith("kpi_"):
            # KPI widgets
            if widget.widget_type == "kpi_revenue":
                value = await financial.get_total_revenue(start_date, end_date)
                widgets_data[widget_id] = {
                    "type": "kpi",
                    "label": "Revenue",
                    "value": float(value),
                    "formatted": f"€{value:,.2f}",
                }
            elif widget.widget_type == "kpi_expenses":
                value = await financial.get_total_expenses(start_date, end_date)
                widgets_data[widget_id] = {
                    "type": "kpi",
                    "label": "Expenses",
                    "value": float(value),
                    "formatted": f"€{value:,.2f}",
                }
            elif widget.widget_type == "kpi_profit":
                revenue = await financial.get_total_revenue(start_date, end_date)
                expenses = await financial.get_total_expenses(start_date, end_date)
                profit = revenue - expenses
                widgets_data[widget_id] = {
                    "type": "kpi",
                    "label": "Profit",
                    "value": float(profit),
                    "formatted": f"€{profit:,.2f}",
                }

        elif widget.widget_type == "list_active_alerts":
            alerts = await alert_service.get_active_alerts()
            widgets_data[widget_id] = {
                "type": "list",
                "items": [
                    {
                        "id": a.id,
                        "title": a.title,
                        "severity": a.severity.value,
                    }
                    for a in alerts[:10]
                ],
            }

    return {
        "name": config.name,
        "generated_at": datetime.utcnow().isoformat(),
        "widgets": widgets_data,
    }
