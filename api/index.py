# -*- coding: utf-8 -*-
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

    def create_batch(self, table, records_list):
        """Create up to 10 records at once."""
        with httpx.Client(timeout=30) as client:
            payload = {"records": [{"fields": f} for f in records_list]}
            r = client.post(f"{self.base_url}/{table}", headers=self.headers, json=payload)
            r.raise_for_status()
            return r.json()

    def update(self, table, record_id, fields):
        with httpx.Client(timeout=30) as client:
            r = client.patch(f"{self.base_url}/{table}/{record_id}", headers=self.headers, json={"fields": fields})
            r.raise_for_status()
            return r.json()

    def delete_batch(self, table, record_ids):
        """Delete up to 10 records at once."""
        with httpx.Client(timeout=30) as client:
            # Airtable expects records[] query params
            params = "&".join([f"records[]={rid}" for rid in record_ids])
            r = client.delete(f"{self.base_url}/{table}?{params}", headers=self.headers)
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
        # Qonto API uses format: organization_slug:secret_key
        return {"Authorization": f"{self.org}:{self.key}"}

    def get_bank_account_id(self):
        """Get the bank_account_id for the configured IBAN."""
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{self.base_url}/organization", headers=self.headers)
            if r.status_code == 200:
                org = r.json().get("organization", {})
                for ba in org.get("bank_accounts", []):
                    if ba.get("iban") == self.iban:
                        return ba.get("slug")  # bank_account_id is the slug
        return None

    def get_all_transactions(self, slug):
        """Fetch all transactions for a given bank account slug."""
        transactions = []
        page = 1

        with httpx.Client(timeout=60) as client:
            while True:
                params = {"slug": slug, "status": "completed", "page": page, "per_page": 100}
                r = client.get(f"{self.base_url}/transactions", headers=self.headers, params=params)

                if r.status_code != 200:
                    break

                data = r.json()
                txs = data.get("transactions", [])

                if not txs:
                    break

                transactions.extend(txs)

                meta = data.get("meta", {})
                total_pages = meta.get("total_pages", 1)
                if page >= total_pages:
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

        table { width: 100vw; max-width: 100vw; border-collapse: collapse; }
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
            <span id="env-status">Verificando configuracion...</span>
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
            <div class="tab active" onclick="showTab('transactions', event)">Transacciones</div>
            <div class="tab" onclick="showTab('categories', event)">Por Categoria</div>
            <div class="tab" onclick="showTab('projects', event)">Por Proyecto</div>
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
                        <th>Descripcion</th>
                        <th>Monto</th>
                        <th>Categoria</th>
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
            <h2>Desglose por Categoria</h2>
            <table>
                <thead>
                    <tr><th>Categoria</th><th>Ingresos</th><th>Gastos</th><th>Neto</th></tr>
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
        /* v5 - clean */
        console.log("G4U Script loading v5...");
        var transactions = [];
        var categories = [];
        var projects = [];

        function fmt(n) {
            return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(n || 0);
        }

        function showTab(name, evt) {
            console.log("showTab:", name);
            var tabs = document.querySelectorAll(".tab");
            for (var i = 0; i < tabs.length; i++) { tabs[i].classList.remove("active"); }
            var panels = document.querySelectorAll("[id^=tab-]");
            for (var i = 0; i < panels.length; i++) { panels[i].classList.add("hidden"); }
            if (evt && evt.target) { evt.target.classList.add("active"); }
            document.getElementById("tab-" + name).classList.remove("hidden");
        }

        function checkEnv() {
            fetch("/api/status")
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var ok = data.airtable && data.qonto;
                    document.getElementById("env-status").innerHTML = ok
                        ? "<span class='status ok'>Sistema configurado</span>"
                        : "<span class='status error'>Faltan variables</span>";
                })
                .catch(function(e) {
                    document.getElementById("env-status").innerHTML = "<span class='status error'>Error: " + e.message + "</span>";
                });
        }

        function loadData() {
            fetch("/api/data")
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) {
                        document.getElementById("transactions-body").innerHTML = "<tr><td colspan='5' style='color:red'>" + data.error + "</td></tr>";
                        return;
                    }
                    transactions = data.transactions || [];
                    categories = data.categories || [];
                    projects = data.projects || [];
                    updateKPIs();
                    loadTransactions();
                    loadCategories();
                    loadProjects();
                })
                .catch(function(e) {
                    console.error(e);
                    document.getElementById("transactions-body").innerHTML = "<tr><td colspan='5' style='color:red'>Error: " + e.message + "</td></tr>";
                });
        }

        function updateKPIs() {
            var income = 0, expenses = 0;
            for (var i = 0; i < transactions.length; i++) {
                var t = transactions[i];
                var amt = parseFloat(t.amount) || 0;
                if (t.side === "credit") income += amt;
                else expenses += amt;
            }
            var net = income - expenses;
            var margin = income > 0 ? (net / income * 100) : 0;
            document.getElementById("total-income").textContent = fmt(income);
            document.getElementById("total-expenses").textContent = fmt(expenses);
            document.getElementById("net-result").textContent = fmt(net);
            document.getElementById("net-result").className = "value " + (net >= 0 ? "positive" : "negative");
            document.getElementById("margin").textContent = margin.toFixed(1) + " pct";
        }

        function loadTransactions() {
            var filter = document.getElementById("filter-side").value;
            var filtered = [];
            for (var i = 0; i < transactions.length; i++) {
                if (!filter || transactions[i].side === filter) {
                    filtered.push(transactions[i]);
                }
            }
            var html = "";
            var max = Math.min(filtered.length, 100);
            for (var i = 0; i < max; i++) {
                var t = filtered[i];
                var dateStr = t.settled_at ? t.settled_at.split("T")[0] : "-";
                var name = t.counterparty_name || t.label || "-";
                var sign = t.side === "credit" ? "+" : "-";
                var cls = t.side === "credit" ? "credit" : "debit";
                html += "<tr>";
                html += "<td>" + dateStr + "</td>";
                html += "<td>" + name + "</td>";
                html += "<td class='amount " + cls + "'>" + sign + fmt(t.amount) + "</td>";
                html += "<td>" + (t.category || "-") + "</td>";
                html += "<td><select onchange='assignProject(this.dataset.id, this.value)' data-id='" + t.id + "' style='width:120px'>";
                html += "<option value=''>Sin proyecto</option>";
                for (var j = 0; j < projects.length; j++) {
                    var p = projects[j];
                    var sel = t.project_id === p.id ? " selected" : "";
                    html += "<option value='" + p.id + "'" + sel + ">" + p.name + "</option>";
                }
                html += "</select></td></tr>";
            }
            document.getElementById("transactions-body").innerHTML = html || "<tr><td colspan='5'>No hay transacciones</td></tr>";
        }

        function loadCategories() {
            var byCategory = {};
            for (var i = 0; i < transactions.length; i++) {
                var t = transactions[i];
                var cat = t.category || "Sin categoria";
                if (!byCategory[cat]) byCategory[cat] = { income: 0, expense: 0 };
                var amt = parseFloat(t.amount) || 0;
                if (t.side === "credit") byCategory[cat].income += amt;
                else byCategory[cat].expense += amt;
            }
            var html = "";
            for (var cat in byCategory) {
                var v = byCategory[cat];
                var netCls = (v.income - v.expense) >= 0 ? "credit" : "debit";
                html += "<tr>";
                html += "<td>" + cat + "</td>";
                html += "<td class='amount credit'>" + fmt(v.income) + "</td>";
                html += "<td class='amount debit'>" + fmt(v.expense) + "</td>";
                html += "<td class='amount " + netCls + "'>" + fmt(v.income - v.expense) + "</td>";
                html += "</tr>";
            }
            document.getElementById("categories-body").innerHTML = html || "<tr><td colspan='4'>No hay datos</td></tr>";
        }

        function loadProjects() {
            var byProject = {};
            for (var i = 0; i < projects.length; i++) {
                var p = projects[i];
                byProject[p.id] = { name: p.name, income: 0, expense: 0 };
            }
            for (var i = 0; i < transactions.length; i++) {
                var t = transactions[i];
                if (t.project_id && byProject[t.project_id]) {
                    var amt = parseFloat(t.amount) || 0;
                    if (t.side === "credit") byProject[t.project_id].income += amt;
                    else byProject[t.project_id].expense += amt;
                }
            }
            var html = "";
            for (var id in byProject) {
                var p = byProject[id];
                var margin = p.income > 0 ? ((p.income - p.expense) / p.income * 100) : 0;
                var roi = p.expense > 0 ? ((p.income - p.expense) / p.expense * 100) : 0;
                html += "<tr>";
                html += "<td>" + p.name + "</td>";
                html += "<td class='amount credit'>" + fmt(p.income) + "</td>";
                html += "<td class='amount debit'>" + fmt(p.expense) + "</td>";
                html += "<td>" + margin.toFixed(1) + " pct</td>";
                html += "<td>" + roi.toFixed(1) + " pct</td>";
                html += "</tr>";
            }
            document.getElementById("projects-body").innerHTML = html || "<tr><td colspan='5'>No hay proyectos</td></tr>";
        }

        function assignProject(txId, projectId) {
            fetch("/api/assign-project", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ transaction_id: txId, project_id: projectId })
            }).then(function() {
                for (var i = 0; i < transactions.length; i++) {
                    if (transactions[i].id === txId) {
                        transactions[i].project_id = projectId;
                        break;
                    }
                }
                loadProjects();
            }).catch(function(e) {
                alert("Error al asignar proyecto");
            });
        }

        function syncQonto() {
            console.log("syncQonto called");
            if (!confirm("Sincronizar transacciones desde Qonto?")) return;
            fetch("/api/sync", { method: "POST" })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    console.log("Sync response:", data);
                    var msg = "Qonto: " + (data.qonto_count || 0) + " transacciones\n";
                    msg += "Sincronizadas: " + (data.synced || 0) + "\n";
                    msg += "Saltadas: " + (data.skipped || 0) + "\n";
                    msg += "En Airtable: " + (data.existing_count || 0) + "\n";
                    if (data.error) msg += "\nError: " + data.error;
                    if (data.errors && data.errors.length > 0) msg += "\nErrores: " + data.errors.join(", ");
                    alert(msg);
                    loadData();
                })
                .catch(function(e) {
                    alert("Error de conexion: " + e.message);
                });
        }

        console.log("G4U initializing...");
        checkEnv();
        loadData();
        console.log("G4U init complete");
    </script>
