"""
Module 1 — Customer Experience AI Services Wrapper
Logic is loaded dynamically from Jupyter capability notebooks.
"""
from backend.utils.notebook_loader import get_notebook_module

def get_recommendations(customer_id: str, top_n: int = 10) -> list[dict]:
    mod = get_notebook_module("01_personalised_recommendations.ipynb")
    res = mod.get_recommendations(customer_id, top_n=top_n)
    recs = res.get("recommendations", [])

    # Enrich with product brand from products dataset to prevent KeyError: 'brand' in Streamlit Page
    from backend.utils.data_loader import get_products
    prods = get_products()
    brand_map = dict(zip(prods["product_id"], prods["brand"]))
    for r in recs:
        r["brand"] = brand_map.get(r.get("product_id"), "Unknown")
    return recs


def get_recommendations_debug(customer_id: str, top_n: int = 10) -> dict:
    """
    Admin-only diagnostic view of the recommendation engine.
    Re-derives every intermediate quantity (raw CF score, category-boost
    multiplier, popularity fallback score, similar customers used) from the
    same in-memory state the notebook already computed, so internal teams
    can inspect / debug / trust *why* a product was recommended.
    """
    import pandas as pd
    from backend.utils.data_loader import get_products, get_reviews

    mod = get_notebook_module("01_personalised_recommendations.ipynb")
    cust_df, tx_df, prod_df = mod.cust, mod.tx, mod.prod
    matrix, cust_sim_df, category_boost = mod.matrix, mod.cust_sim_df, mod.category_boost

    brand_map = dict(zip(get_products()["product_id"], get_products()["brand"]))
    reviews = get_reviews()
    rating_stats = reviews.groupby("product_id")["rating"].agg(["mean", "count"])
    bestsellers = tx_df.groupby("product_id")["quantity"].sum()

    # ── Customer profile ──────────────────────────────────────────────────────
    profile: dict = {}
    cust_row = cust_df[cust_df["customer_id"] == customer_id]
    if not cust_row.empty:
        row = cust_row.iloc[0]
        profile = {
            "name": row.get("name", customer_id),
            "segment": row.get("segment", "Unknown"),
            "loyalty_tier": row.get("loyalty_tier", "Unknown"),
            "preferred_category": row.get("preferred_category", "Unknown"),
            "region": row.get("region", "Unknown"),
            "city": row.get("city", "Unknown"),
        }
    pref_cat = profile.get("preferred_category")

    # ── Raw purchase history ──────────────────────────────────────────────────
    hist = tx_df[tx_df["customer_id"] == customer_id].merge(
        prod_df[["product_id", "product_name", "category"]], on="product_id", how="left"
    )
    purchase_history = []
    category_affinity = []
    if not hist.empty:
        hist = hist.sort_values("transaction_date", ascending=False)
        hist["brand"] = hist["product_id"].map(brand_map)
        for _, r in hist.iterrows():
            purchase_history.append({
                "transaction_id": r["transaction_id"], "product_id": r["product_id"],
                "product_name": r["product_name"], "category": r["category"],
                "brand": r["brand"], "quantity": int(r["quantity"]),
                "unit_price": float(r["unit_price"]), "final_price": float(r["final_price"]),
                "total_amount": float(r["total_amount"]),
                "transaction_date": str(r["transaction_date"])[:10],
            })

        cat_units = hist.groupby("category")["quantity"].sum().sort_values(ascending=False)
        total_units = float(cat_units.sum()) or 1.0
        category_affinity = [
            {"category": cat, "purchase_pct": round(float(units) / total_units * 100, 1),
             "units_purchased": int(units)}
            for cat, units in cat_units.items()
        ]

    # ── Recommendation breakdown (mirrors notebook ranking logic exactly) ─────
    def _fallback_rows(algo_label: str) -> list[dict]:
        pool = prod_df[prod_df["product_id"].isin(bestsellers.index)].copy()
        pool["rank_score"] = pool["product_id"].map(bestsellers)
        if pref_cat:
            pool = pd.concat([pool[pool["category"] == pref_cat], pool[pool["category"] != pref_cat]])
        pool = pool.drop_duplicates("product_id").head(top_n * 3).nlargest(top_n, "rank_score")
        return [{
            "product_id": r["product_id"], "product_name": r["product_name"], "category": r["category"],
            "brand": brand_map.get(r["product_id"], "Unknown"), "price": float(r["price"]),
            "cf_score": 0.0, "category_boost": 1.0, "popularity_score": float(r["rank_score"]),
            "final_score": round(float(r["rank_score"]), 4),
            "is_personalized": False, "algorithm": algo_label,
        } for _, r in pool.iterrows()]

    similar_customers: list[dict] = []
    if customer_id not in matrix.index:
        algorithm = "Bestseller Fallback — Cold Start (no purchase/cart/wishlist history)"
        recs = _fallback_rows(algorithm)
    else:
        sims = cust_sim_df[customer_id].drop(customer_id).nlargest(20)
        sims = sims[sims > 0]
        if len(sims) == 0:
            algorithm = "Bestseller Fallback — No Similar Shoppers Found"
            recs = _fallback_rows(algorithm)
        else:
            name_map = dict(zip(cust_df["customer_id"], cust_df["name"]))
            similar_customers = [
                {"customer_id": cid, "name": name_map.get(cid, cid), "similarity": round(float(s), 4)}
                for cid, s in sims.head(10).items()
            ]
            already_owned = matrix.columns[matrix.loc[customer_id] > 0]
            candidates = (matrix.loc[sims.index].mul(sims.values, axis=0).sum(axis=0) / sims.sum())
            candidates = candidates.drop(index=already_owned, errors="ignore")

            algorithm = "Collaborative Filtering + Category Boost"
            recs = []
            for pid, raw_score in candidates.nlargest(top_n * 3).items():
                if raw_score <= 0:
                    continue
                p_info = prod_df[prod_df["product_id"] == pid].iloc[0]
                boost = category_boost.get(p_info["category"], 1.0)
                recs.append({
                    "product_id": pid, "product_name": p_info["product_name"], "category": p_info["category"],
                    "brand": brand_map.get(pid, "Unknown"), "price": float(p_info["price"]),
                    "cf_score": round(float(raw_score), 4), "category_boost": round(float(boost), 4),
                    "popularity_score": float(bestsellers.get(pid, 0)),
                    "final_score": round(float(raw_score * boost), 4),
                    "is_personalized": True, "algorithm": algorithm,
                })
            recs = sorted(recs, key=lambda x: x["final_score"], reverse=True)[:top_n]
            if not recs:
                algorithm = "Bestseller Fallback — No Positive CF Candidates"
                recs = _fallback_rows(algorithm)
                similar_customers = []

    for r in recs:
        pid = r["product_id"]
        r["avg_rating"] = round(float(rating_stats["mean"].get(pid, 0.0)), 1)
        r["review_count"] = int(rating_stats["count"].get(pid, 0))

    return {
        "customer_id": customer_id,
        "profile": profile,
        "purchase_history": purchase_history,
        "category_affinity": category_affinity,
        "recommendations": recs,
        "similar_customers": similar_customers,
        "algorithm": algorithm,
    }

