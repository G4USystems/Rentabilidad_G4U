"""Service for financial calculations."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy import select, func, and_, or_, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.transaction import Transaction, TransactionSide, ReviewStatus
from app.models.category import Category, CategoryType
from app.models.project import Project
from app.models.transaction_allocation import TransactionAllocation

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
        client_name: Optional[str] = None,
        exclude_vat: bool = False,
    ) -> Decimal:
        """
        Get total revenue for period.

        If project_id or client_name is specified, uses allocations when they exist,
        falling back to direct transaction.project_id when no allocations exist.

        Args:
            exclude_vat: If True, subtract VAT from amounts (show net amounts)
        """
        if project_id or client_name:
            return await self._get_allocated_amount(
                start_date, end_date, TransactionSide.CREDIT,
                project_id=project_id, client_name=client_name,
                category_filter="revenue",
                exclude_vat=exclude_vat
            )

        # No project/client filter - standard query
        # Use amount - vat_amount if exclude_vat is True
        if exclude_vat:
            amount_expr = Transaction.amount - func.coalesce(Transaction.vat_amount, 0)
        else:
            amount_expr = Transaction.amount

        query = select(func.coalesce(func.sum(amount_expr), 0)).where(
            and_(
                Transaction.side == TransactionSide.CREDIT,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_excluded_from_reports == False,
            )
        )

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
        client_name: Optional[str] = None,
        exclude_vat: bool = False,
    ) -> Decimal:
        """
        Get total expenses for period.

        If project_id or client_name is specified, uses allocations when they exist,
        falling back to direct transaction.project_id when no allocations exist.

        Args:
            exclude_vat: If True, subtract VAT from amounts (show net amounts)
        """
        if project_id or client_name:
            return await self._get_allocated_amount(
                start_date, end_date, TransactionSide.DEBIT,
                project_id=project_id, client_name=client_name,
                exclude_vat=exclude_vat
            )

        # No project/client filter - standard query
        # Use amount - vat_amount if exclude_vat is True
        if exclude_vat:
            amount_expr = Transaction.amount - func.coalesce(Transaction.vat_amount, 0)
        else:
            amount_expr = Transaction.amount

        query = select(func.coalesce(func.sum(amount_expr), 0)).where(
            and_(
                Transaction.side == TransactionSide.DEBIT,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_excluded_from_reports == False,
            )
        )

        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    async def _get_allocated_amount(
        self,
        start_date: date,
        end_date: date,
        side: TransactionSide,
        project_id: Optional[int] = None,
        client_name: Optional[str] = None,
        category_filter: Optional[str] = None,
        exclude_vat: bool = False,
    ) -> Decimal:
        """
        Get amounts considering allocations for project/client filtering.

        Logic:
        1. Sum amount_allocated from allocations matching project_id/client_name
        2. For transactions without allocations, use full amount if they match
           the project_id (fallback behavior)

        Args:
            exclude_vat: If True, calculate net amounts by subtracting VAT proportionally
        """
        # Part 1: Sum from allocations
        # When exclude_vat is True, we need to calculate the net portion of the allocation
        # Net allocation = allocation.amount_allocated * (1 - vat_amount/amount)
        if exclude_vat:
            # Calculate net allocation: amount_allocated * (amount - vat_amount) / amount
            # This is equivalent to: amount_allocated - (amount_allocated * vat_amount / amount)
            vat_ratio = func.coalesce(Transaction.vat_amount, 0) / Transaction.amount
            net_amount_expr = TransactionAllocation.amount_allocated * (1 - vat_ratio)
            alloc_sum_expr = func.coalesce(func.sum(net_amount_expr), 0)
        else:
            alloc_sum_expr = func.coalesce(func.sum(TransactionAllocation.amount_allocated), 0)

        alloc_query = (
            select(alloc_sum_expr)
            .join(Transaction, TransactionAllocation.transaction_id == Transaction.id)
            .where(
                and_(
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_excluded_from_reports == False,
                    Transaction.side == side,
                )
            )
        )

        # Apply category filter for revenue if needed
        if category_filter == "revenue":
            alloc_query = alloc_query.join(Category, Transaction.category_id == Category.id, isouter=True).where(
                or_(
                    Category.type.in_([CategoryType.REVENUE, CategoryType.OTHER_INCOME]),
                    Transaction.category_id.is_(None)
                )
            )

        # Filter by project_id and/or client_name
        allocation_conditions = []
        if project_id:
            allocation_conditions.append(TransactionAllocation.project_id == project_id)
        if client_name:
            allocation_conditions.append(TransactionAllocation.client_name == client_name)

        if allocation_conditions:
            alloc_query = alloc_query.where(or_(*allocation_conditions))

        result = await self.db.execute(alloc_query)
        allocated_total = Decimal(str(result.scalar() or 0))

        # Part 2: Fallback - transactions with project_id but NO allocations
        if project_id:
            # Get IDs of transactions that have allocations
            subquery = (
                select(TransactionAllocation.transaction_id)
                .distinct()
            )

            # Use net amount if exclude_vat
            if exclude_vat:
                amount_expr = Transaction.amount - func.coalesce(Transaction.vat_amount, 0)
            else:
                amount_expr = Transaction.amount

            fallback_query = select(func.coalesce(func.sum(amount_expr), 0)).where(
                and_(
                    Transaction.project_id == project_id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_excluded_from_reports == False,
                    Transaction.side == side,
                    ~Transaction.id.in_(subquery),  # Not in allocations table
                )
            )

            if category_filter == "revenue":
                fallback_query = fallback_query.join(Category, isouter=True).where(
                    or_(
                        Category.type.in_([CategoryType.REVENUE, CategoryType.OTHER_INCOME]),
                        Transaction.category_id.is_(None)
                    )
                )

            result = await self.db.execute(fallback_query)
            fallback_total = Decimal(str(result.scalar() or 0))
        else:
            fallback_total = Decimal("0")

        return allocated_total + fallback_total

    async def get_amounts_by_category_type(
        self,
        start_date: date,
        end_date: date,
        category_type: CategoryType,
        project_id: Optional[int] = None,
        client_name: Optional[str] = None,
    ) -> Decimal:
        """Get total amount for a specific category type, considering allocations."""
        if project_id or client_name:
            # Use allocation-aware calculation
            return await self._get_allocated_category_amount(
                start_date, end_date, category_type, project_id, client_name
            )

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

        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    async def _get_allocated_category_amount(
        self,
        start_date: date,
        end_date: date,
        category_type: CategoryType,
        project_id: Optional[int] = None,
        client_name: Optional[str] = None,
    ) -> Decimal:
        """Get category amount considering allocations."""
        # Part 1: Sum from allocations
        alloc_query = (
            select(func.coalesce(func.sum(TransactionAllocation.amount_allocated), 0))
            .join(Transaction, TransactionAllocation.transaction_id == Transaction.id)
            .join(Category, Transaction.category_id == Category.id)
            .where(
                and_(
                    Category.type == category_type,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_excluded_from_reports == False,
                )
            )
        )

        allocation_conditions = []
        if project_id:
            allocation_conditions.append(TransactionAllocation.project_id == project_id)
        if client_name:
            allocation_conditions.append(TransactionAllocation.client_name == client_name)

        if allocation_conditions:
            alloc_query = alloc_query.where(or_(*allocation_conditions))

        result = await self.db.execute(alloc_query)
        allocated_total = Decimal(str(result.scalar() or 0))

        # Part 2: Fallback for transactions without allocations
        if project_id:
            subquery = select(TransactionAllocation.transaction_id).distinct()

            fallback_query = (
                select(func.coalesce(func.sum(Transaction.amount), 0))
                .join(Category)
                .where(
                    and_(
                        Category.type == category_type,
                        Transaction.project_id == project_id,
                        Transaction.transaction_date >= start_date,
                        Transaction.transaction_date <= end_date,
                        Transaction.is_excluded_from_reports == False,
                        ~Transaction.id.in_(subquery),
                    )
                )
            )

            result = await self.db.execute(fallback_query)
            fallback_total = Decimal(str(result.scalar() or 0))
        else:
            fallback_total = Decimal("0")

        return allocated_total + fallback_total

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

    # =========================================================================
    # Client Aggregation Methods (using allocations)
    # =========================================================================

    async def get_all_clients_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Get financial summary aggregated by client_name from allocations.

        Returns clients with their total revenue, expenses, and profit.
        """
        # Get unique client names from allocations
        client_query = (
            select(TransactionAllocation.client_name)
            .join(Transaction, TransactionAllocation.transaction_id == Transaction.id)
            .where(
                and_(
                    TransactionAllocation.client_name.isnot(None),
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_excluded_from_reports == False,
                )
            )
            .distinct()
        )

        result = await self.db.execute(client_query)
        client_names = [row[0] for row in result.fetchall()]

        # Also get clients from projects that have no allocations (fallback)
        project_client_query = (
            select(Project.client_name)
            .join(Transaction, Transaction.project_id == Project.id)
            .where(
                and_(
                    Project.client_name.isnot(None),
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_excluded_from_reports == False,
                    ~Transaction.id.in_(
                        select(TransactionAllocation.transaction_id).distinct()
                    ),
                )
            )
            .distinct()
        )

        result = await self.db.execute(project_client_query)
        for row in result.fetchall():
            if row[0] and row[0] not in client_names:
                client_names.append(row[0])

        # Get summary for each client
        summaries = []
        for client_name in sorted(client_names):
            revenue = await self.get_total_revenue(start_date, end_date, client_name=client_name)
            expenses = await self.get_total_expenses(start_date, end_date, client_name=client_name)
            profit = revenue - expenses
            margin = self._calculate_percentage(profit, revenue)

            summaries.append({
                "client_name": client_name,
                "total_revenue": revenue,
                "total_expenses": expenses,
                "net_profit": profit,
                "profit_margin": margin,
            })

        return summaries

    async def get_client_projects_summary(
        self,
        client_name: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Get project breakdown for a specific client.

        Returns all projects with allocations for this client.
        """
        # Get projects from allocations
        project_query = (
            select(
                TransactionAllocation.project_id,
                Project.name,
                Project.code,
                func.sum(
                    case(
                        (Transaction.side == TransactionSide.CREDIT,
                         TransactionAllocation.amount_allocated),
                        else_=Decimal("0")
                    )
                ).label("revenue"),
                func.sum(
                    case(
                        (Transaction.side == TransactionSide.DEBIT,
                         TransactionAllocation.amount_allocated),
                        else_=Decimal("0")
                    )
                ).label("expenses"),
            )
            .join(Transaction, TransactionAllocation.transaction_id == Transaction.id)
            .join(Project, TransactionAllocation.project_id == Project.id, isouter=True)
            .where(
                and_(
                    TransactionAllocation.client_name == client_name,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_excluded_from_reports == False,
                )
            )
            .group_by(TransactionAllocation.project_id, Project.name, Project.code)
        )

        result = await self.db.execute(project_query)
        rows = result.fetchall()

        projects = []
        for row in rows:
            revenue = Decimal(str(row.revenue or 0))
            expenses = Decimal(str(row.expenses or 0))
            profit = revenue - expenses
            margin = self._calculate_percentage(profit, revenue)

            projects.append({
                "project_id": row.project_id,
                "project_name": row.name,
                "project_code": row.code,
                "total_revenue": revenue,
                "total_expenses": expenses,
                "net_profit": profit,
                "profit_margin": margin,
            })

        return projects