</body>
</html>
"""

# ==================== Routes ====================

@app.route("/")
def index():
    from flask import send_from_directory
    import os
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    return send_from_directory(static_dir, 'index.html')

@app.route("/api/ping")
def api_ping():
    """Simple ping to verify server is running."""
    return jsonify({"ok": True, "time": datetime.now().isoformat()})

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

        transactions = []
        categories = []
        projects = []

        # Step 1: Discover tables from Airtable metadata API
        table_map = {}  # maps purpose -> table name
        with httpx.Client(timeout=30) as client:
            r = client.get(
                f"https://api.airtable.com/v0/meta/bases/{airtable.base_id}/tables",
                headers=airtable.headers
            )
            if r.status_code == 200:
                tables = r.json().get("tables", [])
                for t in tables:
                    name = t.get("name", "")
                    name_lower = name.lower()
                    if "trans" in name_lower or "movimiento" in name_lower:
                        table_map["transactions"] = name
                    elif "categ" in name_lower:
                        table_map["categories"] = name
                    elif "project" in name_lower or "proyecto" in name_lower:
                        table_map["projects"] = name

                # If no transactions table found, use first table
                if "transactions" not in table_map and tables:
                    table_map["transactions"] = tables[0].get("name")

        # Step 2: Load data from discovered tables
        if "transactions" in table_map:
            try:
                raw_records = airtable.get_all(table_map["transactions"])
                # Normalize field names for frontend
                for r in raw_records:
                    # Try to find amount
                    amt = r.get("Amount") or r.get("amount") or r.get("Monto") or r.get("monto") or 0
                    # Try to find side/type and map Income/Expense to credit/debit
                    raw_side = r.get("Type") or r.get("type") or r.get("Side") or r.get("side") or r.get("Tipo") or ""
                    if raw_side == "Income":
                        side = "credit"
                    elif raw_side == "Expense":
                        side = "debit"
                    else:
                        side = raw_side
                    # Try to find label/description
                    label = r.get("Description") or r.get("description") or r.get("Label") or r.get("label") or r.get("Name") or r.get("name") or ""
                    # Try to find date
                    date = r.get("Date") or r.get("date") or r.get("Fecha") or r.get("fecha") or r.get("settled_at") or ""
                    # Try to find counterparty
                    counterparty = r.get("Counterparty") or r.get("counterparty") or r.get("Contraparte") or label

                    transactions.append({
                        "id": r.get("id"),
                        "amount": float(amt) if amt else 0,
                        "side": side.lower() if isinstance(side, str) else "debit",
                        "label": label,
                        "counterparty_name": counterparty,
                        "settled_at": date,
                        "category": r.get("Category") or r.get("category") or r.get("Categoria") or "",
                        "project_id": r.get("Project") or r.get("project") or r.get("Proyecto") or ""
                    })
            except Exception as e:
                pass

        if "categories" in table_map:
            try:
                categories = airtable.get_all(table_map["categories"])
            except:
                pass

        if "projects" in table_map:
            try:
                raw_projects = airtable.get_all(table_map["projects"])
                for p in raw_projects:
                    projects.append({
                        "id": p.get("id"),
                        "name": p.get("Name") or p.get("name") or p.get("Nombre") or p.get("id")
                    })
            except:
                pass

        return jsonify({
            "transactions": transactions,
            "categories": categories,
            "projects": projects,
            "tables_found": table_map
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/sync", methods=["POST"])
def api_sync():
    try:
        qonto = Qonto()
        airtable = Airtable()

        # Get transactions from Qonto
        slug = qonto.get_bank_account_id()
        if not slug:
            return jsonify({"error": "Could not get bank account slug"})

        qonto_txs = qonto.get_all_transactions(slug)
        if not qonto_txs:
            return jsonify({"error": "Qonto returned 0 transactions"})

        # Step 1: Discover the actual table schema from Airtable metadata API
        table_info = None
        table_name = None
        fields_map = {}

        with httpx.Client(timeout=30) as client:
            r = client.get(
                f"https://api.airtable.com/v0/meta/bases/{airtable.base_id}/tables",
                headers=airtable.headers
            )
            if r.status_code == 200:
                tables = r.json().get("tables", [])
                # Find a transactions-like table
                for t in tables:
                    name_lower = t.get("name", "").lower()
                    if "trans" in name_lower or "movimiento" in name_lower or "operacion" in name_lower:
                        table_info = t
                        table_name = t.get("name")
                        break
                # If no match, use the first table
                if not table_info and tables:
                    table_info = tables[0]
                    table_name = tables[0].get("name")

        if not table_name:
            return jsonify({"error": "No tables found in Airtable base. Please create a table first."})

        # Step 2: Map Airtable field names to our data
        # Get actual field names from the table
        actual_fields = {f.get("name"): f.get("type") for f in table_info.get("fields", [])}

        # Try to find matching fields (case-insensitive)
        def find_field(candidates):
            for c in candidates:
                for f in actual_fields:
                    if c.lower() == f.lower():
                        return f
            return None

        # Map our data to actual field names
        id_field = find_field(["Qonto Transaction ID", "qonto_id", "transaction_id", "ID", "id", "Name"])
        amount_field = find_field(["Amount", "amount", "Monto", "monto", "Importe", "importe"])
        desc_field = find_field(["Description", "description", "Descripcion", "descripcion", "Label", "label", "Name", "name"])
        type_field = find_field(["Type", "type", "Tipo", "tipo", "Side", "side"])
        date_field = find_field(["Date", "date", "Fecha", "fecha", "settled_at"])
        counterparty_field = find_field(["Counterparty", "counterparty", "Contraparte", "contraparte"])

        # Get existing records to check for duplicates
        existing = []
        existing_ids = set()
        try:
            existing = airtable.get_all(table_name)
            # Check multiple possible ID fields for existing records
            for r in existing:
                for key in ["Qonto Transaction ID", "qonto_id", "transaction_id", "ID", "id", "Name", "name"]:
                    if r.get(key):
                        existing_ids.add(str(r.get(key)))
        except Exception as e:
            pass  # Table might be empty or field names different

        synced = 0
        skipped = 0
        errors = []

        # Build all records first
        records_to_create = []
        for tx in qonto_txs:
            tx_id = tx.get("transaction_id", "")
            if tx_id in existing_ids:
                skipped += 1
                continue

            # Build record using discovered field names
            record = {}

            if id_field:
                record[id_field] = tx_id
            if amount_field:
                record[amount_field] = float(tx.get("amount", 0))
            if desc_field:
                record[desc_field] = tx.get("label", "") or tx.get("reference", "") or tx_id
            if type_field:
                # Map Qonto's credit/debit to Airtable's Income/Expense
                side = tx.get("side", "")
                if side == "credit":
                    record[type_field] = "Income"
                elif side == "debit":
                    record[type_field] = "Expense"
            if date_field:
                settled = tx.get("settled_at", "")
                if settled:
                    record[date_field] = settled.split("T")[0]
            if counterparty_field:
                record[counterparty_field] = tx.get("label", "")

            # If no fields matched, use Name field (exists in every Airtable table)
            if not record:
                record["Name"] = f"{tx_id} - {tx.get('label', '')} - {tx.get('amount', 0)}"

            # Remove empty values
            record = {k: v for k, v in record.items() if v is not None and v != ""}
            records_to_create.append(record)

        # Batch create in groups of 10 (Airtable limit)
        for i in range(0, len(records_to_create), 10):
            batch = records_to_create[i:i+10]
            try:
                airtable.create_batch(table_name, batch)
                synced += len(batch)
            except Exception as e:
                error_msg = str(e)
                errors.append(error_msg[:150])
                if len(errors) >= 3:
                    break

        return jsonify({
            "qonto_count": len(qonto_txs),
            "synced": synced,
            "skipped": skipped,
            "existing_count": len(existing),
            "table_name": table_name,
            "fields_found": {
                "id": id_field,
                "amount": amount_field,
                "description": desc_field,
                "type": type_field,
                "date": date_field
            },
            "errors": errors if errors else None
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

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

@app.route("/api/transaction", methods=["POST"])
def api_create_transaction():
    """Create a manual transaction."""
    try:
        data = request.json
        airtable = Airtable()

        # Generate a unique ID for manual transactions
        import uuid
        manual_id = f"MANUAL-{uuid.uuid4().hex[:8].upper()}"

        record = {
            "Qonto Transaction ID": manual_id,
            "Type": data.get("type", "Expense"),
            "Amount": float(data.get("amount", 0)),
            "Date": data.get("date"),
            "Description": data.get("description", ""),
            "Counterparty": data.get("counterparty", "")
        }

        # Remove empty values
        record = {k: v for k, v in record.items() if v is not None and v != ""}

        result = airtable.create("Transactions", record)
        return jsonify({"ok": True, "id": result.get("id")})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/api/airtable-schema")
def api_airtable_schema():
    """Return raw Airtable schema."""
    try:
        airtable = Airtable()
        with httpx.Client(timeout=30) as client:
            r = client.get(
                f"https://api.airtable.com/v0/meta/bases/{airtable.base_id}/tables",
                headers=airtable.headers
            )
            return jsonify({"status": r.status_code, "data": r.json() if r.status_code == 200 else r.text})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/schema-check")
def api_schema_check():
    """Check current Airtable schema and return what's missing."""
    try:
        airtable = Airtable()

        # Required schema definition
        required_schema = {
            "Transactions": {
                "fields": ["Qonto Transaction ID", "Date", "Amount", "Description", "Counterparty", "Type", "Category", "Project"],
                "description": "Transacciones de Qonto"
            },
            "Team Members": {
                "fields": ["Name", "Role", "Salary"],
                "description": "Miembros del equipo con salarios"
            },
            "Salary Allocations": {
                "fields": ["Team Member ID", "Team Member Name", "Project ID", "Project Name", "Percentage", "Month", "Amount"],
                "description": "Asignacion de salarios a proyectos por mes"
            },
            "Projects": {
                "fields": ["Name", "Client", "Status"],
                "description": "Proyectos para tracking de rentabilidad"
            },
            "Categories": {
                "fields": ["Name", "Type"],
                "description": "Categorias de ingresos y gastos"
            }
        }

        # Fetch current schema
        with httpx.Client(timeout=30) as client:
            r = client.get(
                f"https://api.airtable.com/v0/meta/bases/{airtable.base_id}/tables",
                headers=airtable.headers
            )
            if r.status_code != 200:
                return jsonify({"error": "Could not fetch schema", "status": r.status_code})

            current_tables = {t["name"]: t for t in r.json().get("tables", [])}

        # Compare and build instructions
        results = {
            "existing_tables": list(current_tables.keys()),
            "missing_tables": [],
            "missing_fields": {},
            "instructions": []
        }

        for table_name, spec in required_schema.items():
            if table_name not in current_tables:
                results["missing_tables"].append(table_name)
                results["instructions"].append({
                    "action": "CREATE_TABLE",
                    "table": table_name,
                    "fields": spec["fields"],
                    "description": spec["description"]
                })
            else:
                # Check fields
                existing_fields = [f["name"] for f in current_tables[table_name].get("fields", [])]
                missing = [f for f in spec["fields"] if f not in existing_fields]
                if missing:
                    results["missing_fields"][table_name] = missing
                    results["instructions"].append({
                        "action": "ADD_FIELDS",
                        "table": table_name,
                        "fields": missing
                    })

        # Generate human-readable instructions
        human_instructions = []
        for inst in results["instructions"]:
            if inst["action"] == "CREATE_TABLE":
                human_instructions.append(f"CREAR TABLA '{inst['table']}' con campos: {', '.join(inst['fields'])}")
            elif inst["action"] == "ADD_FIELDS":
                human_instructions.append(f"AGREGAR a '{inst['table']}': {', '.join(inst['fields'])}")

        results["human_instructions"] = human_instructions
        results["all_good"] = len(results["instructions"]) == 0

        return jsonify(results)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/debug")
