"""Report schemas for P&L and KPIs."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict
from enum import Enum

from pydantic import BaseModel, Field


class ReportPeriod(str, Enum):
    """Report period options."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class PLReportRequest(BaseModel):
    """Request schema for P&L report generation."""

    start_date: date
    end_date: date
    period: ReportPeriod = ReportPeriod.MONTHLY
    project_id: Optional[int] = None
    include_subcategories: bool = True
    compare_previous_period: bool = False
    currency: str = "EUR"


class PLLineItem(BaseModel):
    """Single line item in P&L report."""

    category_id: Optional[int] = None
    category_name: str
    category_type: str
    amount: Decimal
    percentage_of_revenue: Optional[Decimal] = None
    previous_amount: Optional[Decimal] = None
    change_amount: Optional[Decimal] = None
    change_percentage: Optional[Decimal] = None
    transaction_count: int = 0
    children: Optional[List["PLLineItem"]] = None


# Enable forward references
PLLineItem.model_rebuild()


class PLSection(BaseModel):
    """Section of P&L report (e.g., Revenue, Expenses)."""

    name: str
    total: Decimal
    percentage_of_revenue: Optional[Decimal] = None
    items: List[PLLineItem]


class PLReportResponse(BaseModel):
    """Response schema for P&L report."""

    # Report metadata
    report_id: str
    generated_at: datetime
    start_date: date
    end_date: date
    period: ReportPeriod
    currency: str
    project_id: Optional[int] = None
    project_name: Optional[str] = None

    # Revenue section
    revenue: PLSection

    # Cost of Goods Sold
    cogs: PLSection

    # Gross Profit
    gross_profit: Decimal
    gross_margin: Decimal  # Percentage

    # Operating Expenses
    operating_expenses: PLSection

    # Operating Income (EBIT)
    operating_income: Decimal
    operating_margin: Decimal

    # Other Income/Expenses
    other_income: PLSection
    other_expenses: PLSection

    # EBITDA (if depreciation is tracked separately)
    ebitda: Optional[Decimal] = None
    ebitda_margin: Optional[Decimal] = None

    # Net Income
    net_income: Decimal
    net_margin: Decimal

    # Summary totals
    total_revenue: Decimal
    total_expenses: Decimal
    total_transactions: int

    # Comparison with previous period (if requested)
    previous_period: Optional["PLReportResponse"] = None


class KPIResponse(BaseModel):
    """Global KPIs response."""

    # Report period
    start_date: date
    end_date: date
    currency: str

    # Revenue metrics
    total_revenue: Decimal
    revenue_growth: Optional[Decimal] = None  # vs previous period
    average_transaction_value: Decimal
    revenue_per_day: Decimal

    # Profitability metrics
    gross_profit: Decimal
    gross_margin: Decimal  # (Revenue - COGS) / Revenue
    net_profit: Decimal
    net_margin: Decimal  # Net Profit / Revenue
    operating_margin: Decimal  # Operating Income / Revenue

    # EBITDA
    ebitda: Decimal
    ebitda_margin: Decimal

    # Expense metrics
    total_expenses: Decimal
    expense_ratio: Decimal  # Total Expenses / Revenue
    operating_expense_ratio: Decimal

    # Cash flow indicators
    burn_rate: Decimal  # Monthly cash burn
    runway_months: Optional[Decimal] = None  # Cash / Burn Rate

    # Activity metrics
    total_transactions: int
    income_transactions: int
    expense_transactions: int

    # Category breakdown
    expense_by_category: Dict[str, Decimal]
    revenue_by_category: Dict[str, Decimal]

    # Top items
    top_expense_categories: List[Dict]
    top_revenue_sources: List[Dict]


class ProjectKPIResponse(BaseModel):
    """KPIs for a specific project."""

    project_id: int
    project_name: str
    project_code: str
    client_name: Optional[str] = None

    # Report period
    start_date: date
    end_date: date
    currency: str

    # Financial metrics
    total_revenue: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    profit_margin: Decimal

    # ROI metrics
    roi: Optional[Decimal] = None  # (Revenue - Cost) / Cost
    contribution_margin: Decimal  # Revenue - Variable Costs

    # Budget metrics
    budget_amount: Optional[Decimal] = None
    budget_used: Optional[Decimal] = None
    budget_remaining: Optional[Decimal] = None
    budget_used_percentage: Optional[Decimal] = None
    budget_variance: Optional[Decimal] = None  # Budget - Actual

    # Contract metrics
    contract_value: Optional[Decimal] = None
    revenue_vs_contract: Optional[Decimal] = None  # Actual / Contract

    # Activity metrics
    transaction_count: int
    income_count: int
    expense_count: int
    average_expense: Decimal

    # Time metrics
    project_duration_days: Optional[int] = None
    revenue_per_day: Optional[Decimal] = None


class ProjectsKPISummary(BaseModel):
    """Summary of all projects KPIs."""

    total_projects: int
    active_projects: int
    completed_projects: int

    # Aggregated financials
    total_revenue: Decimal
    total_expenses: Decimal
    total_profit: Decimal
    average_profit_margin: Decimal

    # Best/Worst performers
    most_profitable_project: Optional[ProjectKPIResponse] = None
    least_profitable_project: Optional[ProjectKPIResponse] = None
    highest_revenue_project: Optional[ProjectKPIResponse] = None

    # All projects
    projects: List[ProjectKPIResponse]


class TrendDataPoint(BaseModel):
    """Single data point for trend analysis."""

    period: str  # e.g., "2024-01", "Q1 2024"
    start_date: date
    end_date: date
    revenue: Decimal
    expenses: Decimal
    net_profit: Decimal
    gross_margin: Decimal
    net_margin: Decimal
    transaction_count: int


class TrendResponse(BaseModel):
    """Trend analysis response."""

    metric: str
    period_type: ReportPeriod
    data_points: List[TrendDataPoint]
    trend_direction: str  # "up", "down", "stable"
    average_value: Decimal
    min_value: Decimal
    max_value: Decimal
    growth_rate: Optional[Decimal] = None  # Period over period


# Enable forward references
PLReportResponse.model_rebuild()
