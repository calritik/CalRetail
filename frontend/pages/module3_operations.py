"""
Module 3 — Operational Excellence (Streamlit Page)
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

st.set_page_config(page_title="Operational Excellence | CalRetail", page_icon="⚙️", layout="wide")


@st.cache_data(ttl=300)
def load_stores():
    data = api_get("/api/v1/operations/stores", {"limit": 100})
    if not data:
        raise ConnectionError("Backend not responding")
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def load_warehouses():
    data = api_get("/api/v1/operations/warehouses")
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
    stores_df     = load_stores()
except Exception:
    stores_df     = pd.DataFrame()

try:
    warehouses_df = load_warehouses()
except Exception:
    warehouses_df = pd.DataFrame()

try:
    products_df   = load_products()
except Exception:
    products_df   = pd.DataFrame()

if stores_df.empty or warehouses_df.empty or products_df.empty:
    st.warning("⚠️ Backend connection timed out or is not responding. Please check your backend status.")
    if st.button("🔄 Retry Connection", key="retry_conn"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

page_header("Operational Excellence", "Smart inventory, automated replenishment, warehouse & route optimisation", "⚙️")

tab1, tab2, tab3, tab4 = st.tabs([
    "📦 Inventory Health",
    "🔄 Replenishment",
    "🏭 Warehouse Optimisation",
    "🗺️ Route Optimisation",
])

with tab1:
    st.subheader("📦 Inventory Health Dashboard")
    col1, col2, col3 = st.columns(3)
    store_opts = ["All"] + (stores_df["store_id"].tolist() if not stores_df.empty else [])
    cat_opts   = ["All"] + (products_df["category"].unique().tolist() if not products_df.empty else [])
    with col1:
        store_sel = st.selectbox("Store", store_opts)
    with col2:
        cat_sel = st.selectbox("Category", cat_opts)
    with col3:
        top_n = st.slider("Top N products", 20, 200, 50)

    params = {"top_n": top_n}
    if store_sel != "All": params["store_id"] = store_sel
    if cat_sel != "All":   params["category"]  = cat_sel

    with st.spinner("Loading inventory data…"):
        result = api_get("/api/v1/operations/inventory-health", params)
    if result:
        data = result.get("results", result) if isinstance(result, dict) else result
        df = pd.DataFrame(data)
        if not df.empty:
            # KPI row
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total SKUs",  len(df))
            c2.metric("Stockout Risk", int((df["stockout_risk"] > 0.7).sum()) if "stockout_risk" in df.columns else "—")
            c3.metric("Overstock",   int(df["overstock_flag"].sum()) if "overstock_flag" in df.columns else "—")
            c4.metric("Avg Health",  f"{df['health_score'].mean():.2f}" if "health_score" in df.columns else "—")

            # Risk distribution
            if "risk_label" in df.columns:
                risk_dist = df["risk_label"].value_counts().reset_index()
                risk_dist.columns = ["risk","count"]
                fig = px.pie(risk_dist, names="risk", values="count",
                             title="Inventory Risk Distribution",
                             color_discrete_sequence=["#34d399","#fbbf24","#f87171"],
                             template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

            view_cols = [c for c in ["product_name","category","stock_qty","days_cover",
                                      "health_score","risk_label","stockout_risk"] if c in df.columns]
            st.dataframe(df[view_cols], use_container_width=True, hide_index=True)
            export_button(df, "inventory_health.csv")


with tab2:
    st.subheader("🔄 Automated Replenishment")
    prod_opts = (dict(zip(products_df["product_id"] + " — " + products_df["product_name"],
                          products_df["product_id"])) if not products_df.empty else {})
    sel = st.selectbox("Select Product", list(prod_opts.keys()), key="rep_prod")
    pid = prod_opts.get(sel, "")

    with st.spinner("Computing optimal order…"):
        result = api_post("/api/v1/operations/replenishment", {"product_id": pid})
    if result and "error" not in result:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Current Stock", result.get("current_stock","—"))
        c2.metric("Reorder Qty",   result.get("reorder_qty","—"))
        c3.metric("Lead Time",     f"{result.get('lead_time_days','—')} days")
        c4.metric("Estimated Cost", f"₹{result.get('estimated_cost',0):,.0f}")

        if result.get("urgency_flag"):
            st.error("🚨 URGENT ORDER REQUIRED — Stock below reorder point!")
        else:
            st.success("✅ Stock levels acceptable — order planned for replenishment cycle")

        col1, col2 = st.columns(2)
        col1.write(f"**Supplier:** {result.get('supplier_name','—')}")
        col1.write(f"**Reliability:** {result.get('supplier_reliability',0)*100:.1f}%")
        col2.write(f"**Safety Stock:** {result.get('safety_stock','—')}")
        col2.write(f"**Max Stock:**    {result.get('max_stock','—')}")

        # Stock gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=result.get("current_stock",0),
            domain={"x":[0,1],"y":[0,1]},
            title={"text":"Current Stock Level"},
            gauge={
                "axis":{"range":[0, result.get("max_stock",200)]},
                "bar":{"color":"#60a5fa"},
                "steps":[
                    {"range":[0, result.get("reorder_point",30)], "color":"#dc2626"},
                    {"range":[result.get("reorder_point",30), result.get("max_stock",200)*0.75], "color":"#d97706"},
                    {"range":[result.get("max_stock",200)*0.75, result.get("max_stock",200)], "color":"#059669"},
                ],
                "threshold":{"line":{"color":"red","width":4}, "value":result.get("reorder_point",30)},
            }
        ))
        fig.update_layout(template="plotly_dark", height=280)
        st.plotly_chart(fig, use_container_width=True)


with tab3:
    st.subheader("🏭 Warehouse Optimisation — ABC Velocity Slotting")
    wh_opts = (dict(zip(warehouses_df["warehouse_id"] + " — " + warehouses_df["warehouse_name"],
                        warehouses_df["warehouse_id"])) if not warehouses_df.empty else {"WH-001": "WH-001"})
    sel_wh = st.selectbox("Select Warehouse", list(wh_opts.keys()))
    wh_id  = wh_opts.get(sel_wh, "WH-001")

    with st.spinner("Running ABC velocity slotting…"):
        result = api_get("/api/v1/operations/warehouse-optimization", {"warehouse_id": wh_id})
    if result:
        c1,c2,c3 = st.columns(3)
        summary = result.get("class_summary",{})
        c1.metric("Class A (Fast)",   summary.get("A",0))
        c2.metric("Class B (Medium)", summary.get("B",0))
        c3.metric("Class C (Slow)",   summary.get("C",0))
        st.metric("Est. Pick Time Reduction", f"{result.get('estimated_pick_time_reduction_pct',0)}%")

        plan = pd.DataFrame(result.get("slotting_plan",[]))
        if not plan.empty:
            fig = px.sunburst(plan, path=["velocity_class","recommended_zone","category"],
                              values="avg_daily_demand" if "avg_daily_demand" in plan.columns else None,
                              title="Warehouse Slotting Plan",
                              color="velocity_class",
                              color_discrete_map={"A":"#34d399","B":"#fbbf24","C":"#f87171"},
                              template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            view_cols = [c for c in ["product_name","velocity_class","recommended_zone",
                                      "avg_daily_demand","pick_time_savings_pct"] if c in plan.columns]
            st.dataframe(plan[view_cols].head(30), use_container_width=True, hide_index=True)
            export_button(plan, "slotting_plan.csv")


with tab4:
    st.subheader("🗺️ Route Optimisation — Nearest Neighbor 2-opt")
    sel_wh2 = st.selectbox("Select Warehouse", list(wh_opts.keys()), key="route_wh")
    wh_id2  = wh_opts.get(sel_wh2, "WH-001")

    with st.spinner("Running route optimisation…"):
        result = api_post("/api/v1/operations/route-optimization", {"warehouse_id": wh_id2})
    if result:
        if "message" in result and "error" not in str(result):
            st.info(result["message"])
        else:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total Orders", result.get("total_orders","—"))
            c2.metric("Optimised Dist", f"{result.get('optimised_distance_km',0)} km")
            c3.metric("Distance Saved", f"{result.get('distance_saved_km',0)} km")
            c4.metric("Saving %", f"{result.get('saving_pct',0)}%")
            st.metric("Estimated Time", f"{result.get('estimated_time_hrs',0)} hrs")

            # Map
            route = result.get("route", [])
            if route:
                df_route = pd.DataFrame(route)
                df_route["type"] = "Stop"
                origin = result.get("origin", {})
                orig_df = pd.DataFrame([{"lat": origin.get("lat"), "lng": origin.get("lng"),
                                         "city": "Warehouse", "type": "Origin", "items": 0}])
                all_pts = pd.concat([orig_df, df_route], ignore_index=True)
                fig = px.scatter_mapbox(all_pts, lat="lat", lon="lng",
                                       hover_name="city", color="type",
                                       mapbox_style="carto-darkmatter",
                                       zoom=4, height=420,
                                       title="Optimised Delivery Route")
                st.plotly_chart(fig, use_container_width=True)
