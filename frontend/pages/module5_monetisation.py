"""
Module 5 — First Party Data Monetisation (Streamlit Page)
"""
import sys
from pathlib import Path
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.components.utils import api_get, api_post, page_header, export_button

st.set_page_config(page_title="Data Monetisation | CalRetail", page_icon="💰", layout="wide")


@st.cache_data(ttl=300)
def load_campaigns():
    data = api_get("/api/v1/monetization/campaigns", {"limit": 100})
    if not data:
        raise ConnectionError("Backend not responding")
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def load_suppliers():
    data = api_get("/api/v1/monetization/suppliers", {"limit": 100})
    if not data:
        raise ConnectionError("Backend not responding")
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def load_customers():
    data = api_get("/api/v1/customer-experience/customers", {"limit": 200})
    if not data:
        raise ConnectionError("Backend not responding")
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def load_products():
    data = api_get("/api/v1/merchandising/products", {"limit": 200})
    if not data:
        raise ConnectionError("Backend not responding")
    return pd.DataFrame(data)


try:
    campaigns_df  = load_campaigns()
except Exception:
    campaigns_df  = pd.DataFrame()

try:
    suppliers_df  = load_suppliers()
except Exception:
    suppliers_df  = pd.DataFrame()

try:
    customers_df  = load_customers()
except Exception:
    customers_df  = pd.DataFrame()

try:
    products_df   = load_products()
except Exception:
    products_df   = pd.DataFrame()

