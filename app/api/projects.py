"""API endpoints for projects."""

from typing import Optional, List, Dict
from decimal import Decimal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.project import Project, ProjectStatus
from app.models.transaction import Transaction, TransactionSide
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectSummary,
    ClientFinancialSummaryResponse,
    ClientFinancialSummary,
    ProjectFinancialSummary,
)

router = APIRouter()


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[ProjectStatus] = None,
    client_name: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all projects."""
    query = select(Project)

    if status:
        query = query.where(Project.status == status)
    if client_name:
        query = query.where(Project.client_name.ilike(f"%{client_name}%"))
    if active_only:
        query = query.where(Project.is_active == True)

    query = query.order_by(Project.created_at.desc())

    result = await db.execute(query)
    projects = result.scalars().all()

    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            code=p.code,
            description=p.description,
            client_name=p.client_name,
            status=p.status,
            start_date=p.start_date,
            end_date=p.end_date,
            budget_amount=p.budget_amount,
            budget_currency=p.budget_currency,
            contract_value=p.contract_value,
            tags=p.tags,
            tag_list=p.tag_list,
            is_active=p.is_active,
            is_billable=p.is_billable,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects
    ]


@router.get("/summary", response_model=List[ProjectSummary])
async def list_projects_with_summary(
    status: Optional[ProjectStatus] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List projects with financial summary."""
    query = select(Project)

    if status:
        query = query.where(Project.status == status)
    if active_only:
        query = query.where(Project.is_active == True)

    result = await db.execute(query)
    projects = result.scalars().all()

    summaries = []
    for project in projects:
        # Get income
        income_query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.project_id == project.id,
            Transaction.side == TransactionSide.CREDIT,
            Transaction.is_excluded_from_reports == False,
        )
        income_result = await db.execute(income_query)
        total_income = Decimal(str(income_result.scalar() or 0))

        # Get expenses
        expense_query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.project_id == project.id,
            Transaction.side == TransactionSide.DEBIT,
            Transaction.is_excluded_from_reports == False,
        )
        expense_result = await db.execute(expense_query)
        total_expenses = Decimal(str(expense_result.scalar() or 0))

        # Get transaction count
        count_query = select(func.count(Transaction.id)).where(
            Transaction.project_id == project.id
        )
        count_result = await db.execute(count_query)
        tx_count = count_result.scalar() or 0

        # Calculate budget percentage
        budget_used_pct = None
        if project.budget_amount and project.budget_amount > 0:
            budget_used_pct = (total_expenses / project.budget_amount) * 100

        summaries.append(
            ProjectSummary(
                id=project.id,
                name=project.name,
                code=project.code,
                description=project.description,
                client_name=project.client_name,
                status=project.status,
                start_date=project.start_date,
                end_date=project.end_date,
                budget_amount=project.budget_amount,
                budget_currency=project.budget_currency,
                contract_value=project.contract_value,
                tags=project.tags,
                tag_list=project.tag_list,
                is_active=project.is_active,
                is_billable=project.is_billable,
                created_at=project.created_at,
                updated_at=project.updated_at,
                total_income=total_income,
                total_expenses=total_expenses,
                net_profit=total_income - total_expenses,
                transaction_count=tx_count,
                budget_used_percentage=budget_used_pct,
            )
        )

    return summaries


