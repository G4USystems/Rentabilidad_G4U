"""
Rentabilidad G4U - Main Application Entry Point

Sistema de integración con Qonto para reportes P&L y KPIs de rentabilidad.
Almacenamiento en Excel/Google Sheets.
"""

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.excel_api import router as excel_router
from app.api.transactions import router as transactions_router
from app.api.projects import router as projects_router
from app.api.clients import router as clients_router
from app.api.categories import router as categories_router
from app.api.reports import router as reports_router
from app.api.kpis import router as kpis_router
from app.api.assignment_rules import router as assignment_rules_router
from app.api.scenarios import router as scenarios_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
## Sistema de Reportes P&L con Qonto

API para integración con Qonto y generación de reportes financieros.
**Almacenamiento en Excel/Google Sheets** - Sin base de datos requerida.

### Características principales:

- **Sincronización con Qonto**: Importación automática de transacciones bancarias
- **Reportes P&L**: Estados de resultados configurables por período
- **KPIs de Rentabilidad**: Métricas globales y por proyecto
- **Gestión de Proyectos**: Seguimiento de rentabilidad por proyecto
- **Categorización**: Sistema flexible de categorías de ingresos/gastos
- **Almacenamiento**: Excel local o Google Sheets (para producción)

### Flujo de trabajo:

1. Inicializar el sistema (`POST /api/v1/sync/init`)
2. Sincronizar desde Qonto (`POST /api/v1/sync/all`)
3. Ver dashboard (`GET /api/v1/kpis/dashboard`)
4. Generar reportes P&L (`GET /api/v1/reports/pl`)
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Excel-based API routes (storage-agnostic)
app.include_router(excel_router, prefix="/api/v1")

# Include SQLAlchemy-based API routes (database-backed)
app.include_router(transactions_router, prefix="/api/v2/transactions", tags=["transactions"])
app.include_router(projects_router, prefix="/api/v2/projects", tags=["projects"])
app.include_router(clients_router, prefix="/api/v2/clients", tags=["clients"])
app.include_router(categories_router, prefix="/api/v2/categories", tags=["categories"])
app.include_router(reports_router, prefix="/api/v2/reports", tags=["reports"])
app.include_router(kpis_router, prefix="/api/v2/kpis", tags=["kpis"])
app.include_router(assignment_rules_router, prefix="/api/v2/assignment-rules", tags=["assignment-rules"])
app.include_router(scenarios_router, prefix="/api/v2/scenarios", tags=["scenarios"])


@app.get("/")
async def root():
    """Root endpoint - API information."""
    storage_mode = "Google Sheets" if os.getenv("USE_GOOGLE_SHEETS", "").lower() == "true" else "Excel Local"

    return {
        "name": settings.app_name,
        "version": "2.0.0",
        "status": "running",
        "storage": storage_mode,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.app_env,
    }


# Vercel serverless handler
from mangum import Mangum
handler = Mangum(app, lifespan="off")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
