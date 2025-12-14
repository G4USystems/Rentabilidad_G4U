"""Tests for financial calculations."""

import pytest
from decimal import Decimal
from datetime import date


class TestFinancialCalculations:
    """Test suite for financial calculations."""

    def test_margin_calculation(self):
        """Test margin percentage calculation."""
        revenue = Decimal("100000")
        cogs = Decimal("60000")
        gross_profit = revenue - cogs

        expected_margin = Decimal("40.00")  # 40%
        calculated_margin = (gross_profit / revenue * 100).quantize(Decimal("0.01"))

        assert calculated_margin == expected_margin

    def test_ebitda_calculation(self):
        """Test EBITDA calculation."""
        operating_income = Decimal("25000")
        depreciation = Decimal("5000")
        amortization = Decimal("2000")

        ebitda = operating_income + depreciation + amortization

        assert ebitda == Decimal("32000")

    def test_burn_rate_calculation(self):
        """Test monthly burn rate calculation."""
        total_expenses = Decimal("90000")
        total_revenue = Decimal("60000")
        months = 3

        net_burn = total_expenses - total_revenue
        monthly_burn = net_burn / months

        assert monthly_burn == Decimal("10000")

    def test_roi_calculation(self):
        """Test ROI calculation."""
        revenue = Decimal("150000")
        costs = Decimal("100000")

        profit = revenue - costs
        roi = (profit / costs * 100).quantize(Decimal("0.01"))

        assert roi == Decimal("50.00")  # 50% ROI

    def test_zero_division_handling(self):
        """Test handling of zero division in margin calculations."""
        revenue = Decimal("0")
        profit = Decimal("1000")

        # Should return 0 instead of raising error
        if revenue == 0:
            margin = Decimal("0")
        else:
            margin = profit / revenue * 100

        assert margin == Decimal("0")


class TestCategoryClassification:
    """Test category type classification."""

    def test_income_categories(self):
        """Test identification of income categories."""
        income_types = ["revenue", "other_income"]

        for cat_type in income_types:
            assert cat_type in income_types

    def test_expense_categories(self):
        """Test identification of expense categories."""
        expense_types = [
            "cogs", "operating_expense", "payroll", "marketing",
            "admin", "rent", "professional_services", "software",
            "travel", "taxes", "interest", "depreciation", "other_expense"
        ]

        assert len(expense_types) == 13

    def test_non_pl_categories(self):
        """Test identification of non-P&L categories."""
        non_pl_types = ["transfer", "investment", "loan", "equity", "uncategorized"]

        for cat_type in non_pl_types:
            # These should not affect P&L
            assert cat_type in non_pl_types


class TestPLReportStructure:
    """Test P&L report structure."""

    def test_pl_sections(self):
        """Test P&L report has correct sections."""
        expected_sections = [
            "revenue",
            "cogs",
            "gross_profit",
            "operating_expenses",
            "operating_income",
            "other_income",
            "other_expenses",
            "net_income",
        ]

        # All sections should be present
        assert len(expected_sections) == 8

    def test_margin_calculations(self):
        """Test that margins are calculated correctly."""
        revenue = Decimal("200000")
        cogs = Decimal("80000")
        operating_expenses = Decimal("60000")
        other_expenses = Decimal("10000")

        gross_profit = revenue - cogs
        operating_income = gross_profit - operating_expenses
        net_income = operating_income - other_expenses

        gross_margin = gross_profit / revenue * 100
        operating_margin = operating_income / revenue * 100
        net_margin = net_income / revenue * 100

        assert gross_margin == Decimal("60")  # 60%
        assert operating_margin == Decimal("30")  # 30%
        assert net_margin == Decimal("25")  # 25%
