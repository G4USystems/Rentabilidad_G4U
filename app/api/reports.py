"""API endpoints for P&L reports."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json
import io

from app.core.database import get_db
from app.schemas.reports import (
    PLReportRequest,
    PLReportResponse,
    ReportPeriod,
)
from app.services.pl_report_service import PLReportService

router = APIRouter()


@router.get("/pl", response_model=PLReportResponse)
async def generate_pl_report(
    start_date: date,
    end_date: date,
    period: ReportPeriod = ReportPeriod.MONTHLY,
    project_id: Optional[int] = None,
    compare_previous: bool = False,
    currency: str = "EUR",
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a Profit & Loss report.

    Args:
        start_date: Report period start
        end_date: Report period end
        period: Period type for grouping
        project_id: Filter by project (optional)
        compare_previous: Include previous period comparison
        currency: Report currency
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date"
        )

    request = PLReportRequest(
        start_date=start_date,
        end_date=end_date,
        period=period,
        project_id=project_id,
        compare_previous_period=compare_previous,
        currency=currency,
    )

    service = PLReportService(db)
    report = await service.generate_report(request)

    return report


@router.get("/pl/summary")
async def get_pl_summary(
    start_date: date,
    end_date: date,
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a quick P&L summary without full breakdown.

    Returns key metrics: revenue, expenses, gross profit, net income, margins.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before end_date"
        )

    service = PLReportService(db)
    summary = await service.get_summary(start_date, end_date, project_id)

    return summary


@router.get("/pl/monthly")
async def get_monthly_pl(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get P&L report for a specific month."""
    from calendar import monthrange

    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)

    request = PLReportRequest(
        start_date=start_date,
        end_date=end_date,
        period=ReportPeriod.MONTHLY,
        project_id=project_id,
    )

    service = PLReportService(db)
    return await service.generate_report(request)


@router.get("/pl/quarterly")
async def get_quarterly_pl(
    year: int = Query(..., ge=2000, le=2100),
    quarter: int = Query(..., ge=1, le=4),
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get P&L report for a specific quarter."""
    quarter_starts = {
        1: (1, 3),
        2: (4, 6),
        3: (7, 9),
        4: (10, 12),
    }

    start_month, end_month = quarter_starts[quarter]
    from calendar import monthrange

    start_date = date(year, start_month, 1)
    _, last_day = monthrange(year, end_month)
    end_date = date(year, end_month, last_day)

    request = PLReportRequest(
        start_date=start_date,
        end_date=end_date,
        period=ReportPeriod.QUARTERLY,
        project_id=project_id,
    )

    service = PLReportService(db)
    return await service.generate_report(request)


@router.get("/pl/yearly")
async def get_yearly_pl(
    year: int = Query(..., ge=2000, le=2100),
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get P&L report for a full year."""
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    request = PLReportRequest(
        start_date=start_date,
        end_date=end_date,
        period=ReportPeriod.YEARLY,
        project_id=project_id,
    )

    service = PLReportService(db)
    return await service.generate_report(request)


@router.post("/pl/export/json")
async def export_pl_json(
    request: PLReportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export P&L report as JSON file."""
    service = PLReportService(db)
    report = await service.generate_report(request)

    # Convert to JSON
    content = report.model_dump_json(indent=2)

    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=pl_report_{request.start_date}_{request.end_date}.json"
        },
    )


@router.post("/pl/export/csv")
async def export_pl_csv(
    request: PLReportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export P&L report as CSV file."""
    service = PLReportService(db)
    report = await service.generate_report(request)

    # Build CSV content
    lines = []
    lines.append("Rentabilidad G4U - Estado de Resultados (P&L)")
    lines.append(f"Período: {report.start_date} - {report.end_date}")
    if report.project_name:
        lines.append(f"Proyecto: {report.project_name}")
    lines.append("")
    lines.append("Categoría,Tipo,Monto,% de Ingresos,Transacciones")

    # Revenue
    lines.append("")
    lines.append("INGRESOS,,,,")
    for item in report.revenue.items:
        pct = f"{item.percentage_of_revenue:.1f}%" if item.percentage_of_revenue else ""
        lines.append(f"{item.category_name},{item.category_type},{item.amount},{pct},{item.transaction_count}")
    lines.append(f"Total Ingresos,,{report.revenue.total},,")

    # COGS
    lines.append("")
    lines.append("COSTO DE VENTAS,,,,")
    for item in report.cogs.items:
        lines.append(f"{item.category_name},{item.category_type},{item.amount},,{item.transaction_count}")
    lines.append(f"Total COGS,,{report.cogs.total},,")

    # Gross Profit
    lines.append("")
    lines.append(f"UTILIDAD BRUTA,,{report.gross_profit},{report.gross_margin}%,")

    # Operating Expenses
    lines.append("")
    lines.append("GASTOS OPERATIVOS,,,,")
    for item in report.operating_expenses.items:
        lines.append(f"{item.category_name},{item.category_type},{item.amount},,{item.transaction_count}")
    lines.append(f"Total Gastos Operativos,,{report.operating_expenses.total},,")

    # Operating Income
    lines.append("")
    lines.append(f"UTILIDAD OPERATIVA,,{report.operating_income},{report.operating_margin}%,")

    # EBITDA
    if report.ebitda:
        lines.append(f"EBITDA,,{report.ebitda},{report.ebitda_margin}%,")

    # Net Income
    lines.append("")
    lines.append(f"UTILIDAD NETA,,{report.net_income},{report.net_margin}%,")

    content = "\n".join(lines)

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8-sig")),  # UTF-8 with BOM for Excel
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=pl_report_{request.start_date}_{request.end_date}.csv"
        },
    )