@router.get("/clients/summary", response_model=ClientFinancialSummaryResponse)
async def list_clients_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List client summaries with project breakdown."""
    join_conditions = [
        Transaction.project_id == Project.id,
        Transaction.is_excluded_from_reports == False,
    ]
    if start_date:
        join_conditions.append(Transaction.transaction_date >= start_date)
    if end_date:
        join_conditions.append(Transaction.transaction_date <= end_date)

    income_case = case(
        (Transaction.side == TransactionSide.CREDIT, Transaction.amount),
        else_=0,
    )
    expense_case = case(
        (Transaction.side == TransactionSide.DEBIT, Transaction.amount),
        else_=0,
    )

    query = (
        select(
            Project.id,
            Project.name,
            Project.code,
            Project.client_name,
            func.coalesce(func.sum(income_case), 0).label("total_income"),
            func.coalesce(func.sum(expense_case), 0).label("total_expenses"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .join(Transaction, and_(*join_conditions), isouter=True)
        .group_by(Project.id)
        .order_by(Project.client_name.asc().nulls_last(), Project.name.asc())
    )

    if active_only:
        query = query.where(Project.is_active == True)

    result = await db.execute(query)
    rows = result.all()

    clients: Dict[str, ClientFinancialSummary] = {}
    for row in rows:
        client_name = row.client_name or "Sin Cliente"
        total_income = Decimal(str(row.total_income or 0))
        total_expenses = Decimal(str(row.total_expenses or 0))
        net_profit = total_income - total_expenses
        project_summary = ProjectFinancialSummary(
            project_id=row.id,
            project_name=row.name,
            project_code=row.code,
            total_income=total_income,
            total_expenses=total_expenses,
            net_profit=net_profit,
            transaction_count=row.transaction_count or 0,
        )

        if client_name not in clients:
            clients[client_name] = ClientFinancialSummary(
                client_name=client_name,
                total_income=Decimal("0.00"),
                total_expenses=Decimal("0.00"),
                net_profit=Decimal("0.00"),
                project_count=0,
                projects=[],
            )

        client_summary = clients[client_name]
        client_summary.projects.append(project_summary)
        client_summary.project_count += 1
        client_summary.total_income += total_income
        client_summary.total_expenses += total_expenses
        client_summary.net_profit += net_profit

    return ClientFinancialSummaryResponse(
        clients=list(clients.values())
    )


@router.get("/{project_id}", response_model=ProjectSummary)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single project with financial summary."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get financial data
    income_query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.project_id == project.id,
        Transaction.side == TransactionSide.CREDIT,
        Transaction.is_excluded_from_reports == False,
    )
    income_result = await db.execute(income_query)
    total_income = Decimal(str(income_result.scalar() or 0))

    expense_query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.project_id == project.id,
        Transaction.side == TransactionSide.DEBIT,
        Transaction.is_excluded_from_reports == False,
    )
    expense_result = await db.execute(expense_query)
    total_expenses = Decimal(str(expense_result.scalar() or 0))

    count_query = select(func.count(Transaction.id)).where(
        Transaction.project_id == project.id
    )
    count_result = await db.execute(count_query)
    tx_count = count_result.scalar() or 0

    budget_used_pct = None
    if project.budget_amount and project.budget_amount > 0:
        budget_used_pct = (total_expenses / project.budget_amount) * 100

    return ProjectSummary(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        client_name=project.client_name,
        status=project.status,
        start_date=project.start_date,
        end_date=project.end_date,
        budget_amount=project.budget_amount,
        budget_currency=project.budget_currency,
        contract_value=project.contract_value,
        tags=project.tags,
        tag_list=project.tag_list,
        is_active=project.is_active,
        is_billable=project.is_billable,
        created_at=project.created_at,
        updated_at=project.updated_at,
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=total_income - total_expenses,
        transaction_count=tx_count,
        budget_used_percentage=budget_used_pct,
    )


@router.post("", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    # Check code is unique
    result = await db.execute(
        select(Project).where(Project.code == data.code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Project with code '{data.code}' already exists"
        )

    project = Project(
        name=data.name,
        code=data.code,
        description=data.description,
        client_name=data.client_name,
        status=data.status,
        start_date=data.start_date,
        end_date=data.end_date,
        budget_amount=data.budget_amount,
        budget_currency=data.budget_currency,
        contract_value=data.contract_value,
        tags=data.tags,
        is_billable=data.is_billable,
    )

    db.add(project)
    await db.flush()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        client_name=project.client_name,
        status=project.status,
        start_date=project.start_date,
        end_date=project.end_date,
        budget_amount=project.budget_amount,
        budget_currency=project.budget_currency,
        contract_value=project.contract_value,
        tags=project.tags,
        tag_list=project.tag_list,
        is_active=project.is_active,
        is_billable=project.is_billable,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        client_name=project.client_name,
        status=project.status,
        start_date=project.start_date,
        end_date=project.end_date,
        budget_amount=project.budget_amount,
        budget_currency=project.budget_currency,
        contract_value=project.contract_value,
        tags=project.tags,
        tag_list=project.tag_list,
        is_active=project.is_active,
        is_billable=project.is_billable,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a project (soft delete)."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.is_active = False
    await db.flush()

    return {"status": "success", "message": "Project deleted"}


@router.get("/{project_id}/transactions")
async def get_project_transactions(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get transactions for a specific project."""
    # Verify project exists
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Get transactions
    query = (
        select(Transaction)
        .where(Transaction.project_id == project_id)
        .order_by(Transaction.transaction_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    transactions = result.scalars().all()

    # Get count
    count_query = select(func.count(Transaction.id)).where(
        Transaction.project_id == project_id
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "items": [
            {
                "id": tx.id,
                "date": tx.transaction_date.isoformat(),
                "label": tx.label,
                "amount": float(tx.amount),
                "side": tx.side.value,
                "category_id": tx.category_id,
            }
            for tx in transactions
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }
