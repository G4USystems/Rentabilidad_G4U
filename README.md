# Rentabilidad G4U - Sistema de Reportes P&L con Qonto

Sistema de integración con la API de Qonto para generación de reportes de Pérdidas y Ganancias (P&L) con KPIs de rentabilidad global y por proyectos.

## Características

- 🏦 **Integración con Qonto API**: Sincronización automática de transacciones
- 📊 **Reportes P&L**: Estados de resultados configurables por período
- 📈 **KPIs de Rentabilidad**: Métricas globales y por proyecto
- 🏷️ **Categorización**: Sistema flexible de categorías de ingresos/gastos
- 📁 **Gestión de Proyectos**: Asignación de transacciones a proyectos
- 📄 **Exportación**: CSV y JSON

## 🚀 Deploy en Vercel

### 1. Configurar Base de Datos

Necesitas una base de datos PostgreSQL externa. Opciones recomendadas:

| Servicio | Free Tier | Recomendación |
|----------|-----------|---------------|
| [Neon](https://neon.tech) | 512MB | ⭐ Recomendado |
| [Supabase](https://supabase.com) | 500MB | Buena opción |
| [Railway](https://railway.app) | $5/mes crédito | Fácil setup |

### 2. Variables de Entorno en Vercel

En tu dashboard de Vercel → Settings → Environment Variables:

\`\`\`
QONTO_API_KEY=tu_api_key_de_qonto
QONTO_ORGANIZATION_SLUG=tu_organization_slug
QONTO_IBAN=tu_iban
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
\`\`\`

### 3. Deploy

\`\`\`bash
# Opción 1: Conectar repo de GitHub en vercel.com

# Opción 2: CLI
npm i -g vercel
vercel --prod
\`\`\`

### 4. Inicializar el Sistema

Después del deploy, ejecuta en orden:

\`\`\`bash
# 1. Crear categorías predeterminadas
curl -X POST https://tu-app.vercel.app/api/v1/sync/init

# 2. Sincronizar datos de Qonto
curl -X POST https://tu-app.vercel.app/api/v1/sync/all
\`\`\`

## 💻 Desarrollo Local

\`\`\`bash
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
\`\`\`

## 📚 API Endpoints

### Sincronización
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | \`/api/v1/sync/init\` | Inicializar categorías |
| POST | \`/api/v1/sync/all\` | Sincronizar todo |
| POST | \`/api/v1/sync/transactions\` | Solo transacciones |

### Reportes P&L
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | \`/api/v1/reports/pl\` | Generar reporte P&L |
| GET | \`/api/v1/reports/pl/summary\` | Resumen rápido |
| GET | \`/api/v1/reports/pl/monthly\` | P&L mensual |
| GET | \`/api/v1/reports/pl/quarterly\` | P&L trimestral |

### KPIs
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | \`/api/v1/kpis/global\` | KPIs globales |
| GET | \`/api/v1/kpis/projects\` | KPIs por proyecto |
| GET | \`/api/v1/kpis/dashboard\` | Dashboard resumen |
| GET | \`/api/v1/kpis/trends/{metric}\` | Tendencias |

### Proyectos y Transacciones
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | \`/api/v1/projects\` | Listar proyectos |
| GET | \`/api/v1/projects/summary\` | Con resumen financiero |
| GET | \`/api/v1/transactions\` | Listar transacciones |
| PATCH | \`/api/v1/transactions/{id}\` | Categorizar/asignar |

## 📖 Documentación Interactiva

Una vez desplegado:
- **Swagger UI**: \`https://tu-app.vercel.app/docs\`
- **ReDoc**: \`https://tu-app.vercel.app/redoc\`

## 📊 KPIs Disponibles

### Globales
- **Margen Bruto**: (Ingresos - COGS) / Ingresos
- **Margen Neto**: Beneficio Neto / Ingresos
- **EBITDA**: Beneficio antes de intereses, impuestos y depreciación
- **Burn Rate**: Consumo de efectivo mensual

### Por Proyecto
- **ROI**: (Ingresos - Costos) / Costos
- **Margen de Contribución**: Ingresos - Costos Variables
- **Uso de Presupuesto**: % del presupuesto consumido

## 📁 Estructura

\`\`\`
Rentabilidad_G4U/
├── api/                  # Entry point Vercel
├── app/
│   ├── api/              # Endpoints REST
│   ├── core/             # Configuración
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Lógica de negocio
│   └── integrations/     # Cliente Qonto
├── vercel.json           # Config Vercel
└── requirements.txt
\`\`\`

## Licencia

MIT License - G4U Systems
