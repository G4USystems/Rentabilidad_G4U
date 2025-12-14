"""Financial calculations using Excel/Sheets storage."""

from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any, List
import logging

import pandas as pd

from app.storage.excel_storage import get_storage

logger = logging.getLogger(__name__)


# Category types that count as income
INCOME_TYPES = ['revenue', 'other_income']

# Category types that count as expenses
EXPENSE_TYPES = [
    'cogs', 'operating_expense', 'payroll', 'marketing', 'admin',
    'rent', 'professional_services', 'software', 'travel',
    'taxes', 'interest', 'depreciation', 'other_expense'
]

# Operating expense types (excludes taxes, interest, depreciation)
OPERATING_EXPENSE_TYPES = [
    'operating_expense', 'payroll', 'marketing', 'admin',
    'rent', 'professional_services', 'software', 'travel'
]


class ExcelFinancialService:
    """Financial calculations service using Excel/Sheets data."""

    def __init__(self):
        self.storage = get_storage()

    def _get_transactions_with_categories(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> pd.DataFrame:
        """Get transactions merged with category info."""
        tx_df = self.storage.get_transactions(
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
        )

        if tx_df.empty:
            return tx_df

        # Filter out excluded
        tx_df = tx_df[tx_df['is_excluded'] != True]

        # Get categories
        cat_df = self.storage.get_categories(active_only=False)

        if not cat_df.empty:
            tx_df = tx_df.merge(
                cat_df[['id', 'name', 'type']],
                left_on='category_id',
                right_on='id',
                how='left',
                suffixes=('', '_cat')
            )
            tx_df = tx_df.rename(columns={'name': 'category_name', 'type': 'category_type'})

        return tx_df

    def get_total_revenue(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> float:
        """Get total revenue for period."""
        df = self._get_transactions_with_categories(start_date, end_date, project_id)

        if df.empty:
            return 0.0

        # Income = credit transactions with income category types
        income_df = df[
            (df['side'] == 'credit') &
            (df['category_type'].isin(INCOME_TYPES) | df['category_type'].isna())
        ]

        return float(income_df['amount'].sum())

    def get_total_expenses(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> float:
        """Get total expenses for period."""
        df = self._get_transactions_with_categories(start_date, end_date, project_id)

        if df.empty:
            return 0.0

        # Expenses = debit transactions
        expense_df = df[df['side'] == 'debit']

        return float(expense_df['amount'].sum())

    def get_expenses_by_category_type(
        self,
        start_date: date,
        end_date: date,
        category_type: str,
        project_id: Optional[int] = None,
    ) -> float:
        """Get expenses for a specific category type."""
        df = self._get_transactions_with_categories(start_date, end_date, project_id)

        if df.empty:
            return 0.0

        filtered = df[
            (df['side'] == 'debit') &
            (df['category_type'] == category_type)
        ]

        return float(filtered['amount'].sum())

    def get_breakdown_by_category(
        self,
        start_date: date,
        end_date: date,
        side: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get amount breakdown by category."""
        df = self._get_transactions_with_categories(start_date, end_date, project_id)

        if df.empty:
            return []

        if side:
            df = df[df['side'] == side]

        # Group by category
        grouped = df.groupby(['category_id', 'category_name', 'category_type']).agg({
            'amount': 'sum',
            'id': 'count'
        }).reset_index()

        grouped = grouped.rename(columns={'id': 'transaction_count', 'amount': 'total'})
        grouped = grouped.sort_values('total', ascending=False)

        return grouped.to_dict('records')

    def calculate_pl_summary(
        self,
        start_date: date,
        end_date: date,
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Calculate complete P&L summary."""
        df = self._get_transactions_with_categories(start_date, end_date, project_id)

        if df.empty:
            return self._empty_pl_summary()

        # Revenue
        revenue = df[
            (df['side'] == 'credit') &
            (df['category_type'].isin(INCOME_TYPES) | df['category_type'].isna())
        ]['amount'].sum()

        # COGS
        cogs = df[
            (df['side'] == 'debit') &
            (df['category_type'] == 'cogs')
        ]['amount'].sum()

        # Gross Profit
        gross_profit = revenue - cogs
        gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0

        # Operating Expenses
        operating_expenses = df[
            (df['side'] == 'debit') &
            (df['category_type'].isin(OPERATING_EXPENSE_TYPES))
        ]['amount'].sum()

        # Operating Income
        operating_income = gross_profit - operating_expenses
        operating_margin = (operating_income / revenue * 100) if revenue > 0 else 0

        # Other items
        taxes = df[(df['side'] == 'debit') & (df['category_type'] == 'taxes')]['amount'].sum()
        interest = df[(df['side'] == 'debit') & (df['category_type'] == 'interest')]['amount'].sum()
        depreciation = df[(df['side'] == 'debit') & (df['category_type'] == 'depreciation')]['amount'].sum()
        other_income = df[(df['side'] == 'credit') & (df['category_type'] == 'other_income')]['amount'].sum()
        other_expenses = df[(df['side'] == 'debit') & (df['category_type'] == 'other_expense')]['amount'].sum()

        # EBITDA
        ebitda = operating_income + depreciation
        ebitda_margin = (ebitda / revenue * 100) if revenue > 0 else 0

        # Net Income
        net_income = operating_income - taxes - interest - other_expenses + other_income
        net_margin = (net_income / revenue * 100) if revenue > 0 else 0

        # Transaction counts
        total_transactions = len(df)
        income_transactions = len(df[df['side'] == 'credit'])
        expense_transactions = len(df[df['side'] == 'debit'])

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "revenue": round(float(revenue), 2),
            "cogs": round(float(cogs), 2),
            "gross_profit": round(float(gross_profit), 2),
            "gross_margin": round(float(gross_margin), 2),
            "operating_expenses": round(float(operating_expenses), 2),
            "operating_income": round(float(operating_income), 2),
            "operating_margin": round(float(operating_margin), 2),
            "ebitda": round(float(ebitda), 2),
            "ebitda_margin": round(float(ebitda_margin), 2),
            "taxes": round(float(taxes), 2),
            "interest": round(float(interest), 2),
            "depreciation": round(float(depreciation), 2),
            "other_income": round(float(other_income), 2),
            "other_expenses": round(float(other_expenses), 2),
            "net_income": round(float(net_income), 2),
            "net_margin": round(float(net_margin), 2),
            "total_transactions": total_transactions,
            "income_transactions": income_transactions,
            "expense_transactions": expense_transactions,
        }

    def _empty_pl_summary(self) -> Dict[str, Any]:
        """Return empty P&L summary."""
        return {
            "revenue": 0, "cogs": 0, "gross_profit": 0, "gross_margin": 0,
            "operating_expenses": 0, "operating_income": 0, "operating_margin": 0,
            "ebitda": 0, "ebitda_margin": 0, "taxes": 0, "interest": 0,
            "depreciation": 0, "other_income": 0, "other_expenses": 0,
            "net_income": 0, "net_margin": 0,
            "total_transactions": 0, "income_transactions": 0, "expense_transactions": 0,
        }

    def calculate_project_kpis(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Calculate KPIs for a specific project."""
        project = self.storage.get_project(project_id)
        if not project:
            return None

        # Get all project transactions
        tx_df = self.storage.get_transactions(project_id=project_id)

        if tx_df.empty:
            total_income = 0
            total_expenses = 0
            tx_count = 0
        else:
            total_income = float(tx_df[tx_df['side'] == 'credit']['amount'].sum())
            total_expenses = float(tx_df[tx_df['side'] == 'debit']['amount'].sum())
            tx_count = len(tx_df)

        net_profit = total_income - total_expenses
        profit_margin = (net_profit / total_income * 100) if total_income > 0 else 0
        roi = (net_profit / total_expenses * 100) if total_expenses > 0 else None

        # Budget metrics
        budget = project.get('budget_amount')
        budget_used_pct = None
        budget_remaining = None

        if budget and budget > 0:
            budget_used_pct = (total_expenses / budget * 100)
            budget_remaining = budget - total_expenses

        return {
            "project_id": project_id,
            "project_name": project.get('name'),
            "project_code": project.get('code'),
            "client_name": project.get('client_name'),
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2),
            "profit_margin": round(profit_margin, 2),
            "roi": round(roi, 2) if roi else None,
            "budget_amount": budget,
            "budget_used_percentage": round(budget_used_pct, 2) if budget_used_pct else None,
            "budget_remaining": round(budget_remaining, 2) if budget_remaining else None,
            "transaction_count": tx_count,
        }

    def get_dashboard_kpis(self) -> Dict[str, Any]:
        """Get KPIs for dashboard."""
        from datetime import date
        from calendar import monthrange

        today = date.today()

        # Current month
        current_start = today.replace(day=1)
        _, last_day = monthrange(today.year, today.month)
        current_end = today.replace(day=last_day)

        # Previous month
        if today.month == 1:
            prev_start = date(today.year - 1, 12, 1)
            prev_end = date(today.year - 1, 12, 31)
        else:
            prev_start = date(today.year, today.month - 1, 1)
            _, last_day = monthrange(today.year, today.month - 1)
            prev_end = date(today.year, today.month - 1, last_day)

        # YTD
        ytd_start = date(today.year, 1, 1)

        current = self.calculate_pl_summary(current_start, current_end)
        previous = self.calculate_pl_summary(prev_start, prev_end)
        ytd = self.calculate_pl_summary(ytd_start, today)

        # MoM changes
        revenue_change = None
        if previous['revenue'] > 0:
            revenue_change = ((current['revenue'] - previous['revenue']) / previous['revenue'] * 100)

        return {
            "current_month": current,
            "previous_month": previous,
            "year_to_date": ytd,
            "month_over_month": {
                "revenue_change": round(revenue_change, 2) if revenue_change else None,
            },
            "expense_breakdown": self.get_breakdown_by_category(
                current_start, current_end, side='debit'
            )[:5],
        }
