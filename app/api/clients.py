"""API endpoints for client drill-down (using allocations)."""

from datetime import date
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.transaction import Transaction, TransactionSide
from app.models.project import Project
from app.models.transaction_allocation import TransactionAllocation
from app.schemas.project import (
    ClientKPISummary,
    ClientListResponse,
    ClientProjectSummary,
    ClientProjectsResponse,
)
from app.schemas.transaction import (
    TransactionResponse,
    TransactionListResponse,
)
from app.services.financial_service import FinancialService

router = APIRouter()


@router.get("", response_model=ClientListResponse)
async def list_clients(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List all clients with aggregated KPIs from allocations.

    Clients are derived from:
    1. TransactionAllocation.client_name
    2. Project.client_name (fallback for transactions without allocations)
    """
    # Default date range if not specified
    if not start_date:
        start_date = date(2020, 1, 1)
    if not end_date:
        end_date = date.today()

    financial_service = FinancialService(db)
    client_summaries = await financial_service.get_all_clients_summary(start_date, end_date)

    # Get transaction counts per client
    for summary in client_summaries:
        # Count transactions with allocations for this client
        alloc_count_query = (
            select(func.count(func.distinct(TransactionAllocation.transaction_id)))
            .join(Transaction, TransactionAllocation.transaction_id == Transaction.id)
            .where(
                and_(
                    TransactionAllocation.client_name == summary["client_name"],
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_excluded_from_reports == False,
                )
            )
        )
        result = await db.execute(alloc_count_query)
        alloc_tx_count = result.scalar() or 0

        # Count distinct projects
        project_count_query = (
            select(func.count(func.distinct(TransactionAllocation.project_id)))
            .join(Transaction, TransactionAllocation.transaction_id == Transaction.id)
            .where(
                and_(
                    TransactionAllocation.client_name == summary["client_name"],
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                )
            )
        )
        result = await db.execute(project_count_query)
        project_count = result.scalar() or 0

        summary["transaction_count"] = alloc_tx_count
        summary["project_count"] = project_count

    # Convert to response models
    items = [
        ClientKPISummary(
            client_name=s["client_name"],
            total_revenue=s["total_revenue"],
            total_expenses=s["total_expenses"],
            net_profit=s["net_profit"],
            profit_margin=s["profit_margin"],
            project_count=s["project_count"],
            transaction_count=s["transaction_count"],
        )
        for s in client_summaries
    ]

    # Pagination
    total = len(items)
    pages = (total + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]

    return ClientListResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{client_name}/projects", response_model=ClientProjectsResponse)
async def get_client_projects(
    client_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get project breakdown for a specific client.

    Returns all projects associated with this client through allocations,
    with financial summaries for each project.
    """
    # Default date range
    if not start_date:
        start_date = date(2020, 1, 1)
    if not end_date:
        end_date = date.today()

    financial_service = FinancialService(db)

    # Get client totals
    total_revenue = await financial_service.get_total_revenue(
        start_date, end_date, client_name=client_name
    )
    total_expenses = await financial_service.get_total_expenses(
        start_date, end_date, client_name=client_name
    )
    net_profit = total_revenue - total_expenses
    profit_margin = (
        (net_profit / total_revenue * 100).quantize(Decimal("0.01"))
        if total_revenue > 0 else Decimal("0")
    )

    # Get project breakdown
    project_summaries = await financial_service.get_client_projects_summary(
        client_name, start_date, end_date
    )

    # Get transaction counts per project
    for proj in project_summaries:
        if proj["project_id"]:
            count_query = (
                select(func.count(func.distinct(TransactionAllocation.transaction_id)))
                .join(Transaction, TransactionAllocation.transaction_id == Transaction.id)
                .where(
                    and_(
                        TransactionAllocation.client_name == client_name,
                        TransactionAllocation.project_id == proj["project_id"],
                        Transaction.transaction_date >= start_date,
                        Transaction.transaction_date <= end_date,
                    )
                )
            )
        else:
            # Transactions without project (client-only allocations)
            count_query = (
                select(func.count(func.distinct(TransactionAllocation.transaction_id)))
                .join(Transaction, TransactionAllocation.transaction_id == Transaction.id)
                .where(
                    and_(
                        TransactionAllocation.client_name == client_name,
                        TransactionAllocation.project_id.is_(None),
                        Transaction.transaction_date >= start_date,
                        Transaction.transaction_date <= end_date,
                    )
                )
            )

        result = await db.execute(count_query)
        proj["transaction_count"] = result.scalar() or 0

    # Convert to response
    projects = [
        ClientProjectSummary(
            project_id=p["project_id"],
            project_name=p["project_name"],
            project_code=p["project_code"],
            total_revenue=p["total_revenue"],
            total_expenses=p["total_expenses"],
            net_profit=p["net_profit"],
            profit_margin=p["profit_margin"],
            transaction_count=p["transaction_count"],
        )
        for p in project_summaries
    ]

    return ClientProjectsResponse(
        client_name=client_name,
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        net_profit=net_profit,
        profit_margin=profit_margin,
        projects=projects,
    )


@router.get("/{client_name}/transactions", response_model=TransactionListResponse)
async def get_client_transactions(
    client_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    project_id: Optional[int] = None,
    side: Optional[TransactionSide] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get transactions for a specific client.

    Filters transactions that have allocations with this client_name.
    """
    # Default date range
    if not start_date:
        start_date = date(2020, 1, 1)
    if not end_date:
        end_date = date.today()

    # Subquery to get transaction IDs with this client allocation
    alloc_subquery = (
        select(TransactionAllocation.transaction_id)
        .where(TransactionAllocation.client_name == client_name)
    )

    if project_id:
        alloc_subquery = alloc_subquery.where(
            TransactionAllocation.project_id == project_id
        )

    alloc_subquery = alloc_subquery.distinct()

    # Main query
    query = (
        select(Transaction)
        .options(
            joinedload(Transaction.category),
            joinedload(Transaction.project),
        )
        .where(
            and_(
                Transaction.id.in_(alloc_subquery),
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_excluded_from_reports == False,
            )
        )
    )

    if side:
        query = query.where(Transaction.side == side)

    # Count total
    count_query = (
        select(func.count())
        .select_from(Transaction)
        .where(
            and_(
                Transaction.id.in_(alloc_subquery),
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_excluded_from_reports == False,
            )
        )
    )
    if side:
        count_query = count_query.where(Transaction.side == side)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Pagination
    query = query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    transactions = result.unique().scalars().all()

    # Build response
    items = []
    for tx in transactions:
        items.append(
            TransactionResponse(
                id=tx.id,
                qonto_id=tx.qonto_id,
                account_id=tx.account_id,
                amount=tx.amount,
                currency=tx.currency,
                signed_amount=tx.signed_amount,
                local_amount=tx.local_amount,
                local_currency=tx.local_currency,
                side=tx.side,
                status=tx.status,
                operation_type=tx.operation_type,
                emitted_at=tx.emitted_at,
                settled_at=tx.settled_at,
                transaction_date=tx.transaction_date,
                label=tx.label,
                reference=tx.reference,
                note=tx.note,
                counterparty_name=tx.counterparty_name,
                counterparty_iban=tx.counterparty_iban,
                category_id=tx.category_id,
                category_name=tx.category.name if tx.category else None,
                project_id=tx.project_id,
                project_name=tx.project.name if tx.project else None,
                vat_amount=tx.vat_amount,
                vat_rate=tx.vat_rate,
                has_attachments=tx.has_attachments,
                is_reconciled=tx.is_reconciled,
                is_excluded_from_reports=tx.is_excluded_from_reports,
                created_at=tx.created_at,
                updated_at=tx.updated_at,
            )
        )

    pages = (total + page_size - 1) // page_size

    return TransactionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
