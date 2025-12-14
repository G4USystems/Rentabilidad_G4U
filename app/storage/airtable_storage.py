"""
Airtable storage backend for Vercel deployment.

Simple setup:
1. Create Airtable base
2. Get Personal Access Token from airtable.com/account
3. Set AIRTABLE_TOKEN and AIRTABLE_BASE_ID env vars
"""

import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import logging

import httpx

logger = logging.getLogger(__name__)


class AirtableStorage:
    """Storage backend using Airtable."""

    def __init__(self):
        self.token = os.getenv("AIRTABLE_TOKEN", "")
        self.base_id = os.getenv("AIRTABLE_BASE_ID", "")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        if not self.token or not self.base_id:
            raise ValueError("AIRTABLE_TOKEN and AIRTABLE_BASE_ID are required")

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        table: str,
        record_id: Optional[str] = None,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
    ) -> Dict:
        """Make HTTP request to Airtable API."""
        url = f"{self.base_url}/{table}"
        if record_id:
            url = f"{url}/{record_id}"

        with httpx.Client(timeout=30) as client:
            response = client.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json,
            )
            response.raise_for_status()
            return response.json()

    def _get_all_records(self, table: str, filter_formula: Optional[str] = None) -> List[Dict]:
        """Get all records from a table with pagination."""
        records = []
        offset = None

        while True:
            params = {}
            if offset:
                params["offset"] = offset
            if filter_formula:
                params["filterByFormula"] = filter_formula

            result = self._request("GET", table, params=params)
            records.extend(result.get("records", []))

            offset = result.get("offset")
            if not offset:
                break

        return records

    def _create_record(self, table: str, fields: Dict) -> Dict:
        """Create a new record."""
        result = self._request("POST", table, json={"fields": fields})
        return result

    def _update_record(self, table: str, record_id: str, fields: Dict) -> Dict:
        """Update a record."""
        result = self._request("PATCH", table, record_id=record_id, json={"fields": fields})
        return result

    # ==================== Transactions ====================

    def get_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        project_id: Optional[int] = None,
        side: Optional[str] = None,
    ) -> List[Dict]:
        """Get transactions with filters."""
        filters = []

        if start_date:
            filters.append(f"IS_AFTER({{transaction_date}}, '{start_date.isoformat()}')")
        if end_date:
            filters.append(f"IS_BEFORE({{transaction_date}}, '{end_date.isoformat()}')")
        if category_id:
            filters.append(f"{{category_id}} = {category_id}")
        if project_id:
            filters.append(f"{{project_id}} = {project_id}")
        if side:
            filters.append(f"{{side}} = '{side}'")

        formula = None
        if filters:
            formula = "AND(" + ", ".join(filters) + ")"

        records = self._get_all_records("Transactions", formula)

        return [
            {"id": r["id"], **r["fields"]}
            for r in records
        ]

    def add_transaction(self, transaction: Dict[str, Any]) -> str:
        """Add a new transaction. Returns Airtable record ID."""
        # Convert date objects to strings
        for key, value in transaction.items():
            if isinstance(value, (date, datetime)):
                transaction[key] = value.isoformat()

        result = self._create_record("Transactions", transaction)
        return result["id"]

    def update_transaction(self, record_id: str, updates: Dict[str, Any]) -> bool:
        """Update a transaction."""
        try:
            self._update_record("Transactions", record_id, updates)
            return True
        except Exception as e:
            logger.error(f"Failed to update transaction: {e}")
            return False

    def transaction_exists(self, qonto_id: str) -> Optional[str]:
        """Check if transaction exists. Returns record ID if found."""
        formula = f"{{qonto_id}} = '{qonto_id}'"
        records = self._get_all_records("Transactions", formula)
        if records:
            return records[0]["id"]
        return None

    # ==================== Categories ====================

    def get_categories(self, active_only: bool = True) -> List[Dict]:
        """Get all categories."""
        formula = "{is_active} = TRUE()" if active_only else None
        records = self._get_all_records("Categories", formula)

        return [
            {"id": r["id"], **r["fields"]}
            for r in records
        ]

    def add_category(self, category: Dict[str, Any]) -> str:
        """Add a new category."""
        result = self._create_record("Categories", category)
        return result["id"]

    def get_category_by_name(self, name: str) -> Optional[Dict]:
        """Get category by name."""
        formula = f"{{name}} = '{name}'"
        records = self._get_all_records("Categories", formula)
        if records:
            return {"id": records[0]["id"], **records[0]["fields"]}
        return None

    # ==================== Projects ====================

    def get_projects(self, active_only: bool = True) -> List[Dict]:
        """Get all projects."""
        formula = "{is_active} = TRUE()" if active_only else None
        records = self._get_all_records("Projects", formula)

        return [
            {"id": r["id"], **r["fields"]}
            for r in records
        ]

    def add_project(self, project: Dict[str, Any]) -> str:
        """Add a new project."""
        result = self._create_record("Projects", project)
        return result["id"]

    def get_project(self, record_id: str) -> Optional[Dict]:
        """Get project by ID."""
        try:
            result = self._request("GET", "Projects", record_id=record_id)
            return {"id": result["id"], **result["fields"]}
        except:
            return None

    def update_project(self, record_id: str, updates: Dict[str, Any]) -> bool:
        """Update a project."""
        try:
            self._update_record("Projects", record_id, updates)
            return True
        except:
            return False

    # ==================== Accounts ====================

    def get_accounts(self) -> List[Dict]:
        """Get all accounts."""
        records = self._get_all_records("Accounts")
        return [{"id": r["id"], **r["fields"]} for r in records]

    def add_account(self, account: Dict[str, Any]) -> str:
        """Add a new account."""
        result = self._create_record("Accounts", account)
        return result["id"]

    def get_account_by_iban(self, iban: str) -> Optional[Dict]:
        """Get account by IBAN."""
        formula = f"{{iban}} = '{iban}'"
        records = self._get_all_records("Accounts", formula)
        if records:
            return {"id": records[0]["id"], **records[0]["fields"]}
        return None

    def update_account(self, record_id: str, updates: Dict[str, Any]) -> bool:
        """Update an account."""
        try:
            self._update_record("Accounts", record_id, updates)
            return True
        except:
            return False
