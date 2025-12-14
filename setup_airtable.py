#!/usr/bin/env python3
"""
Script para crear las tablas en Airtable.

Uso:
  python setup_airtable.py --token TU_TOKEN --base TU_BASE_ID

O configura variables de entorno:
  export AIRTABLE_TOKEN=tu_token
  export AIRTABLE_BASE_ID=tu_base_id
  python setup_airtable.py
"""

import urllib.request
import urllib.error
import json
import os
import argparse

def get_config():
    parser = argparse.ArgumentParser(description='Setup Airtable tables')
    parser.add_argument('--token', help='Airtable Personal Access Token')
    parser.add_argument('--base', help='Airtable Base ID')
    args = parser.parse_args()

    token = args.token or os.getenv("AIRTABLE_TOKEN")
    base_id = args.base or os.getenv("AIRTABLE_BASE_ID")

    if not token or not base_id:
        print("❌ Error: Necesitas proporcionar token y base_id")
        print("\nUso:")
        print("  python setup_airtable.py --token TU_TOKEN --base TU_BASE_ID")
        print("\nO con variables de entorno:")
        print("  export AIRTABLE_TOKEN=tu_token")
        print("  export AIRTABLE_BASE_ID=tu_base_id")
        exit(1)

    return token, base_id

TABLES = [
    {
        "name": "Transactions",
        "fields": [
            {"name": "qonto_id", "type": "singleLineText"},
            {"name": "amount", "type": "number", "options": {"precision": 2}},
            {"name": "currency", "type": "singleLineText"},
            {"name": "side", "type": "singleLineText"},
            {"name": "transaction_date", "type": "date"},
            {"name": "label", "type": "singleLineText"},
            {"name": "counterparty_name", "type": "singleLineText"},
            {"name": "category_id", "type": "singleLineText"},
            {"name": "project_id", "type": "singleLineText"},
            {"name": "is_excluded", "type": "checkbox"},
            {"name": "created_at", "type": "singleLineText"},
            {"name": "synced_at", "type": "singleLineText"}
        ]
    },
    {
        "name": "Categories",
        "fields": [
            {"name": "name", "type": "singleLineText"},
            {"name": "type", "type": "singleLineText"},
            {"name": "keywords", "type": "multilineText"},
            {"name": "is_active", "type": "checkbox"},
            {"name": "is_system", "type": "checkbox"},
            {"name": "created_at", "type": "singleLineText"}
        ]
    },
    {
        "name": "Projects",
        "fields": [
            {"name": "name", "type": "singleLineText"},
            {"name": "code", "type": "singleLineText"},
            {"name": "client_name", "type": "singleLineText"},
            {"name": "description", "type": "multilineText"},
            {"name": "budget_amount", "type": "number", "options": {"precision": 2}},
            {"name": "contract_value", "type": "number", "options": {"precision": 2}},
            {"name": "status", "type": "singleLineText"},
            {"name": "is_active", "type": "checkbox"},
            {"name": "created_at", "type": "singleLineText"}
        ]
    },
    {
        "name": "Accounts",
        "fields": [
            {"name": "qonto_id", "type": "singleLineText"},
            {"name": "iban", "type": "singleLineText"},
            {"name": "name", "type": "singleLineText"},
            {"name": "currency", "type": "singleLineText"},
            {"name": "balance", "type": "number", "options": {"precision": 2}},
            {"name": "is_main", "type": "checkbox"},
            {"name": "last_synced_at", "type": "singleLineText"},
            {"name": "created_at", "type": "singleLineText"}
        ]
    }
]

def create_tables(token, base_id):
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("🚀 Creando tablas en Airtable...\n")

    for table in TABLES:
        print(f"📋 Creando tabla: {table['name']}...")
        try:
            data = json.dumps(table).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                print(f"   ✅ Creada: {result.get('id')}\n")

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_data = json.loads(error_body)
                if "DUPLICATE_TABLE_NAME" in str(error_data):
                    print(f"   ⚠️  Ya existe, saltando...\n")
                else:
                    print(f"   ❌ Error: {error_data.get('error', {}).get('message', error_body)}\n")
            except:
                print(f"   ❌ Error {e.code}: {error_body[:100]}\n")

        except Exception as e:
            print(f"   ❌ Error: {e}\n")

    print("=" * 50)
    print("✅ ¡Tablas creadas!")
    print("=" * 50)

if __name__ == "__main__":
    token, base_id = get_config()
    create_tables(token, base_id)
