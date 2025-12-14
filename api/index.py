"""
Rentabilidad G4U - Simple P&L Dashboard
"""
import os
import sys
from pathlib import Path
from datetime import datetime, date
from flask import Flask, jsonify, request, render_template_string
import httpx

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)

# ==================== Airtable Client ====================

class Airtable:
    def __init__(self):
        self.token = os.getenv("AIRTABLE_TOKEN", "")
        self.base_id = os.getenv("AIRTABLE_BASE_ID", "")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def get_all(self, table, formula=None):
        records = []
        params = {}
        if formula:
            params["filterByFormula"] = formula

        offset = None
        while True:
            if offset:
                params["offset"] = offset

            with httpx.Client(timeout=30) as client:
                r = client.get(f"{self.base_url}/{table}", headers=self.headers, params=params)
                r.raise_for_status()
                data = r.json()

            for rec in data.get("records", []):
                records.append({"id": rec["id"], **rec.get("fields", {})})

            offset = data.get("offset")
            if not offset:
                break

        return records

    def create(self, table, fields):
        with httpx.Client(timeout=30) as client:
            r = client.post(f"{self.base_url}/{table}", headers=self.headers, json={"fields": fields})
            r.raise_for_status()
            return r.json()

    def update(self, table, record_id, fields):
        with httpx.Client(timeout=30) as client:
            r = client.patch(f"{self.base_url}/{table}/{record_id}", headers=self.headers, json={"fields": fields})
            r.raise_for_status()
            return r.json()

# ==================== Qonto Client ====================

class Qonto:
    def __init__(self):
        self.org = os.getenv("QONTO_ORGANIZATION_SLUG", "")
        self.key = os.getenv("QONTO_API_KEY", "")
        self.iban = os.getenv("QONTO_IBAN", "")
        self.base_url = "https://thirdparty.qonto.com/v2"

    @property
    def headers(self):
        return {"Authorization": f"{self.org}:{self.key}"}

    def get_transactions(self, status="completed"):
        transactions = []
        page = 1

        while True:
            with httpx.Client(timeout=30) as client:
                r = client.get(
                    f"{self.base_url}/transactions",
                    headers=self.headers,
                    params={"iban": self.iban, "status": status, "current_page": page, "per_page": 100}
                )
                r.raise_for_status()
                data = r.json()

            txs = data.get("transactions", [])
            if not txs:
                break

            transactions.extend(txs)

            meta = data.get("meta", {})
            if page >= meta.get("total_pages", 1):
                break
            page += 1

        return transactions

