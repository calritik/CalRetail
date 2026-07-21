"""
Module 2 — Merchandising Intelligence (Streamlit Page)
Covers: Demand Forecasting, Dynamic Pricing, Promotion Optimisation, Competitor Monitoring
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

st.set_page_config(page_title="Merchandising Intelligence | CalRetail", page_icon="📊", layout="wide")


@st.cache_data(ttl=300)
def load_products():
    data = api_get("/api/v1/merchandising/products", {"limit": 200})
    if not data:
        raise ConnectionError("Backend not responding")
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def load_promos():
    data = api_get("/api/v1/merchandising/promotions", {"limit": 100})
    if not data:
        raise ConnectionError("Backend not responding")
    return pd.DataFrame(data)


try:
    products_df = load_products()
except Exception:
    products_df = pd.DataFrame()

try:
    promos_df   = load_promos()
except Exception:
    promos_df   = pd.DataFrame()

if products_df.empty or promos_df.empty:
    st.warning("⚠️ Backend connection timed out or is not responding. Please check your backend status.")
    if st.button("🔄 Retry Connection", key="retry_conn"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

page_header("Merchandising Intelligence",
            "Demand forecasting, dynamic pricing, promo optimisation & competitor monitoring", "📊")

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Demand Forecast",
    "💲 Dynamic Pricing",
    "🎟️ Promo Optimisation",
    "🕵️ Competitor Monitor",
])

# ─── Tab 1: Demand Forecasting ────────────────────────────────────────────────
with tab1:
    st.subheader("📈 Demand Forecasting")
    st.caption("XGBoost + lag features → N-day daily demand forecast with confidence bands")

    col1, col2 = st.columns([3, 1])
    with col1:
        prod_opts = (dict(zip(products_df["product_id"] + " — " + products_df["product_name"],
                              products_df["product_id"]))
                     if not products_df.empty else {})
        sel = st.selectbox("Select Product", list(prod_opts.keys()), key="fc_prod")
        pid = prod_opts.get(sel, "")
    with col2:
        days = st.slider("Forecast horizon (days)", 7, 90, 30)

    if st.button("🚀 Run Forecast", type="primary"):
        with st.spinner("Running demand model…"):
            result = api_get("/api/v1/merchandising/demand-forecast",
                             {"product_id": pid, "days": days})
        if result:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Forecast", f"{result['total_forecast']:,.0f} units")
            col2.metric("Avg Daily Demand", result["avg_daily_demand"])
            col3.metric("MAPE Estimate", f"{result['mape_estimate']}%")
            col4.metric("Model", result["model"])

            # Historical + forecast chart
            hist = pd.DataFrame(result.get("historical", []))
            fore = pd.DataFrame(result.get("forecast", []))
            fig  = go.Figure()

            if not hist.empty:
                fig.add_trace(go.Scatter(
                    x=hist["date"], y=hist["actual_qty"],
                    mode="lines", name="Actual", line=dict(color="#60a5fa", width=2)
                ))

            if not fore.empty:
                fig.add_trace(go.Scatter(
                    x=fore["date"], y=fore["predicted_qty"],
                    mode="lines", name="Forecast", line=dict(color="#a78bfa", width=2.5)
                ))
                fig.add_trace(go.Scatter(
                    x=pd.concat([fore["date"], fore["date"][::-1]]),
                    y=pd.concat([fore["upper_bound"], fore["lower_bound"][::-1]]),
                    fill="toself", fillcolor="rgba(167,139,250,0.15)",
                    line=dict(color="rgba(255,255,255,0)"),
                    name="Confidence Band"
                ))

            fig.update_layout(title=f"Demand Forecast — {days} Days",
                              template="plotly_dark", height=380, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            if not fore.empty:
                export_button(fore, "demand_forecast.csv")


# ─── Tab 2: Dynamic Pricing ────────────────────────────────────────────────────
with tab2:
    st.subheader("💲 Dynamic Pricing")
    st.caption("AI-computed optimal price using inventory pressure, demand, and competitive gaps")

    prod_opts2 = (dict(zip(products_df["product_id"] + " — " + products_df["product_name"],
                           products_df["product_id"]))
                  if not products_df.empty else {})
    sel2 = st.selectbox("Select Product", list(prod_opts2.keys()), key="dp_prod")
    pid2 = prod_opts2.get(sel2, "")

    if st.button("💡 Compute Optimal Price", type="primary"):
        with st.spinner("Analysing demand, inventory, competition…"):
            result = api_post("/api/v1/merchandising/dynamic-pricing",
                              {"product_id": pid2})
        if result and "error" not in result:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Current Price",     f"₹{result['current_price']:,.2f}")
            col2.metric("Recommended Price",
                        f"₹{result['recommended_price']:,.2f}",
                        delta=f"{result['price_delta_pct']:+.1f}%")
            col3.metric("Floor Price",       f"₹{result['floor_price']:,.2f}")
            col4.metric("Est. Revenue Lift", f"{result['expected_revenue_lift_pct']:+.2f}%")

            st.info(f"💡 **Rationale:** {result['rationale']}")

            # Pricing comparison bar
            fig = go.Figure(go.Bar(
                x=["Our Price", "Recommended", "Avg Competitor", "Min Competitor"],
                y=[result["current_price"], result["recommended_price"],
                   result["avg_competitor_price"], result["min_competitor_price"]],
                marker_color=["#60a5fa","#34d399","#f59e0b","#f87171"],
            ))
            fig.update_layout(title="Price Comparison", template="plotly_dark", height=300)
            st.plotly_chart(fig, use_container_width=True)
            st.json(result)


# ─── Tab 3: Promotion Optimisation ────────────────────────────────────────────
with tab3:
    st.subheader("🎟️ Promotion Optimisation")
    st.caption("Uplift estimation + cannibalization modelling per promotion")

    promo_opts = (dict(zip(promos_df["promo_id"] + " — " + promos_df["promo_type"],
                           promos_df["promo_id"]))
                  if not promos_df.empty else {})
    sel_promo = st.selectbox("Select Promotion", list(promo_opts.keys()), key="promo_sel")
    promo_id = promo_opts.get(sel_promo, "")

    if st.button("📐 Analyse Promotion", type="primary"):
        with st.spinner("Computing uplift…"):
            result = api_get("/api/v1/merchandising/promotion-optimization",
                             {"promo_id": promo_id})
        if result and "error" not in result:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Incremental Revenue", f"₹{result['incremental_revenue']:,.0f}")
            col2.metric("Uplift %",            f"{result['uplift_pct']:+.1f}%")
            col3.metric("Cannibalization",     f"{result['cannibalization_rate']*100:.1f}%")
            col4.metric("Confidence",          f"{result['confidence']*100:.1f}%")

            fig = go.Figure(go.Bar(
                x=["Control Revenue","Treated Revenue","Incremental"],
                y=[result["control_revenue"], result["treated_revenue"], result["incremental_revenue"]],
                marker_color=["#60a5fa","#34d399","#a78bfa"]
            ))
            fig.update_layout(title="Promotion Revenue Impact", template="plotly_dark", height=280)
            st.plotly_chart(fig, use_container_width=True)
            st.json(result)


# ─── Tab 4: Competitor Monitoring ─────────────────────────────────────────────
with tab4:
    st.subheader("🕵️ Competitor Price Monitoring")
    st.caption("Real-time alerts when competitors significantly undercut or you can raise prices")

    col1, col2 = st.columns(2)
    with col1:
        cat_filter = st.selectbox("Category Filter (optional)",
                                  [""] + list(products_df["category"].unique() if not products_df.empty else []))
    with col2:
        show_alerts_only = st.checkbox("Show alerts only", value=True)

    if st.button("🔍 Scan Competitor Prices", type="primary"):
        with st.spinner("Scanning competitor pricing data…"):
            params = {}
            if cat_filter:
                params["category"] = cat_filter
            result = api_get("/api/v1/merchandising/competitor-monitoring", params)

        if result:
            data = result.get("results", result) if isinstance(result, dict) else result
            if not data:
                st.info("No competitor data found for the given filters.")
            else:
                df = pd.DataFrame(data)
                if show_alerts_only and "alert_flag" in df.columns:
                    df = df[df["alert_flag"] == True]

                st.metric("Products with Alerts", int(df["alert_flag"].sum()) if "alert_flag" in df.columns else len(df))

                if not df.empty:
                    fig = px.scatter(df, x="our_price", y="avg_competitor_price",
                                     color="price_gap_pct", hover_data=["product_name"],
                                     title="Our Price vs Avg Competitor Price",
                                     color_continuous_scale="RdYlGn",
                                     template="plotly_dark", height=380)
                    fig.add_shape(type="line", x0=0, y0=0,
                                  x1=df["our_price"].max(), y1=df["our_price"].max(),
                                  line=dict(color="white", dash="dash"))
                    st.plotly_chart(fig, use_container_width=True)

                    cols_show = ["product_name","category","our_price","avg_competitor_price",
                                 "price_gap_pct","recommended_action"]
                    cols_show = [c for c in cols_show if c in df.columns]
                    st.dataframe(df[cols_show], use_container_width=True, hide_index=True)
                    export_button(df, "competitor_price_alerts.csv")
