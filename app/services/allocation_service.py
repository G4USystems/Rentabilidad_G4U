"""Service for managing transaction allocations."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.transaction import Transaction
from app.models.project import Project
from app.models.transaction_allocation import TransactionAllocation
from app.schemas.transaction import AllocationInput, AllocationResponse


# Tolerance for percentage sum validation (allows for small rounding errors)
PERCENTAGE_TOLERANCE = Decimal("0.01")


class AllocationService:
    """Service for managing transaction allocations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_allocations(
        self,
        transaction_id: int,
        allocations: List[AllocationInput],
    ) -> List[AllocationResponse]:
        """
        Create or replace allocations for a transaction.

        Validation:
        - Transaction must exist
        - Each allocation must have project_id or client_name (or both)
        - If percentages provided, must sum to 100 (within tolerance)
        - If project_id provided, project must exist
        - Calculates missing percentage or amount_allocated
        """
        # Fetch transaction
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        tx = result.scalar_one_or_none()
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Validate each allocation has project_id or client_name
        for i, alloc in enumerate(allocations):
            if alloc.project_id is None and not alloc.client_name:
                raise HTTPException(
                    status_code=400,
                    detail=f"Allocation {i+1}: must have project_id or client_name (or both)"
                )

        # Collect and validate project_ids
        project_ids = [a.project_id for a in allocations if a.project_id is not None]
        if project_ids:
            result = await self.db.execute(
                select(Project).where(Project.id.in_(project_ids))
            )
            projects = {p.id: p for p in result.scalars().all()}
            for pid in project_ids:
                if pid not in projects:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Project with id={pid} not found"
                    )
        else:
            projects = {}

        # Calculate percentages and amounts
        processed_allocations = self._process_allocations(allocations, tx.amount)

        # Delete existing allocations
        await self.db.execute(
            delete(TransactionAllocation).where(
                TransactionAllocation.transaction_id == transaction_id
            )
        )

        # Create new allocations
        now = datetime.utcnow()
        db_allocations = []
        for alloc_data in processed_allocations:
            db_alloc = TransactionAllocation(
                transaction_id=transaction_id,
                project_id=alloc_data["project_id"],
                client_name=alloc_data["client_name"],
                percentage=alloc_data["percentage"],
                amount_allocated=alloc_data["amount_allocated"],
                created_at=now,
                updated_at=now,
            )
            self.db.add(db_alloc)
            db_allocations.append(db_alloc)

        await self.db.flush()

        # Build response with project info
        responses = []
        for db_alloc in db_allocations:
            project = projects.get(db_alloc.project_id) if db_alloc.project_id else None
            responses.append(
                AllocationResponse(
                    id=db_alloc.id,
                    transaction_id=db_alloc.transaction_id,
                    project_id=db_alloc.project_id,
                    project_name=project.name if project else None,
                    project_code=project.code if project else None,
                    client_name=db_alloc.client_name,
                    percentage=db_alloc.percentage,
                    amount_allocated=db_alloc.amount_allocated,
                    created_at=db_alloc.created_at,
                    updated_at=db_alloc.updated_at,
                )
            )

        return responses

    def _process_allocations(
        self,
        allocations: List[AllocationInput],
        transaction_amount: Decimal,
    ) -> List[dict]:
        """
        Process allocations to calculate missing percentages or amounts.

        Logic:
        1. If both percentage and amount provided, validate they match
        2. If only percentage provided, calculate amount
        3. If only amount provided, calculate percentage
        4. If neither provided and single allocation, use 100%
        5. Validate total percentage = 100 (within tolerance)
        """
        processed = []
        has_any_percentage = any(a.percentage is not None for a in allocations)
        has_any_amount = any(a.amount_allocated is not None for a in allocations)

        # Special case: single allocation with nothing specified = 100%
        if len(allocations) == 1 and not has_any_percentage and not has_any_amount:
            alloc = allocations[0]
            return [{
                "project_id": alloc.project_id,
                "client_name": alloc.client_name,
                "percentage": Decimal("100"),
                "amount_allocated": transaction_amount,
            }]

        # Process each allocation
        for alloc in allocations:
            if alloc.percentage is not None and alloc.amount_allocated is not None:
                # Both provided - validate consistency
                expected_amount = (transaction_amount * alloc.percentage / Decimal("100")).quantize(Decimal("0.01"))
                if abs(expected_amount - alloc.amount_allocated) > Decimal("0.01"):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Allocation for project_id={alloc.project_id}: "
                               f"percentage {alloc.percentage}% would give {expected_amount}, "
                               f"but amount_allocated is {alloc.amount_allocated}"
                    )
                processed.append({
                    "project_id": alloc.project_id,
                    "client_name": alloc.client_name,
                    "percentage": alloc.percentage,
                    "amount_allocated": alloc.amount_allocated,
                })
            elif alloc.percentage is not None:
                # Only percentage - calculate amount
                amount = (transaction_amount * alloc.percentage / Decimal("100")).quantize(Decimal("0.01"))
                processed.append({
                    "project_id": alloc.project_id,
                    "client_name": alloc.client_name,
                    "percentage": alloc.percentage,
                    "amount_allocated": amount,
                })
            elif alloc.amount_allocated is not None:
                # Only amount - calculate percentage
                if transaction_amount == 0:
                    percentage = Decimal("100") if alloc.amount_allocated == 0 else Decimal("0")
                else:
                    percentage = (alloc.amount_allocated / transaction_amount * Decimal("100")).quantize(Decimal("0.0001"))
                processed.append({
                    "project_id": alloc.project_id,
                    "client_name": alloc.client_name,
                    "percentage": percentage,
                    "amount_allocated": alloc.amount_allocated,
                })
            else:
                # Neither provided - error unless inferrable
                raise HTTPException(
                    status_code=400,
                    detail=f"Allocation for project_id={alloc.project_id}, "
                           f"client_name={alloc.client_name}: "
                           "must provide percentage or amount_allocated"
                )

        # Validate total percentage = 100 (within tolerance)
        total_percentage = sum(p["percentage"] for p in processed)
        if abs(total_percentage - Decimal("100")) > PERCENTAGE_TOLERANCE:
            raise HTTPException(
                status_code=400,
                detail=f"Total allocation percentage is {total_percentage}%, must be 100%"
            )

        return processed

    async def get_allocations(self, transaction_id: int) -> List[AllocationResponse]:
        """Get all allocations for a transaction."""
        # Verify transaction exists
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Fetch allocations with project info
        result = await self.db.execute(
            select(TransactionAllocation)
            .options(joinedload(TransactionAllocation.project))
            .where(TransactionAllocation.transaction_id == transaction_id)
            .order_by(TransactionAllocation.id)
        )
        allocations = result.unique().scalars().all()

        return [
            AllocationResponse(
                id=a.id,
                transaction_id=a.transaction_id,
                project_id=a.project_id,
                project_name=a.project.name if a.project else None,
                project_code=a.project.code if a.project else None,
                client_name=a.client_name,
                percentage=a.percentage,
                amount_allocated=a.amount_allocated,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in allocations
        ]

    async def delete_allocations(self, transaction_id: int) -> int:
        """Delete all allocations for a transaction. Returns count deleted."""
        # Verify transaction exists
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Transaction not found")

        result = await self.db.execute(
            delete(TransactionAllocation)
            .where(TransactionAllocation.transaction_id == transaction_id)
            .returning(TransactionAllocation.id)
        )
        deleted_ids = result.fetchall()
        return len(deleted_ids)

    async def get_allocations_by_project(
        self,
        project_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[TransactionAllocation]:
        """Get all allocations for a project, optionally filtered by date."""
        query = (
            select(TransactionAllocation)
            .join(Transaction)
            .where(TransactionAllocation.project_id == project_id)
        )

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.where(Transaction.transaction_date <= end_date)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_allocations_by_client(
        self,
        client_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[TransactionAllocation]:
        """Get all allocations for a client, optionally filtered by date."""
        query = (
            select(TransactionAllocation)
            .join(Transaction)
            .where(TransactionAllocation.client_name == client_name)
        )

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.where(Transaction.transaction_date <= end_date)

        result = await self.db.execute(query)
        return result.scalars().all()