# ==================== HTML Template ====================

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Rentabilidad G4U</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: system-ui, sans-serif; background: #f0f2f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { margin-bottom: 10px; }
        .subtitle { color: #666; margin-bottom: 20px; }

        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card h3 { font-size: 14px; color: #666; margin-bottom: 8px; }
        .card .value { font-size: 28px; font-weight: 600; }
        .card .value.positive { color: #22c55e; }
        .card .value.negative { color: #ef4444; }

        .section { background: white; border-radius: 12px; padding: 20px; margin: 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .section h2 { margin-bottom: 15px; font-size: 18px; }

        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; font-size: 13px; color: #666; }

        .amount { font-family: monospace; font-weight: 500; }
        .amount.credit { color: #22c55e; }
        .amount.debit { color: #ef4444; }

        .btn { background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; }
        .btn:hover { background: #2563eb; }
        .btn.success { background: #22c55e; }
        .btn.sm { padding: 6px 12px; font-size: 12px; }

        select { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }

        .status { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .status.ok { background: #dcfce7; color: #166534; }
        .status.error { background: #fee2e2; color: #991b1b; }

        .loading { text-align: center; padding: 40px; color: #666; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: #e5e7eb; border-radius: 8px; cursor: pointer; }
        .tab.active { background: #3b82f6; color: white; }

        .hidden { display: none; }
        .flex { display: flex; gap: 10px; align-items: center; }
        .ml-auto { margin-left: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Rentabilidad G4U</h1>
        <p class="subtitle">Dashboard financiero conectado a Qonto</p>

        <div id="status-bar" class="flex" style="margin-bottom: 20px;">
            <span id="env-status">Verificando configuración...</span>
            <div class="ml-auto">
                <button class="btn" onclick="syncQonto()">Sincronizar Qonto</button>
            </div>
        </div>

        <!-- KPIs -->
        <div class="grid" id="kpis">
            <div class="card"><h3>Ingresos</h3><div class="value positive" id="total-income">-</div></div>
            <div class="card"><h3>Gastos</h3><div class="value negative" id="total-expenses">-</div></div>
            <div class="card"><h3>Resultado Neto</h3><div class="value" id="net-result">-</div></div>
            <div class="card"><h3>Margen</h3><div class="value" id="margin">-</div></div>
        </div>

        <!-- Tabs -->
        <div class="tabs">
            <div class="tab active" onclick="showTab('transactions')">Transacciones</div>
            <div class="tab" onclick="showTab('categories')">Por Categoría</div>
            <div class="tab" onclick="showTab('projects')">Por Proyecto</div>
        </div>

        <!-- Transactions Tab -->
        <div id="tab-transactions" class="section">
            <div class="flex" style="margin-bottom: 15px;">
                <h2>Transacciones</h2>
                <div class="ml-auto flex">
                    <select id="filter-side" onchange="loadTransactions()">
                        <option value="">Todos</option>
                        <option value="credit">Ingresos</option>
                        <option value="debit">Gastos</option>
                    </select>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Descripción</th>
                        <th>Monto</th>
                        <th>Categoría</th>
                        <th>Proyecto</th>
                    </tr>
                </thead>
                <tbody id="transactions-body">
                    <tr><td colspan="5" class="loading">Cargando...</td></tr>
                </tbody>
            </table>
        </div>

        <!-- Categories Tab -->
        <div id="tab-categories" class="section hidden">
            <h2>Desglose por Categoría</h2>
            <table>
                <thead>
                    <tr><th>Categoría</th><th>Ingresos</th><th>Gastos</th><th>Neto</th></tr>
                </thead>
                <tbody id="categories-body">
                    <tr><td colspan="4" class="loading">Cargando...</td></tr>
                </tbody>
            </table>
        </div>

        <!-- Projects Tab -->
        <div id="tab-projects" class="section hidden">
            <h2>Rentabilidad por Proyecto</h2>
            <table>
                <thead>
                    <tr><th>Proyecto</th><th>Ingresos</th><th>Costos</th><th>Margen</th><th>ROI</th></tr>
                </thead>
                <tbody id="projects-body">
                    <tr><td colspan="5" class="loading">Cargando...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let transactions = [];
        let categories = [];
        let projects = [];

        // Format currency
        function fmt(n) {
            return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(n || 0);
        }

        // Show tab
        function showTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('[id^="tab-"]').forEach(t => t.classList.add('hidden'));
            event.target.classList.add('active');
            document.getElementById('tab-' + name).classList.remove('hidden');
        }

        // Check environment
        async function checkEnv() {
            try {
                const r = await fetch('/api/status');
                const data = await r.json();
                const allOk = Object.values(data).every(v => v === true || v === 'SET');
                document.getElementById('env-status').innerHTML = allOk
                    ? '<span class="status ok">Sistema configurado</span>'
                    : '<span class="status error">Faltan variables de entorno</span>';
            } catch(e) {
                document.getElementById('env-status').innerHTML = '<span class="status error">Error de conexión</span>';
            }
        }

        // Load data
        async function loadData() {
            try {
                const r = await fetch('/api/data');
                const data = await r.json();

                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }

                transactions = data.transactions || [];
                categories = data.categories || [];
                projects = data.projects || [];

                updateKPIs();
                loadTransactions();
                loadCategories();
                loadProjects();
            } catch(e) {
                console.error(e);
            }
        }

        // Update KPIs
        function updateKPIs() {
            let income = 0, expenses = 0;
            transactions.forEach(t => {
                const amt = parseFloat(t.amount) || 0;
                if (t.side === 'credit') income += amt;
                else expenses += amt;
            });

            const net = income - expenses;
            const margin = income > 0 ? (net / income * 100) : 0;

            document.getElementById('total-income').textContent = fmt(income);
            document.getElementById('total-expenses').textContent = fmt(expenses);
            document.getElementById('net-result').textContent = fmt(net);
            document.getElementById('net-result').className = 'value ' + (net >= 0 ? 'positive' : 'negative');
            document.getElementById('margin').textContent = margin.toFixed(1) + '%';
        }

        // Load transactions table
        function loadTransactions() {
            const filter = document.getElementById('filter-side').value;
            let filtered = transactions;
            if (filter) filtered = transactions.filter(t => t.side === filter);

            const projectsMap = {};
            projects.forEach(p => projectsMap[p.id] = p.name);

            const html = filtered.slice(0, 100).map(t => `
                <tr>
                    <td>${t.settled_at ? t.settled_at.split('T')[0] : '-'}</td>
                    <td>${t.counterparty_name || t.label || '-'}</td>
                    <td class="amount ${t.side}">${t.side === 'credit' ? '+' : '-'}${fmt(t.amount)}</td>
                    <td>${t.category || '-'}</td>
                    <td>
                        <select onchange="assignProject('${t.id}', this.value)" style="width:120px">
                            <option value="">Sin proyecto</option>
                            ${projects.map(p => `<option value="${p.id}" ${t.project_id === p.id ? 'selected' : ''}>${p.name}</option>`).join('')}
                        </select>
                    </td>
                </tr>
            `).join('');

            document.getElementById('transactions-body').innerHTML = html || '<tr><td colspan="5">No hay transacciones</td></tr>';
        }

        // Load categories breakdown
        function loadCategories() {
            const byCategory = {};
            transactions.forEach(t => {
                const cat = t.category || 'Sin categoría';
                if (!byCategory[cat]) byCategory[cat] = { income: 0, expense: 0 };
                const amt = parseFloat(t.amount) || 0;
                if (t.side === 'credit') byCategory[cat].income += amt;
                else byCategory[cat].expense += amt;
            });

            const html = Object.entries(byCategory).map(([cat, v]) => `
                <tr>
                    <td>${cat}</td>
                    <td class="amount credit">${fmt(v.income)}</td>
                    <td class="amount debit">${fmt(v.expense)}</td>
                    <td class="amount ${v.income - v.expense >= 0 ? 'credit' : 'debit'}">${fmt(v.income - v.expense)}</td>
                </tr>
            `).join('');

            document.getElementById('categories-body').innerHTML = html || '<tr><td colspan="4">No hay datos</td></tr>';
        }

        // Load projects breakdown
        function loadProjects() {
            const byProject = {};
            projects.forEach(p => byProject[p.id] = { name: p.name, income: 0, expense: 0 });

            transactions.forEach(t => {
                if (t.project_id && byProject[t.project_id]) {
                    const amt = parseFloat(t.amount) || 0;
                    if (t.side === 'credit') byProject[t.project_id].income += amt;
                    else byProject[t.project_id].expense += amt;
                }
            });

            const html = Object.values(byProject).map(p => {
                const margin = p.income > 0 ? ((p.income - p.expense) / p.income * 100) : 0;
                const roi = p.expense > 0 ? ((p.income - p.expense) / p.expense * 100) : 0;
                return `
                    <tr>
                        <td>${p.name}</td>
                        <td class="amount credit">${fmt(p.income)}</td>
                        <td class="amount debit">${fmt(p.expense)}</td>
                        <td>${margin.toFixed(1)}%</td>
                        <td>${roi.toFixed(1)}%</td>
                    </tr>
                `;
            }).join('');

            document.getElementById('projects-body').innerHTML = html || '<tr><td colspan="5">No hay proyectos</td></tr>';
        }

        // Assign project to transaction
        async function assignProject(txId, projectId) {
            try {
                await fetch('/api/assign-project', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ transaction_id: txId, project_id: projectId })
                });
                // Update local data
                const tx = transactions.find(t => t.id === txId);
                if (tx) tx.project_id = projectId;
                loadProjects();
            } catch(e) {
                alert('Error al asignar proyecto');
            }
        }

        // Sync from Qonto
        async function syncQonto() {
            if (!confirm('¿Sincronizar transacciones desde Qonto?')) return;

            try {
                const r = await fetch('/api/sync', { method: 'POST' });
                const data = await r.json();

                if (data.error) {
                    alert('Error: ' + data.error);
                } else {
                    alert(`Sincronizado: ${data.synced} transacciones`);
                    loadData();
                }
            } catch(e) {
                alert('Error de conexión');
            }
        }

        // Init
        checkEnv();
        loadData();
    </script>
</body>
</html>
"""

# ==================== Routes ====================

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/status")
def api_status():
    return jsonify({
        "airtable": bool(os.getenv("AIRTABLE_TOKEN") and os.getenv("AIRTABLE_BASE_ID")),
        "qonto": bool(os.getenv("QONTO_API_KEY") and os.getenv("QONTO_ORGANIZATION_SLUG") and os.getenv("QONTO_IBAN")),
    })

@app.route("/api/data")
def api_data():
    try:
        airtable = Airtable()

        transactions = airtable.get_all("Transactions")
        categories = airtable.get_all("Categories")
        projects = airtable.get_all("Projects")

        return jsonify({
            "transactions": transactions,
            "categories": categories,
            "projects": projects,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sync", methods=["POST"])
def api_sync():
    try:
        qonto = Qonto()
        airtable = Airtable()

        # Get existing transaction IDs
        existing = airtable.get_all("Transactions")
        existing_ids = {t.get("qonto_id") for t in existing}

        # Get from Qonto
        qonto_txs = qonto.get_transactions()

        synced = 0
        for tx in qonto_txs:
            tx_id = tx.get("transaction_id")
            if tx_id in existing_ids:
                continue

            # Create in Airtable
            airtable.create("Transactions", {
                "qonto_id": tx_id,
                "amount": tx.get("amount", 0),
                "currency": tx.get("currency", "EUR"),
                "side": tx.get("side", ""),
                "counterparty_name": tx.get("label", ""),
                "label": tx.get("note") or tx.get("reference", ""),
                "settled_at": tx.get("settled_at", ""),
                "status": tx.get("status", ""),
            })
            synced += 1

        return jsonify({"synced": synced, "total": len(qonto_txs)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/assign-project", methods=["POST"])
def api_assign_project():
    try:
        data = request.json
        tx_id = data.get("transaction_id")
        project_id = data.get("project_id")

        airtable = Airtable()
        airtable.update("Transactions", tx_id, {"project_id": project_id or None})

        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({"status": "ok"})