def api_debug():
    """Debug endpoint to check all connections."""
    result = {
        "env": {
            "AIRTABLE_TOKEN": "SET" if os.getenv("AIRTABLE_TOKEN") else "MISSING",
            "AIRTABLE_BASE_ID": os.getenv("AIRTABLE_BASE_ID", "MISSING"),
            "QONTO_API_KEY": "SET" if os.getenv("QONTO_API_KEY") else "MISSING",
            "QONTO_ORGANIZATION_SLUG": os.getenv("QONTO_ORGANIZATION_SLUG", "MISSING"),
            "QONTO_IBAN": "SET" if os.getenv("QONTO_IBAN") else "MISSING",
        },
        "airtable": {"status": "unknown"},
        "qonto": {"status": "unknown"},
    }

    # Test Airtable
    try:
        airtable = Airtable()
        # Try to list tables by making requests
        tables_found = []
        for table in ["Transactions", "transactions", "Transacciones", "Categories", "categories", "Categorias", "Projects", "projects", "Proyectos"]:
            try:
                records = airtable.get_all(table)
                tables_found.append({"name": table, "records": len(records)})
            except Exception as e:
                pass

        result["airtable"] = {
            "status": "ok" if tables_found else "no_tables",
            "tables": tables_found,
        }
    except Exception as e:
        result["airtable"] = {"status": "error", "error": str(e)}

    # Test Qonto
    try:
        qonto = Qonto()
        with httpx.Client(timeout=10) as client:
            r = client.get(
                f"{qonto.base_url}/organization",
                headers=qonto.headers
            )
            if r.status_code == 200:
                org = r.json().get("organization", {})
                result["qonto"] = {
                    "status": "ok",
                    "organization": org.get("slug"),
                }
            else:
                result["qonto"] = {"status": "error", "code": r.status_code, "response": r.text[:200]}
    except Exception as e:
        result["qonto"] = {"status": "error", "error": str(e)}

    return jsonify(result)

