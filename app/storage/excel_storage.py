"""
Storage service for Excel/Google Sheets data persistence.

Supports:
- Local Excel files (.xlsx) for development
- Google Sheets for production (Vercel)
"""

import os
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelStorage:
    """Storage backend using local Excel files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Excel file paths
        self.transactions_file = self.data_dir / "transactions.xlsx"
        self.categories_file = self.data_dir / "categories.xlsx"
        self.projects_file = self.data_dir / "projects.xlsx"
        self.accounts_file = self.data_dir / "accounts.xlsx"

        # Initialize files if they don't exist
        self._init_files()

    def _init_files(self):
        """Initialize Excel files with headers if they don't exist."""
        if not self.transactions_file.exists():
            df = pd.DataFrame(columns=[
                'id', 'qonto_id', 'account_id', 'amount', 'currency', 'side',
                'status', 'operation_type', 'emitted_at', 'settled_at',
                'transaction_date', 'label', 'reference', 'note',
                'counterparty_name', 'category_id', 'project_id',
                'is_excluded', 'created_at', 'synced_at'
            ])
            df.to_excel(self.transactions_file, index=False)

        if not self.categories_file.exists():
            df = pd.DataFrame(columns=[
                'id', 'name', 'description', 'type', 'parent_id',
                'keywords', 'is_active', 'is_system', 'created_at'
            ])
            df.to_excel(self.categories_file, index=False)

        if not self.projects_file.exists():
            df = pd.DataFrame(columns=[
                'id', 'name', 'code', 'description', 'client_name',
                'status', 'start_date', 'end_date', 'budget_amount',
                'contract_value', 'is_active', 'created_at'
            ])
            df.to_excel(self.projects_file, index=False)

        if not self.accounts_file.exists():
            df = pd.DataFrame(columns=[
                'id', 'qonto_id', 'iban', 'name', 'currency',
                'balance', 'is_main', 'last_synced_at', 'created_at'
            ])
            df.to_excel(self.accounts_file, index=False)

    # ==================== Transactions ====================

    def get_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        project_id: Optional[int] = None,
        side: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get transactions with optional filters."""
        df = pd.read_excel(self.transactions_file)

        if df.empty:
            return df

        # Convert date column
        df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.date

        # Apply filters
        if start_date:
            df = df[df['transaction_date'] >= start_date]
        if end_date:
            df = df[df['transaction_date'] <= end_date]
        if category_id:
            df = df[df['category_id'] == category_id]
        if project_id:
            df = df[df['project_id'] == project_id]
        if side:
            df = df[df['side'] == side]

        return df

    def add_transaction(self, transaction: Dict[str, Any]) -> int:
        """Add a new transaction."""
        df = pd.read_excel(self.transactions_file)

        # Generate ID
        new_id = 1 if df.empty else df['id'].max() + 1
        transaction['id'] = new_id
        transaction['created_at'] = datetime.utcnow().isoformat()

        # Append
        df = pd.concat([df, pd.DataFrame([transaction])], ignore_index=True)
        df.to_excel(self.transactions_file, index=False)

        return new_id

    def update_transaction(self, tx_id: int, updates: Dict[str, Any]) -> bool:
        """Update a transaction."""
        df = pd.read_excel(self.transactions_file)

        if tx_id not in df['id'].values:
            return False

        for key, value in updates.items():
            df.loc[df['id'] == tx_id, key] = value

        df.to_excel(self.transactions_file, index=False)
        return True

    def transaction_exists(self, qonto_id: str) -> bool:
        """Check if transaction already exists by Qonto ID."""
        df = pd.read_excel(self.transactions_file)
        return qonto_id in df['qonto_id'].values

    # ==================== Categories ====================

    def get_categories(self, active_only: bool = True) -> pd.DataFrame:
        """Get all categories."""
        df = pd.read_excel(self.categories_file)

        if active_only and not df.empty:
            df = df[df['is_active'] == True]

        return df

    def add_category(self, category: Dict[str, Any]) -> int:
        """Add a new category."""
        df = pd.read_excel(self.categories_file)

        new_id = 1 if df.empty else df['id'].max() + 1
        category['id'] = new_id
        category['created_at'] = datetime.utcnow().isoformat()

        df = pd.concat([df, pd.DataFrame([category])], ignore_index=True)
        df.to_excel(self.categories_file, index=False)

        return new_id

    def get_category_by_name(self, name: str) -> Optional[Dict]:
        """Get category by name."""
        df = pd.read_excel(self.categories_file)
        match = df[df['name'] == name]
        if match.empty:
            return None
        return match.iloc[0].to_dict()

    # ==================== Projects ====================

    def get_projects(self, active_only: bool = True) -> pd.DataFrame:
        """Get all projects."""
        df = pd.read_excel(self.projects_file)

        if active_only and not df.empty:
            df = df[df['is_active'] == True]

        return df

    def add_project(self, project: Dict[str, Any]) -> int:
        """Add a new project."""
        df = pd.read_excel(self.projects_file)

        new_id = 1 if df.empty else df['id'].max() + 1
        project['id'] = new_id
        project['created_at'] = datetime.utcnow().isoformat()

        df = pd.concat([df, pd.DataFrame([project])], ignore_index=True)
        df.to_excel(self.projects_file, index=False)

        return new_id

    def get_project(self, project_id: int) -> Optional[Dict]:
        """Get project by ID."""
        df = pd.read_excel(self.projects_file)
        match = df[df['id'] == project_id]
        if match.empty:
            return None
        return match.iloc[0].to_dict()

    def update_project(self, project_id: int, updates: Dict[str, Any]) -> bool:
        """Update a project."""
        df = pd.read_excel(self.projects_file)

        if project_id not in df['id'].values:
            return False

        for key, value in updates.items():
            df.loc[df['id'] == project_id, key] = value

        df.to_excel(self.projects_file, index=False)
        return True

    # ==================== Accounts ====================

    def get_accounts(self) -> pd.DataFrame:
        """Get all accounts."""
        return pd.read_excel(self.accounts_file)

    def add_account(self, account: Dict[str, Any]) -> int:
        """Add a new account."""
        df = pd.read_excel(self.accounts_file)

        new_id = 1 if df.empty else df['id'].max() + 1
        account['id'] = new_id
        account['created_at'] = datetime.utcnow().isoformat()

        df = pd.concat([df, pd.DataFrame([account])], ignore_index=True)
        df.to_excel(self.accounts_file, index=False)

        return new_id

    def get_account_by_iban(self, iban: str) -> Optional[Dict]:
        """Get account by IBAN."""
        df = pd.read_excel(self.accounts_file)
        match = df[df['iban'] == iban]
        if match.empty:
            return None
        return match.iloc[0].to_dict()

    def update_account(self, account_id: int, updates: Dict[str, Any]) -> bool:
        """Update an account."""
        df = pd.read_excel(self.accounts_file)

        if account_id not in df['id'].values:
            return False

        for key, value in updates.items():
            df.loc[df['id'] == account_id, key] = value

        df.to_excel(self.accounts_file, index=False)
        return True


class GoogleSheetsStorage:
    """
    Storage backend using Google Sheets.

    Requires:
    - GOOGLE_SHEETS_CREDENTIALS: JSON credentials for service account
    - GOOGLE_SHEETS_ID: ID of the Google Sheets document
    """

    def __init__(self):
        self.credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")
        self.spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID", "")
        self._client = None
        self._spreadsheet = None

    def _get_client(self):
        """Get or create Google Sheets client."""
        if self._client is None:
            try:
                import gspread
                from google.oauth2.service_account import Credentials

                scopes = [
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]

                creds_dict = json.loads(self.credentials_json)
                credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                self._client = gspread.authorize(credentials)
                self._spreadsheet = self._client.open_by_key(self.spreadsheet_id)

            except Exception as e:
                logger.error(f"Failed to connect to Google Sheets: {e}")
                raise

        return self._client, self._spreadsheet

    def _get_worksheet(self, name: str):
        """Get or create a worksheet."""
        _, spreadsheet = self._get_client()

        try:
            return spreadsheet.worksheet(name)
        except:
            # Create worksheet if it doesn't exist
            return spreadsheet.add_worksheet(title=name, rows=1000, cols=20)

    def _worksheet_to_df(self, worksheet) -> pd.DataFrame:
        """Convert worksheet to DataFrame."""
        data = worksheet.get_all_records()
        return pd.DataFrame(data)

    def _df_to_worksheet(self, df: pd.DataFrame, worksheet):
        """Write DataFrame to worksheet."""
        worksheet.clear()
        if not df.empty:
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())

    # Similar methods as ExcelStorage but using Google Sheets...
    # (Implementation follows same pattern)

    def get_transactions(self, **filters) -> pd.DataFrame:
        ws = self._get_worksheet("Transactions")
        df = self._worksheet_to_df(ws)

        if df.empty:
            return df

        # Apply filters
        if filters.get('start_date'):
            df['transaction_date'] = pd.to_datetime(df['transaction_date']).dt.date
            df = df[df['transaction_date'] >= filters['start_date']]
        if filters.get('end_date'):
            df = df[df['transaction_date'] <= filters['end_date']]
        if filters.get('category_id'):
            df = df[df['category_id'] == filters['category_id']]
        if filters.get('project_id'):
            df = df[df['project_id'] == filters['project_id']]
        if filters.get('side'):
            df = df[df['side'] == filters['side']]

        return df

    def add_transaction(self, transaction: Dict[str, Any]) -> int:
        ws = self._get_worksheet("Transactions")
        df = self._worksheet_to_df(ws)

        new_id = 1 if df.empty else int(df['id'].max()) + 1
        transaction['id'] = new_id
        transaction['created_at'] = datetime.utcnow().isoformat()

        df = pd.concat([df, pd.DataFrame([transaction])], ignore_index=True)
        self._df_to_worksheet(df, ws)

        return new_id

    def get_categories(self, active_only: bool = True) -> pd.DataFrame:
        ws = self._get_worksheet("Categories")
        df = self._worksheet_to_df(ws)

        if active_only and not df.empty and 'is_active' in df.columns:
            df = df[df['is_active'] == True]

        return df

    def add_category(self, category: Dict[str, Any]) -> int:
        ws = self._get_worksheet("Categories")
        df = self._worksheet_to_df(ws)

        new_id = 1 if df.empty else int(df['id'].max()) + 1
        category['id'] = new_id
        category['created_at'] = datetime.utcnow().isoformat()

        df = pd.concat([df, pd.DataFrame([category])], ignore_index=True)
        self._df_to_worksheet(df, ws)

        return new_id

    def get_projects(self, active_only: bool = True) -> pd.DataFrame:
        ws = self._get_worksheet("Projects")
        df = self._worksheet_to_df(ws)

        if active_only and not df.empty and 'is_active' in df.columns:
            df = df[df['is_active'] == True]

        return df

    def add_project(self, project: Dict[str, Any]) -> int:
        ws = self._get_worksheet("Projects")
        df = self._worksheet_to_df(ws)

        new_id = 1 if df.empty else int(df['id'].max()) + 1
        project['id'] = new_id
        project['created_at'] = datetime.utcnow().isoformat()

        df = pd.concat([df, pd.DataFrame([project])], ignore_index=True)
        self._df_to_worksheet(df, ws)

        return new_id


def get_storage():
    """Get the appropriate storage backend based on environment."""
    storage_type = os.getenv("STORAGE_TYPE", "excel").lower()

    if storage_type == "airtable":
        from app.storage.airtable_storage import AirtableStorage
        return AirtableStorage()
    elif storage_type == "google_sheets":
        return GoogleSheetsStorage()
    else:
        return ExcelStorage()
