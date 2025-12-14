"""Category schemas for API validation."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.category import CategoryType


class CategoryBase(BaseModel):
    """Base category schema."""

    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    type: CategoryType = CategoryType.UNCATEGORIZED
    parent_id: Optional[int] = None
    keywords: Optional[str] = None


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""
    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    type: Optional[CategoryType] = None
    parent_id: Optional[int] = None
    keywords: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """Schema for category response."""

    id: int
    name: str
    description: Optional[str] = None
    type: CategoryType
    parent_id: Optional[int] = None
    keywords: Optional[str] = None
    is_active: bool
    is_system: bool
    is_income: bool
    is_expense: bool
    affects_pl: bool
    created_at: datetime
    updated_at: datetime

    # Nested children (optional)
    children: Optional[List["CategoryResponse"]] = None

    class Config:
        from_attributes = True


class CategoryWithTransactionCount(CategoryResponse):
    """Category response with transaction count."""

    transaction_count: int = 0
    total_amount: float = 0.0


# Enable forward references
CategoryResponse.model_rebuild()
