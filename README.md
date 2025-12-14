# Rentabilidad G4U - Sistema de Reportes P&L con Qonto

Sistema de integración con la API de Qonto para generación de reportes de Pérdidas y Ganancias (P&L) con KPIs de rentabilidad global y por proyectos.

**Sin base de datos requerida** - Almacenamiento en Excel local o Google Sheets.

## Características

- 🏦 **Integración con Qonto API**: Sincronización automática de transacciones
- 📊 **Reportes P&L**: Estados de resultados configurables por período
- 📈 **KPIs de Rentabilidad**: Métricas globales y por proyecto
- 🏷️ **Categorización**: Auto-categorización por palabras clave
- 📁 **Gestión de Proyectos**: Seguimiento de rentabilidad por proyecto
- 📄 **Almacenamiento flexible**: Excel local o Google Sheets

## Opciones de Almacenamiento

| Modo | Uso | Ideal para |
|------|-----|------------|
| **Excel Local** | Archivos .xlsx en carpeta `data/` | Desarrollo, uso personal |
| **Google Sheets** | Documento en Google Drive | Producción, Vercel, equipo |

## 🚀 Deploy en Vercel (Google Sheets)

### 1. Configurar Google Sheets

1. Crear un [Google Sheet](https://sheets.google.com) nuevo
2. Copiar el ID del documento (de la URL: `docs.google.com/spreadsheets/d/[ESTE_ES_EL_ID]/edit`)

### 2. Configurar Google Cloud (Service Account)

1. Ir a [Google Cloud Console](https://console.cloud.google.com)
2. Crear proyecto nuevo o seleccionar existente
3. Habilitar **Google Sheets API**
4. Crear **Service Account** (IAM & Admin → Service Accounts)
5. Crear clave JSON y descargar
6. **Importante**: Compartir tu Google Sheet con el email del service account

### 3. Variables en Vercel

| Variable | Valor |
|----------|-------|
| `QONTO_API_KEY` | Tu API key de Qonto |
| `QONTO_ORGANIZATION_SLUG` | Slug de tu organización |
| `QONTO_IBAN` | IBAN de tu cuenta |
| `USE_GOOGLE_SHEETS` | `true` |
| `GOOGLE_SHEETS_ID` | ID de tu documento |
| `GOOGLE_SHEETS_CREDENTIALS` | Contenido JSON del service account (una línea) |

### 4. Deploy

```bash
vercel --prod
```

### 5. Inicializar

```bash
# Crear categorías
curl -X POST https://tu-app.vercel.app/api/v1/sync/init

# Sincronizar Qonto
curl -X POST https://tu-app.vercel.app/api/v1/sync/all
```

## 💻 Desarrollo Local (Excel)

```bash
# Clonar e instalar
git clone <repository-url>
cd Rentabilidad_G4U
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar
cp .env.example .env
# Editar .env con credenciales de Qonto

# Ejecutar
uvicorn app.main:app --reload
```

Los datos se guardan en la carpeta `data/`:
- `transactions.xlsx`
- `categories.xlsx`
- `projects.xlsx`
- `accounts.xlsx`

## 📚 API Endpoints

### Sincronización
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/sync/init` | Crear categorías predeterminadas |
| POST | `/api/v1/sync/all` | Sincronizar todo desde Qonto |
| POST | `/api/v1/sync/transactions` | Solo transacciones |

### Reportes P&L
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/reports/pl?start_date=X&end_date=Y` | Generar P&L |
| GET | `/api/v1/reports/pl/monthly?year=2024&month=1` | P&L mensual |
| GET | `/api/v1/reports/pl/yearly?year=2024` | P&L anual |

### KPIs
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/kpis/dashboard` | Dashboard con métricas clave |
| GET | `/api/v1/kpis/global?start_date=X&end_date=Y` | KPIs globales |
| GET | `/api/v1/kpis/projects` | KPIs por proyecto |

### Transacciones
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/transactions` | Listar transacciones |
| PATCH | `/api/v1/transactions/{id}` | Categorizar/asignar |

### Proyectos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/v1/projects` | Listar proyectos |
| POST | `/api/v1/projects` | Crear proyecto |
| GET | `/api/v1/projects/{id}` | KPIs del proyecto |

## 📊 KPIs Disponibles

- **Margen Bruto**: (Ingresos - COGS) / Ingresos
- **Margen Neto**: Beneficio Neto / Ingresos  
- **EBITDA**: Beneficio antes de intereses, impuestos y depreciación
- **Margen Operativo**: Utilidad Operativa / Ingresos
- **ROI por Proyecto**: (Ingresos - Costos) / Costos

## 📁 Estructura

```
Rentabilidad_G4U/
├── api/                  # Entry point Vercel
├── app/
│   ├── api/              # Endpoints REST
│   ├── core/             # Configuración
│   ├── storage/          # Excel/Google Sheets
│   ├── services/         # Lógica de negocio
│   └── integrations/     # Cliente Qonto
├── data/                 # Archivos Excel (local)
├── vercel.json
└── requirements.txt
```

## Licencia

MIT License - G4U Systems
