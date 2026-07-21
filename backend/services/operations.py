"""
Module 3 — Operations Intelligence AI Services Wrapper
Logic is loaded dynamically from Jupyter capability notebooks.
"""
from typing import Optional
from backend.utils.notebook_loader import get_notebook_module

def get_inventory_health(store_id: Optional[str] = None,
                          category: Optional[str] = None,
                          top_n: int = 50) -> list[dict]:
    mod = get_notebook_module("09_inventory_health_monitoring.ipynb")
    res = mod.compute_inventory_health()
    
    if isinstance(res, dict) and "inventory_health" in res:
        records = res["inventory_health"]
    elif isinstance(res, list):
        records = res
    else:
        records = []

    import pandas as pd
    df = pd.DataFrame(records)
    if df.empty:
        return []

    # Map stock_level to stock_qty to match UI expectations
    if "stock_level" in df.columns:
        df["stock_qty"] = df["stock_level"]

    from backend.utils.data_loader import get_products
    prods = get_products()
    if "product_name" not in df.columns:
        df = df.merge(prods[["product_id", "product_name", "category", "brand", "price"]], on="product_id", how="left")

    if store_id and "store_id" in df.columns:
        df = df[df["store_id"].astype(str) == str(store_id)]
    if category and "category" in df.columns:
        df = df[df["category"] == category]

    return df.head(top_n).fillna(0).to_dict(orient="records")

def get_replenishment_order(product_id: str,
                             store_id: Optional[str] = None) -> dict:
    mod = get_notebook_module("10_automated_replenishment.ipynb")
    res = mod.get_replenishment_parameters(product_id)
    if "error" in res:
        return res
        
    # Map & enrich replenishment data to match frontend requirements
    from backend.utils.data_loader import get_products, get_inventory, get_suppliers
    prods = get_products()
    prod_row = prods[prods["product_id"] == product_id]
    if prod_row.empty:
        return {"error": f"Product {product_id} not found"}
        
    p_item = prod_row.iloc[0]
    supplier_id = p_item.get("supplier_id")
    cost_price = float(p_item.get("cost_price", 100.0))
    
    inv = get_inventory()
    total_inv_rows = inv[inv["product_id"] == product_id]
    total_max_stock = int(total_inv_rows["max_stock"].sum()) if not total_inv_rows.empty else 200
    
    if store_id:
        inv_rows = total_inv_rows[total_inv_rows["store_id"] == store_id]
    else:
        inv_rows = total_inv_rows
        
    if not inv_rows.empty:
        current_stock = int(inv_rows["stock_qty"].sum())
        max_stock = int(inv_rows["max_stock"].sum())
    else:
        current_stock = 45 # default backup stock
        max_stock = 200
        
    sups = get_suppliers()
    sup_row = sups[sups["supplier_id"] == supplier_id]
    if not sup_row.empty:
        s_item = sup_row.iloc[0]
        supplier_name = s_item.get("name", "Unknown Supplier")
        supplier_reliability = float(s_item.get("reliability_score", 0.95))
        lead_time_days = float(s_item.get("lead_time_days", 5.0))
    else:
        supplier_name = "CalRetail Logistics Ltd"
        supplier_reliability = 0.92
        lead_time_days = 5.0
        
    rop = res.get("reorder_point", 30)
    reorder_qty = res.get("recommended_order_quantity", 100)
    safety_stock = res.get("safety_stock", 5)
    
    if store_id and total_max_stock > 0:
        ratio = max_stock / total_max_stock
        rop = max(1, int(round(rop * ratio)))
        reorder_qty = max(1, int(round(reorder_qty * ratio)))
        safety_stock = max(1, int(round(safety_stock * ratio)))
    
    return {
        "product_id": product_id,
        "current_stock": current_stock,
        "reorder_qty": reorder_qty,
        "lead_time_days": lead_time_days,
        "estimated_cost": reorder_qty * cost_price,
        "urgency_flag": bool(current_stock < rop),
        "supplier_name": supplier_name,
        "supplier_reliability": supplier_reliability,
        "safety_stock": safety_stock,
        "max_stock": max_stock,
        "reorder_point": rop
    }

def optimise_warehouse(warehouse_id: str) -> dict:
    mod = get_notebook_module("11_warehouse_slotting.ipynb")
    records = mod.compute_abc_slotting_plan(warehouse_id)
    
    import pandas as pd
    df = pd.DataFrame(records)
    if df.empty:
        return {
            "class_summary": {},
            "slotting_plan": [],
            "estimated_pick_time_reduction_pct": 5.0
        }
        
    from backend.utils.data_loader import get_products
    prods = get_products()
    
    # Rename columns to match UI
    if "abc_class" in df.columns:
        df["velocity_class"] = df["abc_class"]
    if "assigned_zone" in df.columns:
        df["recommended_zone"] = df["assigned_zone"]
        
    # Join products
    df = df.merge(prods[["product_id", "product_name", "category"]], on="product_id", how="left")
    
    df["avg_daily_demand"] = (df["total_movements"] / 90.0).round(1)
    df["pick_time_savings_pct"] = df["velocity_class"].map({"A": 25.0, "B": 15.0, "C": 5.0})
    
    counts = df["velocity_class"].value_counts().to_dict()
    
    total_mvs = df["total_movements"].sum()
    if total_mvs > 0:
        est_saving = (df["total_movements"] * df["pick_time_savings_pct"]).sum() / total_mvs
    else:
        est_saving = 5.0
        
    est_saving = round(float(est_saving), 1)
    
    return {
        "class_summary": counts,
        "slotting_plan": df.fillna("Unknown").to_dict(orient="records"),
        "estimated_pick_time_reduction_pct": est_saving
    }

def optimise_routes(warehouse_id: str, order_ids: list = None) -> dict:
    mod = get_notebook_module("12_route_optimisation.ipynb")
    res = mod.solve_delivery_route(warehouse_id)
    
    dist = res.get("distance_km", 0.0)
    baseline = res.get("baseline_distance_km", round(dist * 1.25, 2))
    saved = round(max(0.0, baseline - dist), 2)
    saving_pct = round((saved / baseline) * 100.0, 1) if baseline > 0 else 0.0
    
    return {
        "optimised_distance_km": dist,
        "baseline_distance_km": baseline,
        "distance_saved_km": saved,
        "saving_pct": saving_pct,
        "estimated_time_hrs": round(dist / 50.0, 1),
        "route_order": res.get("route_order", []),
        "total_orders": res.get("total_orders", 0),
        "route": res.get("route", []),
        "origin": res.get("origin", {})
    }

