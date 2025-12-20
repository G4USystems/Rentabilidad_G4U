"""Service for auto-categorizing transactions with AI support."""

from typing import Optional, List, Dict, Any
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, CategoryType
from app.models.transaction import Transaction, ReviewStatus
from app.models.project import Project
from app.services.llm_provider import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


CATEGORIZATION_SYSTEM_PROMPT = """You are a financial categorization assistant for a consulting/agency business.
Your task is to analyze transaction details and suggest the most appropriate category, project, and client.

Match transactions based on:
1. Counterparty name patterns (e.g., "AWS" → Software & Tools)
2. Description keywords (e.g., "consulting" → Consulting Revenue)
3. Amount patterns (e.g., recurring monthly amounts → likely salaries or subscriptions)
4. Transaction type (income vs expense)

Be conservative - only suggest high-confidence matches. When uncertain, leave fields as null.
Always provide your confidence level (0-100) and reasoning."""


class CategorizationSuggestion:
    """A categorization suggestion from AI."""

    def __init__(
        self,
        category_name: Optional[str] = None,
        project_name: Optional[str] = None,
        client_name: Optional[str] = None,
        confidence: float = 0.0,
        reasoning: str = "",
    ):
        self.category_name = category_name
        self.project_name = project_name
        self.client_name = client_name
        self.confidence = confidence
        self.reasoning = reasoning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category_name": self.category_name,
            "project_name": self.project_name,
            "client_name": self.client_name,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


class CategorizationService:
    """Service for categorizing transactions based on rules and AI."""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: Optional[LLMProvider] = None,
        confidence_threshold: float = 70.0,
    ):
        self.db = db
        self.llm = llm_provider
        self.confidence_threshold = confidence_threshold
        self._categories_cache: Optional[List[Category]] = None

    def _get_llm(self) -> LLMProvider:
        """Get LLM provider lazily."""
        if self.llm is None:
            self.llm = get_llm_provider()
        return self.llm

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