if campaigns_df.empty or suppliers_df.empty or customers_df.empty or products_df.empty:
    st.warning("⚠️ Backend connection timed out or is not responding. Please check your backend status.")
    if st.button("🔄 Retry Connection", key="retry_conn"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

customer_opts = (dict(zip(customers_df["customer_id"] + " — " + customers_df["name"],
                          customers_df["customer_id"])) if not customers_df.empty else {})
prod_opts     = (dict(zip(products_df["product_id"] + " — " + products_df["product_name"],
                          products_df["product_id"])) if not products_df.empty else {})

page_header("First Party Data Monetisation",
            "Retail media, audience intelligence, buying intent & supplier insights", "💰")

tab1, tab2, tab3, tab4 = st.tabs([
    "📺 Retail Media",
    "🧩 Audience Segments",
    "🎯 Buying Intent",
    "🏢 Supplier Insights",
])

# ─── Tab 1: Retail Media ──────────────────────────────────────────────────────
with tab1:
    st.subheader("📺 Retail Media Network Planner")
    st.caption("Match campaigns to audiences and predict CTR, CVR, ROAS")

    camp_opts = (dict(zip(campaigns_df["campaign_id"] + " — " + campaigns_df["campaign_name"],
                          campaigns_df["campaign_id"])) if not campaigns_df.empty else {})
    sel = st.selectbox("Select Campaign", list(camp_opts.keys()))
    cid = camp_opts.get(sel, "")

    with st.spinner("Computing audience match and predicted metrics…"):
        result = api_get("/api/v1/monetization/retail-media", {"campaign_id": cid})
    if result and "error" not in result:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Audience Size",   f"{result.get('matched_audience_size',0):,}")
        c2.metric("Predicted CTR",   f"{result.get('predicted_ctr',0):.2f}%")
        c3.metric("Predicted CVR",   f"{result.get('predicted_cvr',0):.2f}%")
        c4.metric("Predicted ROAS",  f"{result.get('predicted_roas',0):.2f}×")

        st.info(f"📍 **Placement:** {result.get('recommended_placement','—')}")
        st.caption(f"Channel: **{result.get('channel','—')}** | Segment: **{result.get('target_segment','—')}**")

        funnel = pd.DataFrame({
            "Stage":  ["Impressions","Clicks","Conversions"],
            "Volume": [result.get("estimated_impressions",0),
                       result.get("estimated_clicks",0),
                       result.get("estimated_conversions",0)]
        })
        fig = px.funnel(funnel, x="Volume", y="Stage", title="Campaign Funnel Forecast",
                        template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)


# ─── Tab 2: Audience Segmentation ────────────────────────────────────────────
with tab2:
    st.subheader("🧩 First Party Audience Segmentation")
    st.caption("K-Means clustering on RFM + browsing behaviour features")

    n_clusters = st.slider("Number of segments", 4, 12, 8)

    with st.spinner("Running K-Means clustering…"):
        result = api_get("/api/v1/monetization/audience-segments", {"n_clusters": n_clusters})
    if result:
        st.metric("Total Customers", f"{result.get('total_customers',0):,}")
        segs = pd.DataFrame(result.get("segments", []))
        if not segs.empty:
            fig = px.treemap(segs, path=["segment_label"],
                             values="size",
                             color="avg_monetary" if "avg_monetary" in segs.columns else "size",
                             color_continuous_scale="Blues",
                             title="Audience Segment Tree Map",
                             template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Segment Profiles")
            view_cols = [c for c in ["cluster_id","segment_label","size","pct_of_total",
                                      "avg_recency_days","avg_frequency","avg_monetary",
                                      "avg_order_val","avg_browse_count"] if c in segs.columns]
            st.dataframe(segs[view_cols], use_container_width=True, hide_index=True)
            export_button(segs, "audience_segments.csv")


# ─── Tab 3: Buying Intent ─────────────────────────────────────────────────────
with tab3:
    st.subheader("🎯 Buying Intent Intelligence")
    st.caption("Gradient Boosting model scores purchase probability for customer × product pair")

    col1, col2 = st.columns(2)
    with col1:
        sel_c = st.selectbox("Select Customer", list(customer_opts.keys()), key="intent_cust")
        cid3  = customer_opts.get(sel_c, "")
    with col2:
        sel_p = st.selectbox("Select Product", list(prod_opts.keys()), key="intent_prod")
        pid3  = prod_opts.get(sel_p, "")

    with st.spinner("Scoring intent…"):
        result = api_post("/api/v1/monetization/buying-intent",
                          {"customer_id": cid3, "product_id": pid3})
    if result:
        c1,c2,c3 = st.columns(3)
        c1.metric("Intent Score",  f"{result.get('intent_score',0):.1f} / 100")
        c2.metric("Intent Level",  result.get("intent_label","—"))
        c3.metric("Confidence",    f"{result.get('confidence',0)*100:.1f}%")

        score = result.get("intent_score", 0) / 100
        color = "green" if score > 0.6 else "orange" if score > 0.35 else "red"
        st.progress(score)
        st.info(f"💡 **Recommended Nudge:** {result.get('recommended_nudge','—')}")

        # Feature importances
        fi = result.get("feature_importances", {})
        if fi:
            fi_df = pd.DataFrame(list(fi.items()), columns=["Feature","Importance"]).sort_values(
                "Importance", ascending=True)
            fig = px.bar(fi_df, x="Importance", y="Feature", orientation="h",
                         title="Feature Importance", template="plotly_dark", height=250)
            st.plotly_chart(fig, use_container_width=True)


# ─── Tab 4: Supplier Insights ─────────────────────────────────────────────────
with tab4:
    st.subheader("🏢 Supplier Insight Dashboard")
    st.caption("Full supplier scorecard: GMV, sell-through, returns, ratings, price competitive index")

    sup_opts = (dict(zip(suppliers_df["supplier_id"] + " — " + suppliers_df["name"],
                         suppliers_df["supplier_id"])) if not suppliers_df.empty else {})
    sel_s = st.selectbox("Select Supplier", list(sup_opts.keys()))
    sid   = sup_opts.get(sel_s, "")

    with st.spinner("Computing supplier scorecard…"):
        result = api_get("/api/v1/monetization/supplier-insights", {"supplier_id": sid})
    if result and "error" not in result:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("GMV",               f"₹{result.get('gmv',0):,.0f}")
        c2.metric("Sell-Through",      f"{result.get('sell_through_pct',0):.1f}%")
        c3.metric("Return Rate",       f"{result.get('return_rate_pct',0):.2f}%")
        c4.metric("Avg Rating",        result.get("avg_rating",0))

        c1,c2,c3 = st.columns(3)
        c1.metric("Reliability",       f"{result.get('reliability_score',0)*100:.1f}%")
        c2.metric("Lead Time",         f"{result.get('lead_time_days','—')} days")
        c3.metric("Price Comp. Index", f"{result.get('competitive_price_index',100):.1f}")

        # Scorecard radar
        sc = result.get("scorecard", {})
        if sc:
            categories = list(sc.keys())
            values     = [max(0, v) for v in sc.values()]
            fig = go.Figure(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor="rgba(99,102,241,0.2)",
                line=dict(color="#818cf8")
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0,10])),
                title="Supplier Scorecard",
                template="plotly_dark",
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)

        # Top products
        top_prods = pd.DataFrame(result.get("top_products", []))
        if not top_prods.empty:
            st.subheader("🏆 Top Products by Revenue")
            view = [c for c in ["product_name","category","total_amount"] if c in top_prods.columns]
            st.dataframe(top_prods[view], use_container_width=True, hide_index=True)
