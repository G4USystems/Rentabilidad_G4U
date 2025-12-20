"""Service for managing alerts and automatic notifications."""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional
import logging

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.models.project import Project
from app.models.transaction import Transaction, TransactionSide, ReviewStatus
from app.models.transaction_allocation import TransactionAllocation
from app.services.financial_service import FinancialService

logger = logging.getLogger(__name__)


class AlertConfig:
    """Configuration for alert thresholds."""

    # Margin alerts
    LOW_MARGIN_WARNING = Decimal("15.0")  # 15% margin warning
    LOW_MARGIN_CRITICAL = Decimal("5.0")  # 5% margin critical

    # Budget alerts
    BUDGET_WARNING_PERCENT = Decimal("80.0")  # 80% of budget used
    BUDGET_EXCEEDED_PERCENT = Decimal("100.0")  # Budget exceeded

    # Expense alerts
    UNUSUAL_EXPENSE_MULTIPLIER = Decimal("3.0")  # 3x average = unusual

    # Review alerts
    PENDING_REVIEW_DAYS = 7  # Alert after 7 days pending


class AlertService:
    """Service for creating and managing alerts."""

    def __init__(self, db: AsyncSession, config: Optional[AlertConfig] = None):
        self.db = db
        self.financial = FinancialService(db)
        self.config = config or AlertConfig()

    async def check_all_alerts(self) -> List[Alert]:
        """Run all alert checks and create new alerts."""
        alerts = []

        # Check various conditions
        alerts.extend(await self.check_low_margin_alerts())
        alerts.extend(await self.check_budget_exceeded_alerts())
        alerts.extend(await self.check_pending_review_alerts())
        alerts.extend(await self.check_missing_allocation_alerts())

        return alerts

    async def check_low_margin_alerts(self) -> List[Alert]:
        """Check for projects with low profit margins."""
        alerts = []

        # Get active projects
        query = select(Project).where(Project.is_active == True)
        result = await self.db.execute(query)
        projects = result.scalars().all()

        for project in projects:
            # Calculate project margin
            revenue, expenses = await self._get_project_financials(project.id)
            if revenue > 0:
                margin = ((revenue - expenses) / revenue) * 100

                # Check thresholds
                if margin <= self.config.LOW_MARGIN_CRITICAL:
                    alert = await self._create_alert_if_not_exists(
                        alert_type=AlertType.LOW_MARGIN,
                        severity=AlertSeverity.CRITICAL,
                        title=f"Critical: Low margin on {project.name}",
                        message=f"Project '{project.name}' has only {margin:.1f}% margin. "
                                f"Revenue: {revenue:.2f}, Expenses: {expenses:.2f}",
                        project_id=project.id,
                        threshold_value=self.config.LOW_MARGIN_CRITICAL,
                        actual_value=Decimal(str(margin)),
                    )
                    if alert:
                        alerts.append(alert)

                elif margin <= self.config.LOW_MARGIN_WARNING:
                    alert = await self._create_alert_if_not_exists(
                        alert_type=AlertType.LOW_MARGIN,
                        severity=AlertSeverity.WARNING,
                        title=f"Warning: Low margin on {project.name}",
                        message=f"Project '{project.name}' has {margin:.1f}% margin. "
                                f"Consider reviewing expenses.",
                        project_id=project.id,
                        threshold_value=self.config.LOW_MARGIN_WARNING,
                        actual_value=Decimal(str(margin)),
                    )
                    if alert:
                        alerts.append(alert)

        return alerts

    async def check_budget_exceeded_alerts(self) -> List[Alert]:
        """Check for projects exceeding budget."""
        alerts = []

        # Get projects with budget
        query = select(Project).where(
            and_(
                Project.is_active == True,
                Project.budget_amount.isnot(None),
                Project.budget_amount > 0,
            )
        )
        result = await self.db.execute(query)
        projects = result.scalars().all()

        for project in projects:
            _, expenses = await self._get_project_financials(project.id)
            budget = float(project.budget_amount)
            usage_percent = (expenses / budget) * 100 if budget > 0 else 0

            if usage_percent >= 100:
                alert = await self._create_alert_if_not_exists(
                    alert_type=AlertType.BUDGET_EXCEEDED,
                    severity=AlertSeverity.CRITICAL,
                    title=f"Budget exceeded: {project.name}",
                    message=f"Project '{project.name}' has exceeded budget by "
                            f"{usage_percent - 100:.1f}%. "
                            f"Budget: {budget:.2f}, Spent: {expenses:.2f}",
                    project_id=project.id,
                    threshold_value=Decimal(str(budget)),
                    actual_value=Decimal(str(expenses)),
                )
                if alert:
                    alerts.append(alert)

            elif usage_percent >= float(self.config.BUDGET_WARNING_PERCENT):
                alert = await self._create_alert_if_not_exists(
                    alert_type=AlertType.BUDGET_EXCEEDED,
                    severity=AlertSeverity.WARNING,
                    title=f"Budget warning: {project.name}",
                    message=f"Project '{project.name}' has used {usage_percent:.1f}% of budget. "
                            f"Budget: {budget:.2f}, Spent: {expenses:.2f}",
                    project_id=project.id,
                    threshold_value=Decimal(str(budget * 0.8)),
                    actual_value=Decimal(str(expenses)),
                )
                if alert:
                    alerts.append(alert)

        return alerts

    async def check_pending_review_alerts(self) -> List[Alert]:
        """Check for transactions pending review for too long."""
        alerts = []
        cutoff_date = datetime.utcnow() - relativedelta(days=self.config.PENDING_REVIEW_DAYS)

        query = select(func.count(Transaction.id)).where(
            and_(
                Transaction.review_status == ReviewStatus.PENDING,
                Transaction.created_at <= cutoff_date,
            )
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0

        if count > 0:
            alert = await self._create_alert_if_not_exists(
                alert_type=AlertType.PENDING_REVIEW,
                severity=AlertSeverity.INFO,
                title=f"{count} transactions pending review",
                message=f"There are {count} transactions that have been pending review "
                        f"for more than {self.config.PENDING_REVIEW_DAYS} days.",
                threshold_value=Decimal(str(self.config.PENDING_REVIEW_DAYS)),
                actual_value=Decimal(str(count)),
            )
            if alert:
                alerts.append(alert)

        return alerts

    async def check_missing_allocation_alerts(self) -> List[Alert]:
        """Check for transactions without allocations."""
        alerts = []

        # Find transactions without any allocations
        subquery = (
            select(TransactionAllocation.transaction_id)
            .distinct()
        )

        query = select(func.count(Transaction.id)).where(
            and_(
                Transaction.id.notin_(subquery),
                Transaction.is_excluded == False,
            )
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0

        if count > 10:  # Only alert if significant number
            alert = await self._create_alert_if_not_exists(
                alert_type=AlertType.MISSING_ALLOCATION,
                severity=AlertSeverity.WARNING,
                title=f"{count} transactions without allocation",
                message=f"There are {count} transactions that haven't been allocated "
                        f"to any project or client. Consider reviewing them.",
                actual_value=Decimal(str(count)),
            )
            if alert:
                alerts.append(alert)

        return alerts

    async def _get_project_financials(self, project_id: int) -> tuple:
        """Get project revenue and expenses."""
        revenue = await self.financial.get_project_revenue(project_id)
        expenses = await self.financial.get_project_expenses(project_id)
        return float(revenue), float(expenses)

    async def _create_alert_if_not_exists(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        project_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
        client_name: Optional[str] = None,
        threshold_value: Optional[Decimal] = None,
        actual_value: Optional[Decimal] = None,
    ) -> Optional[Alert]:
        """Create an alert only if a similar active one doesn't exist."""
        # Check for existing active alert
        conditions = [
            Alert.alert_type == alert_type,
            Alert.status == AlertStatus.ACTIVE,
        ]
        if project_id:
            conditions.append(Alert.project_id == project_id)
        if transaction_id:
            conditions.append(Alert.transaction_id == transaction_id)

        query = select(Alert).where(and_(*conditions))
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            return None  # Already have an active alert

        # Create new alert
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            project_id=project_id,
            transaction_id=transaction_id,
            client_name=client_name,
            threshold_value=threshold_value,
            actual_value=actual_value,
        )
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Created alert: {alert}")
        return alert

    async def get_active_alerts(
        self,
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        project_id: Optional[int] = None,
    ) -> List[Alert]:
        """Get active alerts with optional filters."""
        conditions = [Alert.status == AlertStatus.ACTIVE]

        if alert_type:
            conditions.append(Alert.alert_type == alert_type)
        if severity:
            conditions.append(Alert.severity == severity)
        if project_id:
            conditions.append(Alert.project_id == project_id)

        query = (
            select(Alert)
            .where(and_(*conditions))
            .order_by(Alert.severity.desc(), Alert.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def acknowledge_alert(
        self,
        alert_id: int,
        user_id: Optional[str] = None,
    ) -> Optional[Alert]:
        """Mark an alert as acknowledged."""
        query = select(Alert).where(Alert.id == alert_id)
        result = await self.db.execute(query)
        alert = result.scalar_one_or_none()

        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = user_id
            await self.db.commit()
            await self.db.refresh(alert)

        return alert

    async def resolve_alert(self, alert_id: int) -> Optional[Alert]:
        """Mark an alert as resolved."""
        query = select(Alert).where(Alert.id == alert_id)
        result = await self.db.execute(query)
        alert = result.scalar_one_or_none()

        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(alert)

        return alert

    async def dismiss_alert(self, alert_id: int) -> Optional[Alert]:
        """Dismiss an alert (won't be shown again)."""
        query = select(Alert).where(Alert.id == alert_id)
        result = await self.db.execute(query)
        alert = result.scalar_one_or_none()

        if alert:
            alert.status = AlertStatus.DISMISSED
            await self.db.commit()
            await self.db.refresh(alert)

        return alert

    async def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alerts."""
        query = select(
            Alert.severity,
            func.count(Alert.id)
        ).where(
            Alert.status == AlertStatus.ACTIVE
        ).group_by(Alert.severity)

        result = await self.db.execute(query)
        by_severity = {row[0].value: row[1] for row in result.all()}

        return {
            "total_active": sum(by_severity.values()),
            "by_severity": by_severity,
            "critical": by_severity.get("critical", 0),
            "warning": by_severity.get("warning", 0),
            "info": by_severity.get("info", 0),
        }
