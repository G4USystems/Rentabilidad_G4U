"""Service for generating P&L reports."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionSide
from app.models.category import Category, CategoryType
from app.schemas.reports import (
    PLReportRequest,
    PLReportResponse,
    PLLineItem,
    PLSection,
    ReportPeriod,
)
from app.services.financial_service import FinancialService

logger = logging.getLogger(__name__)


class PLReportService:
    """Service for generating Profit & Loss reports."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.financial = FinancialService(db)

    async def generate_report(
        self,
        request: PLReportRequest,
    ) -> PLReportResponse:
        """
        Generate a complete P&L report.

        Args:
            request: Report parameters

        Returns:
            Complete P&L report
        """
        logger.info(f"Generating P&L report from {request.start_date} to {request.end_date}")

        # Get revenue section
        revenue_section = await self._build_section(
            "Ingresos / Revenue",
            request.start_date,
            request.end_date,
            [CategoryType.REVENUE],
            TransactionSide.CREDIT,
            request.project_id,
        )

        # Get COGS section
        cogs_section = await self._build_section(
            "Costo de Ventas / COGS",
            request.start_date,
            request.end_date,
            [CategoryType.COGS],
            TransactionSide.DEBIT,
            request.project_id,
        )

        # Calculate gross profit
        gross_profit = revenue_section.total - cogs_section.total
        gross_margin = self._calculate_margin(gross_profit, revenue_section.total)

        # Get operating expenses section
        operating_section = await self._build_section(
            "Gastos Operativos / Operating Expenses",
            request.start_date,
            request.end_date,
            [
                CategoryType.OPERATING_EXPENSE,
                CategoryType.PAYROLL,
                CategoryType.MARKETING,
                CategoryType.ADMIN,
                CategoryType.RENT,
                CategoryType.PROFESSIONAL_SERVICES,
                CategoryType.SOFTWARE,
                CategoryType.TRAVEL,
            ],
            TransactionSide.DEBIT,
            request.project_id,
        )

        # Calculate operating income
        operating_income = gross_profit - operating_section.total
        operating_margin = self._calculate_margin(operating_income, revenue_section.total)

        # Get other income section
        other_income_section = await self._build_section(
            "Otros Ingresos / Other Income",
            request.start_date,
            request.end_date,
            [CategoryType.OTHER_INCOME],
            TransactionSide.CREDIT,
            request.project_id,
        )

        # Get other expenses section
        other_expenses_section = await self._build_section(
            "Otros Gastos / Other Expenses",
            request.start_date,
            request.end_date,
            [
                CategoryType.TAXES,
                CategoryType.INTEREST,
                CategoryType.DEPRECIATION,
                CategoryType.OTHER_EXPENSE,
            ],
            TransactionSide.DEBIT,
            request.project_id,
        )

        # Calculate net income
        net_income = (
            operating_income
            + other_income_section.total
            - other_expenses_section.total
        )
        net_margin = self._calculate_margin(net_income, revenue_section.total)

        # Calculate EBITDA
        depreciation = await self._get_category_total(
            request.start_date,
            request.end_date,
            CategoryType.DEPRECIATION,
            request.project_id,
        )
        interest = await self._get_category_total(
            request.start_date,
            request.end_date,
            CategoryType.INTEREST,
            request.project_id,
        )
        taxes = await self._get_category_total(
            request.start_date,
            request.end_date,
            CategoryType.TAXES,
            request.project_id,
        )

        ebitda = net_income + depreciation + interest + taxes
        ebitda_margin = self._calculate_margin(ebitda, revenue_section.total)

        # Get transaction counts
        counts = await self.financial.get_transaction_counts(
            request.start_date,
            request.end_date,
            request.project_id,
        )

        # Calculate totals
        total_revenue = revenue_section.total + other_income_section.total
        total_expenses = cogs_section.total + operating_section.total + other_expenses_section.total

        # Get project name if applicable
        project_name = None
        if request.project_id:
            from app.models.project import Project
            result = await self.db.execute(
                select(Project.name).where(Project.id == request.project_id)
            )
            project_name = result.scalar_one_or_none()

        # Build report
        report = PLReportResponse(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.utcnow(),
            start_date=request.start_date,
            end_date=request.end_date,
            period=request.period,
            currency=request.currency,
            project_id=request.project_id,
            project_name=project_name,
            revenue=revenue_section,
            cogs=cogs_section,
            gross_profit=gross_profit,
            gross_margin=gross_margin,
            operating_expenses=operating_section,
            operating_income=operating_income,
            operating_margin=operating_margin,
            other_income=other_income_section,
            other_expenses=other_expenses_section,
            ebitda=ebitda,
            ebitda_margin=ebitda_margin,
            net_income=net_income,
            net_margin=net_margin,
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            total_transactions=counts["total"],
        )

        # Add previous period comparison if requested
        if request.compare_previous_period:
            previous = await self._get_previous_period_report(request)
            report.previous_period = previous

        return report

    async def _build_section(
        self,
        name: str,
        start_date: date,
        end_date: date,
        category_types: List[CategoryType],
        side: TransactionSide,
        project_id: Optional[int] = None,
    ) -> PLSection:
        """Build a P&L section with line items."""

        # Get categories with these types
        query = (
            select(
                Category.id,
                Category.name,
                Category.type,
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .select_from(Category)
            .outerjoin(
                Transaction,
                and_(
                    Transaction.category_id == Category.id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date,
                    Transaction.is_excluded_from_reports == False,
                    Transaction.side == side,
                    (Transaction.project_id == project_id) if project_id else True,
                ),
            )
            .where(Category.type.in_(category_types))
            .group_by(Category.id, Category.name, Category.type)
            .order_by(func.sum(Transaction.amount).desc().nulls_last())
        )

        result = await self.db.execute(query)
        rows = result.all()

        items = []
        section_total = Decimal("0")

        for row in rows:
            amount = Decimal(str(row.total or 0))
            if amount > 0:
                items.append(
                    PLLineItem(
                        category_id=row.id,
                        category_name=row.name,
                        category_type=row.type.value,
                        amount=amount,
                        transaction_count=row.count or 0,
                    )
                )
                section_total += amount

        # Also get uncategorized transactions of this side
        uncategorized = await self._get_uncategorized_total(
            start_date, end_date, side, project_id
        )
        if uncategorized > 0:
            items.append(
                PLLineItem(
                    category_id=None,
                    category_name="Sin Categorizar",
                    category_type="uncategorized",
                    amount=uncategorized,
                    transaction_count=0,
                )
            )
            section_total += uncategorized

        return PLSection(
            name=name,
            total=section_total,
            items=items,
        )

    async def _get_category_total(
        self,
        start_date: date,
        end_date: date,
        category_type: CategoryType,
        project_id: Optional[int] = None,
    ) -> Decimal:
        """Get total amount for a category type."""
        return await self.financial.get_amounts_by_category_type(
            start_date, end_date, category_type, project_id
        )

    async def _get_uncategorized_total(
        self,
        start_date: date,
        end_date: date,
        side: TransactionSide,
        project_id: Optional[int] = None,
    ) -> Decimal:
        """Get total of uncategorized transactions."""
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            and_(
                Transaction.category_id.is_(None),
                Transaction.side == side,
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_excluded_from_reports == False,
            )
        )

        if project_id:
            query = query.where(Transaction.project_id == project_id)

        result = await self.db.execute(query)
        return Decimal(str(result.scalar() or 0))

    def _calculate_margin(self, value: Decimal, base: Decimal) -> Decimal:
        """Calculate margin percentage."""
        if base == 0:
            return Decimal("0")
        return (value / base * 100).quantize(Decimal("0.01"))

    async def _get_previous_period_report(
        self,
        request: PLReportRequest,
    ) -> Optional[PLReportResponse]:
        """Get report for previous period."""
        from dateutil.relativedelta import relativedelta

        # Calculate previous period dates
        duration = request.end_date - request.start_date
        previous_end = request.start_date - relativedelta(days=1)
        previous_start = previous_end - duration

        # Generate previous period report
        previous_request = PLReportRequest(
            start_date=previous_start,
            end_date=previous_end,
            period=request.period,
            project_id=request.project_id,
            currency=request.currency,
            compare_previous_period=False,
        )

        return await self.generate_report(previous_request)

    async def get_summary(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get a quick P&L summary without full breakdown."""
        financials = await self.financial.calculate_net_income(
            start_date, end_date, project_id
        )
        counts = await self.financial.get_transaction_counts(
            start_date, end_date, project_id
        )

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "revenue": float(financials["revenue"]),
            "cogs": float(financials["cogs"]),
            "gross_profit": float(financials["gross_profit"]),
            "gross_margin": float(financials["gross_margin"]),
            "operating_expenses": float(financials["operating_expenses"]),
            "operating_income": float(financials["operating_income"]),
            "operating_margin": float(financials["operating_margin"]),
            "ebitda": float(financials["ebitda"]),
            "ebitda_margin": float(financials["ebitda_margin"]),
            "net_income": float(financials["net_income"]),
            "net_margin": float(financials["net_margin"]),
            "transaction_count": counts["total"],
        }
