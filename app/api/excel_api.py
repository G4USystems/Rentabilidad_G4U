"""
Simplified API endpoints using Excel/Google Sheets storage.

This is an alternative to the database-backed API.
"""

from datetime import date
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.excel_sync_service import ExcelSyncService
from app.services.excel_financial_service import ExcelFinancialService
from app.storage.excel_storage import get_storage

router = APIRouter()


# ==================== Schemas ====================

class ProjectCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    client_name: Optional[str] = None
    budget_amount: Optional[float] = None
    contract_value: Optional[float] = None


class TransactionUpdate(BaseModel):
    category_id: Optional[int] = None
    project_id: Optional[int] = None
    note: Optional[str] = None
    is_excluded: Optional[bool] = None


# ==================== Sync Endpoints ====================

@router.post("/sync/init")
async def initialize_system():
    """Initialize the system with default categories."""
    service = ExcelSyncService()
    result = await service.initialize_categories()

    return {
        "status": "success",
        "message": "System initialized",
        "categories_created": result["created"],
        "categories_existing": result["existing"],
    }


@router.post("/sync/accounts")
async def sync_accounts():
    """Sync bank accounts from Qonto."""
    try:
        service = ExcelSyncService()
        accounts = await service.sync_accounts()

        return {
            "status": "success",
            "synced_count": len(accounts),
            "accounts": accounts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/transactions")
async def sync_transactions(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
):
    """Sync transactions from Qonto."""
    try:
        service = ExcelSyncService()
        stats = await service.sync_transactions(from_date, to_date)

        return {
            "status": "success",
            **stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/all")
async def sync_all():
    """Sync all data from Qonto (accounts and transactions)."""
    try:
        service = ExcelSyncService()
        result = await service.sync_all()

        return {
            "status": "success",
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Transaction Endpoints ====================

@router.get("/transactions")
async def list_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    project_id: Optional[int] = None,
    side: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List transactions with filters."""
    storage = get_storage()
    df = storage.get_transactions(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        project_id=project_id,
        side=side,
    )

    total = len(df)

    # Pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    df_page = df.iloc[start_idx:end_idx]

    return {
        "items": df_page.to_dict('records'),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.patch("/transactions/{transaction_id}")
async def update_transaction(transaction_id: int, update: TransactionUpdate):
    """Update a transaction (categorize, assign project, etc.)."""
    storage = get_storage()

    updates = update.model_dump(exclude_unset=True)
    success = storage.update_transaction(transaction_id, updates)

    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {"status": "success", "updated": updates}


@router.post("/transactions/bulk/categorize")
async def bulk_categorize(transaction_ids: List[int], category_id: int):
    """Assign category to multiple transactions."""
    storage = get_storage()
    updated = 0

    for tx_id in transaction_ids:
        if storage.update_transaction(tx_id, {'category_id': category_id}):
            updated += 1

    return {"status": "success", "updated_count": updated}


@router.post("/transactions/bulk/assign-project")
async def bulk_assign_project(transaction_ids: List[int], project_id: int):
    """Assign project to multiple transactions."""
    storage = get_storage()
    updated = 0

    for tx_id in transaction_ids:
        if storage.update_transaction(tx_id, {'project_id': project_id}):
            updated += 1

    return {"status": "success", "updated_count": updated}


# ==================== Category Endpoints ====================

@router.get("/categories")
async def list_categories(active_only: bool = True):
    """List all categories."""
    storage = get_storage()
    df = storage.get_categories(active_only=active_only)

    return {"categories": df.to_dict('records')}


# ==================== Project Endpoints ====================

@router.get("/projects")
async def list_projects(active_only: bool = True):
    """List all projects."""
    storage = get_storage()
    df = storage.get_projects(active_only=active_only)

    return {"projects": df.to_dict('records')}


@router.post("/projects")
async def create_project(project: ProjectCreate):
    """Create a new project."""
    storage = get_storage()

    project_id = storage.add_project({
        'name': project.name,
        'code': project.code,
        'description': project.description,
        'client_name': project.client_name,
        'budget_amount': project.budget_amount,
        'contract_value': project.contract_value,
        'status': 'active',
        'is_active': True,
    })

    return {"status": "success", "project_id": project_id}


@router.get("/projects/{project_id}")
async def get_project(project_id: int):
    """Get project with KPIs."""
    service = ExcelFinancialService()
    kpis = service.calculate_project_kpis(project_id)

    if not kpis:
        raise HTTPException(status_code=404, detail="Project not found")

    return kpis


# ==================== Reports Endpoints ====================

@router.get("/reports/pl")
async def get_pl_report(
    start_date: date,
    end_date: date,
    project_id: Optional[int] = None,
):
    """Generate P&L report."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    service = ExcelFinancialService()
    return service.calculate_pl_summary(start_date, end_date, project_id)


@router.get("/reports/pl/monthly")
async def get_monthly_pl(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    project_id: Optional[int] = None,
):
    """Get P&L for a specific month."""
    from calendar import monthrange

    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)

    service = ExcelFinancialService()
    return service.calculate_pl_summary(start_date, end_date, project_id)


@router.get("/reports/pl/yearly")
async def get_yearly_pl(
    year: int = Query(..., ge=2000, le=2100),
    project_id: Optional[int] = None,
):
    """Get P&L for a full year."""
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    service = ExcelFinancialService()
    return service.calculate_pl_summary(start_date, end_date, project_id)


# ==================== KPI Endpoints ====================

@router.get("/kpis/dashboard")
async def get_dashboard():
    """Get dashboard KPIs."""
    service = ExcelFinancialService()
    return service.get_dashboard_kpis()


@router.get("/kpis/projects")
async def get_all_projects_kpis():
    """Get KPIs for all projects."""
    storage = get_storage()
    service = ExcelFinancialService()

    projects_df = storage.get_projects()

    if projects_df.empty:
        return {"projects": [], "totals": {}}

    project_kpis = []
    total_income = 0
    total_expenses = 0

    for _, project in projects_df.iterrows():
        kpi = service.calculate_project_kpis(int(project['id']))
        if kpi:
            project_kpis.append(kpi)
            total_income += kpi['total_income']
            total_expenses += kpi['total_expenses']

    return {
        "projects": project_kpis,
        "totals": {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "total_profit": round(total_income - total_expenses, 2),
        },
    }


@router.get("/kpis/global")
async def get_global_kpis(
    start_date: date,
    end_date: date,
):
    """Get global KPIs."""
    service = ExcelFinancialService()
    pl = service.calculate_pl_summary(start_date, end_date)

    # Add expense breakdown
    expense_breakdown = service.get_breakdown_by_category(start_date, end_date, side='debit')
    revenue_breakdown = service.get_breakdown_by_category(start_date, end_date, side='credit')

    return {
        **pl,
        "expense_by_category": expense_breakdown[:10],
        "revenue_by_category": revenue_breakdown[:10],
    }
