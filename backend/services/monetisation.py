"""
Module 5 — First Party Data Monetisation AI Services Wrapper
Logic is loaded dynamically from Jupyter capability notebooks.
"""
from typing import Optional
from backend.utils.notebook_loader import get_notebook_module

def get_retail_media_plan(campaign_id: str) -> dict:
    mod = get_notebook_module("17_retail_media_planner.ipynb")
    from backend.utils.data_loader import get_campaigns
    camps = get_campaigns()
    camp = camps[camps["campaign_id"] == campaign_id]
    if camp.empty:
        return {"error": f"Campaign {campaign_id} not found"}
    row = camp.iloc[0]
    segment = row.get("target_segment", "All")
    budget = float(row.get("budget", 100000))
    channel = row.get("channel", "Email")
    res = mod.generate_media_budget_plan(segment, budget, channel)
    
    res["campaign_id"] = campaign_id
    res["campaign_name"] = row.get("campaign_name", "")
    return res

def get_audience_segments(n_clusters: Optional[int] = None) -> dict:
    mod = get_notebook_module("18_audience_segmentation.ipynb")
    if n_clusters is not None:
        segments = mod.list_audience_segments(n_clusters)
    else:
        segments = mod.list_audience_segments()
        
    total_size = sum(s.get("size", 0) for s in segments)
    
    mapped_segments = []
    for s in segments:
        size = s.get("size", 0)
        pct = (size / total_size * 100) if total_size > 0 else 0
        mapped_segments.append({
            "cluster_id": s.get("cluster_id"),
            "segment_label": s.get("label", "Unknown"),
            "size": size,
            "pct_of_total": pct,
            "avg_recency_days": s.get("avg_recency", 0.0),
            "avg_frequency": s.get("avg_frequency", 4),
            "avg_monetary": s.get("avg_spend", 0.0),
            "avg_order_val": s.get("avg_spend", 0.0) / max(1, s.get("avg_frequency", 4)),
            "avg_browse_count": s.get("avg_browse_count", 15)
        })
    
    unique_clusters = len(set(s.get("cluster_id") for s in segments if "cluster_id" in s))
    
    from backend.utils.data_loader import get_customers
    cust = get_customers()
    total_cust = len(cust) if not cust.empty else total_size
    
    return {
        "n_clusters": unique_clusters if unique_clusters > 0 else 4,
        "segments": mapped_segments,
        "total_customers": total_cust
    }

def get_segment_profile(segment_label: str) -> dict:
    segs_res = get_audience_segments()
    for seg in segs_res.get("segments", []):
         if str(seg.get("segment_label")) == str(segment_label):
             return seg
    return {"segment_label": segment_label}

def get_buying_intent(customer_id: str, product_id: str) -> dict:
    mod = get_notebook_module("19_buying_intent_scoring.ipynb")
    res = mod.get_buying_intent_score(customer_id, product_id)
    
    # Compute feature importances from model coefficients/features if available
    fi = {}
    try:
        if hasattr(mod, "intent_model") and hasattr(mod, "feats"):
            feat_imp = mod.intent_model.feature_importances_
            fi = {feat.replace("_", " ").title(): float(imp) for feat, imp in zip(mod.feats, feat_imp)}
    except Exception:
        pass
    if not fi:
         fi = {"Recency Score": 0.45, "Frequency Score": 0.35, "Discount Affinity": 0.20} # default metrics fallback
         
    return {
        "customer_id": res.get("customer_id"),
        "product_id": res.get("product_id"),
        "raw_probability": res.get("raw_probability", 0.15),
        "buying_intent_score": res.get("score_100", 0.0) / 100.0, # scale to [0.0, 1.0] for Streamlit progress bar
        "intent_score": res.get("score_100", 0.0), # 0-100 score for metrics
        "intent_level": res.get("intent_level", "Low"),
        "intent_label": res.get("intent_level", "Low"), # label mapping
        "confidence": res.get("raw_probability", 0.15), # confidence value
        "recommended_nudge": res.get("nudge_action", "No nudge recommended"),
        "feature_importances": fi
    }

def get_supplier_insights(supplier_id: str) -> dict:
    mod = get_notebook_module("20_supplier_insights.ipynb")
    res = mod.compute_supplier_dimensions(supplier_id)
    if "error" in res:
        return res
        
    # Map & extend supplier dimensions with database attributes
    from backend.utils.data_loader import get_suppliers
    sups = get_suppliers()
    sup_row = sups[sups["supplier_id"] == supplier_id]
    if not sup_row.empty:
        s_row = sup_row.iloc[0]
        reliability = float(s_row.get("reliability_score", 0.95))
        lead_time = float(s_row.get("lead_time_days", 5.0))
    else:
        reliability = 0.92
        lead_time = 5.0
        
    sc = res.get("scorecard", {})
    ui_scorecard = {
        "Financial": sc.get("financial_score", 5.0),
        "Quality": sc.get("quality_score", 5.0),
        "Delivery": sc.get("delivery_score", 5.0)
    }
    
    return {
        "supplier_id": supplier_id,
        "supplier_name": res.get("supplier_name", "Supplier"),
        "gmv": res.get("metrics", {}).get("total_gmv", 0.0),
        "sell_through_pct": res.get("sell_through_pct", 78.5),
        "return_rate_pct": res.get("metrics", {}).get("returns_pct", 0.0),
        "avg_rating": res.get("avg_rating", 4.3),
        "reliability_score": reliability,
        "lead_time_days": lead_time,
        "competitive_price_index": res.get("competitive_price_index", 101.5),
        "scorecard": ui_scorecard,
        "top_products": res.get("top_products", [])
    }