def buying_assistant_query(customer_id: str, message: str) -> dict:
    mod = get_notebook_module("02_conversational_buying_assistant.ipynb")
    res = mod.process_chat_message(customer_id, message)
    return {
        "intent": res.get("intent", "browse"),
        "detected_category": res.get("category"),
        "max_price": res.get("price_limit"),
        "response": res.get("response", ""),
        "product_suggestions": res.get("suggestions", []),
    }

def get_next_best_offer(customer_id: str) -> dict:
    mod = get_notebook_module("03_next_best_offer.ipynb")
    res = mod.resolve_nbo(customer_id)
    
    # Map NBO return values to frontend expectations
    opt = res.get("recommended_offer", {})
    disc_str = opt.get("discount", "0%").replace("%", "")
    try:
        disc_pct = float(disc_str)
    except ValueError:
        disc_pct = 0.0
        
    p_type = opt.get("promo_type", "Discount (Product Boost)")
    return {
        "promo_type": p_type,
        "discount_pct": disc_pct,
        "predicted_uplift": float(res.get("uplift_pct", 0.0)),
        "confidence": float(res.get("confidence_score", 0.0)),
        "message": f"Send push notification recommending product {opt.get('product_id')} with {opt.get('discount')} discount."
    }


def get_communication_timing(customer_id: str) -> dict:
    mod = get_notebook_module("04_communication_timing.ipynb")
    res = mod.recommend_communication(customer_id)
    
    # Calculate hourly activity dynamically from notebook variables
    import pandas as pd
    browsing = mod.browsing
    events = browsing[browsing['customer_id'] == customer_id]
    if len(events) > 0:
        hourly_counts = events['hour'].value_counts().to_dict()
        hourly_pct = {str(h): float(count / len(events)) for h, count in hourly_counts.items()}
    else:
        hourly_pct = {str(h): 0.1 for h in range(12, 19)} # default spread fallback
        
    best_h = res.get("best_hour", 17)
    return {
        "best_send_hour_label": f"{best_h:02d}:00",
        "best_day_of_week": res.get("best_day", "Saturday"),
        "recommended_channel": res.get("channel", "Email"),
        "predicted_open_rate": res.get("open_rate", 0.22),
        "hourly_activity": hourly_pct
    }

