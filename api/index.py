# -*- coding: utf-8 -*-
"""
Rentabilidad G4U - Simple P&L Dashboard
"""
import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from urllib.parse import quote
from functools import wraps
from flask import Flask, jsonify, request, render_template_string, redirect, make_response
import httpx
import jwt as pyjwt
from authlib.integrations.flask_client import OAuth

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
app.secret_key = SECRET_KEY

# ==================== OAuth Configuration ====================

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# ==================== Auth Helpers ====================

def require_auth(f):
    """Decorator to require authentication for Flask routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Skip auth in development mode
        if os.getenv("APP_ENV") == "development" and os.getenv("SKIP_AUTH", "").lower() == "true":
            request.current_user = {"email": "dev@localhost", "name": "Developer"}
            return f(*args, **kwargs)

        token = request.cookies.get('auth_token')
        if not token:
            return jsonify({"error": "Not authenticated"}), 401
        try:
            payload = pyjwt.decode(
                token,
                SECRET_KEY,
                algorithms=["HS256"]
            )
            request.current_user = payload
        except pyjwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


def render_login_page(error=None):
    """Render the login page HTML."""
    error_html = f"<div class='error'>{error}</div>" if error else ""
    return f'''<!DOCTYPE html>
<html>
<head>
    <title>G4U - Login</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .login-container {{
            background: white;
            border-radius: 16px;
            padding: 48px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            text-align: center;
            max-width: 400px;
            width: 90%;
        }}
        .logo {{ font-size: 32px; font-weight: 700; color: #4f46e5; margin-bottom: 8px; }}
        .subtitle {{ color: #64748b; margin-bottom: 32px; font-size: 14px; }}
        .google-btn {{
            display: inline-flex;
            align-items: center;
            gap: 12px;
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 14px 28px;
            font-size: 16px;
            font-weight: 500;
            color: #1e293b;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s;
        }}
        .google-btn:hover {{
            background: #f8fafc;
            border-color: #4f46e5;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15);
        }}
        .google-btn svg {{ width: 20px; height: 20px; }}
        .error {{
            background: #fef2f2;
            color: #dc2626;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 24px;
            font-size: 14px;
            border: 1px solid #fecaca;
        }}
        .domain-note {{
            margin-top: 32px;
            font-size: 13px;
            color: #94a3b8;
        }}
        .domain-note strong {{ color: #64748b; }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">G4U Finance</div>
        <p class="subtitle">Dashboard de Rentabilidad</p>

        {error_html}

        <a href="/auth/login" class="google-btn">
            <svg viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Iniciar sesion con Google
        </a>

        <p class="domain-note">
            Solo usuarios con email <strong>@growth4u.io</strong>
        </p>
    </div>
</body>
</html>'''


# ==================== Auth Routes ====================

@app.route("/auth/login")
def auth_login():
    """Initiate Google OAuth login."""
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
    return google.authorize_redirect(redirect_uri)


@app.route("/auth/callback")
def auth_callback():
    """Handle Google OAuth callback."""
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        # If userinfo not in token, fetch it from Google
        if not user_info or not user_info.get('picture'):
            user_info = google.userinfo()

        if not user_info:
            return render_login_page(error="No se pudo obtener informacion del usuario de Google")

        email = user_info.get('email', '')

        # Validate domain
        domain = email.split('@')[-1].lower()
        allowed_domains_env = os.getenv("ALLOWED_EMAIL_DOMAINS", "")
        if not allowed_domains_env:
            return render_login_page(
                error="Error de configuracion: ALLOWED_EMAIL_DOMAINS no esta definida"
            )
        allowed_domains = [d.strip().lower() for d in allowed_domains_env.split(",") if d.strip()]
        if domain not in allowed_domains:
            domains_list = ", ".join(f"@{d.strip()}" for d in allowed_domains)
            return render_login_page(
                error=f"Acceso restringido a emails {domains_list}. Tu email: {email}"
            )

        # Validate email against allowed list (if configured)
        allowed_emails_env = os.getenv("ALLOWED_EMAILS", "")
        if allowed_emails_env:
            allowed_emails = [e.strip().lower() for e in allowed_emails_env.split(",") if e.strip()]
            if email.lower() not in allowed_emails:
                return render_login_page(
                    error=f"Tu email ({email}) no esta en la lista de usuarios autorizados"
                )

        # Create user data for JWT
        user_data = {
            "id": hash(user_info.get('sub')) % 10000000,
            "email": email,
            "google_id": user_info.get('sub'),
            "name": user_info.get('name', email),
            "picture": user_info.get('picture'),
        }

        # Create JWT token
        expire = datetime.utcnow() + timedelta(hours=24)
        jwt_payload = {
            "sub": email,
            "user_id": user_data["id"],
            "name": user_data["name"],
            "picture": user_data.get("picture"),
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        jwt_token = pyjwt.encode(
            jwt_payload,
            SECRET_KEY,
            algorithm="HS256"
        )

        # Set cookie and redirect to app
        response = make_response(redirect('/'))
        response.set_cookie(
            'auth_token',
            jwt_token,
            httponly=True,
            secure=os.getenv("APP_ENV") == "production",
            samesite='Lax',
            max_age=24 * 60 * 60  # 24 hours
        )
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return render_login_page(error=f"Error de autenticacion: {str(e)}")


@app.route("/auth/logout")
def auth_logout():
    """Log out user by clearing cookie."""
    response = make_response(redirect('/auth/login-page'))
    response.delete_cookie('auth_token')
    return response


@app.route("/auth/login-page")
def auth_login_page():
    """Show login page. Redirect to / if already authenticated."""
    token = request.cookies.get('auth_token')
    if token:
        try:
            pyjwt.decode(
                token,
                SECRET_KEY,
                algorithms=["HS256"]
            )
            return redirect('/')
        except:
            pass  # Token invalid, show login page
    return render_login_page()


@app.route("/auth/me")
def auth_me():
    """Get current user info."""
    # Skip auth in development mode
    if os.getenv("APP_ENV") == "development" and os.getenv("SKIP_AUTH", "").lower() == "true":
        return jsonify({
            "authenticated": True,
            "user": {
                "email": "dev@localhost",
                "name": "Developer",
                "picture": None,
            }
        })

    token = request.cookies.get('auth_token')
    if not token:
        return jsonify({"authenticated": False}), 401

    try:
        payload = pyjwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )
        return jsonify({
            "authenticated": True,
            "user": {
                "email": payload.get("sub"),
                "name": payload.get("name"),
                "picture": payload.get("picture"),
            }
        })
    except:
        return jsonify({"authenticated": False}), 401

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
        # URL-encode table name for special characters
        encoded_table = quote(table, safe='')
        while True:
            if offset:
                params["offset"] = offset

            with httpx.Client(timeout=30) as client:
                r = client.get(f"{self.base_url}/{encoded_table}", headers=self.headers, params=params)
                r.raise_for_status()
                data = r.json()

            for rec in data.get("records", []):
                records.append({"id": rec["id"], **rec.get("fields", {})})

            offset = data.get("offset")
            if not offset:
                break

        return records

    def create(self, table, fields):
        encoded_table = quote(table, safe='')
        with httpx.Client(timeout=30) as client:
            r = client.post(f"{self.base_url}/{encoded_table}", headers=self.headers, json={"fields": fields})
            r.raise_for_status()
            return r.json()

    def create_batch(self, table, records_list):
        """Create up to 10 records at once."""
        encoded_table = quote(table, safe='')
        with httpx.Client(timeout=30) as client:
            payload = {"records": [{"fields": f} for f in records_list]}
            r = client.post(f"{self.base_url}/{encoded_table}", headers=self.headers, json=payload)
            r.raise_for_status()
            return r.json()

    def update(self, table, record_id, fields):
        encoded_table = quote(table, safe='')
        with httpx.Client(timeout=30) as client:
            r = client.patch(f"{self.base_url}/{encoded_table}/{record_id}", headers=self.headers, json={"fields": fields})
            if r.status_code == 422:
                # Airtable 422 usually means invalid field value (e.g., Single Select option doesn't exist)
                error_detail = r.json() if r.headers.get('content-type', '').startswith('application/json') else r.text
                raise Exception(f"Airtable 422: {error_detail}. Fields sent: {fields}")
            r.raise_for_status()
            return r.json()

    def delete_batch(self, table, record_ids):
        """Delete up to 10 records at once."""
        encoded_table = quote(table, safe='')
        with httpx.Client(timeout=30) as client:
            # Airtable expects records[] query params
            params = "&".join([f"records[]={rid}" for rid in record_ids])
            r = client.delete(f"{self.base_url}/{encoded_table}?{params}", headers=self.headers)
            r.raise_for_status()
            return r.json()

    def create_table(self, name, fields):
        """Create a new table in the base.

        fields format: [{"name": "Field Name", "type": "singleLineText"}, ...]
        Types: singleLineText, multilineText, singleSelect, date, number, checkbox,
               multipleRecordLinks (for linked records)
        """
        meta_url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables"
        with httpx.Client(timeout=30) as client:
            r = client.post(meta_url, headers=self.headers, json={
                "name": name,
                "fields": fields
            })
            if r.status_code == 422:
                error_detail = r.json() if r.headers.get('content-type', '').startswith('application/json') else r.text
                raise Exception(f"Airtable 422 creating table: {error_detail}")
            r.raise_for_status()
            return r.json()

    def create_field(self, table_id, name, field_type, options=None):
        """Create a new field in a table.

        table_id: The table ID (not name)
        field_type: singleLineText, date, singleSelect, multipleRecordLinks, etc.
        options: For singleSelect: {"choices": [{"name": "Option1"}, ...]}
                 For multipleRecordLinks: {"linkedTableId": "tblXXX"}
        """
        meta_url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables/{table_id}/fields"
        payload = {"name": name, "type": field_type}
        if options:
            payload["options"] = options

        with httpx.Client(timeout=30) as client:
            r = client.post(meta_url, headers=self.headers, json=payload)
            if r.status_code == 422:
                error_detail = r.json() if r.headers.get('content-type', '').startswith('application/json') else r.text
                raise Exception(f"Airtable 422 creating field: {error_detail}")
            r.raise_for_status()
            return r.json()

    def get_base_schema(self):
        """Get the schema of all tables in the base."""
        meta_url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables"
        with httpx.Client(timeout=30) as client:
            r = client.get(meta_url, headers=self.headers)
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
        """Fetch all transactions for a given bank account slug with extended data."""
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

    def get_transaction_detail(self, transaction_id):
        """Fetch detailed info for a single transaction."""
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{self.base_url}/transactions/{transaction_id}", headers=self.headers)
            if r.status_code == 200:
                return r.json().get("transaction", {})
        return None

    def get_labels(self):
        """Fetch all labels from Qonto."""
        labels = []
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{self.base_url}/labels", headers=self.headers)
            if r.status_code == 200:
                labels = r.json().get("labels", [])
        return labels

    def get_memberships(self):
        """Fetch all memberships (team members) from Qonto."""
        memberships = []
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{self.base_url}/memberships", headers=self.headers)
            if r.status_code == 200:
                memberships = r.json().get("memberships", [])
        return memberships

    def get_attachment(self, attachment_id):
        """Get attachment details including download URL."""
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{self.base_url}/attachments/{attachment_id}", headers=self.headers)
            if r.status_code == 200:
                return r.json().get("attachment", {})
        return None

    def get_organization(self):
        """Get organization details including bank accounts."""
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{self.base_url}/organization", headers=self.headers)
            if r.status_code == 200:
                return r.json().get("organization", {})
        return None

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
    """Serve main app - requires authentication."""
    from flask import send_from_directory

    # Skip auth in development mode
    if os.getenv("APP_ENV") == "development" and os.getenv("SKIP_AUTH", "").lower() == "true":
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, 'index.html')

    # Check authentication
    token = request.cookies.get('auth_token')
    if not token:
        return redirect('/auth/login-page')

    try:
        pyjwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )
    except:
        return redirect('/auth/login-page')

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
@require_auth
def api_data():
    try:
        airtable = Airtable()

        transactions = []
        categories = []
        projects = []
        clients = []

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
                    # Exclude "allocation" tables from being matched as transactions
                    if ("trans" in name_lower or "movimiento" in name_lower) and "alloc" not in name_lower:
                        table_map["transactions"] = name
                    elif "categ" in name_lower:
                        table_map["categories"] = name
                    elif "project" in name_lower or "proyecto" in name_lower:
                        table_map["projects"] = name
                    elif "client" in name_lower or "cliente" in name_lower:
                        table_map["clients"] = name

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

                    # Client is a linked record - returns array of record IDs
                    client_field = r.get("Client") or r.get("client") or r.get("Cliente") or []
                    client_id = client_field[0] if isinstance(client_field, list) and client_field else ""

                    # Qonto Category (stored as text)
                    qonto_category = r.get("Qonto Category") or r.get("qonto_category") or r.get("Categoria Qonto") or ""

                    # VAT fields
                    vat_amount = r.get("VAT Amount") or r.get("vat_amount") or r.get("IVA") or 0
                    vat_rate = r.get("VAT Rate") or r.get("vat_rate") or r.get("Tipo IVA") or 0

                    # Status field (for detecting refunds/reversals)
                    status = r.get("Status") or r.get("status") or "completed"

                    transactions.append({
                        "id": r.get("id"),
                        "amount": float(amt) if amt else 0,
                        "side": side.lower() if isinstance(side, str) else "debit",
                        "label": label,
                        "counterparty_name": counterparty,
                        "settled_at": date,
                        "category": r.get("Category") or r.get("category") or r.get("Categoria") or "",
                        "project_id": r.get("Project") or r.get("project") or r.get("Proyecto") or "",
                        "client_id": client_id,
                        "qonto_category": qonto_category,
                        "vat_amount": float(vat_amount) if vat_amount else 0,
                        "vat_rate": float(vat_rate) if vat_rate else 0,
                        "is_excluded": bool(r.get("is_excluded") or r.get("Is Excluded") or False),
                        "status": status
                    })
            except Exception as e:
                pass

        if "categories" in table_map:
            try:
                raw_categories = airtable.get_all(table_map["categories"])
                for c in raw_categories:
                    categories.append({
                        "id": c.get("id"),
                        "name": c.get("Name") or c.get("name") or "",
                        "type": c.get("Type") or c.get("type") or "Expense"
                    })
            except:
                pass

        if "projects" in table_map:
            try:
                raw_projects = airtable.get_all(table_map["projects"])
                for p in raw_projects:
                    # Client is a text field (name)
                    client_val = p.get("Client") or p.get("client") or ""
                    projects.append({
                        "id": p.get("id"),
                        "name": p.get("Name") or p.get("name") or p.get("Nombre") or p.get("id"),
                        "client": client_val,
                        "status": p.get("Status") or p.get("status") or "Active"
                    })
            except:
                pass

        if "clients" in table_map:
            try:
                raw_clients = airtable.get_all(table_map["clients"])
                for c in raw_clients:
                    clients.append({
                        "id": c.get("id"),
                        "name": c.get("Name") or c.get("name") or "",
                        "contact": c.get("Contact") or c.get("contact") or "",
                        "email": c.get("Email") or c.get("email") or "",
                        "phone": c.get("Phone") or c.get("phone") or ""
                    })
            except:
                pass

        return jsonify({
            "transactions": transactions,
            "categories": categories,
            "projects": projects,
            "clients": clients,
            "tables_found": table_map
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/qonto/transaction-fields")
def api_qonto_transaction_fields():
    """Get ALL fields that Qonto returns for transactions."""
    try:
        qonto = Qonto()
        slug = qonto.get_bank_account_id()

        with httpx.Client(timeout=30) as client:
            # Get one transaction to see all fields
            r = client.get(
                f"{qonto.base_url}/transactions",
                headers=qonto.headers,
                params={"slug": slug, "status": "completed", "per_page": 5}
            )
            if r.status_code == 200:
                txs = r.json().get("transactions", [])
                if txs:
                    # Get all unique keys across transactions
                    all_keys = set()
                    for tx in txs:
                        all_keys.update(tx.keys())

                    return jsonify({
                        "all_fields_available": sorted(list(all_keys)),
                        "sample_transactions": txs
                    })

            return jsonify({"error": "Could not fetch transactions", "status": r.status_code})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/qonto/debug-vat")
def api_debug_vat():
    """Debug endpoint to check VAT data from Qonto."""
    try:
        qonto = Qonto()
        slug = qonto.get_bank_account_id()
        if not slug:
            return jsonify({"error": "Could not get bank account slug"})

        qonto_txs = qonto.get_all_transactions(slug)

        # Check what VAT fields exist in transactions
        sample_txs = []
        vat_count = 0
        for tx in qonto_txs[:20]:  # First 20 transactions as sample
            has_vat = tx.get("vat_amount") or tx.get("vat_amount_cents") or tx.get("vat_rate")
            if has_vat:
                vat_count += 1
            sample_txs.append({
                "transaction_id": tx.get("transaction_id"),
                "label": tx.get("label"),
                "amount": tx.get("amount"),
                "vat_amount": tx.get("vat_amount"),
                "vat_amount_cents": tx.get("vat_amount_cents"),
                "vat_rate": tx.get("vat_rate"),
                "category": tx.get("category")
            })

        # Count total with VAT
        total_with_vat = sum(1 for tx in qonto_txs if tx.get("vat_amount") or tx.get("vat_amount_cents"))

        return jsonify({
            "total_transactions": len(qonto_txs),
            "transactions_with_vat": total_with_vat,
            "sample_transactions": sample_txs
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/sync", methods=["POST"])
@require_auth
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
                # Find a transactions-like table (exclude allocation tables)
                for t in tables:
                    name_lower = t.get("name", "").lower()
                    if ("trans" in name_lower or "movimiento" in name_lower or "operacion" in name_lower) and "alloc" not in name_lower:
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
        # Extended fields
        reference_field = find_field(["Reference", "reference", "Referencia", "referencia"])
        note_field = find_field(["Note", "note", "Nota", "nota", "Notes", "notes"])
        vat_amount_field = find_field(["VAT Amount", "vat_amount", "IVA", "iva"])
        vat_rate_field = find_field(["VAT Rate", "vat_rate", "Tipo IVA", "tipo_iva"])
        attachment_ids_field = find_field(["Attachment IDs", "attachment_ids", "Attachments", "attachments"])
        label_ids_field = find_field(["Label IDs", "label_ids", "Labels", "labels"])
        qonto_category_field = find_field(["Qonto Category", "qonto_category", "Categoria Qonto", "categoria_qonto"])
        card_digits_field = find_field(["Card Last Digits", "card_last_digits", "Tarjeta", "tarjeta"])

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

            # Extended Qonto fields
            if reference_field and tx.get("reference"):
                record[reference_field] = tx.get("reference", "")
            if note_field and tx.get("note"):
                record[note_field] = tx.get("note", "")
            # VAT - check multiple field names (Qonto may use vat_amount or vat_amount_cents)
            if vat_amount_field:
                vat_val = tx.get("vat_amount") or tx.get("vat_amount_cents")
                if vat_val:
                    # If it's in cents, convert to euros
                    vat_float = float(vat_val)
                    if vat_float > 1000 and tx.get("vat_amount_cents"):  # Likely cents
                        vat_float = vat_float / 100
                    record[vat_amount_field] = vat_float
            if vat_rate_field:
                vat_rate_val = tx.get("vat_rate") or tx.get("vat_rate_cents")
                if vat_rate_val:
                    record[vat_rate_field] = float(vat_rate_val)
            if attachment_ids_field and tx.get("attachment_ids"):
                record[attachment_ids_field] = ",".join(tx.get("attachment_ids", []))
            if label_ids_field and tx.get("label_ids"):
                record[label_ids_field] = ",".join(tx.get("label_ids", []))
            if qonto_category_field and tx.get("category"):
                record[qonto_category_field] = tx.get("category", "")
            if card_digits_field and tx.get("card_last_digits"):
                record[card_digits_field] = tx.get("card_last_digits", "")

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

        # ===== UPDATE CATEGORIES AND VAT ON EXISTING TRANSACTIONS =====
        categories_updated = 0
        vat_updated = 0

        # Build map of Qonto transaction_id -> data (category and VAT)
        qonto_data_map = {}
        for tx in qonto_txs:
            tx_id = tx.get("transaction_id", "")
            if tx_id:
                qonto_data_map[tx_id] = {
                    "category": tx.get("category", ""),
                    "vat_amount": tx.get("vat_amount") or tx.get("vat_amount_cents") or 0
                }

        # Re-fetch existing records to get fresh data
        try:
            existing = airtable.get_all(table_name)
        except:
            existing = []

        for record in existing:
            record_id = record.get("id")
            # Find Qonto transaction ID
            qonto_id = None
            for key in ["Qonto Transaction ID", "qonto_id", "transaction_id", "ID", "Name"]:
                if record.get(key):
                    qonto_id = record.get(key)
                    break

            if not qonto_id or qonto_id not in qonto_data_map:
                continue

            qonto_data = qonto_data_map[qonto_id]
            updates = {}

            # Check if needs category update
            if qonto_category_field:
                current_category = record.get(qonto_category_field) or ""
                new_category = qonto_data.get("category", "")
                if not current_category and new_category:
                    updates[qonto_category_field] = new_category

            # Check if needs VAT update
            if vat_amount_field:
                current_vat = record.get(vat_amount_field) or 0
                new_vat = qonto_data.get("vat_amount", 0)
                if new_vat and not current_vat:
                    # Convert from cents if needed
                    vat_float = float(new_vat)
                    if vat_float > 1000:  # Likely cents
                        vat_float = vat_float / 100
                    updates[vat_amount_field] = vat_float

            # Apply updates if any
            if updates:
                try:
                    airtable.update(table_name, record_id, updates)
                    if qonto_category_field in updates:
                        categories_updated += 1
                    if vat_amount_field in updates:
                        vat_updated += 1
                except:
                    pass

        return jsonify({
            "qonto_count": len(qonto_txs),
            "synced": synced,
            "skipped": skipped,
            "categories_updated": categories_updated,
            "vat_updated": vat_updated,
            "existing_count": len(existing),
            "table_name": table_name,
            "fields_found": {
                "id": id_field,
                "amount": amount_field,
                "description": desc_field,
                "type": type_field,
                "date": date_field,
                "qonto_category": qonto_category_field,
                "vat_amount": vat_amount_field
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
        # Use "Project" field name to match schema
        airtable.update("Transactions", tx_id, {"Project": project_id or ""})

        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/transaction", methods=["POST"])
@require_auth
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
            "Transaction Allocations": {
                "fields": ["Transaction", "Project", "Client", "Percentage"],
                "description": "Asignacion de transacciones a proyectos/clientes en porcentaje"
            },
            "Projects": {
                "fields": ["Name", "Client", "Status"],
                "description": "Proyectos para tracking de rentabilidad"
            },
            "Clients": {
                "fields": ["Name", "Contact", "Email", "Phone", "Notes"],
                "description": "Clientes para asociar a proyectos"
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
@require_auth
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
@require_auth
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
@require_auth
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
@require_auth
def api_delete_team_member(member_id):
    """Delete a team member."""
    try:
        airtable = Airtable()
        airtable.delete_batch("Team Members", [member_id])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Projects CRUD ====================

@app.route("/api/debug/table-fields/<table>")
@require_auth
def api_debug_table_fields(table):
    """Debug: Get raw Airtable fields for a table (first record)."""
    try:
        airtable = Airtable()
        records = airtable.get_all(table)
        if records:
            # Return all field names from first record
            sample = records[0]
            return jsonify({
                "table": table,
                "record_count": len(records),
                "fields": list(sample.keys()),
                "sample_record": sample
            })
        return jsonify({"table": table, "record_count": 0, "fields": [], "sample_record": None})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/debug/airtable-schema")
@require_auth
def api_debug_airtable_schema():
    """Get full Airtable base schema (all tables and fields)."""
    try:
        airtable = Airtable()
        schema = airtable.get_base_schema()
        return jsonify(schema)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/admin/create-offerings-table", methods=["POST"])
@require_auth
def api_create_offerings_table():
    """Create the 'Ofertas G4U' table and link it to Projects."""
    try:
        airtable = Airtable()

        # First get the schema to find Projects table ID
        schema = airtable.get_base_schema()
        projects_table = None
        for table in schema.get("tables", []):
            if table["name"] == "Projects":
                projects_table = table
                break

        if not projects_table:
            return jsonify({"error": "Projects table not found"}), 404

        projects_table_id = projects_table["id"]

        # Create Ofertas G4U table with Name field
        offerings_table = airtable.create_table("Ofertas G4U", [
            {"name": "Name", "type": "singleLineText"},
            {"name": "Descripcion", "type": "multilineText"}
        ])

        offerings_table_id = offerings_table["id"]

        # Now create Service field in Projects linking to Ofertas G4U
        service_field = airtable.create_field(
            projects_table_id,
            "Service",
            "multipleRecordLinks",
            {"linkedTableId": offerings_table_id}
        )

        # Populate Ofertas G4U with default offerings
        settings = load_local_settings()
        offerings = settings.get("service_offerings", [])
        for offering in offerings:
            airtable.create("Ofertas G4U", {"Name": offering["name"]})

        return jsonify({
            "ok": True,
            "offerings_table_id": offerings_table_id,
            "service_field_id": service_field.get("id"),
            "offerings_created": len(offerings)
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/projects")
@require_auth
def api_projects():
    """Get all projects."""
    try:
        airtable = Airtable()
        try:
            records = airtable.get_all("Projects")
            projects = []
            for r in records:
                # Client and Service are text fields, dates are date fields
                projects.append({
                    "id": r.get("id"),
                    "name": r.get("Name") or r.get("name") or "",
                    "service": r.get("Service") or r.get("service") or r.get("Oferta G4U") or "",
                    "client": r.get("Client") or r.get("client") or "",
                    "status": r.get("Status") or r.get("status") or "Active",
                    "start_date": r.get("Start Date") or r.get("start_date") or "",
                    "end_date": r.get("End Date") or r.get("end_date") or ""
                })
            return jsonify({"projects": projects})
        except Exception:
            return jsonify({"projects": [], "note": "Create 'Projects' table in Airtable with Name, Service, Client, Status fields"})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/project", methods=["POST"])
@require_auth
def api_create_project():
    """Create a project.

    IMPORTANT: Airtable rejects empty strings for certain field types.
    Only include fields with actual non-empty values.
    """
    try:
        data = request.json
        airtable = Airtable()

        # Build record with only non-empty values
        record = {}

        name = (data.get("name") or "").strip()
        if name:
            record["Name"] = name
        else:
            return jsonify({"error": "El nombre del proyecto es requerido"}), 400

        # Service (Oferta G4U) - Linked record to "Ofertas G4U" table
        # Frontend sends the record ID from Ofertas G4U
        service = (data.get("service") or "").strip()
        if service:
            # Service is a linked record - send as array with single ID
            record["Service"] = [service]

        status = (data.get("status") or "").strip()
        if status:
            record["Status"] = status
        else:
            record["Status"] = "Active"  # Default

        client = (data.get("client") or "").strip()
        if client:
            record["Client"] = client

        start_date = (data.get("start_date") or "").strip()
        if start_date:
            record["Start Date"] = start_date

        end_date = (data.get("end_date") or "").strip()
        if end_date:
            record["End Date"] = end_date

        result = airtable.create("Projects", record)
        return jsonify({"ok": True, "id": result.get("id")})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/project/<project_id>", methods=["PUT"])
@require_auth
def api_update_project(project_id):
    """Update a project.

    IMPORTANT: Airtable rejects empty strings for certain field types (Single Select, Date).
    We only include fields that have actual non-empty values.
    To clear a field, send null (but this is handled separately).
    """
    try:
        data = request.json
        airtable = Airtable()

        # Build record only with fields that have actual non-empty values
        record = {}

        # Name is required
        name = (data.get("name") or "").strip()
        if name:
            record["Name"] = name
        else:
            return jsonify({"error": "El nombre del proyecto es requerido"}), 400

        # Status - only add if has value
        status = (data.get("status") or "").strip()
        if status:
            record["Status"] = status

        # Service (Oferta G4U) - Linked record to "Ofertas G4U" table
        service = (data.get("service") or "").strip()
        if service:
            # Service is a linked record - send as array with single ID
            record["Service"] = [service]

        # Client - text field, only include if has value
        client = (data.get("client") or "").strip()
        if client:
            record["Client"] = client
        # If empty, don't include - this preserves existing value

        # Date fields - NEVER send empty strings to Date fields
        start_date = (data.get("start_date") or "").strip()
        if start_date:
            record["Start Date"] = start_date

        end_date = (data.get("end_date") or "").strip()
        if end_date:
            record["End Date"] = end_date

        airtable.update("Projects", project_id, record)
        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/project/<project_id>", methods=["DELETE"])
@require_auth
def api_delete_project(project_id):
    """Delete a project."""
    try:
        airtable = Airtable()
        airtable.delete_batch("Projects", [project_id])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Clients CRUD ====================

@app.route("/api/clients")
@require_auth
def api_clients():
    """Get all clients."""
    try:
        airtable = Airtable()
        try:
            records = airtable.get_all("Clients")
            clients = []
            for r in records:
                clients.append({
                    "id": r.get("id"),
                    "name": r.get("Name") or r.get("name") or "",
                    "contact": r.get("Contact") or r.get("contact") or "",
                    "email": r.get("Email") or r.get("email") or "",
                    "phone": r.get("Phone") or r.get("phone") or "",
                    "notes": r.get("Notes") or r.get("notes") or "",
                    "status": r.get("Status") or r.get("status") or "Activo"
                })
            return jsonify({"clients": clients})
        except Exception:
            return jsonify({"clients": [], "note": "Create 'Clients' table in Airtable"})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/client", methods=["POST"])
@require_auth
def api_create_client():
    """Create a client."""
    try:
        data = request.json
        airtable = Airtable()
        record = {
            "Name": data.get("name", ""),
            "Contact": data.get("contact", ""),
            "Email": data.get("email", ""),
            "Phone": data.get("phone", ""),
            "Notes": data.get("notes", ""),
            "Status": data.get("status", "Activo")
        }
        record = {k: v for k, v in record.items() if v}
        result = airtable.create("Clients", record)
        return jsonify({"ok": True, "id": result.get("id")})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/client/<client_id>", methods=["PUT"])
@require_auth
def api_update_client(client_id):
    """Update a client."""
    try:
        data = request.json
        airtable = Airtable()
        record = {}
        if "name" in data:
            record["Name"] = data["name"]
        if "contact" in data:
            record["Contact"] = data["contact"]
        if "email" in data:
            record["Email"] = data["email"]
        if "phone" in data:
            record["Phone"] = data["phone"]
        if "notes" in data:
            record["Notes"] = data["notes"]
        if "status" in data:
            record["Status"] = data["status"]
        airtable.update("Clients", client_id, record)
        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/client/<client_id>", methods=["DELETE"])
@require_auth
def api_delete_client(client_id):
    """Delete a client."""
    try:
        airtable = Airtable()
        airtable.delete_batch("Clients", [client_id])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Categories CRUD ====================

@app.route("/api/categories")
@require_auth
def api_categories():
    """Get all categories from Categories table."""
    try:
        airtable = Airtable()
        try:
            records = airtable.get_all("Categories")
            categories = []
            for r in records:
                categories.append({
                    "id": r.get("id"),
                    "name": r.get("Name") or r.get("name") or "",
                    "type": r.get("Type") or r.get("type") or "Expense"  # Income or Expense
                })
            return jsonify({"categories": categories})
        except Exception:
            return jsonify({"categories": [], "note": "Create 'Categories' table in Airtable with Name, Type (Income/Expense) fields"})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/category", methods=["POST"])
@require_auth
def api_create_category():
    """Create a category in Categories table."""
    try:
        data = request.json
        airtable = Airtable()
        record = {
            "Name": data.get("name", ""),
            "Type": data.get("type", "Expense")
        }
        record = {k: v for k, v in record.items() if v}
        result = airtable.create("Categories", record)
        return jsonify({"ok": True, "id": result.get("id")})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/category/<category_id>", methods=["PUT"])
@require_auth
def api_update_category(category_id):
    """Update a category in Categories table."""
    try:
        data = request.json
        airtable = Airtable()
        record = {
            "Name": data.get("name", ""),
            "Type": data.get("type", "")
        }
        record = {k: v for k, v in record.items() if v is not None and v != ""}
        airtable.update("Categories", category_id, record)
        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/category/<category_id>", methods=["DELETE"])
@require_auth
def api_delete_category(category_id):
    """Delete a category from Categories table."""
    try:
        airtable = Airtable()
        airtable.delete_batch("Categories", [category_id])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Settings/Configuration ====================

# In-memory cache for settings (persisted in Airtable Settings table)
_settings_cache = {}

import json as json_module

# Local settings file path for fallback
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'settings.json')

def load_local_settings():
    """Load settings from local file."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                return json_module.load(f)
    except:
        pass
    return {}

