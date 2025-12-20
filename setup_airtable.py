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

# Base tables (original)
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
            {"name": "review_status", "type": "singleSelect", "options": {
                "choices": [
                    {"name": "pending", "color": "yellowBright"},
                    {"name": "confirmed", "color": "greenBright"}
                ]
            }},
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

# New tables for allocation system (v2 backend)
NEW_TABLES = [
    {
        "name": "TransactionAllocations",
        "fields": [
            {"name": "transaction_id", "type": "singleLineText"},  # Reference to Transactions record
            {"name": "project_id", "type": "singleLineText"},      # Reference to Projects record (optional)
            {"name": "client_name", "type": "singleLineText"},     # Client name (optional, independent)
            {"name": "percentage", "type": "number", "options": {"precision": 4}},  # 0-100%
            {"name": "amount_allocated", "type": "number", "options": {"precision": 2}},
            {"name": "notes", "type": "multilineText"},
            {"name": "created_at", "type": "singleLineText"},
            {"name": "updated_at", "type": "singleLineText"}
        ]
    },
    {
        "name": "AssignmentRules",
        "fields": [
            {"name": "name", "type": "singleLineText"},
            {"name": "description", "type": "multilineText"},
            {"name": "keywords", "type": "multilineText"},           # JSON array or comma-separated
            {"name": "counterparty", "type": "singleLineText"},      # Exact match
            {"name": "counterparty_pattern", "type": "singleLineText"},  # Regex pattern
            {"name": "client_name_suggested", "type": "singleLineText"},
            {"name": "project_id_suggested", "type": "singleLineText"},
            {"name": "priority", "type": "number", "options": {"precision": 0}},
            {"name": "is_active", "type": "checkbox"},
            {"name": "created_at", "type": "singleLineText"},
            {"name": "updated_at", "type": "singleLineText"}
        ]
    }
]

# Fields to add to existing tables
FIELD_UPDATES = {
    "Transactions": [
        {"name": "review_status", "type": "singleSelect", "options": {
            "choices": [
                {"name": "pending", "color": "yellowBright"},
                {"name": "confirmed", "color": "greenBright"}
            ]
        }}
    ]
}

def get_table_id(token, base_id, table_name):
    """Get table ID by name."""
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            for table in result.get("tables", []):
                if table.get("name") == table_name:
                    return table.get("id")
    except Exception as e:
        print(f"   ⚠️  Error getting table ID: {e}")
    return None


def add_field_to_table(token, base_id, table_id, field):
    """Add a field to an existing table."""
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{table_id}/fields"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        data = json.dumps(field).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            return True, result.get('id')
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        if "DUPLICATE_FIELD_NAME" in error_body or "already exists" in error_body.lower():
            return False, "already_exists"
        return False, error_body
    except Exception as e:
        return False, str(e)


def create_tables(token, base_id):
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("🚀 Creando tablas base en Airtable...\n")

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
    print("✅ ¡Tablas base creadas!")
    print("=" * 50)


def create_new_tables(token, base_id):
    """Create new tables for v2 allocation system."""
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("\n🚀 Creando tablas nuevas (sistema de allocations)...\n")

    for table in NEW_TABLES:
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
    print("✅ ¡Tablas nuevas creadas!")
    print("=" * 50)


def update_existing_tables(token, base_id):
    """Add new fields to existing tables."""
    print("\n🔧 Actualizando tablas existentes...\n")

    for table_name, fields in FIELD_UPDATES.items():
        print(f"📋 Actualizando tabla: {table_name}...")
        table_id = get_table_id(token, base_id, table_name)

        if not table_id:
            print(f"   ❌ No se encontró la tabla {table_name}\n")
            continue

        for field in fields:
            success, result = add_field_to_table(token, base_id, table_id, field)
            if success:
                print(f"   ✅ Campo '{field['name']}' agregado: {result}\n")
            elif result == "already_exists":
                print(f"   ⚠️  Campo '{field['name']}' ya existe, saltando...\n")
            else:
                print(f"   ❌ Error agregando '{field['name']}': {result}\n")

    print("=" * 50)
    print("✅ ¡Tablas actualizadas!")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description='Setup Airtable tables')
    parser.add_argument('--token', help='Airtable Personal Access Token')
    parser.add_argument('--base', help='Airtable Base ID')
    parser.add_argument('--mode', choices=['all', 'base', 'new', 'update'],
                       default='all', help='What to create/update')
    args = parser.parse_args()

    token = args.token or os.getenv("AIRTABLE_TOKEN")
    base_id = args.base or os.getenv("AIRTABLE_BASE_ID")

    if not token or not base_id:
        print("❌ Error: Necesitas proporcionar token y base_id")
        print("\nUso:")
        print("  python setup_airtable.py --token TU_TOKEN --base TU_BASE_ID")
        print("\nModos disponibles:")
        print("  --mode all    : Crear todo (base + nuevas + actualizar)")
        print("  --mode base   : Solo tablas base originales")
        print("  --mode new    : Solo tablas nuevas (allocations, rules)")
        print("  --mode update : Solo actualizar campos en tablas existentes")
        exit(1)

    if args.mode in ['all', 'base']:
        create_tables(token, base_id)

    if args.mode in ['all', 'new']:
        create_new_tables(token, base_id)

    if args.mode in ['all', 'update']:
        update_existing_tables(token, base_id)

    print("\n" + "=" * 50)
    print("🎉 ¡Proceso completado!")
    print("=" * 50)


if __name__ == "__main__":
    main()
