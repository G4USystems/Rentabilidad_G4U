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
    from flask import Response
    return Response(HTML, mimetype='text/html')

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

        # Try different table name variations
        transactions = []
        categories = []
        projects = []
        errors = []

        # Try to get transactions
        tx_found = False
        for table_name in ["Transactions", "transactions", "Transacciones"]:
            try:
                transactions = airtable.get_all(table_name)
                tx_found = True
                break
            except Exception as e:
                continue

        if not tx_found:
            errors.append("No se encontro tabla de transacciones. Crea una tabla 'Transactions' en Airtable con campos: qonto_id, amount, currency, side, counterparty_name, label, settled_at, status")

        # Try to get categories
        for table_name in ["Categories", "categories", "Categorias"]:
            try:
                categories = airtable.get_all(table_name)
                break
            except:
                continue

        # Try to get projects
        for table_name in ["Projects", "projects", "Proyectos"]:
            try:
                projects = airtable.get_all(table_name)
                break
            except:
                continue

        if errors:
            return jsonify({"error": errors[0], "transactions": [], "categories": [], "projects": []})

        return jsonify({
            "transactions": transactions,
            "categories": categories,
            "projects": projects,
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/sync", methods=["POST"])
def api_sync():
    try:
        qonto = Qonto()
        airtable = Airtable()
        result = {}

        # Step 1: Get bank account slug
        slug = qonto.get_bank_account_id()
        if not slug:
            return jsonify({"error": "Could not get bank account slug", "iban": qonto.iban})

        # Step 2: Fetch ALL transactions from Qonto
        qonto_txs = qonto.get_all_transactions(slug)
        result["qonto_count"] = len(qonto_txs)

        if not qonto_txs:
            return jsonify({"error": "Qonto returned 0 transactions", "slug": slug})

        # Step 3: Find Airtable table and get existing IDs
        table_name = "Transactions"
        for name in ["Transactions", "transactions", "Transacciones"]:
            try:
                airtable.get_all(name)
                table_name = name
                break
            except:
                continue

        existing = airtable.get_all(table_name)
        existing_ids = {t.get("qonto_id") for t in existing if t.get("qonto_id")}
        result["existing_count"] = len(existing)
        result["table_name"] = table_name

        # Step 4: Sync new transactions
        synced = 0
        skipped = 0
        errors = []

        for tx in qonto_txs:
            tx_id = tx.get("transaction_id")
            if tx_id in existing_ids:
                skipped += 1
                continue

            try:
                airtable.create(table_name, {
                    "qonto_id": tx_id,
                    "amount": float(tx.get("amount", 0)),
                    "currency": tx.get("currency", "EUR"),
                    "side": tx.get("side", ""),
                    "counterparty_name": tx.get("label", ""),
                    "label": tx.get("note") or tx.get("reference", ""),
                    "settled_at": tx.get("settled_at", ""),
                    "status": tx.get("status", ""),
                })
                synced += 1
            except Exception as e:
                errors.append(str(e)[:100])
                if len(errors) >= 3:
                    break

        result["synced"] = synced
        result["skipped"] = skipped
        if errors:
            result["errors"] = errors
        return jsonify(result)
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

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

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
