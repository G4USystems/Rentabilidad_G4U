"""Service for auto-categorizing transactions."""

from typing import Optional, List
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, CategoryType
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


class CategorizationService:
    """Service for categorizing transactions based on rules."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._categories_cache: Optional[List[Category]] = None

    async def get_categories_with_keywords(self) -> List[Category]:
        """Get all active categories with keywords."""
        if self._categories_cache is None:
            result = await self.db.execute(
                select(Category).where(
                    Category.is_active == True,
                    Category.keywords.isnot(None),
                )
            )
            self._categories_cache = list(result.scalars().all())
        return self._categories_cache

    def clear_cache(self):
        """Clear the categories cache."""
        self._categories_cache = None

    async def auto_categorize_transaction(
        self,
        transaction: Transaction,
        force: bool = False,
    ) -> Optional[Category]:
        """
        Auto-categorize a transaction based on keywords.

        Args:
            transaction: Transaction to categorize
            force: If True, recategorize even if already categorized

        Returns:
            Matched category or None
        """
        # Skip if already categorized
        if transaction.category_id and not force:
            return None

        categories = await self.get_categories_with_keywords()

        # Text to match against
        match_text = f"{transaction.label} {transaction.counterparty_name or ''} {transaction.note or ''}".lower()

        best_match: Optional[Category] = None
        best_score = 0

        for category in categories:
            if not category.keywords:
                continue

            keywords = [k.strip().lower() for k in category.keywords.split(",")]
            score = 0

            for keyword in keywords:
                if keyword and keyword in match_text:
                    # Longer keywords get higher scores
                    score += len(keyword)

            if score > best_score:
                best_score = score
                best_match = category

        if best_match:
            transaction.category_id = best_match.id
            logger.debug(
                f"Auto-categorized transaction {transaction.id} "
                f"as {best_match.name} (score: {best_score})"
            )

        return best_match

    async def auto_categorize_all(
        self,
        uncategorized_only: bool = True,
    ) -> dict:
        """
        Auto-categorize all transactions.

        Args:
            uncategorized_only: Only process uncategorized transactions

        Returns:
            Statistics dictionary
        """
        query = select(Transaction)
        if uncategorized_only:
            query = query.where(Transaction.category_id.is_(None))

        result = await self.db.execute(query)
        transactions = result.scalars().all()

        stats = {
            "total": len(transactions),
            "categorized": 0,
            "unchanged": 0,
        }

        for tx in transactions:
            category = await self.auto_categorize_transaction(tx, force=not uncategorized_only)
            if category:
                stats["categorized"] += 1
            else:
                stats["unchanged"] += 1

        await self.db.flush()
        return stats


async def create_default_categories(db: AsyncSession) -> List[Category]:
    """Create default categories for P&L reporting."""

    default_categories = [
        # Revenue
        {"name": "Ventas de Servicios", "type": CategoryType.REVENUE, "keywords": "factura,invoice,pago cliente,cobro"},
        {"name": "Ventas de Productos", "type": CategoryType.REVENUE, "keywords": "venta,sale"},
        {"name": "Otros Ingresos", "type": CategoryType.OTHER_INCOME, "keywords": "reembolso,refund,intereses"},

        # COGS
        {"name": "Costos Directos", "type": CategoryType.COGS, "keywords": "proveedor,supplier,materiales"},
        {"name": "Subcontratación", "type": CategoryType.COGS, "keywords": "freelance,subcontrat"},

        # Operating Expenses
        {"name": "Nómina y Salarios", "type": CategoryType.PAYROLL, "keywords": "nomina,salario,sueldo,payroll"},
        {"name": "Seguridad Social", "type": CategoryType.PAYROLL, "keywords": "seguridad social,ss,cotizacion"},

        {"name": "Marketing y Publicidad", "type": CategoryType.MARKETING, "keywords": "google ads,facebook,publicidad,marketing,ads"},
        {"name": "Software y Suscripciones", "type": CategoryType.SOFTWARE, "keywords": "software,saas,subscription,aws,azure,google cloud,slack,notion"},

        {"name": "Alquiler", "type": CategoryType.RENT, "keywords": "alquiler,rent,oficina,coworking"},
        {"name": "Suministros", "type": CategoryType.RENT, "keywords": "electricidad,agua,gas,internet,telefono"},

        {"name": "Servicios Profesionales", "type": CategoryType.PROFESSIONAL_SERVICES, "keywords": "abogado,gestor,contable,asesoria,consultor"},
        {"name": "Viajes", "type": CategoryType.TRAVEL, "keywords": "vuelo,hotel,taxi,uber,tren,viaje,travel"},

        {"name": "Material de Oficina", "type": CategoryType.ADMIN, "keywords": "material,papeleria,amazon"},
        {"name": "Gastos Bancarios", "type": CategoryType.ADMIN, "keywords": "comision,fee,qonto"},

        # Taxes
        {"name": "Impuestos", "type": CategoryType.TAXES, "keywords": "impuesto,tax,iva,irpf,hacienda"},

        # Non-P&L
        {"name": "Transferencias Internas", "type": CategoryType.TRANSFER, "keywords": "transferencia interna,traspaso"},
        {"name": "Sin Categorizar", "type": CategoryType.UNCATEGORIZED, "keywords": ""},
    ]

    created = []
    for cat_data in default_categories:
        # Check if exists
        result = await db.execute(
            select(Category).where(Category.name == cat_data["name"])
        )
        existing = result.scalar_one_or_none()

        if not existing:
            category = Category(
                name=cat_data["name"],
                type=cat_data["type"],
                keywords=cat_data["keywords"],
                is_system=True,
            )
            db.add(category)
            created.append(category)

    await db.flush()
    return created
