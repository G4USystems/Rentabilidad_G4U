# Rentabilidad G4U - Sistema de Reportes P&L con Qonto

Sistema de integración con la API de Qonto para generación de reportes de Pérdidas y Ganancias (P&L) con KPIs de rentabilidad global y por proyectos.

**Almacenamiento en Airtable** - Base de datos visual y colaborativa en la nube.

## Características

- **Integración con Qonto API**: Sincronización automática de transacciones bancarias
- **Reportes P&L**: Estados de resultados configurables por período
- **KPIs de Rentabilidad**: Métricas globales y por proyecto
- **Categorización**: Auto-categorización de transacciones por palabras clave
- **Gestión de Proyectos**: Seguimiento de rentabilidad por proyecto
- **Almacenamiento en Airtable**: Base de datos visual, colaborativa y en tiempo real

## Requisitos

- Cuenta en [Qonto](https://qonto.com) con API habilitada
- Base en [Airtable](https://airtable.com) con las tablas requeridas
- [Vercel](https://vercel.com) para el deploy (opcional)

## Configuración de Airtable

### 1. Crear Base en Airtable

Crea una nueva base en Airtable con las siguientes tablas:

| Tabla | Campos principales |
|-------|-------------------|
| **transactions** | id, qonto_id, amount, side, currency, counterparty_name, label, settled_at, category_id, project_id, is_excluded |
| **categories** | id, name, type, keywords, is_active |
| **projects** | id, name, code, client_name, budget_amount, contract_value, status, is_active |
| **accounts** | id, qonto_id, iban, name, balance, currency |

### 2. Obtener Credenciales de Airtable

1. Ir a [airtable.com/create/tokens](https://airtable.com/create/tokens)
2. Crear un **Personal Access Token** con permisos:
   - `data.records:read`
   - `data.records:write`
   - `schema.bases:read`
3. Copiar el **Base ID** de la URL de tu base: `airtable.com/[BASE_ID]/...`

## Deploy en Vercel

### Variables de Entorno

| Variable | Descripción |
|----------|-------------|
| `QONTO_API_KEY` | API key de Qonto |
| `QONTO_ORGANIZATION_SLUG` | Slug de tu organización en Qonto |
| `QONTO_IBAN` | IBAN de la cuenta a sincronizar |
| `STORAGE_TYPE` | `airtable` |
| `AIRTABLE_TOKEN` | Personal Access Token de Airtable |
| `AIRTABLE_BASE_ID` | ID de tu base de Airtable |

### Deploy

```bash
vercel --prod
```

### Inicializar Sistema

```bash
# Crear categorías predeterminadas
curl -X POST https://tu-app.vercel.app/api/v1/sync/init

# Sincronizar datos de Qonto
curl -X POST https://tu-app.vercel.app/api/v1/sync/all
```

## Desarrollo Local

```bash
# Clonar e instalar
git clone <repository-url>
cd Rentabilidad_G4U
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar
uvicorn app.main:app --reload
```

## API Endpoints

### Sincronización
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/sync/init` | Crear categorías predeterminadas |
| POST | `/api/v1/sync/all` | Sincronizar todo desde Qonto |
| POST | `/api/v1/sync/accounts` | Sincronizar cuentas |
| POST | `/api/v1/sync/transactions` | Sincronizar transacciones |

### Reportes P&L
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/reports/pl?start_date=X&end_date=Y` | Generar P&L por fechas |
| GET | `/api/v1/reports/pl/monthly?year=2024&month=1` | P&L mensual |
| GET | `/api/v1/reports/pl/yearly?year=2024` | P&L anual |

### KPIs
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/kpis/dashboard` | Dashboard con métricas clave |
| GET | `/api/v1/kpis/global?start_date=X&end_date=Y` | KPIs globales |
| GET | `/api/v1/kpis/projects` | KPIs de todos los proyectos |

### Transacciones
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/transactions` | Listar transacciones |
| PATCH | `/api/v1/transactions/{id}` | Categorizar/asignar proyecto |
| POST | `/api/v1/transactions/bulk/categorize` | Categorizar en lote |
| POST | `/api/v1/transactions/bulk/assign-project` | Asignar proyecto en lote |

### Proyectos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/projects` | Listar proyectos |
| POST | `/api/v1/projects` | Crear proyecto |
| GET | `/api/v1/projects/{id}` | KPIs del proyecto |

### Categorías
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/categories` | Listar categorías |

## KPIs Disponibles

| KPI | Descripción |
|-----|-------------|
| **Margen Bruto** | (Ingresos - COGS) / Ingresos |
| **Margen Neto** | Beneficio Neto / Ingresos |
| **EBITDA** | Beneficio antes de intereses, impuestos y depreciación |
| **Margen Operativo** | Utilidad Operativa / Ingresos |
| **ROI por Proyecto** | (Ingresos - Costos) / Costos |

## Estructura del Proyecto

```
Rentabilidad_G4U/
├── api/                  # Entry point Vercel
├── app/
│   ├── api/              # Endpoints REST
│   ├── core/             # Configuración
│   ├── storage/          # Airtable storage
│   ├── services/         # Lógica de negocio
│   └── integrations/     # Cliente Qonto API
├── vercel.json
└── requirements.txt
```

## Licencia

MIT License - G4U Systems
