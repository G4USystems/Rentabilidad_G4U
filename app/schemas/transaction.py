"""Transaction schemas for API validation."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.transaction import TransactionSide, TransactionStatus, TransactionType, ReviewStatus


class TransactionBase(BaseModel):
    """Base transaction schema."""

    label: str = Field(..., max_length=500)
    note: Optional[str] = None
    category_id: Optional[int] = None
    project_id: Optional[int] = None
    is_excluded_from_reports: bool = False


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction manually."""

    amount: Decimal
    currency: str = "EUR"
    side: TransactionSide
    transaction_date: date
    counterparty_name: Optional[str] = None
    reference: Optional[str] = None


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction."""

    note: Optional[str] = None
    category_id: Optional[int] = None
    project_id: Optional[int] = None
    is_reconciled: Optional[bool] = None
    is_excluded_from_reports: Optional[bool] = None


class TransactionResponse(BaseModel):
    """Schema for transaction response."""

    id: int
    qonto_id: str
    account_id: int

    # Amount
    amount: Decimal
    currency: str
    signed_amount: Decimal
    local_amount: Optional[Decimal] = None
    local_currency: Optional[str] = None

    # Classification
    side: TransactionSide
    status: TransactionStatus
    operation_type: TransactionType

    # Dates
    emitted_at: datetime
    settled_at: Optional[datetime] = None
    transaction_date: date

    # Description
    label: str
    reference: Optional[str] = None
    note: Optional[str] = None

    # Counterparty
    counterparty_name: Optional[str] = None
    counterparty_iban: Optional[str] = None

    # Categories and projects
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None

    # VAT
    vat_amount: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None

    # Flags
    has_attachments: bool
    is_reconciled: bool
    is_excluded_from_reports: bool

    # Review status
    review_status: ReviewStatus = ReviewStatus.PENDING

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Schema for paginated transaction list."""

    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TransactionFilter(BaseModel):
    """Schema for filtering transactions."""

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category_id: Optional[int] = None
    project_id: Optional[int] = None
    side: Optional[TransactionSide] = None
    status: Optional[TransactionStatus] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    search: Optional[str] = None
    include_excluded: bool = False


class ProjectSuggestion(BaseModel):
    """Schema for project suggestion response."""

    project_id: int
    project_name: str
    project_code: str
    client_name: Optional[str] = None
    score: int
    matched_terms: List[str]


class TransactionProjectSuggestion(BaseModel):
    """Schema for project suggestion for a transaction."""

    transaction_id: int
    suggestion: Optional[ProjectSuggestion] = None


# ============================================================================
# Allocation Schemas for partial project/client assignments
# ============================================================================

class AllocationInput(BaseModel):
    """Schema for creating a single allocation entry."""

    project_id: Optional[int] = None
    client_name: Optional[str] = Field(None, max_length=200)
    percentage: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        le=Decimal("100"),
        description="Percentage of transaction to allocate (0-100)"
    )
    amount_allocated: Optional[Decimal] = Field(
        None,
        description="Absolute amount to allocate. If not provided, calculated from percentage."
    )


class AllocationResponse(BaseModel):
    """Schema for allocation response."""

    id: int
    transaction_id: int
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    project_code: Optional[str] = None
    client_name: Optional[str] = None
    percentage: Decimal
    amount_allocated: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionAllocationsPayload(BaseModel):
    """Schema for bulk allocation update on a transaction."""

    allocations: List[AllocationInput] = Field(
        ...,
        min_length=1,
        description="List of allocations. Each must have project_id or client_name (or both)."
    )


class TransactionWithAllocationsResponse(TransactionResponse):
    """Transaction response including allocation details."""

    allocations: List[AllocationResponse] = []
    has_allocations: bool = False


class AllocationSummary(BaseModel):
    """Summary of allocations for reporting."""

    total_allocated: Decimal
    total_percentage: Decimal
    allocation_count: int
    is_fully_allocated: bool


# ============================================================================
# Review Status Schemas
# ============================================================================

class ReviewConfirmRequest(BaseModel):
    """Request to confirm review status of transactions."""

    transaction_ids: List[int] = Field(
        ...,
        min_length=1,
        description="List of transaction IDs to confirm"
    )


class ReviewConfirmResponse(BaseModel):
    """Response after confirming transactions."""

    confirmed_count: int
    transaction_ids: List[int]
