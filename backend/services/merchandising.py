"""
Module 2 — Merchandising Intelligence AI Services Wrapper
Logic is loaded dynamically from Jupyter capability notebooks.
"""
from backend.utils.notebook_loader import get_notebook_module

def forecast_demand(product_id: str, days: int = 7) -> dict:
    mod = get_notebook_module("05_demand_forecasting.ipynb")
    res = mod.get_demand_forecast(product_id, forecast_days=days)

    if not isinstance(res, dict):
        res = {}

    import datetime
    import numpy as np

    forecast_list = res.get("forecast", [])
    historical_list = res.get("historical", [])

    # Anchor forecast dates the day *after* the product's real last sale date
    # (from the notebook's historical series) so the chart is continuous —
    # falls back to today only when there's no sales history at all.
    if historical_list:
        anchor = datetime.date.fromisoformat(historical_list[-1]["date"])
    else:
        anchor = datetime.date.today()

    mapped_forecast = []
    total_forecast = 0.0
    for item in forecast_list:
        day_idx = item.get("day", 1)
        qty = float(item.get("forecast_qty", 0.0))
        total_forecast += qty
        date_str = str(anchor + datetime.timedelta(days=day_idx))

        # Confidence band from the model's own real held-out error (MAPE),
        # not an arbitrary guess.
        mape_frac = float(res.get("mape", 15.0)) / 100.0
        std_err = max(mape_frac * qty, 0.5)
        mapped_forecast.append({
            "date": date_str,
            "predicted_qty": qty,
            "upper_bound": round(qty + 1.96 * std_err, 1),
            "lower_bound": round(max(0.0, qty - 1.96 * std_err), 1)
        })

    mape = res.get("mape", 15.0)
    if hasattr(mape, "item"):
        mape = mape.item()
    mape = float(mape)

    return {
        "product_id": product_id,
        "total_forecast": round(total_forecast, 1),
        "avg_daily_demand": round(total_forecast / max(1, days), 2),
        "mape_estimate": round(mape, 2),
        "model": res.get("model", "XGBoost (Global Multi-Product Regressor)"),
        "forecast": mapped_forecast,
        "historical": historical_list
    }

def get_dynamic_price(product_id: str, store_id: str = None) -> dict:
    mod = get_notebook_module("06_dynamic_pricing.ipynb")
    res = mod.recommend_dynamic_price(product_id)
    
    if not isinstance(res, dict):
        res = {}
    if "error" in res:
        return res
        
    current_price = float(res.get("current_price", 0.0))
    recommended_price = float(res.get("recommended_price", current_price))
    
    price_delta_pct = 0.0
    if current_price > 0.0:
        price_delta_pct = ((recommended_price - current_price) / current_price) * 100.0
        
    floor_price = current_price * 0.75
    rationale = res.get("inventory_nudge", "Stock level stable. Pricing aligned with competitor average.")
    avg_competitor_price = float(res.get("competitor_avg", current_price))
    
    # Calculate min competitor price dynamically
    try:
        cust_pr = mod.cust_pr
        comp_matches = cust_pr[cust_pr['product_id'] == product_id]
        if not comp_matches.empty:
            min_competitor_price = float(comp_matches['price'].min())
        else:
            min_competitor_price = avg_competitor_price * 0.92
    except Exception:
        min_competitor_price = avg_competitor_price * 0.92
        
    expected_revenue_lift_pct = float(res.get("est_revenue_lift_pct", 0.0))
    
    return {
        "product_id": product_id,
        "product_name": res.get("product_name", ""),
        "current_price": round(current_price, 2),
        "recommended_price": round(recommended_price, 2),
        "price_delta_pct": round(price_delta_pct, 2),
        "floor_price": round(floor_price, 2),
        "expected_revenue_lift_pct": round(expected_revenue_lift_pct, 2),
        "rationale": rationale,
        "avg_competitor_price": round(avg_competitor_price, 2),
        "min_competitor_price": round(min_competitor_price, 2),
        "stock_level": int(res.get("stock_level", 0))
    }

def optimise_promotion(promo_id: str) -> dict:
    mod = get_notebook_module("07_promotion_optimization.ipynb")
    res = mod.analyze_promo_performance(promo_id)
    
    if not isinstance(res, dict):
        res = {}
    if "error" in res:
        return res
        
    control_revenue = float(res.get("baseline_revenue", 0.0))
    treated_revenue = float(res.get("promo_revenue", 0.0))
    incremental_revenue = float(res.get("incremental_uplift_value", 0.0))
    
    # Compute uplift_pct which stream lit app metrics display
    uplift_pct = 0.0
    if control_revenue > 0.0:
        uplift_pct = ((treated_revenue - control_revenue) / control_revenue) * 100.0
        
    # Cannibalization rate (from percentage to fraction: cannibalization_rate_pct / 100)
    cannibalization_pct = float(res.get("cannibalization_rate_pct", 0.0))
    cannibalization_rate = cannibalization_pct / 100.0
    
    confidence = float(res.get("confidence_level", 0.92))
    
    return {
        "promo_id": promo_id,
        "product_id": res.get("product_id", ""),
        "control_revenue": round(control_revenue, 2),
        "treated_revenue": round(treated_revenue, 2),
        "incremental_revenue": round(incremental_revenue, 2),
        "uplift_pct": round(uplift_pct, 2),
        "cannibalization_rate": round(cannibalization_rate, 4),
        "confidence": round(confidence, 2)
    }

def monitor_competitor_prices(product_id: str = None, category: str = None) -> list[dict]:
    mod = get_notebook_module("08_competitor_price_monitoring.ipynb")
    res = mod.detect_pricing_outliers()
    
    if not isinstance(res, list):
        if isinstance(res, dict) and "alerts" in res:
            res = res["alerts"]
        elif isinstance(res, dict) and "outliers" in res:
            res = res["outliers"]
        else:
            res = []
            
    # Get categories to populate "category"
    categories_map = {}
    try:
        prod_df = mod.prod
        categories_map = dict(zip(prod_df["product_id"], prod_df["category"]))
    except Exception:
        pass
        
    processed_results = []
    for item in res:
        pid = item.get("product_id")
        pcat = categories_map.get(pid, item.get("category", "General"))
        
        # Filter by product_id
        if product_id and pid != product_id:
            continue
            
        # Filter by category
        if category and pcat != category:
            continue
            
        our_price = float(item.get("our_price", 0.0))
        competitor_mean = float(item.get("competitor_mean", 0.0))
        gap_pct = float(item.get("gap_pct", 0.0))
        
        action = item.get("recommended_action", "Maintain current pricing")
        alert_flag = "Maintain" not in action
        
        processed_results.append({
            "product_id": pid,
            "product_name": item.get("product_name", ""),
            "category": pcat,
            "our_price": our_price,
            "avg_competitor_price": competitor_mean,
            "price_gap_pct": gap_pct,
            "z_score": float(item.get("z_score", 0.0)),
            "status": item.get("status", ""),
            "recommended_action": action,
            "alert_flag": alert_flag
        })
        
    return processed_results

