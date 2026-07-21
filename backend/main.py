"""
CalRetail — FastAPI Main Application
"""
import sys
import time
from pathlib import Path

# Ensure backend package is importable regardless of CWD
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config.settings import settings
from backend.routers.customer_experience import router as ce_router
from backend.routers.merchandising import router as merch_router
from backend.routers.ops_support_monetise import ops_router, support_router, monetise_router
from backend.utils.logger import logger

# ── App init ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Enterprise Retail AI Intelligence Platform — 20 AI capabilities "
        "across 5 business modules for a fashion retail company."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (allow Streamlit frontend running on localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware: Request logging ───────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path}  →  {response.status_code}  ({elapsed}ms)")
    return response


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(ce_router)
app.include_router(merch_router)
app.include_router(ops_router)
app.include_router(support_router)
app.include_router(monetise_router)


# ── Root & health ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "platform": settings.APP_NAME,
        "version":  settings.APP_VERSION,
        "status":   "running",
        "modules": [
            "Customer Experience",
            "Merchandising Intelligence",
            "Operational Excellence",
            "Customer Support Intelligence",
            "First Party Data Monetisation",
        ],
        "total_ai_capabilities": 20,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/api/v1/categories", tags=["Common"])
def list_categories():
    """Return all product categories for UI dropdowns."""
    return {
        "categories": [
            "Tops","Bottoms","Dresses","Outerwear","Footwear",
            "Accessories","Activewear","Innerwear","Ethnic Wear"
        ]
    }


# ── Startup: warm up data caches ─────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 55)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("  Warming up data caches...")
    try:
        from backend.utils.data_loader import (
            get_customers, get_products, get_transactions
        )
        c = get_customers()
        p = get_products()
        t = get_transactions()
        logger.info(f"  ✓ Customers: {len(c):,}  Products: {len(p):,}  Transactions: {len(t):,}")
    except Exception as e:
        logger.warning(f"  Data warmup failed: {e} — run notebooks first!")
    logger.info("  API ready at http://localhost:8000")
    logger.info("  Docs at      http://localhost:8000/docs")
    logger.info("=" * 55)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
