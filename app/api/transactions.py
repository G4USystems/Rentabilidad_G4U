"""API endpoints for transactions."""

from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.transaction import Transaction, TransactionSide, TransactionStatus
from app.models.category import Category
from app.models.project import Project
from app.schemas.transaction import (
    TransactionResponse,
    TransactionListResponse,
    TransactionUpdate,
)

router = APIRouter()


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[int] = None,
    project_id: Optional[int] = None,
    side: Optional[TransactionSide] = None,
    status: Optional[TransactionStatus] = None,
    search: Optional[str] = None,
    include_excluded: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List transactions with filters and pagination.
    """
    # Base query
    query = select(Transaction).options(
        joinedload(Transaction.category),
        joinedload(Transaction.project),
    )

    # Apply filters
    conditions = []

    if start_date:
        conditions.append(Transaction.transaction_date >= start_date)
    if end_date:
        conditions.append(Transaction.transaction_date <= end_date)
    if category_id:
        conditions.append(Transaction.category_id == category_id)
    if project_id:
        conditions.append(Transaction.project_id == project_id)
    if side:
        conditions.append(Transaction.side == side)
    if status:
        conditions.append(Transaction.status == status)
    if not include_excluded:
        conditions.append(Transaction.is_excluded_from_reports == False)
    if search:
        search_filter = or_(
            Transaction.label.ilike(f"%{search}%"),
            Transaction.counterparty_name.ilike(f"%{search}%"),
            Transaction.reference.ilike(f"%{search}%"),
        )
        conditions.append(search_filter)

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(Transaction)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Apply pagination
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


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single transaction by ID."""
    result = await db.execute(
        select(Transaction)
        .options(
            joinedload(Transaction.category),
            joinedload(Transaction.project),
        )
        .where(Transaction.id == transaction_id)
    )
    tx = result.unique().scalar_one_or_none()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return TransactionResponse(
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


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    update: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a transaction (category, project, notes, etc.)."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update fields
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tx, field, value)

    await db.flush()
    await db.refresh(tx)

    # Reload with relationships
    result = await db.execute(
        select(Transaction)
        .options(
            joinedload(Transaction.category),
            joinedload(Transaction.project),
        )
        .where(Transaction.id == transaction_id)
    )
    tx = result.unique().scalar_one()

    return TransactionResponse(
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


@router.post("/{transaction_id}/categorize")
async def categorize_transaction(
    transaction_id: int,
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Assign a category to a transaction."""
    # Verify transaction exists
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Verify category exists
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    tx.category_id = category_id
    await db.flush()

    return {"status": "success", "category_id": category_id}


@router.post("/{transaction_id}/assign-project")
async def assign_project(
    transaction_id: int,
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Assign a project to a transaction."""
    # Verify transaction exists
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Verify project exists
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tx.project_id = project_id
    await db.flush()

    return {"status": "success", "project_id": project_id}


@router.post("/bulk/categorize")
async def bulk_categorize(
    transaction_ids: List[int],
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Assign a category to multiple transactions."""
    # Verify category exists
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Category not found")

    # Update transactions
    result = await db.execute(
        select(Transaction).where(Transaction.id.in_(transaction_ids))
    )
    transactions = result.scalars().all()

    for tx in transactions:
        tx.category_id = category_id

    await db.flush()

    return {
        "status": "success",
        "updated_count": len(transactions),
    }


@router.post("/bulk/assign-project")
async def bulk_assign_project(
    transaction_ids: List[int],
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Assign a project to multiple transactions."""
    # Verify project exists
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Update transactions
    result = await db.execute(
        select(Transaction).where(Transaction.id.in_(transaction_ids))
    )
    transactions = result.scalars().all()

    for tx in transactions:
        tx.project_id = project_id

    await db.flush()

    return {
        "status": "success",
        "updated_count": len(transactions),
    }
