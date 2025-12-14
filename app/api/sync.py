"""API endpoints for syncing with Qonto."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.sync_service import SyncService
from app.services.categorization_service import CategorizationService, create_default_categories

router = APIRouter()


@router.post("/accounts")
async def sync_accounts(
    db: AsyncSession = Depends(get_db),
):
    """
    Sync bank accounts from Qonto.

    Returns list of synced accounts.
    """
    try:
        service = SyncService(db)
        accounts = await service.sync_accounts()

        return {
            "status": "success",
            "synced_count": len(accounts),
            "accounts": [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "iban": acc.iban,
                    "balance": float(acc.balance),
                    "currency": acc.currency,
                }
                for acc in accounts
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transactions")
async def sync_transactions(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    full_sync: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Sync transactions from Qonto.

    Args:
        from_date: Start date for sync
        to_date: End date for sync
        full_sync: If true, sync all transactions (ignores last sync time)
    """
    try:
        service = SyncService(db)
        stats = await service.sync_transactions(
            from_date=from_date,
            to_date=to_date,
            full_sync=full_sync,
        )

        return {
            "status": "success",
            **stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/all")
async def sync_all(
    full_sync: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Sync all data from Qonto (accounts and transactions).
    """
    try:
        service = SyncService(db)

        # Sync accounts first
        accounts = await service.sync_accounts()

        # Then transactions
        tx_stats = await service.sync_transactions(full_sync=full_sync)

        return {
            "status": "success",
            "accounts_synced": len(accounts),
            "transactions": tx_stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categories/auto")
async def auto_categorize(
    uncategorized_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-categorize transactions based on keyword rules.

    Args:
        uncategorized_only: Only process uncategorized transactions
    """
    try:
        service = CategorizationService(db)
        stats = await service.auto_categorize_all(uncategorized_only=uncategorized_only)

        return {
            "status": "success",
            **stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init")
async def initialize_system(
    db: AsyncSession = Depends(get_db),
):
    """
    Initialize the system with default categories.
    Run this once after database setup.
    """
    try:
        categories = await create_default_categories(db)
        await db.commit()

        return {
            "status": "success",
            "message": "System initialized",
            "categories_created": len(categories),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
