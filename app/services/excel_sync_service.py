"""Sync service using Excel/Google Sheets storage."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List
import logging

from app.storage.excel_storage import get_storage
from app.integrations.qonto_client import QontoClient, get_qonto_client

logger = logging.getLogger(__name__)


# Default categories for P&L
DEFAULT_CATEGORIES = [
    # Revenue
    {"name": "Ventas de Servicios", "type": "revenue", "keywords": "factura,invoice,pago cliente,cobro"},
    {"name": "Ventas de Productos", "type": "revenue", "keywords": "venta,sale"},
    {"name": "Otros Ingresos", "type": "other_income", "keywords": "reembolso,refund,intereses"},

    # COGS
    {"name": "Costos Directos", "type": "cogs", "keywords": "proveedor,supplier,materiales"},
    {"name": "Subcontratación", "type": "cogs", "keywords": "freelance,subcontrat"},

    # Operating Expenses
    {"name": "Nómina y Salarios", "type": "payroll", "keywords": "nomina,salario,sueldo,payroll"},
    {"name": "Seguridad Social", "type": "payroll", "keywords": "seguridad social,ss,cotizacion"},
    {"name": "Marketing y Publicidad", "type": "marketing", "keywords": "google ads,facebook,publicidad,marketing,ads"},
    {"name": "Software y Suscripciones", "type": "software", "keywords": "software,saas,subscription,aws,azure,slack,notion"},
    {"name": "Alquiler", "type": "rent", "keywords": "alquiler,rent,oficina,coworking"},
    {"name": "Suministros", "type": "rent", "keywords": "electricidad,agua,gas,internet,telefono"},
    {"name": "Servicios Profesionales", "type": "professional_services", "keywords": "abogado,gestor,contable,asesoria,consultor"},
    {"name": "Viajes", "type": "travel", "keywords": "vuelo,hotel,taxi,uber,tren,viaje,travel"},
    {"name": "Material de Oficina", "type": "admin", "keywords": "material,papeleria,amazon"},
    {"name": "Gastos Bancarios", "type": "admin", "keywords": "comision,fee,qonto"},

    # Taxes
    {"name": "Impuestos", "type": "taxes", "keywords": "impuesto,tax,iva,irpf,hacienda"},

    # Non-P&L
    {"name": "Transferencias Internas", "type": "transfer", "keywords": "transferencia interna,traspaso"},
    {"name": "Sin Categorizar", "type": "uncategorized", "keywords": ""},
]


class ExcelSyncService:
    """Service for syncing Qonto data to Excel/Sheets."""

    def __init__(self, qonto_client: Optional[QontoClient] = None):
        self.storage = get_storage()
        self.qonto = qonto_client or get_qonto_client()

    async def initialize_categories(self) -> Dict[str, int]:
        """Create default categories if they don't exist."""
        created = 0
        existing = 0

        categories_df = self.storage.get_categories(active_only=False)
        existing_names = set(categories_df['name'].tolist()) if not categories_df.empty else set()

        for cat in DEFAULT_CATEGORIES:
            if cat['name'] not in existing_names:
                self.storage.add_category({
                    'name': cat['name'],
                    'type': cat['type'],
                    'keywords': cat['keywords'],
                    'is_active': True,
                    'is_system': True,
                    'description': '',
                    'parent_id': None,
                })
                created += 1
            else:
                existing += 1

        return {"created": created, "existing": existing}

    async def sync_accounts(self) -> List[Dict]:
        """Sync bank accounts from Qonto."""
        logger.info("Syncing accounts from Qonto...")

        qonto_accounts = await self.qonto.get_bank_accounts()
        synced = []

        for qa in qonto_accounts:
            existing = self.storage.get_account_by_iban(qa['iban'])

            account_data = {
                'qonto_id': qa['slug'],
                'iban': qa['iban'],
                'name': qa.get('name', 'Main Account'),
                'currency': qa.get('currency', 'EUR'),
                'balance': float(QontoClient.parse_amount(qa.get('balance_cents', 0))),
                'is_main': qa['iban'] == self.qonto.iban,
                'last_synced_at': datetime.utcnow().isoformat(),
            }

            if existing:
                self.storage.update_account(existing['id'], account_data)
                account_data['id'] = existing['id']
            else:
                account_data['id'] = self.storage.add_account(account_data)

            synced.append(account_data)

        return synced

    async def sync_transactions(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Dict[str, int]:
        """Sync transactions from Qonto."""
        logger.info(f"Syncing transactions from Qonto (from={from_date}, to={to_date})...")

        stats = {
            "fetched": 0,
            "created": 0,
            "skipped": 0,
            "errors": 0,
        }

        # Get account
        account = self.storage.get_account_by_iban(self.qonto.iban)
        if not account:
            # Sync accounts first
            accounts = await self.sync_accounts()
            account = next((a for a in accounts if a['iban'] == self.qonto.iban), None)

        if not account:
            raise ValueError("Could not find or create account")

        # Fetch from Qonto
        raw_transactions = await self.qonto.get_all_transactions(
            settled_at_from=from_date,
            settled_at_to=to_date,
            status=["completed"],
        )

        stats["fetched"] = len(raw_transactions)

        for raw_tx in raw_transactions:
            try:
                qonto_id = raw_tx.get('id')

                # Skip if exists
                if self.storage.transaction_exists(qonto_id):
                    stats["skipped"] += 1
                    continue

                # Parse transaction
                parsed = QontoClient.parse_transaction(raw_tx)

                tx_data = {
                    'qonto_id': qonto_id,
                    'account_id': account['id'],
                    'amount': float(parsed['amount']),
                    'currency': parsed['currency'],
                    'side': parsed['side'],
                    'status': parsed.get('status', 'completed'),
                    'operation_type': parsed.get('operation_type', 'other'),
                    'emitted_at': parsed['emitted_at'].isoformat() if parsed.get('emitted_at') else None,
                    'settled_at': parsed['settled_at'].isoformat() if parsed.get('settled_at') else None,
                    'transaction_date': (parsed['settled_at'] or parsed['emitted_at']).date().isoformat(),
                    'label': parsed['label'],
                    'reference': parsed.get('reference'),
                    'note': parsed.get('note'),
                    'counterparty_name': parsed.get('counterparty_name'),
                    'category_id': None,
                    'project_id': None,
                    'is_excluded': False,
                    'synced_at': datetime.utcnow().isoformat(),
                }

                # Auto-categorize
                category_id = self._auto_categorize(tx_data)
                tx_data['category_id'] = category_id

                self.storage.add_transaction(tx_data)
                stats["created"] += 1

            except Exception as e:
                logger.error(f"Error processing transaction {raw_tx.get('id')}: {e}")
                stats["errors"] += 1

        return stats

    def _auto_categorize(self, transaction: Dict) -> Optional[int]:
        """Auto-categorize transaction based on keywords."""
        categories_df = self.storage.get_categories()

        if categories_df.empty:
            return None

        match_text = f"{transaction.get('label', '')} {transaction.get('counterparty_name', '')}".lower()

        best_match = None
        best_score = 0

        for _, cat in categories_df.iterrows():
            keywords = cat.get('keywords', '')
            if not keywords:
                continue

            for keyword in keywords.split(','):
                keyword = keyword.strip().lower()
                if keyword and keyword in match_text:
                    score = len(keyword)
                    if score > best_score:
                        best_score = score
                        best_match = int(cat['id'])

        return best_match

    async def sync_all(self) -> Dict[str, Any]:
        """Sync everything from Qonto."""
        accounts = await self.sync_accounts()
        transactions = await self.sync_transactions()

        return {
            "accounts_synced": len(accounts),
            "transactions": transactions,
        }
