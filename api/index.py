"""
Vercel serverless entry point using Flask with web interface.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# HTML Template for web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Rentabilidad G4U</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #333; }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h2 { margin-top: 0; color: #444; }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            margin: 5px;
        }
        button:hover { background: #0056b3; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        button.success { background: #28a745; }
        button.danger { background: #dc3545; }
        .result {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            margin-top: 15px;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 13px;
            max-height: 400px;
            overflow: auto;
        }
        .status { padding: 5px 10px; border-radius: 4px; display: inline-block; margin: 5px 0; }
        .status.ok { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .env-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .env-item { padding: 10px; background: #f8f9fa; border-radius: 4px; }
        .loading { opacity: 0.6; pointer-events: none; }
        input[type="date"] { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>Rentabilidad G4U</h1>
    <p>Sistema de reportes P&L conectado a Qonto + Airtable</p>

    <div class="card">
        <h2>Estado del Sistema</h2>
        <div id="env-status">Cargando...</div>
    </div>

    <div class="card">
        <h2>1. Sincronizacion</h2>
        <p>Primero inicializa las categorias, luego sincroniza con Qonto.</p>
        <button onclick="apiCall('/api/v1/sync/init', 'POST')">Inicializar Categorias</button>
        <button onclick="apiCall('/api/v1/sync/accounts', 'POST')">Sync Cuentas</button>
        <button onclick="apiCall('/api/v1/sync/transactions', 'POST')">Sync Transacciones</button>
        <button onclick="apiCall('/api/v1/sync/all', 'POST')" class="success">Sync Todo</button>
        <div id="sync-result" class="result" style="display:none;"></div>
    </div>

    <div class="card">
        <h2>2. Datos</h2>
        <button onclick="apiCall('/api/v1/categories')">Ver Categorias</button>
        <button onclick="apiCall('/api/v1/transactions')">Ver Transacciones</button>
        <button onclick="apiCall('/api/v1/projects')">Ver Proyectos</button>
        <div id="data-result" class="result" style="display:none;"></div>
    </div>

    <div class="card">
        <h2>3. Reportes P&L</h2>
        <div style="margin: 10px 0;">
            <label>Desde: <input type="date" id="start_date" value="2024-01-01"></label>
            <label>Hasta: <input type="date" id="end_date" value="2024-12-31"></label>
        </div>
        <button onclick="getPL()">Generar Reporte P&L</button>
        <button onclick="apiCall('/api/v1/kpis/dashboard')">Dashboard KPIs</button>
        <button onclick="apiCall('/api/v1/kpis/projects')">KPIs por Proyecto</button>
        <div id="report-result" class="result" style="display:none;"></div>
    </div>

    <script>
        // Check environment on load
        fetch('/debug/env')
            .then(r => r.json())
            .then(data => {
                let html = '<div class="env-grid">';
                for (let [key, value] of Object.entries(data)) {
                    const status = value === 'NOT SET' ? 'error' : 'ok';
                    html += '<div class="env-item"><strong>' + key + '</strong><br><span class="status ' + status + '">' + value + '</span></div>';
                }
                html += '</div>';
                document.getElementById('env-status').innerHTML = html;
            })
            .catch(e => {
                document.getElementById('env-status').innerHTML = '<span class="status error">Error: ' + e + '</span>';
            });

        function apiCall(url, method = 'GET') {
            const resultDiv = url.includes('sync') ? 'sync-result' :
                              url.includes('report') || url.includes('kpi') ? 'report-result' : 'data-result';
            const el = document.getElementById(resultDiv);
            el.style.display = 'block';
            el.textContent = 'Cargando...';

            fetch(url, { method: method })
                .then(r => r.json())
                .then(data => {
                    el.textContent = JSON.stringify(data, null, 2);
                })
                .catch(e => {
                    el.textContent = 'Error: ' + e;
                });
        }

        function getPL() {
            const start = document.getElementById('start_date').value;
            const end = document.getElementById('end_date').value;
            apiCall('/api/v1/reports/pl?start_date=' + start + '&end_date=' + end);
        }
    </script>
</body>
</html>
"""

@app.route("/")
def root():
    return render_template_string(HTML_TEMPLATE)

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
        "QONTO_ORGANIZATION_SLUG": os.getenv("QONTO_ORGANIZATION_SLUG", "NOT SET"),
        "QONTO_IBAN": "SET" if os.getenv("QONTO_IBAN") else "NOT SET",
    })

# ==================== Sync Endpoints ====================

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
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

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
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

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
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

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
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

# ==================== Data Endpoints ====================

@app.route("/api/v1/categories")
def list_categories():
    try:
        from app.storage.excel_storage import get_storage
        storage = get_storage()
        data = storage.get_categories()
        if hasattr(data, 'to_dict'):
            data = data.to_dict('records')
        return jsonify({"categories": data, "count": len(data)})
    except Exception as e:
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

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
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

@app.route("/api/v1/projects")
def list_projects():
    try:
        from app.storage.excel_storage import get_storage
        storage = get_storage()
        data = storage.get_projects()
        if hasattr(data, 'to_dict'):
            data = data.to_dict('records')
        return jsonify({"projects": data, "count": len(data)})
    except Exception as e:
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

# ==================== Report Endpoints ====================

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
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

@app.route("/api/v1/kpis/dashboard")
def dashboard():
    try:
        from app.services.excel_financial_service import ExcelFinancialService
        service = ExcelFinancialService()
        result = service.get_dashboard_kpis()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

@app.route("/api/v1/kpis/projects")
def projects_kpis():
    try:
        from app.storage.excel_storage import get_storage
        from app.services.excel_financial_service import ExcelFinancialService

        storage = get_storage()
        service = ExcelFinancialService()

        data = storage.get_projects()
        if hasattr(data, 'to_dict'):
            projects = data.to_dict('records')
        else:
            projects = data if data else []

        if not projects:
            return jsonify({"projects": [], "totals": {"total_income": 0, "total_expenses": 0, "total_profit": 0}})

        project_kpis = []
        total_income = 0
        total_expenses = 0

        for project in projects:
            kpi = service.calculate_project_kpis(project.get('id'))
            if kpi:
                project_kpis.append(kpi)
                total_income += kpi['total_income']
                total_expenses += kpi['total_expenses']

        return jsonify({
            "projects": project_kpis,
            "totals": {
                "total_income": round(total_income, 2),
                "total_expenses": round(total_expenses, 2),
                "total_profit": round(total_income - total_expenses, 2),
            },
        })
    except Exception as e:
        return jsonify({"error": str(e), "type": type(e).__name__}), 500
