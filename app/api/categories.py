"""API endpoints for categories."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.category import Category, CategoryType
from app.models.transaction import Transaction
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithTransactionCount,
)

router = APIRouter()


@router.get("", response_model=List[CategoryResponse])
async def list_categories(
    type: Optional[CategoryType] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all categories."""
    query = select(Category)

    if type:
        query = query.where(Category.type == type)
    if active_only:
        query = query.where(Category.is_active == True)

    query = query.order_by(Category.type, Category.name)

    result = await db.execute(query)
    categories = result.scalars().all()

    return [
        CategoryResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            type=cat.type,
            parent_id=cat.parent_id,
            keywords=cat.keywords,
            is_active=cat.is_active,
            is_system=cat.is_system,
            is_income=cat.is_income,
            is_expense=cat.is_expense,
            affects_pl=cat.affects_pl,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
        )
        for cat in categories
    ]


@router.get("/with-counts", response_model=List[CategoryWithTransactionCount])
async def list_categories_with_counts(
    type: Optional[CategoryType] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List categories with transaction counts."""
    query = (
        select(
            Category,
            func.count(Transaction.id).label("tx_count"),
            func.coalesce(func.sum(Transaction.amount), 0).label("tx_total"),
        )
        .outerjoin(Transaction)
        .group_by(Category.id)
    )

    if type:
        query = query.where(Category.type == type)
    if active_only:
        query = query.where(Category.is_active == True)

    query = query.order_by(Category.type, Category.name)

    result = await db.execute(query)
    rows = result.all()

    return [
        CategoryWithTransactionCount(
            id=row.Category.id,
            name=row.Category.name,
            description=row.Category.description,
            type=row.Category.type,
            parent_id=row.Category.parent_id,
            keywords=row.Category.keywords,
            is_active=row.Category.is_active,
            is_system=row.Category.is_system,
            is_income=row.Category.is_income,
            is_expense=row.Category.is_expense,
            affects_pl=row.Category.affects_pl,
            created_at=row.Category.created_at,
            updated_at=row.Category.updated_at,
            transaction_count=row.tx_count,
            total_amount=float(row.tx_total),
        )
        for row in rows
    ]


@router.get("/types")
async def list_category_types():
    """List all available category types."""
    return {
        "income_types": [
            {"value": CategoryType.REVENUE.value, "label": "Ingresos por Ventas"},
            {"value": CategoryType.OTHER_INCOME.value, "label": "Otros Ingresos"},
        ],
        "expense_types": [
            {"value": CategoryType.COGS.value, "label": "Costo de Ventas (COGS)"},
            {"value": CategoryType.OPERATING_EXPENSE.value, "label": "Gastos Operativos"},
            {"value": CategoryType.PAYROLL.value, "label": "Nómina"},
            {"value": CategoryType.MARKETING.value, "label": "Marketing"},
            {"value": CategoryType.ADMIN.value, "label": "Administración"},
            {"value": CategoryType.RENT.value, "label": "Alquiler y Servicios"},
            {"value": CategoryType.PROFESSIONAL_SERVICES.value, "label": "Servicios Profesionales"},
            {"value": CategoryType.SOFTWARE.value, "label": "Software"},
            {"value": CategoryType.TRAVEL.value, "label": "Viajes"},
            {"value": CategoryType.TAXES.value, "label": "Impuestos"},
            {"value": CategoryType.INTEREST.value, "label": "Intereses"},
            {"value": CategoryType.DEPRECIATION.value, "label": "Depreciación"},
            {"value": CategoryType.OTHER_EXPENSE.value, "label": "Otros Gastos"},
        ],
        "non_pl_types": [
            {"value": CategoryType.TRANSFER.value, "label": "Transferencias"},
            {"value": CategoryType.INVESTMENT.value, "label": "Inversiones"},
            {"value": CategoryType.LOAN.value, "label": "Préstamos"},
            {"value": CategoryType.EQUITY.value, "label": "Capital"},
            {"value": CategoryType.UNCATEGORIZED.value, "label": "Sin Categorizar"},
        ],
    }


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single category."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        type=category.type,
        parent_id=category.parent_id,
        keywords=category.keywords,
        is_active=category.is_active,
        is_system=category.is_system,
        is_income=category.is_income,
        is_expense=category.is_expense,
        affects_pl=category.affects_pl,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.post("", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new category."""
    category = Category(
        name=data.name,
        description=data.description,
        type=data.type,
        parent_id=data.parent_id,
        keywords=data.keywords,
    )

    db.add(category)
    await db.flush()
    await db.refresh(category)

    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        type=category.type,
        parent_id=category.parent_id,
        keywords=category.keywords,
        is_active=category.is_active,
        is_system=category.is_system,
        is_income=category.is_income,
        is_expense=category.is_expense,
        affects_pl=category.affects_pl,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a category."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.is_system:
        raise HTTPException(
            status_code=400,
            detail="System categories cannot be modified"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.flush()
    await db.refresh(category)

    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        type=category.type,
        parent_id=category.parent_id,
        keywords=category.keywords,
        is_active=category.is_active,
        is_system=category.is_system,
        is_income=category.is_income,
        is_expense=category.is_expense,
        affects_pl=category.affects_pl,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a category (soft delete)."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.is_system:
        raise HTTPException(
            status_code=400,
            detail="System categories cannot be deleted"
        )

    category.is_active = False
    await db.flush()

    return {"status": "success", "message": "Category deleted"}
