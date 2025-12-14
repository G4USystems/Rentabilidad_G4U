"""Transaction schemas for API validation."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.transaction import TransactionSide, TransactionStatus, TransactionType


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
