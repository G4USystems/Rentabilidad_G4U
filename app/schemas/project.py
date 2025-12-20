"""Project schemas for API validation."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.project import ProjectStatus


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., max_length=200)
    code: str = Field(..., max_length=50)
    description: Optional[str] = None
    client_name: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_amount: Optional[Decimal] = None
    budget_currency: str = "EUR"
    contract_value: Optional[Decimal] = None
    tags: Optional[str] = None
    is_billable: bool = True


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    client_name: Optional[str] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_amount: Optional[Decimal] = None
    contract_value: Optional[Decimal] = None
    tags: Optional[str] = None
    is_active: Optional[bool] = None
    is_billable: Optional[bool] = None


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: int
    name: str
    code: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    status: ProjectStatus
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_amount: Optional[Decimal] = None
    budget_currency: str
    contract_value: Optional[Decimal] = None
    tags: Optional[str] = None
    tag_list: List[str]
    is_active: bool
    is_billable: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectSummary(ProjectResponse):
    """Project response with financial summary."""

    total_income: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_profit: Decimal = Decimal("0.00")
    transaction_count: int = 0
    budget_used_percentage: Optional[Decimal] = None


class ProjectFinancialSummary(BaseModel):
    """Project financial summary for client grouping."""

    project_id: int
    project_name: str
    project_code: str
    total_income: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_profit: Decimal = Decimal("0.00")
    transaction_count: int = 0


class ClientFinancialSummary(BaseModel):
    """Client summary with aggregated project data."""

    client_name: str
    total_income: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_profit: Decimal = Decimal("0.00")
    project_count: int = 0
    projects: List[ProjectFinancialSummary]


class ClientFinancialSummaryResponse(BaseModel):
    """Response schema for client summaries."""

    clients: List[ClientFinancialSummary]


# ============================================================================
# Drill-down Schemas for Client → Project → Transaction navigation
# ============================================================================

class ClientKPISummary(BaseModel):
    """Client summary with KPIs from allocations."""

    client_name: str
    total_revenue: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_profit: Decimal = Decimal("0.00")
    profit_margin: Decimal = Decimal("0.00")
    project_count: int = 0
    transaction_count: int = 0


class ClientListResponse(BaseModel):
    """Response for GET /clients with pagination."""

    items: List[ClientKPISummary]
    total: int
    page: int
    page_size: int
    pages: int


class ClientProjectSummary(BaseModel):
    """Project summary within a client drill-down."""

    project_id: Optional[int] = None
    project_name: Optional[str] = None
    project_code: Optional[str] = None
    total_revenue: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_profit: Decimal = Decimal("0.00")
    profit_margin: Decimal = Decimal("0.00")
    transaction_count: int = 0


class ClientProjectsResponse(BaseModel):
    """Response for GET /clients/{client_name}/projects."""

    client_name: str
    total_revenue: Decimal = Decimal("0.00")
    total_expenses: Decimal = Decimal("0.00")
    net_profit: Decimal = Decimal("0.00")
    profit_margin: Decimal = Decimal("0.00")
    projects: List[ClientProjectSummary]
