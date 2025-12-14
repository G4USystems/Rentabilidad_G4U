"""
Vercel serverless entry point.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Set default environment variables if not set
if not os.getenv("STORAGE_TYPE"):
    os.environ["STORAGE_TYPE"] = "airtable"

from mangum import Mangum
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create a minimal app first to catch import errors
app = FastAPI(title="Rentabilidad G4U")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Rentabilidad G4U",
        "version": "2.0.0",
        "status": "running",
        "storage": os.getenv("STORAGE_TYPE", "airtable"),
    }

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}

# Try to import and mount the main API routes
try:
    from app.api.excel_api import router as api_router
    app.include_router(api_router, prefix="/api/v1")
except Exception as e:
    @app.get("/api/v1/error")
    async def api_error():
        return {"error": str(e), "type": type(e).__name__}

# Vercel handler
handler = Mangum(app, lifespan="off")
