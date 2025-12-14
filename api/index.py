"""
Vercel serverless entry point using Flask.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/")
def root():
    return jsonify({
        "name": "Rentabilidad G4U",
        "status": "running",
        "storage_type": os.getenv("STORAGE_TYPE", "not_set"),
    })

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

@app.route("/debug/env")
def debug_env():
    return jsonify({
        "STORAGE_TYPE": os.getenv("STORAGE_TYPE", "NOT SET"),
        "AIRTABLE_BASE_ID": "SET" if os.getenv("AIRTABLE_BASE_ID") else "NOT SET",
        "AIRTABLE_TOKEN": "SET" if os.getenv("AIRTABLE_TOKEN") else "NOT SET",
        "QONTO_API_KEY": "SET" if os.getenv("QONTO_API_KEY") else "NOT SET",
    })

# API routes
@app.route("/api/v1/sync/init", methods=["POST"])
def sync_init():
    try:
        from app.services.excel_sync_service import SyncService
        import asyncio
        service = SyncService()
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(service.initialize_categories())
        loop.close()
        return jsonify({
            "status": "success",
            "categories_created": result["created"],
            "categories_existing": result["existing"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/sync/accounts", methods=["POST"])
def sync_accounts():
    try:
        from app.services.excel_sync_service import SyncService
        import asyncio
        service = SyncService()
        loop = asyncio.new_event_loop()
        accounts = loop.run_until_complete(service.sync_accounts())
        loop.close()
        return jsonify({
            "status": "success",
            "synced_count": len(accounts),
            "accounts": accounts,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/sync/transactions", methods=["POST"])
def sync_transactions():
    try:
        from app.services.excel_sync_service import SyncService
        import asyncio
        service = SyncService()
        loop = asyncio.new_event_loop()
        stats = loop.run_until_complete(service.sync_transactions())
        loop.close()
        return jsonify({"status": "success", **stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/sync/all", methods=["POST"])
def sync_all():
    try:
        from app.services.excel_sync_service import SyncService
        import asyncio
        service = SyncService()
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(service.sync_all())
        loop.close()
        return jsonify({"status": "success", **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/categories")
def list_categories():
    try:
        from app.storage.excel_storage import get_storage
        storage = get_storage()
        data = storage.get_categories()
        if hasattr(data, 'to_dict'):
            data = data.to_dict('records')
        return jsonify({"categories": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/transactions")
def list_transactions():
    try:
        from app.storage.excel_storage import get_storage
        storage = get_storage()
        data = storage.get_transactions()
        if hasattr(data, 'to_dict'):
            data = data.to_dict('records')
        return jsonify({"items": data, "total": len(data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/reports/pl")
def pl_report():
    try:
        from datetime import date
        from app.services.excel_financial_service import ExcelFinancialService

        start = request.args.get('start_date', '2024-01-01')
        end = request.args.get('end_date', '2024-12-31')

        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)

        service = ExcelFinancialService()
        result = service.calculate_pl_summary(start_date, end_date)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/kpis/dashboard")
def dashboard():
    try:
        from app.services.excel_financial_service import ExcelFinancialService
        service = ExcelFinancialService()
        result = service.get_dashboard_kpis()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
