"""
Module 1 — Customer Experience Router
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.services.customer_experience import (
    get_recommendations, buying_assistant_query,
    get_next_best_offer, get_communication_timing,
    get_recommendations_debug,
)

router = APIRouter(prefix="/api/v1/customer-experience", tags=["Customer Experience"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class RecommendRequest(BaseModel):
    customer_id: str
    top_n: int = 10

class AssistantRequest(BaseModel):
    customer_id: str
    message: str
    session_id: str = "default"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/recommendations")
def recommendations(req: RecommendRequest):
    """Get top-N personalised product recommendations for a customer."""
    result = get_recommendations(req.customer_id, req.top_n)
    return {"customer_id": req.customer_id, "recommendations": result, "count": len(result)}


@router.get("/recommendations/debug")
def recommendations_debug(customer_id: str = Query(...), top_n: int = Query(10, le=50)):
    """Admin-only: full internal breakdown of the recommendation engine for a customer
    (sub-scores, similar customers, purchase history, category affinity)."""
    return get_recommendations_debug(customer_id, top_n)


@router.post("/buying-assistant")
def buying_assistant(req: AssistantRequest):
    """Conversational buying assistant — parse intent and suggest products."""
    return buying_assistant_query(req.customer_id, req.message)


@router.get("/next-best-offer")
def next_best_offer(customer_id: str = Query(..., description="Customer ID")):
    """Get the single best promotional offer for a customer right now."""
    result = get_next_best_offer(customer_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/communication-timing")
def communication_timing(customer_id: str = Query(...)):
    """Predict the best send time and channel for customer communications."""
    result = get_communication_timing(customer_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/customers")
def list_customers(limit: int = Query(50, le=500)):
    """List available customer IDs for UI dropdowns."""
    from backend.utils.data_loader import get_customers
    df = get_customers()
    sample = df[["customer_id","name","segment","city","loyalty_tier"]].head(limit)
    return sample.to_dict(orient="records")
