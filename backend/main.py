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
from backend.routers.ops_support_monetise import ops_router, support_router
from backend.routers.overview import router as overview_router
from backend.utils.logger import logger

# ── App init ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Enterprise Retail AI Intelligence Platform — 16 AI capabilities "
        "across 4 business domains."
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

app.include_router(overview_router)
app.include_router(ce_router)
app.include_router(merch_router)
app.include_router(ops_router)
app.include_router(support_router)


# ── Root & health ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "platform": settings.APP_NAME,
        "version":  settings.APP_VERSION,
        "status":   "running",
        "domains": [
            "Customer Experience",
            "Merchandising Intelligence",
            "Operational Excellence",
            "Customer Support Intelligence",
        ],
        "total_ai_capabilities": 16,
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
    import asyncio
    import threading

    logger.info("=" * 55)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("  Warming up data caches...")
    from backend.utils import db

    if not db.database_exists():
        # Worth shouting about: without the database every capability falls back
        # to an empty frame and the console looks merely "wrong" rather than
        # unconfigured, which is a slow thing to diagnose from the UI alone.
        logger.error("  ✗ No database at %s", db.DB_PATH)
        logger.error("    Build it with:  python -m notebooks.build_db")
    else:
        try:
            from backend.utils.data_loader import (
                get_customers, get_products, get_transactions
            )
            c = get_customers()
            p = get_products()
            t = get_transactions()
            logger.info(f"  ✓ Customers: {len(c):,}  Products: {len(p):,}  Transactions: {len(t):,}")
            logger.info(f"  ✓ Database: {db.DB_PATH.name} "
                        f"({db.DB_PATH.stat().st_size / 1_048_576:.1f} MB, "
                        f"{len(db.table_names())} tables)")
        except Exception as e:
            logger.warning(f"  Data warmup failed: {e}")

    # Pre-load Module 2 notebooks in the background so the first page visit
    # doesn't block on notebook execution (which can take 10-30 s each).
    def _warm_merch_notebooks():
        from backend.utils.notebook_loader import get_notebook_module
        notebooks = [
            "05_demand_forecasting.ipynb",
            "06_dynamic_pricing.ipynb",
            "07_promotion_optimization.ipynb",
            "08_competitor_price_monitoring.ipynb",
        ]
        for nb in notebooks:
            try:
                get_notebook_module(nb)
                logger.info(f"  ✓ Notebook warm: {nb}")
            except Exception as exc:
                logger.warning(f"  ✗ Notebook warm failed ({nb}): {exc}")

    threading.Thread(target=_warm_merch_notebooks, daemon=True, name="merch-warmup").start()
    logger.info("  Notebook pre-loader started in background thread.")
    logger.info("  API ready at http://localhost:8000")
    logger.info("  Docs at      http://localhost:8000/docs")
    logger.info("=" * 55)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