def save_local_settings(settings):
    """Save settings to local file."""
    with open(SETTINGS_FILE, 'w') as f:
        json_module.dump(settings, f, indent=2)

@app.route("/api/general-expenses-distribution", methods=["GET"])
@require_auth
def api_get_general_expenses_distribution():
    """Get the general expenses distribution configuration."""
    try:
        airtable = Airtable()
        try:
            records = airtable.get_all("Settings")
            for r in records:
                if r.get("Key") == "general_expenses_distribution":
                    distribution = json_module.loads(r.get("Value") or "{}")
                    return jsonify({"distribution": distribution})
            return jsonify({"distribution": {}})
        except Exception:
            # Fallback to local file
            settings = load_local_settings()
            return jsonify({"distribution": settings.get("general_expenses_distribution", {})})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/general-expenses-distribution", methods=["POST"])
@require_auth
def api_save_general_expenses_distribution():
    """Save the general expenses distribution configuration."""
    try:
        data = request.json
        distribution = data.get("distribution", {})

        value = json_module.dumps(distribution)

        airtable = Airtable()

        # Try to save to Airtable first
        try:
            records = airtable.get_all("Settings")
            existing_id = None
            for r in records:
                if r.get("Key") == "general_expenses_distribution":
                    existing_id = r.get("id")
                    break

            if existing_id:
                airtable.update("Settings", existing_id, {"Value": value})
            else:
                airtable.create("Settings", {"Key": "general_expenses_distribution", "Value": value})

            return jsonify({"ok": True})
        except Exception as e:
            # Fallback to local file
            settings = load_local_settings()
            settings["general_expenses_distribution"] = distribution
            save_local_settings(settings)
            return jsonify({"ok": True, "note": "Saved to local file (Settings table not found in Airtable)"})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

