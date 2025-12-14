"""Service for financial calculations."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionSide
from app.models.category import Category, CategoryType
from app.models.project import Project

logger = logging.getLogger(__name__)


class FinancialService:
    """Service for financial calculations and aggregations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _round_decimal(self, value: Decimal, places: int = 2) -> Decimal:
        """Round decimal to specified places."""
        return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)

    def _calculate_percentage(
        self,
        numerator: Decimal,
        denominator: Decimal,
    ) -> Decimal:
        """Calculate percentage safely."""
        if denominator == 0:
            return Decimal("0")
        return self._round_decimal((numerator / denominator) * 100)

    async def get_total_revenue(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> Decimal:
        """Get total revenue for period."""
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.side == TransactionSide.CREDIT,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_excluded_from_reports == False,
            )
        )

        if project_id:
            query = query.where(Transaction.project_id == project_id)

        # Only include revenue categories
        query = query.join(Category, isouter=True).where(
            (Category.type.in_([CategoryType.REVENUE, CategoryType.OTHER_INCOME])) |
            (Transaction.category_id.is_(None))
        )

        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    async def get_total_expenses(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> Decimal:
        """Get total expenses for period."""
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.side == TransactionSide.DEBIT,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_excluded_from_reports == False,
            )
        )

        if project_id:
            query = query.where(Transaction.project_id == project_id)

        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    async def get_amounts_by_category_type(
        self,
        start_date: date,
        end_date: date,
        category_type: CategoryType,
        project_id: Optional[int] = None,
    ) -> Decimal:
        """Get total amount for a specific category type."""
        query = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .join(Category)
            .where(
                and_(
                    Category.type == category_type,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_excluded_from_reports == False,
                )
            )
        )

        if project_id:
            query = query.where(Transaction.project_id == project_id)

        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    async def get_breakdown_by_category(
        self,
        start_date: date,
        end_date: date,
        side: Optional[TransactionSide] = None,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get amount breakdown by category."""
        query = (
            select(
                Category.id,
                Category.name,
                Category.type,
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .join(Category)
            .where(
                and_(
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_excluded_from_reports == False,
                )
            )
            .group_by(Category.id, Category.name, Category.type)
            .order_by(func.sum(Transaction.amount).desc())
        )

        if side:
            query = query.where(Transaction.side == side)
        if project_id:
            query = query.where(Transaction.project_id == project_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "category_id": row.id,
                "category_name": row.name,
                "category_type": row.type.value,
                "total": Decimal(str(row.total)),
                "transaction_count": row.count,
            }
            for row in rows
        ]

    async def calculate_gross_profit(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> Dict[str, Decimal]:
        """
        Calculate gross profit.

        Gross Profit = Revenue - COGS
        """
        revenue = await self.get_total_revenue(start_date, end_date, project_id)
        cogs = await self.get_amounts_by_category_type(
            start_date, end_date, CategoryType.COGS, project_id
        )

        gross_profit = revenue - cogs
        gross_margin = self._calculate_percentage(gross_profit, revenue)

        return {
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "gross_margin": gross_margin,
        }

    async def calculate_operating_income(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> Dict[str, Decimal]:
        """
        Calculate operating income.

        Operating Income = Gross Profit - Operating Expenses
        """
        gross = await self.calculate_gross_profit(start_date, end_date, project_id)

        # Get all operating expenses
        operating_expense_types = [
            CategoryType.OPERATING_EXPENSE,
            CategoryType.PAYROLL,
            CategoryType.MARKETING,
            CategoryType.ADMIN,
            CategoryType.RENT,
            CategoryType.PROFESSIONAL_SERVICES,
            CategoryType.SOFTWARE,
            CategoryType.TRAVEL,
        ]

        total_operating = Decimal("0")
        for expense_type in operating_expense_types:
            amount = await self.get_amounts_by_category_type(
                start_date, end_date, expense_type, project_id
            )
            total_operating += amount

        operating_income = gross["gross_profit"] - total_operating
        operating_margin = self._calculate_percentage(operating_income, gross["revenue"])

        return {
            **gross,
            "operating_expenses": total_operating,
            "operating_income": operating_income,
            "operating_margin": operating_margin,
        }

    async def calculate_ebitda(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> Dict[str, Decimal]:
        """
        Calculate EBITDA.

        EBITDA = Operating Income + Depreciation + Amortization
        (Since we may not have depreciation tracked, EBITDA = Operating Income for now)
        """
        operating = await self.calculate_operating_income(start_date, end_date, project_id)

        # Get depreciation if tracked
        depreciation = await self.get_amounts_by_category_type(
            start_date, end_date, CategoryType.DEPRECIATION, project_id
        )

        ebitda = operating["operating_income"] + depreciation
        ebitda_margin = self._calculate_percentage(ebitda, operating["revenue"])

        return {
            **operating,
            "depreciation": depreciation,
            "ebitda": ebitda,
            "ebitda_margin": ebitda_margin,
        }

    async def calculate_net_income(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> Dict[str, Decimal]:
        """
        Calculate net income.

        Net Income = Operating Income - Interest - Taxes + Other Income
        """
        ebitda = await self.calculate_ebitda(start_date, end_date, project_id)

        # Get interest
        interest = await self.get_amounts_by_category_type(
            start_date, end_date, CategoryType.INTEREST, project_id
        )

        # Get taxes
        taxes = await self.get_amounts_by_category_type(
            start_date, end_date, CategoryType.TAXES, project_id
        )

        # Get other income
        other_income = await self.get_amounts_by_category_type(
            start_date, end_date, CategoryType.OTHER_INCOME, project_id
        )

        # Get other expenses
        other_expense = await self.get_amounts_by_category_type(
            start_date, end_date, CategoryType.OTHER_EXPENSE, project_id
        )

        net_income = (
            ebitda["operating_income"]
            - interest
            - taxes
            + other_income
            - other_expense
        )
        net_margin = self._calculate_percentage(net_income, ebitda["revenue"])

        return {
            **ebitda,
            "interest": interest,
            "taxes": taxes,
            "other_income": other_income,
            "other_expenses": other_expense,
            "net_income": net_income,
            "net_margin": net_margin,
        }

    async def get_transaction_counts(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """Get transaction counts by type."""
        base_query = select(func.count(Transaction.id)).where(
            and_(
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_excluded_from_reports == False,
            )
        )

        if project_id:
            base_query = base_query.where(Transaction.project_id == project_id)

        # Total
        result = await self.db.execute(base_query)
        total = result.scalar() or 0

        # Income
        income_query = base_query.where(Transaction.side == TransactionSide.CREDIT)
        result = await self.db.execute(income_query)
        income = result.scalar() or 0

        # Expense
        expense_query = base_query.where(Transaction.side == TransactionSide.DEBIT)
        result = await self.db.execute(expense_query)
        expense = result.scalar() or 0

        return {
            "total": total,
            "income": income,
            "expense": expense,
        }

    async def calculate_burn_rate(
        self,
        months: int = 3,
        end_date: Optional[date] = None,
    ) -> Decimal:
        """
        Calculate monthly burn rate (average monthly expenses).

        Args:
            months: Number of months to average
            end_date: End date for calculation

        Returns:
            Monthly burn rate
        """
        from dateutil.relativedelta import relativedelta

        if end_date is None:
            end_date = date.today()

        start_date = end_date - relativedelta(months=months)

        total_expenses = await self.get_total_expenses(start_date, end_date)
        total_revenue = await self.get_total_revenue(start_date, end_date)

        # Net burn = Expenses - Revenue (if negative, company is profitable)
        net_burn = total_expenses - total_revenue

        # Monthly average
        return self._round_decimal(net_burn / months)
