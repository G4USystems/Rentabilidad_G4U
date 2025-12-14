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

# Include Excel-based API routes
app.include_router(excel_router, prefix="/api/v1")


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
