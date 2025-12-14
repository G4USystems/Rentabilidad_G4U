"""
Vercel serverless entry point - minimal version for debugging.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Minimal FastAPI app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    return {
        "name": "Rentabilidad G4U",
        "status": "running",
        "storage_type": os.getenv("STORAGE_TYPE", "not_set"),
        "airtable_base": os.getenv("AIRTABLE_BASE_ID", "not_set")[:10] + "..." if os.getenv("AIRTABLE_BASE_ID") else "not_set",
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/debug/env")
async def debug_env():
    """Check environment variables (safe)."""
    return {
        "STORAGE_TYPE": os.getenv("STORAGE_TYPE", "NOT SET"),
        "AIRTABLE_BASE_ID": "SET" if os.getenv("AIRTABLE_BASE_ID") else "NOT SET",
        "AIRTABLE_TOKEN": "SET" if os.getenv("AIRTABLE_TOKEN") else "NOT SET",
        "QONTO_API_KEY": "SET" if os.getenv("QONTO_API_KEY") else "NOT SET",
        "QONTO_ORGANIZATION_SLUG": os.getenv("QONTO_ORGANIZATION_SLUG", "NOT SET"),
    }

@app.get("/debug/import")
async def debug_import():
    """Test imports step by step."""
    results = {}

    try:
        import pandas
        results["pandas"] = "OK"
    except Exception as e:
        results["pandas"] = str(e)

    try:
        import httpx
        results["httpx"] = "OK"
    except Exception as e:
        results["httpx"] = str(e)

    try:
        from app.storage.excel_storage import get_storage
        results["get_storage"] = "OK"
    except Exception as e:
        results["get_storage"] = str(e)

    try:
        from app.storage.excel_storage import get_storage
        storage = get_storage()
        results["storage_init"] = f"OK - {type(storage).__name__}"
    except Exception as e:
        results["storage_init"] = str(e)

    try:
        from app.api.excel_api import router
        results["api_router"] = "OK"
    except Exception as e:
        results["api_router"] = str(e)

    return results

# Try to mount API routes
import_error = None
try:
    from app.api.excel_api import router as api_router
    app.include_router(api_router, prefix="/api/v1")
except Exception as e:
    import_error = str(e)

    @app.get("/api/v1/{path:path}")
    async def api_fallback(path: str):
        return {"error": import_error, "path": path}

# Mangum handler for Vercel
from mangum import Mangum
handler = Mangum(app, lifespan="off")