@app.route("/api/debug/qonto")
def api_debug_qonto():
    """Debug Qonto API - see raw transactions and bank accounts."""
    try:
        qonto = Qonto()
        results = {"iban_configured": qonto.iban}

        with httpx.Client(timeout=30) as client:
            # Get organization with bank accounts
            r = client.get(f"{qonto.base_url}/organization", headers=qonto.headers)
            if r.status_code == 200:
                org = r.json().get("organization", {})
                bank_accounts = org.get("bank_accounts", [])
                results["bank_accounts"] = [
                    {"iban": ba.get("iban"), "slug": ba.get("slug"), "name": ba.get("name"), "balance": ba.get("balance")}
                    for ba in bank_accounts
                ]

                # Find the matching account
                matching_account = None
                for ba in bank_accounts:
                    if ba.get("iban") == qonto.iban:
                        matching_account = ba
                        break

                results["iban_valid"] = matching_account is not None
                if matching_account:
                    results["bank_account_slug"] = matching_account.get("slug")
                elif bank_accounts:
                    results["suggestion"] = f"El IBAN configurado no coincide. IBANs disponibles: {[ba.get('iban') for ba in bank_accounts]}"
            else:
                results["org_error"] = {"status": r.status_code, "response": r.text[:300]}

            # Get transactions using slug if available
            slug = qonto.get_bank_account_id()
            results["using_slug"] = slug

            for status in ["completed", "pending"]:
                params = {"status": status, "per_page": 5}
                if slug:
                    params["slug"] = slug
                else:
                    params["iban"] = qonto.iban

                r = client.get(
                    f"{qonto.base_url}/transactions",
                    headers=qonto.headers,
                    params=params
                )
                if r.status_code == 200:
                    data = r.json()
                    txs = data.get("transactions", [])
                    meta = data.get("meta", {})
                    results[f"tx_{status}"] = {
                        "total": meta.get("total_count", len(txs)),
                        "sample": [{"id": t.get("transaction_id"), "amount": t.get("amount"), "side": t.get("side"), "label": t.get("label")} for t in txs[:3]]
                    }
                else:
                    results[f"tx_{status}"] = {"error": r.status_code, "msg": r.text[:200]}

        return jsonify(results)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/diagnostics")