class AICategorizationService(CategorizationService):
    """Extended categorization service with AI/LLM support."""

    async def get_available_projects(self) -> List[Dict[str, Any]]:
        """Get all active projects for context."""
        query = select(Project).where(Project.is_active == True)
        result = await self.db.execute(query)
        projects = result.scalars().all()

        return [
            {
                "name": p.name,
                "client_name": p.client_name,
                "code": p.code,
            }
            for p in projects
        ]

    async def suggest_with_ai(
        self,
        transaction: Transaction,
    ) -> CategorizationSuggestion:
        """Get AI suggestion for categorizing a transaction."""
        # Get context
        categories = await self.get_categories_with_keywords()
        projects = await self.get_available_projects()

        categories_context = [
            {
                "name": c.name,
                "type": c.category_type.value if c.category_type else "unknown",
                "keywords": c.keywords,
            }
            for c in categories
        ]

        context = {
            "transaction": {
                "amount": float(transaction.amount) if transaction.amount else 0,
                "side": transaction.side.value if transaction.side else "unknown",
                "counterparty": transaction.counterparty_name,
                "description": transaction.label,
                "date": transaction.transaction_date.isoformat() if transaction.transaction_date else None,
            },
            "available_categories": categories_context,
            "available_projects": projects,
        }

        user_prompt = f"""Analyze this transaction and suggest categorization:

Transaction:
- Amount: {context['transaction']['amount']}€
- Type: {context['transaction']['side']}
- Counterparty: {context['transaction']['counterparty']}
- Description: {context['transaction']['description']}
- Date: {context['transaction']['date']}

Respond with a JSON object:
{{
    "category_name": "exact category name from the list or null",
    "project_name": "exact project name from the list or null",
    "client_name": "client name if identifiable or null",
    "confidence": 0-100,
    "reasoning": "brief explanation of your suggestion"
}}"""

        try:
            llm = self._get_llm()
            result = await llm.generate_scenario(
                system_prompt=CATEGORIZATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                context=context,
            )

            return CategorizationSuggestion(
                category_name=result.get("category_name"),
                project_name=result.get("project_name"),
                client_name=result.get("client_name"),
                confidence=float(result.get("confidence", 0)),
                reasoning=result.get("reasoning", ""),
            )

        except Exception as e:
            logger.error(f"Error getting AI categorization: {e}")
            return CategorizationSuggestion(
                confidence=0,
                reasoning=f"Error: {str(e)}",
            )

    async def batch_suggest_with_ai(
        self,
        transaction_ids: List[int],
    ) -> Dict[int, CategorizationSuggestion]:
        """Get AI suggestions for multiple transactions."""
        suggestions = {}

        for tx_id in transaction_ids:
            query = select(Transaction).where(Transaction.id == tx_id)
            result = await self.db.execute(query)
            transaction = result.scalar_one_or_none()

            if transaction:
                suggestion = await self.suggest_with_ai(transaction)
                suggestions[tx_id] = suggestion

        return suggestions

    async def auto_categorize_with_review(
        self,
        limit: int = 50,
        auto_apply_threshold: float = 90.0,
    ) -> Dict[str, Any]:
        """
        Auto-categorize pending transactions with AI.

        High-confidence suggestions are applied automatically.
        Others are flagged for manual review.
        """
        # Get uncategorized transactions
        query = (
            select(Transaction)
            .where(Transaction.review_status == ReviewStatus.PENDING)
            .limit(limit)
        )
        result = await self.db.execute(query)
        transactions = result.scalars().all()

        results = {
            "processed": 0,
            "auto_applied": 0,
            "needs_review": 0,
            "failed": 0,
            "details": [],
        }

        for transaction in transactions:
            try:
                # First try rule-based
                category = await self.auto_categorize_transaction(transaction)

                if category:
                    results["processed"] += 1
                    results["auto_applied"] += 1
                    results["details"].append({
                        "transaction_id": transaction.id,
                        "method": "rule_based",
                        "category": category.name,
                        "action": "applied",
                    })
                    continue

                # Fall back to AI
                suggestion = await self.suggest_with_ai(transaction)
                results["processed"] += 1

                detail = {
                    "transaction_id": transaction.id,
                    "method": "ai",
                    "suggestion": suggestion.to_dict(),
                    "action": "pending",
                }

                if suggestion.confidence >= auto_apply_threshold:
                    # High confidence - could auto-apply but mark for review
                    detail["action"] = "high_confidence_pending_review"
                    results["auto_applied"] += 1
                else:
                    detail["action"] = "needs_review"
                    results["needs_review"] += 1

                results["details"].append(detail)

            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "transaction_id": transaction.id,
                    "action": "failed",
                    "error": str(e),
                })

        return results

    async def apply_ai_suggestion(
        self,
        transaction_id: int,
        suggestion: CategorizationSuggestion,
        confirmed_by: Optional[str] = None,
    ) -> Transaction:
        """Apply a categorization suggestion to a transaction after manual review."""
        query = select(Transaction).where(Transaction.id == transaction_id)
        result = await self.db.execute(query)
        transaction = result.scalar_one_or_none()

        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")

        # Apply category if suggested
        if suggestion.category_name:
            cat_query = select(Category).where(Category.name == suggestion.category_name)
            cat_result = await self.db.execute(cat_query)
            category = cat_result.scalar_one_or_none()
            if category:
                transaction.category_id = category.id

        # Apply project if suggested
        if suggestion.project_name:
            proj_query = select(Project).where(Project.name == suggestion.project_name)
            proj_result = await self.db.execute(proj_query)
            project = proj_result.scalar_one_or_none()
            if project:
                transaction.project_id = project.id

        # Mark as confirmed
        transaction.review_status = ReviewStatus.CONFIRMED

        await self.db.commit()
        await self.db.refresh(transaction)

        return transaction
