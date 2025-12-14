"""
Rentabilidad G4U - Main Application Entry Point

Sistema de integración con Qonto para reportes P&L y KPIs de rentabilidad.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Rentabilidad G4U API...")
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
## Sistema de Reportes P&L con Qonto

API para integración con Qonto y generación de reportes financieros.

### Características principales:

- **Sincronización con Qonto**: Importación automática de transacciones bancarias
- **Reportes P&L**: Estados de resultados configurables por período
- **KPIs de Rentabilidad**: Métricas globales y por proyecto
- **Gestión de Proyectos**: Seguimiento de rentabilidad por proyecto
- **Categorización**: Sistema flexible de categorías de ingresos/gastos

### Flujo de trabajo típico:

1. Inicializar el sistema (`POST /api/v1/sync/init`)
2. Sincronizar cuentas y transacciones desde Qonto (`POST /api/v1/sync/all`)
3. Categorizar transacciones (`POST /api/v1/sync/categories/auto`)
4. Crear proyectos y asignar transacciones
5. Generar reportes P&L y KPIs
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
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
