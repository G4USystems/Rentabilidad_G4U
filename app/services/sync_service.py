"""Service for syncing data from Qonto."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.qonto_client import QontoClient, get_qonto_client
from app.models.account import QontoAccount
from app.models.transaction import Transaction, TransactionSide, TransactionStatus, TransactionType
from app.services.categorization_service import CategorizationService

logger = logging.getLogger(__name__)


class SyncService:
    """Service for synchronizing data from Qonto to local database."""

    def __init__(
        self,
        db: AsyncSession,
        qonto_client: Optional[QontoClient] = None,
    ):
        self.db = db
        self.qonto = qonto_client or get_qonto_client()
        self.categorization = CategorizationService(db)

    async def sync_accounts(self) -> List[QontoAccount]:
        """
        Sync bank accounts from Qonto.

        Returns:
            List of synced accounts
        """
        logger.info("Starting account sync from Qonto")

        # Get accounts from Qonto
        qonto_accounts = await self.qonto.get_bank_accounts()
        synced_accounts = []

        for qonto_account in qonto_accounts:
            # Check if account exists
            result = await self.db.execute(
                select(QontoAccount).where(
                    QontoAccount.qonto_id == qonto_account["slug"]
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing account
                existing.name = qonto_account.get("name", existing.name)
                existing.balance = QontoClient.parse_amount(
                    qonto_account.get("balance_cents", 0)
                )
                existing.authorized_balance = QontoClient.parse_amount(
                    qonto_account.get("authorized_balance_cents", 0)
                )
                existing.last_synced_at = datetime.utcnow()
                synced_accounts.append(existing)
            else:
                # Create new account
                new_account = QontoAccount(
                    qonto_id=qonto_account["slug"],
                    slug=qonto_account["slug"],
                    iban=qonto_account["iban"],
                    bic=qonto_account.get("bic"),
                    name=qonto_account.get("name", "Main Account"),
                    currency=qonto_account.get("currency", "EUR"),
                    balance=QontoClient.parse_amount(
                        qonto_account.get("balance_cents", 0)
                    ),
                    authorized_balance=QontoClient.parse_amount(
                        qonto_account.get("authorized_balance_cents", 0)
                    ),
                    is_main=qonto_account.get("iban") == self.qonto.iban,
                    last_synced_at=datetime.utcnow(),
                )
                self.db.add(new_account)
                synced_accounts.append(new_account)

        await self.db.flush()
        logger.info(f"Synced {len(synced_accounts)} accounts")

        return synced_accounts

    async def sync_transactions(
        self,
        iban: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        full_sync: bool = False,
    ) -> Dict[str, Any]:
        """
        Sync transactions from Qonto.

        Args:
            iban: Specific IBAN to sync (defaults to configured)
            from_date: Start date for sync
            to_date: End date for sync
            full_sync: If True, sync all transactions, otherwise only new ones

        Returns:
            Sync statistics
        """
        logger.info(f"Starting transaction sync (full_sync={full_sync})")

        stats = {
            "total_fetched": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
        }

        # Get account
        account = await self._get_or_create_account(iban)
        if not account:
            raise ValueError("Could not find or create account")

        # Get last sync time if not full sync
        if not full_sync and not from_date and account.last_synced_at:
            from_date = account.last_synced_at.date()

        # Fetch transactions from Qonto
        raw_transactions = await self.qonto.get_all_transactions(
            iban=iban,
            settled_at_from=from_date,
            settled_at_to=to_date,
            status=["completed"],  # Only completed transactions
        )

        stats["total_fetched"] = len(raw_transactions)
        logger.info(f"Fetched {len(raw_transactions)} transactions from Qonto")

        # Process each transaction
        for raw_tx in raw_transactions:
            try:
                result = await self._process_transaction(raw_tx, account)
                stats[result] += 1
            except Exception as e:
                logger.error(f"Error processing transaction {raw_tx.get('id')}: {e}")
                stats["errors"] += 1

        # Update account last sync time
        account.last_synced_at = datetime.utcnow()

        await self.db.flush()
        logger.info(f"Sync completed: {stats}")

        return stats

    async def _get_or_create_account(self, iban: Optional[str] = None) -> Optional[QontoAccount]:
        """Get existing account or create from Qonto."""
        target_iban = iban or self.qonto.iban

        # Try to find existing
        result = await self.db.execute(
            select(QontoAccount).where(QontoAccount.iban == target_iban)
        )
        account = result.scalar_one_or_none()

        if account:
            return account

        # Sync accounts first
        accounts = await self.sync_accounts()
        for acc in accounts:
            if acc.iban == target_iban:
                return acc

        return None

    async def _process_transaction(
        self,
        raw_tx: Dict[str, Any],
        account: QontoAccount,
    ) -> str:
        """
        Process a single transaction.

        Returns:
            "created", "updated", or "skipped"
        """
        qonto_id = raw_tx.get("id")

        # Check if exists
        result = await self.db.execute(
            select(Transaction).where(Transaction.qonto_id == qonto_id)
        )
        existing = result.scalar_one_or_none()

        # Parse transaction data
        parsed = QontoClient.parse_transaction(raw_tx)

        if existing:
            # Update only if status changed
            if existing.status.value != parsed["status"]:
                existing.status = TransactionStatus(parsed["status"])
                existing.synced_at = datetime.utcnow()
                return "updated"
            return "skipped"

        # Create new transaction
        transaction = Transaction(
            qonto_id=qonto_id,
            account_id=account.id,
            amount=parsed["amount"],
            amount_cents=parsed["amount_cents"],
            currency=parsed["currency"],
            local_amount=parsed.get("local_amount"),
            local_currency=parsed.get("local_currency"),
            side=TransactionSide(parsed["side"]),
            status=TransactionStatus(parsed["status"]) if parsed.get("status") else TransactionStatus.COMPLETED,
            operation_type=self._map_operation_type(parsed.get("operation_type")),
            emitted_at=parsed["emitted_at"],
            settled_at=parsed.get("settled_at"),
            transaction_date=parsed["settled_at"].date() if parsed.get("settled_at") else parsed["emitted_at"].date(),
            label=parsed["label"],
            reference=parsed.get("reference"),
            note=parsed.get("note"),
            counterparty_name=parsed.get("counterparty_name"),
            vat_amount=parsed.get("vat_amount"),
            vat_rate=parsed.get("vat_rate"),
            has_attachments=bool(parsed.get("attachment_ids")),
            attachment_count=len(parsed.get("attachment_ids", [])),
            synced_at=datetime.utcnow(),
        )

        self.db.add(transaction)
        await self.db.flush()

        # Try to auto-categorize
        await self.categorization.auto_categorize_transaction(transaction)

        return "created"

    @staticmethod
    def _map_operation_type(qonto_type: Optional[str]) -> TransactionType:
        """Map Qonto operation type to our enum."""
        mapping = {
            "transfer": TransactionType.TRANSFER,
            "card": TransactionType.CARD,
            "direct_debit": TransactionType.DIRECT_DEBIT,
            "income": TransactionType.INCOME,
            "qonto_fee": TransactionType.QONTO_FEE,
            "check": TransactionType.CHECK,
            "swift_income": TransactionType.SWIFT,
            "swift_outcome": TransactionType.SWIFT,
        }
        return mapping.get(qonto_type, TransactionType.OTHER)