def api_diagnostics():
    """Analyze transactions for issues like duplicates, missing types, etc."""
    try:
        airtable = Airtable()
        records = airtable.get_all("Transactions")

        # Analyze the data
        total = len(records)
        by_type = {}
        by_qonto_id = {}
        income_total = 0
        expense_total = 0
        no_type_total = 0

        for r in records:
            # Count by Type
            tx_type = r.get("Type", "")
            by_type[tx_type or "(empty)"] = by_type.get(tx_type or "(empty)", 0) + 1

            # Check for duplicates by Qonto Transaction ID
            qonto_id = r.get("Qonto Transaction ID", "")
            if qonto_id:
                by_qonto_id[qonto_id] = by_qonto_id.get(qonto_id, 0) + 1

            # Calculate totals
            amt = float(r.get("Amount", 0) or 0)
            if tx_type == "Income":
                income_total += amt
            elif tx_type == "Expense":
                expense_total += amt
            else:
                no_type_total += amt

        # Find duplicates
        duplicates = {k: v for k, v in by_qonto_id.items() if v > 1}

        return jsonify({
            "total_records": total,
            "by_type": by_type,
            "duplicates_count": len(duplicates),
            "duplicates": duplicates if len(duplicates) < 20 else f"{len(duplicates)} duplicates found",
            "totals": {
                "income": income_total,
                "expense": expense_total,
                "no_type": no_type_total
            },
            "net": income_total - expense_total
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

# ==================== Salary Allocation ====================

@app.route("/api/team-members")
def api_team_members():
    """Get all team members."""
    try:
        airtable = Airtable()
        # Try to get Team Members table
        try:
            records = airtable.get_all("Team Members")
            members = []
            for r in records:
                members.append({
                    "id": r.get("id"),
                    "name": r.get("Name") or r.get("name") or "",
                    "salary": float(r.get("Salary") or r.get("salary") or r.get("Monthly Salary") or 0),
                    "role": r.get("Role") or r.get("role") or ""
                })
            return jsonify({"members": members})
        except Exception:
            # Table doesn't exist, return empty
            return jsonify({"members": [], "note": "Create 'Team Members' table in Airtable with Name, Salary, Role fields"})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/team-member", methods=["POST"])
def api_create_team_member():
    """Create a team member."""
    try:
        data = request.json
        airtable = Airtable()
        record = {
            "Name": data.get("name", ""),
            "Salary": float(data.get("salary", 0)),
            "Role": data.get("role", "")
        }
        record = {k: v for k, v in record.items() if v}
        result = airtable.create("Team Members", record)
        return jsonify({"ok": True, "id": result.get("id")})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/team-member/<member_id>", methods=["PUT"])
def api_update_team_member(member_id):
    """Update a team member."""
    try:
        data = request.json
        airtable = Airtable()
        record = {
            "Name": data.get("name", ""),
            "Salary": float(data.get("salary", 0)),
            "Role": data.get("role", "")
        }
        record = {k: v for k, v in record.items() if v is not None}
        airtable.update("Team Members", member_id, record)
        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/team-member/<member_id>", methods=["DELETE"])
def api_delete_team_member(member_id):
    """Delete a team member."""
    try:
        airtable = Airtable()
        airtable.delete_batch("Team Members", [member_id])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Projects CRUD ====================

@app.route("/api/projects")
def api_projects():
    """Get all projects."""
    try:
        airtable = Airtable()
        try:
            records = airtable.get_all("Projects")
            projects = []
            for r in records:
                projects.append({
                    "id": r.get("id"),
                    "name": r.get("Name") or r.get("name") or "",
                    "client": r.get("Client") or r.get("client") or "",
                    "status": r.get("Status") or r.get("status") or "Active"
                })
            return jsonify({"projects": projects})
        except Exception:
            return jsonify({"projects": [], "note": "Create 'Projects' table in Airtable with Name, Client, Status fields"})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/project", methods=["POST"])
def api_create_project():
    """Create a project."""
    try:
        data = request.json
        airtable = Airtable()
        record = {
            "Name": data.get("name", ""),
            "Client": data.get("client", ""),
            "Status": data.get("status", "Active")
        }
        record = {k: v for k, v in record.items() if v}
        result = airtable.create("Projects", record)
        return jsonify({"ok": True, "id": result.get("id")})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/project/<project_id>", methods=["PUT"])
def api_update_project(project_id):
    """Update a project."""
    try:
        data = request.json
        airtable = Airtable()
        record = {
            "Name": data.get("name", ""),
            "Client": data.get("client", ""),
            "Status": data.get("status", "")
        }
        record = {k: v for k, v in record.items() if v is not None}
        airtable.update("Projects", project_id, record)
        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/project/<project_id>", methods=["DELETE"])
def api_delete_project(project_id):
    """Delete a project."""
    try:
        airtable = Airtable()
        airtable.delete_batch("Projects", [project_id])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Categories CRUD ====================

@app.route("/api/categories")
def api_categories():
    """Get all categories."""
    try:
        airtable = Airtable()
        try:
            records = airtable.get_all("Categories")
            categories = []
            for r in records:
                categories.append({
                    "id": r.get("id"),
                    "name": r.get("Name") or r.get("name") or "",
                    "type": r.get("Type") or r.get("type") or "Expense",  # Income or Expense
                    "parent": r.get("Parent") or r.get("parent") or ""
                })
            return jsonify({"categories": categories})
        except Exception:
            return jsonify({"categories": [], "note": "Create 'Categories' table in Airtable with Name, Type (Income/Expense), Parent fields"})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/category", methods=["POST"])
def api_create_category():
    """Create a category."""
    try:
        data = request.json
        airtable = Airtable()
        record = {
            "Name": data.get("name", ""),
            "Type": data.get("type", "Expense"),
            "Parent": data.get("parent", "")
        }
        record = {k: v for k, v in record.items() if v}
        result = airtable.create("Categories", record)
        return jsonify({"ok": True, "id": result.get("id")})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/category/<category_id>", methods=["PUT"])
def api_update_category(category_id):
    """Update a category."""
    try:
        data = request.json
        airtable = Airtable()
        record = {
            "Name": data.get("name", ""),
            "Type": data.get("type", ""),
            "Parent": data.get("parent", "")
        }
        record = {k: v for k, v in record.items() if v is not None}
        airtable.update("Categories", category_id, record)
        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/category/<category_id>", methods=["DELETE"])
def api_delete_category(category_id):
    """Delete a category."""
    try:
        airtable = Airtable()
        airtable.delete_batch("Categories", [category_id])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Transaction Updates ====================

@app.route("/api/transaction/<tx_id>", methods=["PUT"])
def api_update_transaction(tx_id):
    """Update a transaction (category, project assignment, etc)."""
    try:
        data = request.json
        airtable = Airtable()

        record = {}
        if "category" in data:
            record["Category"] = data["category"]
        if "project_id" in data:
            record["Project"] = data["project_id"]
        if "description" in data:
            record["Description"] = data["description"]

        if record:
            airtable.update("Transactions", tx_id, record)
        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/salary-allocations")
def api_salary_allocations():
    """Get salary allocations. Optional ?month=YYYY-MM parameter."""
    try:
        airtable = Airtable()
        month = request.args.get("month")  # Format: YYYY-MM

        try:
            records = airtable.get_all("Salary Allocations")
            allocations = []
            for r in records:
                alloc = {
                    "id": r.get("id"),
                    "team_member_id": r.get("Team Member ID") or r.get("team_member_id") or "",
                    "team_member_name": r.get("Team Member Name") or r.get("team_member_name") or "",
                    "project_id": r.get("Project ID") or r.get("project_id") or "",
                    "project_name": r.get("Project Name") or r.get("project_name") or "",
                    "percentage": float(r.get("Percentage") or r.get("percentage") or 0),
                    "month": r.get("Month") or r.get("month") or "",  # Format: YYYY-MM
                    "amount": float(r.get("Amount") or r.get("amount") or 0)
                }
                # Filter by month if specified
                if month and alloc["month"] != month:
                    continue
                allocations.append(alloc)
            return jsonify({"allocations": allocations})
        except Exception:
            return jsonify({"allocations": [], "note": "Create 'Salary Allocations' table in Airtable"})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/salary-allocation", methods=["POST"])
def api_save_salary_allocation():
    """Save or update a salary allocation for a specific month."""
    try:
        data = request.json
        airtable = Airtable()

        month = data.get("month")  # Required: YYYY-MM
        team_member_id = data.get("team_member_id")
        team_member_name = data.get("team_member_name", "")
        project_id = data.get("project_id")
        project_name = data.get("project_name", "")
        percentage = float(data.get("percentage", 0))
        amount = float(data.get("amount", 0))

        if not month or not team_member_id:
            return jsonify({"error": "month and team_member_id are required"}), 400

        # Check if allocation already exists for this member/project/month
        existing_id = None
        try:
            formula = f"AND({{Team Member ID}}='{team_member_id}', {{Project ID}}='{project_id}', {{Month}}='{month}')"
            existing = airtable.get_all("Salary Allocations", formula=formula)
            if existing:
                existing_id = existing[0].get("id")
        except Exception:
            pass

        record = {
            "Team Member ID": team_member_id,
            "Team Member Name": team_member_name,
            "Project ID": project_id,
            "Project Name": project_name,
            "Percentage": percentage,
            "Month": month,
            "Amount": amount
        }
        record = {k: v for k, v in record.items() if v is not None}

        if existing_id:
            # Update existing allocation
            result = airtable.update("Salary Allocations", existing_id, record)
        else:
            # Create new allocation
            result = airtable.create("Salary Allocations", record)

        return jsonify({"ok": True, "id": result.get("id") or existing_id})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/salary-allocation/<allocation_id>", methods=["DELETE"])
def api_delete_salary_allocation(allocation_id):
    """Delete a salary allocation."""
    try:
        airtable = Airtable()
        airtable.delete_batch("Salary Allocations", [allocation_id])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/project-costs")
def api_project_costs():
    """Get project costs including salary allocations for a given month."""
    try:
        airtable = Airtable()
        month = request.args.get("month")  # Optional: YYYY-MM

        # Get salary allocations
        allocations = []
        try:
            records = airtable.get_all("Salary Allocations")
            for r in records:
                alloc_month = r.get("Month") or ""
                if month and alloc_month != month:
                    continue
                allocations.append({
                    "project_id": r.get("Project ID") or "",
                    "amount": float(r.get("Amount") or 0)
                })
        except Exception:
            pass

        # Aggregate by project
        by_project = {}
        for a in allocations:
            pid = a["project_id"]
            if pid not in by_project:
                by_project[pid] = 0
            by_project[pid] += a["amount"]

        return jsonify({"salary_costs": by_project})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/cleanup-duplicates", methods=["POST"])
def api_cleanup_duplicates():
    """Remove duplicate transactions, keeping only the first occurrence of each Qonto Transaction ID."""
    try:
        airtable = Airtable()
        records = airtable.get_all("Transactions")

        # Group records by Qonto Transaction ID
        by_qonto_id = {}
        for r in records:
            qonto_id = r.get("Qonto Transaction ID", "")
            if qonto_id:
                if qonto_id not in by_qonto_id:
                    by_qonto_id[qonto_id] = []
                by_qonto_id[qonto_id].append(r.get("id"))

        # Find records to delete (all but the first for each Qonto ID)
        to_delete = []
        for qonto_id, record_ids in by_qonto_id.items():
            if len(record_ids) > 1:
                # Keep the first, delete the rest
                to_delete.extend(record_ids[1:])

        if not to_delete:
            return jsonify({"message": "No duplicates found", "deleted": 0})

        # Delete in batches of 10
        deleted = 0
        errors = []
        for i in range(0, len(to_delete), 10):
            batch = to_delete[i:i+10]
            try:
                airtable.delete_batch("Transactions", batch)
                deleted += len(batch)
            except Exception as e:
                errors.append(str(e)[:100])
                if len(errors) >= 3:
                    break

        return jsonify({
            "deleted": deleted,
            "total_duplicates": len(to_delete),
            "remaining": len(to_delete) - deleted,
            "errors": errors if errors else None
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
