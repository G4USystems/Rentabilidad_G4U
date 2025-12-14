"""Qonto API client for fetching banking data."""

import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class QontoAPIError(Exception):
    """Custom exception for Qonto API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class QontoClient:
    """
    Client for interacting with the Qonto API.

    API Documentation: https://api-doc.qonto.com/
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        organization_slug: Optional[str] = None,
        iban: Optional[str] = None,
    ):
        """
        Initialize Qonto client.

        Args:
            api_key: Qonto API key (defaults to settings)
            organization_slug: Organization slug (defaults to settings)
            iban: IBAN to use (defaults to settings)
        """
        self.api_key = api_key or settings.qonto_api_key
        self.organization_slug = organization_slug or settings.qonto_organization_slug
        self.iban = iban or settings.qonto_iban
        self.base_url = settings.qonto_api_base_url

        if not self.api_key:
            raise ValueError("Qonto API key is required")

        self._client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"{self.organization_slug}:{self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Qonto API with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json: JSON body
            retries: Number of retries

        Returns:
            API response as dictionary
        """
        client = await self._get_client()
        last_exception = None

        for attempt in range(retries):
            try:
                response = await client.request(
                    method=method,
                    url=endpoint,
                    params=params,
                    json=json,
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise QontoAPIError(
                        "Authentication failed. Check your API key and organization slug.",
                        status_code=401,
                    )
                elif response.status_code == 403:
                    raise QontoAPIError(
                        "Access forbidden. Check your permissions.",
                        status_code=403,
                    )
                elif response.status_code == 404:
                    raise QontoAPIError(
                        f"Resource not found: {endpoint}",
                        status_code=404,
                    )
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise QontoAPIError(
                        f"API error: {response.status_code}",
                        status_code=response.status_code,
                        response=response.json() if response.content else None,
                    )

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                await asyncio.sleep(2 ** attempt)
            except httpx.RequestError as e:
                last_exception = e
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")
                await asyncio.sleep(2 ** attempt)

        raise QontoAPIError(
            f"Request failed after {retries} attempts: {last_exception}"
        )

    # ==================== Organization ====================

    async def get_organization(self) -> Dict[str, Any]:
        """
        Get organization details.

        Returns:
            Organization data including bank accounts
        """
        response = await self._request("GET", "/organization")
        return response.get("organization", {})

    # ==================== Bank Accounts ====================

    async def get_bank_accounts(self) -> List[Dict[str, Any]]:
        """
        Get all bank accounts for the organization.

        Returns:
            List of bank account data
        """
        org = await self.get_organization()
        return org.get("bank_accounts", [])

    async def get_bank_account_by_iban(self, iban: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific bank account by IBAN.

        Args:
            iban: IBAN to search for (defaults to configured IBAN)

        Returns:
            Bank account data or None if not found
        """
        target_iban = iban or self.iban
        accounts = await self.get_bank_accounts()

        for account in accounts:
            if account.get("iban") == target_iban:
                return account

        return None

    # ==================== Transactions ====================

    async def get_transactions(
        self,
        iban: Optional[str] = None,
        status: Optional[List[str]] = None,
        updated_at_from: Optional[datetime] = None,
        updated_at_to: Optional[datetime] = None,
        settled_at_from: Optional[date] = None,
        settled_at_to: Optional[date] = None,
        side: Optional[str] = None,  # "credit" or "debit"
        page: int = 1,
        per_page: int = 100,
    ) -> Dict[str, Any]:
        """
        Get transactions with filters.

        Args:
            iban: Bank account IBAN (defaults to configured)
            status: Filter by status(es): pending, reversed, declined, completed
            updated_at_from: Filter by update time (from)
            updated_at_to: Filter by update time (to)
            settled_at_from: Filter by settlement date (from)
            settled_at_to: Filter by settlement date (to)
            side: Filter by side: "credit" (income) or "debit" (expense)
            page: Page number (1-indexed)
            per_page: Items per page (max 100)

        Returns:
            Dictionary with transactions and pagination meta
        """
        params = {
            "iban": iban or self.iban,
            "current_page": page,
            "per_page": min(per_page, 100),
        }

        if status:
            params["status[]"] = status
        if updated_at_from:
            params["updated_at_from"] = updated_at_from.isoformat()
        if updated_at_to:
            params["updated_at_to"] = updated_at_to.isoformat()
        if settled_at_from:
            params["settled_at_from"] = settled_at_from.isoformat()
        if settled_at_to:
            params["settled_at_to"] = settled_at_to.isoformat()
        if side:
            params["side"] = side

        response = await self._request("GET", "/transactions", params=params)

        return {
            "transactions": response.get("transactions", []),
            "meta": response.get("meta", {}),
        }

    async def get_all_transactions(
        self,
        iban: Optional[str] = None,
        status: Optional[List[str]] = None,
        settled_at_from: Optional[date] = None,
        settled_at_to: Optional[date] = None,
        side: Optional[str] = None,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all transactions with automatic pagination.

        Args:
            iban: Bank account IBAN
            status: Filter by status(es)
            settled_at_from: Filter by settlement date (from)
            settled_at_to: Filter by settlement date (to)
            side: Filter by side
            max_pages: Maximum pages to fetch (None for all)

        Returns:
            List of all transactions
        """
        all_transactions = []
        page = 1
        total_pages = None

        while True:
            result = await self.get_transactions(
                iban=iban,
                status=status,
                settled_at_from=settled_at_from,
                settled_at_to=settled_at_to,
                side=side,
                page=page,
                per_page=100,
            )

            transactions = result.get("transactions", [])
            meta = result.get("meta", {})

            all_transactions.extend(transactions)

            # Get pagination info
            if total_pages is None:
                total_pages = meta.get("total_pages", 1)

            page += 1

            # Check if we should stop
            if page > total_pages:
                break
            if max_pages and page > max_pages:
                break

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)

        return all_transactions

    async def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single transaction by ID.

        Args:
            transaction_id: Qonto transaction ID

        Returns:
            Transaction data or None
        """
        try:
            response = await self._request("GET", f"/transactions/{transaction_id}")
            return response.get("transaction")
        except QontoAPIError as e:
            if e.status_code == 404:
                return None
            raise

    # ==================== Labels (Categories from Qonto) ====================

    async def get_labels(self) -> List[Dict[str, Any]]:
        """
        Get all labels (Qonto's categorization system).

        Returns:
            List of labels
        """
        response = await self._request("GET", "/labels")
        return response.get("labels", [])

    # ==================== Memberships ====================

    async def get_memberships(self) -> List[Dict[str, Any]]:
        """
        Get all team memberships.

        Returns:
            List of memberships
        """
        response = await self._request("GET", "/memberships")
        return response.get("memberships", [])

    # ==================== Attachments ====================

    async def get_attachments(self, transaction_id: str) -> List[Dict[str, Any]]:
        """
        Get attachments for a transaction.

        Args:
            transaction_id: Transaction ID

        Returns:
            List of attachments
        """
        response = await self._request(
            "GET",
            f"/transactions/{transaction_id}/attachments"
        )
        return response.get("attachments", [])

    # ==================== Helper Methods ====================

    @staticmethod
    def parse_amount(amount_cents: int, currency: str = "EUR") -> Decimal:
        """
        Convert amount from cents to decimal.

        Args:
            amount_cents: Amount in cents
            currency: Currency code

        Returns:
            Decimal amount
        """
        return Decimal(str(amount_cents)) / Decimal("100")

    @staticmethod
    def parse_transaction(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw transaction data into a cleaner format.

        Args:
            raw: Raw transaction from API

        Returns:
            Parsed transaction data
        """
        amount_cents = raw.get("amount_cents", 0)
        currency = raw.get("currency", "EUR")

        return {
            "qonto_id": raw.get("id"),
            "amount": QontoClient.parse_amount(amount_cents, currency),
            "amount_cents": amount_cents,
            "currency": currency,
            "local_amount": (
                QontoClient.parse_amount(raw["local_amount_cents"], raw.get("local_currency", currency))
                if raw.get("local_amount_cents")
                else None
            ),
            "local_currency": raw.get("local_currency"),
            "side": raw.get("side"),  # "credit" or "debit"
            "status": raw.get("status"),
            "operation_type": raw.get("operation_type"),
            "emitted_at": datetime.fromisoformat(raw["emitted_at"].replace("Z", "+00:00"))
            if raw.get("emitted_at") else None,
            "settled_at": datetime.fromisoformat(raw["settled_at"].replace("Z", "+00:00"))
            if raw.get("settled_at") else None,
            "label": raw.get("label", ""),
            "reference": raw.get("reference"),
            "note": raw.get("note"),
            "counterparty_name": raw.get("label"),  # Qonto uses label for counterparty
            "vat_amount": (
                QontoClient.parse_amount(raw["vat_amount_cents"], currency)
                if raw.get("vat_amount_cents")
                else None
            ),
            "vat_rate": Decimal(str(raw["vat_rate"])) if raw.get("vat_rate") else None,
            "attachment_ids": raw.get("attachment_ids", []),
            "label_ids": raw.get("label_ids", []),
        }


# Singleton instance
_qonto_client: Optional[QontoClient] = None


def get_qonto_client() -> QontoClient:
    """Get or create Qonto client singleton."""
    global _qonto_client
    if _qonto_client is None:
        _qonto_client = QontoClient()
    return _qonto_client