# ==================== Monthly Distribution ====================

@app.route("/api/monthly-distribution", methods=["GET"])
@require_auth
def api_get_monthly_distribution():
    """Get the monthly general expenses distribution for a specific month.

    Query params:
    - month: YYYY-MM format (e.g., "2025-01")

    Returns:
    - distributions: [{project_id, project_name, client_name, percentage}]
    - general_expenses: total unassigned expenses for that month
    - active_projects: list of all active projects
    """
    try:
        month = request.args.get("month")
        if not month:
            return jsonify({"error": "month parameter required (YYYY-MM format)"}), 400

        # Load all monthly distributions from settings
        settings = load_local_settings()
        monthly_distributions = settings.get("monthly_distributions", {})
        month_data = monthly_distributions.get(month, {})

        # Get all projects to build the distribution list
        airtable = Airtable()
        projects_raw = airtable.get_all("Projects")

        # Parse month to get date range for checking project activity
        year, mon = month.split("-")
        month_start = f"{year}-{mon}-01"
        import calendar
        last_day = calendar.monthrange(int(year), int(mon))[1]
        month_end = f"{year}-{mon}-{last_day:02d}"

        # Find the "General" project (the bucket for distributable expenses)
        general_project_id = None
        all_names = []
        for p in projects_raw:
            name = p.get("Name") or p.get("name") or ""
            all_names.append(name)
            if name.lower() == "general":
                general_project_id = p.get("id")
                break

        # Debug: log all project names if General not found
        if not general_project_id:
            print(f"DEBUG: Looking for 'General' project in: {all_names}")

        # Build active projects list (excluding "General" project)
        # A project is active in a month if:
        # - Its start_date <= month_end AND (end_date is null OR end_date >= month_start)
        active_projects = []
        for p in projects_raw:
            proj_name = p.get("Name") or p.get("name") or "Sin nombre"

            # Skip the "General" project - it's the source, not a destination
            if proj_name.lower() == "general":
                continue

            # Check status
            status = p.get("Status") or p.get("status") or "active"
            if status.lower() not in ["active", "activo", ""]:
                continue

            # Check date range for project activity in this month
            start_date = p.get("Start Date") or p.get("start_date") or ""
            end_date = p.get("End Date") or p.get("end_date") or ""

            # If no dates set, consider always active
            is_active_in_month = True
            if start_date and start_date > month_end:
                is_active_in_month = False  # Project starts after this month
            if end_date and end_date < month_start:
                is_active_in_month = False  # Project ended before this month

            if is_active_in_month:
                proj = {
                    "id": p.get("id"),
                    "name": proj_name,
                    "client_name": p.get("Client Name") or p.get("client_name") or p.get("Client") or "",
                    "start_date": start_date,
                    "end_date": end_date
                }
                active_projects.append(proj)

        # Build distributions list with percentages for this month
        distributions = []
        for proj in active_projects:
            pct = month_data.get(proj["id"], 0)
            distributions.append({
                "project_id": proj["id"],
                "project_name": proj["name"],
                "client_name": proj["client_name"],
                "percentage": pct,
                "start_date": proj.get("start_date", ""),
                "end_date": proj.get("end_date", "")
            })

        # Calculate general expenses for this month
        # "General expenses" = expenses assigned to the "General" project
        transactions_raw = airtable.get_all("Transactions")

        general_expenses = 0.0
        for t in transactions_raw:
            # Check date range - try multiple field names
            tx_date = (t.get("Settled At") or t.get("Date") or
                       t.get("settled_at") or t.get("transaction_date") or "")
            if tx_date < month_start or tx_date > month_end:
                continue

            # Check if it's an expense (debit)
            side = t.get("Side") or t.get("side") or ""
            if side.lower() != "debit":
                continue

            # Check if excluded
            is_excluded = t.get("is_excluded") or t.get("Is Excluded") or False
            if is_excluded:
                continue

            # Check if assigned to the "General" project
            # "Project" in Airtable is a linked record (array of IDs)
            project_field = t.get("Project") or t.get("project_id") or []
            if isinstance(project_field, list):
                is_general = general_project_id and general_project_id in project_field
            else:
                is_general = general_project_id and project_field == general_project_id

            if is_general:
                amount = abs(float(t.get("Amount") or t.get("amount") or 0))
                general_expenses += amount

        return jsonify({
            "month": month,
            "distributions": distributions,
            "general_expenses": round(general_expenses, 2),
            "active_projects": active_projects,
            "general_project_id": general_project_id
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/monthly-distribution", methods=["POST"])
@require_auth
def api_save_monthly_distribution():
    """Save the monthly general expenses distribution for a specific month.

    Body:
    {
        "month": "2025-01",
        "distributions": {"project_id_1": 40, "project_id_2": 60, ...}
    }
    """
    try:
        data = request.json
        month = data.get("month")
        distributions = data.get("distributions", {})

        if not month:
            return jsonify({"error": "month parameter required"}), 400

        # Validate percentages sum to <= 100
        total_pct = sum(float(v) for v in distributions.values())
        if total_pct > 100.01:  # Allow small rounding errors
            return jsonify({"error": f"Total percentage ({total_pct}%) exceeds 100%"}), 400

        # Load existing settings and update
        settings = load_local_settings()
        if "monthly_distributions" not in settings:
            settings["monthly_distributions"] = {}

        # Clean up zero percentages
        cleaned = {k: v for k, v in distributions.items() if float(v) > 0}
        settings["monthly_distributions"][month] = cleaned

        save_local_settings(settings)

        return jsonify({"ok": True, "month": month, "total_percentage": total_pct})

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/monthly-distribution/all", methods=["GET"])
@require_auth
def api_get_all_monthly_distributions():
    """Get all monthly distributions (for loading into frontend).

    Returns all months with their distribution configurations.
    """
    try:
        settings = load_local_settings()
        monthly_distributions = settings.get("monthly_distributions", {})

        return jsonify({
            "monthly_distributions": monthly_distributions
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ==================== Service Offerings (Ofertas G4U) ====================

@app.route("/api/settings/offerings", methods=["GET"])
@require_auth
def api_get_offerings():
    """Get list of service offerings (Ofertas G4U) from Airtable."""
    try:
        airtable = Airtable()
        # Get offerings from Airtable table "Ofertas G4U"
        try:
            records = airtable.get_all("Ofertas G4U")
            offerings = []
            for rec in records:
                # Note: get_all() flattens fields into the record dict
                name = rec.get("Name", "")
                if name:  # Only include offerings with a name
                    offerings.append({
                        "id": rec.get("id"),  # Airtable record ID for linking
                        "name": name,
                        "description": rec.get("Descripcion", "")
                    })
            return jsonify({"offerings": offerings, "source": "airtable"})
        except Exception as airtable_error:
            # Fallback to local settings if Airtable table doesn't exist
            settings = load_local_settings()
            offerings = settings.get("service_offerings", [
                {"id": "GTM", "name": "GTM (Go-To-Market)"},
                {"id": "Consulting", "name": "Consulting"},
                {"id": "Training", "name": "Training"},
                {"id": "Development", "name": "Development"},
                {"id": "Marketing", "name": "Marketing"},
                {"id": "Other", "name": "Otro"}
            ])
            return jsonify({"offerings": offerings, "source": "local", "airtable_error": str(airtable_error)})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/settings/offerings", methods=["POST"])
@require_auth
def api_save_offerings():
    """Save list of service offerings (Ofertas G4U)."""
    try:
        data = request.json
        offerings = data.get("offerings", [])

        # Validate offerings structure
        for offering in offerings:
            if not offering.get("id") or not offering.get("name"):
                return jsonify({"error": "Cada oferta debe tener ID y nombre"}), 400

        # Load current settings
        settings = load_local_settings()

        # Update offerings
        settings["service_offerings"] = offerings

        # Save settings
        save_local_settings(settings)

        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ==================== Excluded Transactions ====================

@app.route("/api/excluded-transactions", methods=["GET"])
@require_auth
def api_get_excluded_transactions():
    """Get list of excluded transaction IDs."""
    try:
        settings = load_local_settings()
        excluded = settings.get("excluded_transactions", [])
        return jsonify({"excluded": excluded})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ==================== Transaction Updates ====================

@app.route("/api/transaction/<tx_id>", methods=["PUT"])
@require_auth
def api_update_transaction(tx_id):
    """Update a transaction (category, project, client assignment, etc)."""
    try:
        data = request.json
        airtable = Airtable()

        record = {}
        if "category" in data:
            record["Category"] = data["category"]
        if "project_id" in data:
            record["Project"] = data["project_id"]
        if "client_id" in data:
            # Client is a linked record - send as array of record IDs
            client_id = data["client_id"]
            record["Client"] = [client_id] if client_id else []
        if "description" in data:
            record["Description"] = data["description"]
        if "counterparty_name" in data:
            # Try multiple possible field names
            record["Counterparty Name"] = data["counterparty_name"]
            record["Description"] = data["counterparty_name"]  # Also update Description
        if "vat_amount" in data:
            # VAT Amount - user can edit this directly
            record["VAT Amount"] = float(data["vat_amount"]) if data["vat_amount"] else 0
        if "vat_rate" in data:
            # VAT Rate (%) - calculate VAT from rate and amount
            # Formula: amount includes VAT, so VAT = amount × rate / (100 + rate)
            vat_rate = float(data.get("vat_rate", 0))
            amount = float(data.get("amount", 0))
            if vat_rate > 0 and amount > 0:
                vat_amount = abs(amount) * vat_rate / (100 + vat_rate)
                record["VAT Amount"] = round(vat_amount, 2)
            elif vat_rate == 0:
                record["VAT Amount"] = 0
        if "is_excluded" in data:
            # Store excluded transactions locally (not in Airtable)
            settings = load_local_settings()
            excluded_txs = settings.get("excluded_transactions", [])
            if bool(data["is_excluded"]):
                if tx_id not in excluded_txs:
                    excluded_txs.append(tx_id)
            else:
                excluded_txs = [x for x in excluded_txs if x != tx_id]
            settings["excluded_transactions"] = excluded_txs
            save_local_settings(settings)
            # Don't add to Airtable record - handle separately

        if record:
            airtable.update("Transactions", tx_id, record)
        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/salary-allocations")
@require_auth
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
@require_auth
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
@require_auth
def api_delete_salary_allocation(allocation_id):
    """Delete a salary allocation."""
    try:
        airtable = Airtable()
        airtable.delete_batch("Salary Allocations", [allocation_id])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Transaction Allocations ====================

@app.route("/api/transaction-allocations")
@require_auth
def api_transaction_allocations():
    """Get all transaction allocations."""
    try:
        airtable = Airtable()
        records = airtable.get_all("Transaction Allocations")
        allocations = []
        for r in records:
            # Linked records return arrays
            tx_field = r.get("Transaction") or []
            tx_id = tx_field[0] if isinstance(tx_field, list) and tx_field else ""
            proj_field = r.get("Project") or []
            proj_id = proj_field[0] if isinstance(proj_field, list) and proj_field else ""
            client_field = r.get("Client") or []
            client_id = client_field[0] if isinstance(client_field, list) and client_field else ""

            allocations.append({
                "id": r.get("id"),
                "transaction_id": tx_id,
                "project_id": proj_id,
                "client_id": client_id,
                "category": r.get("Category") or "",
                "percentage": (float(r.get("Percentage") or 0) * 100) if (float(r.get("Percentage") or 0) <= 1) else float(r.get("Percentage") or 0)
            })
        return jsonify({"allocations": allocations})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/transaction-allocations/<transaction_id>")
@require_auth
def api_transaction_allocations_by_tx(transaction_id):
    """Get allocations for a specific transaction."""
    try:
        airtable = Airtable()
        records = airtable.get_all("Transaction Allocations")
        allocations = []
        for r in records:
            tx_field = r.get("Transaction") or []
            tx_id = tx_field[0] if isinstance(tx_field, list) and tx_field else ""
            if tx_id != transaction_id:
                continue
            proj_field = r.get("Project") or []
            proj_id = proj_field[0] if isinstance(proj_field, list) and proj_field else ""
            client_field = r.get("Client") or []
            client_id = client_field[0] if isinstance(client_field, list) and client_field else ""

            allocations.append({
                "id": r.get("id"),
                "transaction_id": tx_id,
                "project_id": proj_id,
                "client_id": client_id,
                "category": r.get("Category") or "",
                "percentage": (float(r.get("Percentage") or 0) * 100) if (float(r.get("Percentage") or 0) <= 1) else float(r.get("Percentage") or 0)
            })
        return jsonify({"allocations": allocations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/transaction-allocation", methods=["POST"])
@require_auth
def api_create_transaction_allocation():
    """Create a new transaction allocation."""
    try:
        data = request.json
        airtable = Airtable()

        # Airtable Percent field expects decimal (0.5 = 50%)
        pct_value = float(data.get("percentage", 100)) / 100
        record = {
            "Percentage": pct_value
        }
        # Linked records must be arrays
        if data.get("transaction_id"):
            record["Transaction"] = [data["transaction_id"]]
        if data.get("project_id"):
            record["Project"] = [data["project_id"]]
        if data.get("client_id"):
            record["Client"] = [data["client_id"]]
        # Category is a text field
        if data.get("category"):
            record["Category"] = data["category"]

        result = airtable.create("Transaction Allocations", record)
        return jsonify({"ok": True, "id": result.get("id")})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/transaction-allocation/<allocation_id>", methods=["PUT"])
@require_auth
def api_update_transaction_allocation(allocation_id):
    """Update a transaction allocation."""
    try:
        data = request.json
        airtable = Airtable()

        record = {}
        if "project_id" in data:
            record["Project"] = [data["project_id"]] if data["project_id"] else []
        if "client_id" in data:
            record["Client"] = [data["client_id"]] if data["client_id"] else []
        if "percentage" in data:
            # Airtable Percent field expects decimal (0.5 = 50%)
            record["Percentage"] = float(data["percentage"]) / 100

        airtable.update("Transaction Allocations", allocation_id, record)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/transaction-allocation/<allocation_id>", methods=["DELETE"])
@require_auth
def api_delete_transaction_allocation(allocation_id):
    """Delete a transaction allocation."""
    try:
        airtable = Airtable()
        airtable.delete_batch("Transaction Allocations", [allocation_id])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/project-costs")
@require_auth
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

# ==================== Qonto Extended Data ====================

@app.route("/api/qonto/labels")
def api_qonto_labels():
    """Get all labels from Qonto."""
    try:
        qonto = Qonto()
        labels = qonto.get_labels()
        return jsonify({
            "labels": [
                {
                    "id": l.get("id"),
                    "name": l.get("name"),
                    "parent_id": l.get("parent_id")
                }
                for l in labels
            ],
            "count": len(labels)
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/qonto/sync-labels", methods=["POST"])
def api_qonto_sync_labels():
    """Sync Qonto labels to Categories table."""
    try:
        qonto = Qonto()
        airtable = Airtable()

        # Get labels from Qonto
        qonto_labels = qonto.get_labels()
        if not qonto_labels:
            return jsonify({"error": "No labels found in Qonto or API error"})

        # Get existing categories
        existing = []
        try:
            existing = airtable.get_all("Categories")
        except:
            pass

        existing_names = {c.get("Name", "").lower() for c in existing}

        # Create new categories from Qonto labels
        created = 0
        skipped = 0
        for label in qonto_labels:
            name = label.get("name", "")
            if not name:
                continue

            if name.lower() in existing_names:
                skipped += 1
                continue

            try:
                airtable.create("Categories", {
                    "Name": name,
                    "Type": "Expense"  # Default to expense, user can change
                })
                created += 1
                existing_names.add(name.lower())
            except Exception as e:
                pass

        return jsonify({
            "qonto_labels": len(qonto_labels),
            "created": created,
            "skipped": skipped
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/qonto/update-vat", methods=["POST"])
def api_qonto_update_vat():
    """Update existing transactions with VAT amount from Qonto."""
    try:
        qonto = Qonto()
        airtable = Airtable()

        slug = qonto.get_bank_account_id()
        if not slug:
            return jsonify({"error": "Could not get bank account slug"})

        qonto_txs = qonto.get_all_transactions(slug)
        if not qonto_txs:
            return jsonify({"error": "No transactions from Qonto"})

        # Build map of Qonto transaction_id -> vat_amount
        qonto_vat_map = {}
        for tx in qonto_txs:
            tx_id = tx.get("transaction_id", "")
            vat = tx.get("vat_amount") or tx.get("vat_amount_cents") or 0
            if tx_id and vat:
                vat_float = float(vat)
                # Convert cents to euros if needed
                if vat_float > 1000 and tx.get("vat_amount_cents"):
                    vat_float = vat_float / 100
                qonto_vat_map[tx_id] = vat_float

        # Find transactions table
        table_name = None
        vat_field = None
        with httpx.Client(timeout=30) as client:
            r = client.get(
                f"https://api.airtable.com/v0/meta/bases/{airtable.base_id}/tables",
                headers=airtable.headers
            )
            if r.status_code == 200:
                tables = r.json().get("tables", [])
                for t in tables:
                    name_lower = t.get("name", "").lower()
                    if ("trans" in name_lower or "movimiento" in name_lower) and "alloc" not in name_lower:
                        table_name = t.get("name")
                        # Find VAT field
                        for f in t.get("fields", []):
                            if f.get("name", "").lower() in ["vat amount", "vat_amount", "iva"]:
                                vat_field = f.get("name")
                                break
                        break

        if not table_name:
            return jsonify({"error": "No transactions table found"})
        if not vat_field:
            return jsonify({"error": "No VAT field found in table. Create a number field called 'VAT Amount' or 'IVA'"})

        # Get all Airtable transactions
        airtable_txs = airtable.get_all(table_name)

        updated = 0
        skipped = 0
        no_vat = 0

        for atx in airtable_txs:
            record_id = atx.get("id")
            qonto_id = None
            for key in ["Qonto Transaction ID", "qonto_id", "transaction_id", "ID", "Name"]:
                if atx.get(key):
                    qonto_id = atx.get(key)
                    break

            if not qonto_id:
                skipped += 1
                continue

            # Check if already has VAT
            current_vat = atx.get(vat_field) or atx.get("VAT Amount") or atx.get("IVA") or 0
            if current_vat:
                skipped += 1
                continue

            # Find VAT from Qonto
            new_vat = qonto_vat_map.get(qonto_id, 0)
            if not new_vat:
                no_vat += 1
                continue

            # Update record
            try:
                airtable.update(table_name, record_id, {vat_field: new_vat})
                updated += 1
            except Exception:
                pass

        return jsonify({
            "qonto_transactions": len(qonto_txs),
            "transactions_with_vat": len(qonto_vat_map),
            "airtable_transactions": len(airtable_txs),
            "updated": updated,
            "skipped": skipped,
            "no_vat_in_qonto": no_vat
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/qonto/update-transaction-labels", methods=["POST"])
def api_qonto_update_transaction_labels():
    """Update existing transactions with their Qonto label IDs."""
    try:
        qonto = Qonto()
        airtable = Airtable()

        # Get bank account slug
        slug = qonto.get_bank_account_id()
        if not slug:
            return jsonify({"error": "Could not get bank account slug"})

        # Get all transactions from Qonto
        qonto_txs = qonto.get_all_transactions(slug)
        if not qonto_txs:
            return jsonify({"error": "No transactions from Qonto"})

        # Build a map of Qonto transaction_id -> label_ids
        qonto_labels_map = {}
        for tx in qonto_txs:
            tx_id = tx.get("transaction_id", "")
            label_ids = tx.get("label_ids", [])
            if tx_id and label_ids:
                qonto_labels_map[tx_id] = ",".join(label_ids)

        # Discover table name
        table_name = None
        with httpx.Client(timeout=30) as client:
            r = client.get(
                f"https://api.airtable.com/v0/meta/bases/{airtable.base_id}/tables",
                headers=airtable.headers
            )
            if r.status_code == 200:
                tables = r.json().get("tables", [])
                for t in tables:
                    name_lower = t.get("name", "").lower()
                    if ("trans" in name_lower or "movimiento" in name_lower) and "alloc" not in name_lower:
                        table_name = t.get("name")
                        break
                if not table_name and tables:
                    table_name = tables[0].get("name")

        if not table_name:
            return jsonify({"error": "No transactions table found"})

        # Get all Airtable transactions
        airtable_txs = airtable.get_all(table_name)

        updated = 0
        skipped = 0
        no_labels = 0

        for atx in airtable_txs:
            record_id = atx.get("id")
            # Find the Qonto transaction ID field
            qonto_id = None
            for key in ["Qonto Transaction ID", "qonto_id", "transaction_id", "ID", "Name"]:
                if atx.get(key):
                    qonto_id = atx.get(key)
                    break

            if not qonto_id:
                skipped += 1
                continue

            # Check if already has labels
            current_labels = atx.get("Label IDs") or atx.get("label_ids") or ""
            if current_labels:
                skipped += 1
                continue

            # Find label_ids from Qonto
            new_labels = qonto_labels_map.get(qonto_id, "")
            if not new_labels:
                no_labels += 1
                continue

            # Update the record
            try:
                airtable.update(table_name, record_id, {"Label IDs": new_labels})
                updated += 1
            except Exception as e:
                pass

        return jsonify({
            "qonto_transactions": len(qonto_txs),
            "transactions_with_labels": len(qonto_labels_map),
            "airtable_transactions": len(airtable_txs),
            "updated": updated,
            "skipped": skipped,
            "no_labels_in_qonto": no_labels
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/debug/labels")
def api_debug_labels():
    """Debug endpoint to see label data from Qonto and Airtable."""
    try:
        qonto = Qonto()
        airtable = Airtable()

        # Get Qonto transactions with labels
        slug = qonto.get_bank_account_id()
        qonto_txs = qonto.get_all_transactions(slug) if slug else []

        # Find transactions that have labels
        qonto_with_labels = []
        for tx in qonto_txs[:50]:  # Check first 50
            label_ids = tx.get("label_ids", [])
            if label_ids:
                qonto_with_labels.append({
                    "transaction_id": tx.get("transaction_id"),
                    "label": tx.get("label"),
                    "label_ids": label_ids,
                    "amount": tx.get("amount")
                })

        # Get Airtable transactions
        airtable_txs = airtable.get_all("Transactions")
        airtable_sample = []
        for atx in airtable_txs[:10]:
            airtable_sample.append({
                "id": atx.get("id"),
                "Qonto Transaction ID": atx.get("Qonto Transaction ID"),
                "Name": atx.get("Name"),
                "Label IDs": atx.get("Label IDs"),
                "Description": atx.get("Description")
            })

        return jsonify({
            "qonto_total": len(qonto_txs),
            "qonto_with_labels": qonto_with_labels,
            "qonto_with_labels_count": len(qonto_with_labels),
            "airtable_sample": airtable_sample
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/debug/transaction-sample")
def api_debug_transaction_sample():
    """Show raw Qonto transaction data to see all available fields."""
    try:
        qonto = Qonto()
        slug = qonto.get_bank_account_id()
        if not slug:
            return jsonify({"error": "No bank account"})

        with httpx.Client(timeout=30) as client:
            params = {"slug": slug, "status": "completed", "per_page": 5}
            r = client.get(f"{qonto.base_url}/transactions", headers=qonto.headers, params=params)
            if r.status_code == 200:
                data = r.json()
                return jsonify({
                    "sample_transactions": data.get("transactions", []),
                    "meta": data.get("meta", {})
                })
            else:
                return jsonify({"error": f"Qonto API error: {r.status_code}", "body": r.text})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/qonto/memberships")
def api_qonto_memberships():
    """Get all memberships from Qonto."""
    try:
        qonto = Qonto()
        memberships = qonto.get_memberships()
        return jsonify({
            "memberships": [
                {
                    "id": m.get("id"),
                    "first_name": m.get("first_name"),
                    "last_name": m.get("last_name"),
                    "email": m.get("email"),
                    "role": m.get("role")
                }
                for m in memberships
            ],
            "count": len(memberships)
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/qonto/sync-members", methods=["POST"])
def api_qonto_sync_members():
    """Sync Qonto memberships to Team Members table."""
    try:
        qonto = Qonto()
        airtable = Airtable()

        # Get memberships from Qonto
        memberships = qonto.get_memberships()
        if not memberships:
            return jsonify({"error": "No memberships found in Qonto or API error"})

        # Get existing team members
        existing = []
        try:
            existing = airtable.get_all("Team Members")
        except:
            pass

        existing_names = {m.get("Name", "").lower() for m in existing}

        # Create new team members from Qonto memberships
        created = 0
        skipped = 0
        for m in memberships:
            first = m.get("first_name", "")
            last = m.get("last_name", "")
            name = f"{first} {last}".strip()

            if not name:
                continue

            if name.lower() in existing_names:
                skipped += 1
                continue

            try:
                airtable.create("Team Members", {
                    "Name": name,
                    "Role": m.get("role", ""),
                    "Salary": 0  # Default, user must set
                })
                created += 1
                existing_names.add(name.lower())
            except Exception as e:
                pass

        return jsonify({
            "qonto_memberships": len(memberships),
            "created": created,
            "skipped": skipped
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/qonto/attachment/<attachment_id>")
def api_qonto_attachment(attachment_id):
    """Get attachment details from Qonto."""
    try:
        qonto = Qonto()
        attachment = qonto.get_attachment(attachment_id)
        if attachment:
            return jsonify({
                "id": attachment.get("id"),
                "filename": attachment.get("file_name"),
                "file_size": attachment.get("file_size"),
                "file_type": attachment.get("file_content_type"),
                "url": attachment.get("url"),
                "created_at": attachment.get("created_at")
            })
        return jsonify({"error": "Attachment not found"}), 404
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/qonto/organization")
def api_qonto_organization():
    """Get organization details from Qonto."""
    try:
        qonto = Qonto()
        org = qonto.get_organization()
        if org:
            bank_accounts = []
            for ba in org.get("bank_accounts", []):
                bank_accounts.append({
                    "slug": ba.get("slug"),
                    "iban": ba.get("iban"),
                    "bic": ba.get("bic"),
                    "name": ba.get("name"),
                    "balance": ba.get("balance"),
                    "balance_cents": ba.get("balance_cents"),
                    "currency": ba.get("currency")
                })
            return jsonify({
                "slug": org.get("slug"),
                "legal_name": org.get("legal_name"),
                "bank_accounts": bank_accounts
            })
        return jsonify({"error": "Organization not found"}), 404
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route("/api/qonto/transaction-details/<tx_id>")
def api_qonto_transaction_details(tx_id):
    """Get extended transaction details from Airtable including Qonto metadata."""
    try:
        airtable = Airtable()
        qonto = Qonto()

        # Get transaction from Airtable
        records = airtable.get_all("Transactions", formula=f"{{Qonto Transaction ID}}='{tx_id}'")
        if not records:
            return jsonify({"error": "Transaction not found"}), 404

        tx = records[0]

        # Get attachment info if available
        attachments = []
        attachment_ids = tx.get("Attachment IDs", "") or ""
        if attachment_ids:
            for att_id in attachment_ids.split(","):
                att_id = att_id.strip()
                if att_id:
                    att_info = qonto.get_attachment(att_id)
                    if att_info:
                        attachments.append({
                            "id": att_id,
                            "filename": att_info.get("file_name"),
                            "url": att_info.get("url"),
                            "type": att_info.get("file_content_type")
                        })

        return jsonify({
            "id": tx.get("id"),
            "qonto_id": tx.get("Qonto Transaction ID"),
            "amount": tx.get("Amount"),
            "type": tx.get("Type"),
            "date": tx.get("Date"),
            "description": tx.get("Description"),
            "counterparty": tx.get("Counterparty"),
            "reference": tx.get("Reference"),
            "note": tx.get("Note"),
            "vat_amount": tx.get("VAT Amount"),
            "vat_rate": tx.get("VAT Rate"),
            "label_ids": tx.get("Label IDs"),
            "category": tx.get("Category"),
            "project": tx.get("Project"),
            "client": tx.get("Client"),
            "attachments": attachments,
            "attachment_required": tx.get("Attachment Required"),
            "attachment_lost": tx.get("Attachment Lost")
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


# ==================== AI Brain - Financial Simulations ====================

AI_MODEL_CONFIGS = {
    # Groq (Ultra Fast)
    "groq-llama3-70b": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1"
    },
    "groq-mixtral": {
        "provider": "groq",
        "model": "mixtral-8x7b-32768",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1"
    },
    # OpenAI
    "openai-gpt4o": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    "openai-gpt4o-mini": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    "openai-o1": {
        "provider": "openai",
        "model": "o1",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    "openai-o1-mini": {
        "provider": "openai",
        "model": "o1-mini",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    # Anthropic Claude
    "anthropic-opus": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1"
    },
    "anthropic-sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1"
    },
    "anthropic-haiku": {
        "provider": "anthropic",
        "model": "claude-3-5-haiku-20241022",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1"
    },
    # Google Gemini
    "gemini-pro": {
        "provider": "gemini",
        "model": "gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta"
    },
    "gemini-flash": {
        "provider": "gemini",
        "model": "gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta"
    },
    # xAI Grok
    "grok-2": {
        "provider": "xai",
        "model": "grok-2-latest",
        "api_key_env": "XAI_API_KEY",
        "base_url": "https://api.x.ai/v1"
    }
}

SYSTEM_PROMPT = """Eres un analista financiero experto para G4U (Growth4U), una consultora de negocios.
Tu rol es analizar datos financieros y proporcionar insights accionables.

DATOS ACTUALES DEL PERIODO:
{context}

INSTRUCCIONES:
1. Responde siempre en español
2. Se conciso pero completo
3. Usa numeros formateados con simbolo € y separadores de miles
4. Cuando hagas proyecciones, muestra rangos (optimista/base/pesimista)
5. Identifica patrones y anomalias
6. Da recomendaciones practicas y especificas
7. Si no tienes suficientes datos para una conclusion, dilo claramente

FORMATO DE RESPUESTA:
- Usa markdown para estructura
- Incluye listas y tablas cuando sea util
- Destaca KPIs importantes con **negrita**"""

def call_ai_api(model_id: str, messages: list, context: str) -> str:
    """Call the appropriate AI API based on model selection."""
    config = AI_MODEL_CONFIGS.get(model_id)
    if not config:
        return f"Error: Modelo '{model_id}' no configurado"

    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        return f"Error: API key no configurada ({config['api_key_env']}). Configurala en variables de entorno."

    provider = config["provider"]

    try:
        if provider in ["openai", "groq", "xai"]:
            # OpenAI-compatible API (OpenAI, Groq, xAI)
            response = httpx.post(
                f"{config['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config["model"],
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
                        *messages
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        elif provider == "anthropic":
            # Anthropic Claude API
            response = httpx.post(
                f"{config['base_url']}/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config["model"],
                    "max_tokens": 2000,
                    "system": SYSTEM_PROMPT.format(context=context),
                    "messages": messages
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

        elif provider == "gemini":
            # Google Gemini API
            response = httpx.post(
                f"{config['base_url']}/models/{config['model']}:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [
                        {"role": "user", "parts": [{"text": SYSTEM_PROMPT.format(context=context)}]},
                        *[{"role": m["role"], "parts": [{"text": m["content"]}]} for m in messages]
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 2000
                    }
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

        else:
            return f"Error: Proveedor '{provider}' no soportado"

    except httpx.HTTPStatusError as e:
        return f"Error API ({e.response.status_code}): {e.response.text[:200]}"
    except Exception as e:
        return f"Error: {str(e)}"


@app.route("/api/ai/chat", methods=["POST"])
@require_auth
def api_ai_chat():
    """Send a message to the AI and get a response."""
    try:
        data = request.json
        model_id = data.get("model", "groq-llama3-70b")
        messages = data.get("messages", [])
        context = data.get("context", "")

        if not messages:
            return jsonify({"error": "No messages provided"}), 400

        response = call_ai_api(model_id, messages, context)
        return jsonify({"response": response})

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/ai/scenario", methods=["POST"])
@require_auth
def api_ai_scenario():
    """Run a predefined AI scenario."""
    try:
        data = request.json
        model_id = data.get("model", "groq-llama3-70b")
        scenario = data.get("scenario", "")
        context = data.get("context", "")

        # Predefined scenario prompts
        scenarios = {
            "projection": "Analiza los datos financieros y genera una proyeccion para los proximos 3 meses. Incluye ingresos esperados, gastos proyectados y margen estimado. Presenta escenarios optimista, base y pesimista.",
            "anomalies": "Revisa los datos y detecta cualquier anomalia o gasto inusual. Identifica transacciones que se desvian significativamente del patron normal. Lista los hallazgos por orden de importancia.",
            "trends": "Analiza las tendencias en ingresos y gastos. Identifica patrones estacionales, crecimiento/decrecimiento, y categorias con mayor variacion. Incluye graficos conceptuales si es util.",
            "optimization": "Basandote en los gastos actuales, sugiere areas de optimizacion. Prioriza por impacto potencial y facilidad de implementacion. Incluye estimacion de ahorro.",
            "whatif_revenue": "Simula un escenario donde los ingresos aumentan un 20%. Calcula el impacto en el margen, el punto de equilibrio y recomienda como gestionar el crecimiento.",
            "whatif_cost": "Simula un escenario donde los costos se reducen un 10%. Identifica que gastos podrian reducirse de forma realista y calcula el impacto en rentabilidad."
        }

        prompt = scenarios.get(scenario, scenario)
        if not prompt:
            return jsonify({"error": "Scenario not found"}), 400

        messages = [{"role": "user", "content": prompt}]
        response = call_ai_api(model_id, messages, context)

        return jsonify({
            "scenario": scenario,
            "response": response
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/ai/settings", methods=["GET"])
@require_auth
def api_ai_settings_get():
    """Get AI settings (selected model)."""
    try:
        settings = load_local_settings()
        return jsonify({
            "model": settings.get("ai_model", "groq-llama3-70b"),
            "available_models": list(AI_MODEL_CONFIGS.keys())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai/settings", methods=["POST"])
@require_auth
def api_ai_settings_save():
    """Save AI settings (selected model)."""
    try:
        data = request.json
        model = data.get("model", "groq-llama3-70b")

        if model not in AI_MODEL_CONFIGS:
            return jsonify({"error": "Modelo no valido"}), 400

        settings = load_local_settings()
        settings["ai_model"] = model
        save_local_settings(settings)

        return jsonify({"ok": True, "model": model})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
