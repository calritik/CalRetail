"""
Module 1 — Customer Experience (Streamlit Page)
Covers: Recommendations, Buying Assistant, Next Best Offer, Communication Timing
"""
import sys
from pathlib import Path
_root = Path(__file__).parent.parent.parent  # pages/ → frontend/ → CalRetail/
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.components.utils import api_get, api_post, page_header, export_button

st.set_page_config(page_title="Customer Experience | CalRetail", page_icon="👤", layout="wide")

# ─── Color palette (shared across all Recommendation Engine charts) ────────
PRIMARY = "#E8484B"
PALETTE = ["#E8484B", "#6366F1", "#10B981", "#F59E0B", "#8B5CF6",
           "#EC4899", "#14B8A6", "#F472B6", "#84CC16", "#38BDF8"]


def _category_color_map(categories):
    """Deterministic category → color mapping, reused across every admin chart."""
    cats = sorted(set(categories))
    return {cat: PALETTE[i % len(PALETTE)] for i, cat in enumerate(cats)}


def _spacer(height_px: int = 24):
    st.markdown(f"<div style='height:{height_px}px'></div>", unsafe_allow_html=True)

# Load customer list for selectors
@st.cache_data(ttl=300)
def load_customers():
    data = api_get("/api/v1/customer-experience/customers", {"limit": 200})
    if not data:
        raise ConnectionError("Backend not responding")
    return pd.DataFrame(data)


try:
    customers_df = load_customers()
except Exception as e:
    customers_df = pd.DataFrame()
    st.exception(e)

if customers_df.empty:
    st.warning("⚠️ Backend connection timed out or is not responding. Please check your backend status.")
    if st.button("🔄 Retry Connection", key="retry_conn"):
        st.cache_data.clear()
        st.rerun()
    st.stop()

customer_options = (
    dict(zip(customers_df["customer_id"] + " — " + customers_df["name"],
             customers_df["customer_id"]))
    if not customers_df.empty else {}
)

page_header("Customer Experience", "Hyper-personalised AI journeys for every shopper", "👤")

tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Recommendations",
    "🤝 Buying Assistant",
    "🎁 Next Best Offer",
    "⏰ Communication Timing",
])

# ─── Tab 1: Personalised Recommendations ────────────────────────────────────
with tab1:
    st.subheader("🎯 Hyper Personalised Recommendations")
    st.caption("Collaborative filtering + category boost — with full model transparency (customer profile, "
               "recommendation breakdown, and diagnostics)")
    col1, col2 = st.columns([2, 1])
    with col1:
        sel_key = st.selectbox("Select Customer", list(customer_options.keys()), key="rec_cust")
        customer_id = customer_options.get(sel_key, "")
    with col2:
        top_n = st.slider("Number of recommendations", 5, 30, 10)

    if st.button("🚀 Generate Recommendations", type="primary"):
        with st.spinner("Running collaborative filtering…"):
            result = api_get("/api/v1/customer-experience/recommendations/debug",
                             {"customer_id": customer_id, "top_n": top_n})
        if result:
            st.session_state["rec_result"] = result

    result = st.session_state.get("rec_result")

    if result:
        profile = result.get("profile", {})
        purchase_history = pd.DataFrame(result.get("purchase_history", []))
        category_affinity = pd.DataFrame(result.get("category_affinity", []))
        recs = pd.DataFrame(result.get("recommendations", []))
        similar_customers = pd.DataFrame(result.get("similar_customers", []))
        algorithm = result.get("algorithm", "Unknown")

        all_categories = list(pd.concat([
            category_affinity.get("category", pd.Series(dtype=str)),
            recs.get("category", pd.Series(dtype=str)),
        ])) if not (category_affinity.empty and recs.empty) else []
        cat_colors = _category_color_map(all_categories)

        st.success(f"✅ {len(recs)} recommendations generated · Algorithm: {algorithm}")

        # 1. Customer profile panel ------------------------------------------------
        st.markdown("#### 👤 Customer Profile")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Segment / Cohort", profile.get("segment", "—"))
        p2.metric("Loyalty Tier", profile.get("loyalty_tier", "—"))
        p3.metric("Preferred Category", profile.get("preferred_category", "—"))
        p4.metric("Region / City", f"{profile.get('region','—')} · {profile.get('city','—')}")

        st.markdown("**Raw purchase history**")
        if not purchase_history.empty:
            st.dataframe(
                purchase_history, use_container_width=True, hide_index=True,
                column_config={
                    "unit_price": st.column_config.NumberColumn("Unit Price", format="₹%.0f"),
                    "final_price": st.column_config.NumberColumn("Final Price", format="₹%.0f"),
                    "total_amount": st.column_config.NumberColumn("Total", format="₹%.0f"),
                },
            )
            export_button(purchase_history, "purchase_history.csv")
        else:
            st.info("No transaction history for this customer (cold start).")

        _spacer(32)
        st.markdown("**Category affinity — % of past purchases by category**")
        if not category_affinity.empty:
            fig_affinity = px.bar(
                category_affinity.sort_values("purchase_pct", ascending=True),
                x="purchase_pct", y="category", orientation="h",
                color="category", color_discrete_map=cat_colors,
                text="purchase_pct", height=380, template="plotly_dark",
            )
            fig_affinity.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_affinity.update_layout(
                title="Category Affinity (% of Units Purchased)",
                xaxis_title="% of past purchases", yaxis_title="", showlegend=False,
                margin=dict(t=60, b=40, l=10, r=10),
            )
            st.plotly_chart(fig_affinity, use_container_width=True)
        else:
            st.info("No purchase history to compute category affinity.")

        _spacer(40)
        st.divider()

        # 2. Recommendation breakdown table -----------------------------------------
        st.markdown("#### 📊 Recommendation Breakdown")
        if not recs.empty:
            filt_col1, filt_col2 = st.columns(2)
            with filt_col1:
                cat_filter = st.multiselect("Filter by category", sorted(recs["category"].unique()),
                                            key="rec_cat_filter")
            with filt_col2:
                algo_filter = st.multiselect("Filter by type", ["Personalized", "Fallback"],
                                             key="rec_algo_filter")

            table_df = recs.copy()
            table_df["type"] = table_df["is_personalized"].map({True: "Personalized", False: "Fallback"})
            if cat_filter:
                table_df = table_df[table_df["category"].isin(cat_filter)]
            if algo_filter:
                table_df = table_df[table_df["type"].isin(algo_filter)]

            st.dataframe(
                table_df[["product_name", "category", "brand", "price", "final_score",
                         "cf_score", "category_boost", "popularity_score",
                         "avg_rating", "review_count", "type", "algorithm"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "product_name": st.column_config.TextColumn("Product"),
                    "price": st.column_config.NumberColumn("Price", format="₹%.0f"),
                    "final_score": st.column_config.NumberColumn("Final Score", format="%.4f"),
                    "cf_score": st.column_config.NumberColumn("CF Score", format="%.4f"),
                    "category_boost": st.column_config.NumberColumn("Category Boost ×", format="%.4f"),
                    "popularity_score": st.column_config.NumberColumn("Popularity (units sold)", format="%.0f"),
                    "avg_rating": st.column_config.NumberColumn("Avg Rating", format="%.1f ⭐"),
                    "type": st.column_config.TextColumn("Rec Type"),
                },
            )
            export_button(table_df, "recommendation_breakdown.csv")
        else:
            st.info("No recommendations returned.")

        _spacer(32)
        st.markdown("**Sub-score breakdown per product**")
        if not recs.empty:
            fig_scores = go.Figure()
            fig_scores.add_bar(name="CF Score", x=recs["product_name"], y=recs["cf_score"],
                               marker_color=PRIMARY)
            fig_scores.add_bar(name="Category Boost ×", x=recs["product_name"], y=recs["category_boost"],
                               marker_color=PALETTE[1])
            fig_scores.add_bar(name="Final Score", x=recs["product_name"], y=recs["final_score"],
                               marker_color=PALETTE[2])
            fig_scores.update_layout(
                title="CF Score vs Category Boost vs Final Score", barmode="group", height=400,
                template="plotly_dark", xaxis_tickangle=-30, xaxis_title="", yaxis_title="Score",
                margin=dict(t=60, b=100, l=10, r=10),
            )
            st.plotly_chart(fig_scores, use_container_width=True)

        _spacer(40)
        st.divider()

        # 3. Model transparency panel -------------------------------------------------
        st.markdown("#### 🔬 Model Transparency")
        is_cf = algorithm.startswith("Collaborative Filtering")
        if is_cf:
            st.success(f"**Algorithm used:** {algorithm}")
        else:
            st.warning(f"**Algorithm used:** {algorithm}")

        if not similar_customers.empty:
            st.markdown(f"**Top {len(similar_customers)} similar customers used for collaborative filtering**")
            st.dataframe(
                similar_customers, use_container_width=True, hide_index=True,
                column_config={"similarity": st.column_config.NumberColumn("Cosine Similarity", format="%.4f")},
            )
            _spacer(32)
            fig_sim = px.bar(
                similar_customers.sort_values("similarity", ascending=True),
                x="similarity", y="name", orientation="h",
                color_discrete_sequence=[PRIMARY], height=380, template="plotly_dark",
            )
            fig_sim.update_layout(
                title="Similarity Score of Neighbours Used in CF",
                xaxis_title="Cosine similarity", yaxis_title="",
                margin=dict(t=60, b=40, l=10, r=10),
            )
            st.plotly_chart(fig_sim, use_container_width=True)
        else:
            st.info("No similar customers were used — this result came from the bestseller fallback path, "
                   "not collaborative filtering.")

        _spacer(40)
        st.divider()

        # 4. Ratings chart --------------------------------------------------------------
        st.markdown("**⭐ Average customer rating of each recommended product**")
        if not recs.empty:
            fig_rating = px.bar(
                recs.sort_values("avg_rating", ascending=False),
                x="product_name", y="avg_rating", color="category",
                color_discrete_map=cat_colors, height=380, range_y=[0, 5],
                template="plotly_dark",
            )
            fig_rating.update_layout(
                title="Average Rating by Recommended Product", xaxis_tickangle=-30,
                xaxis_title="", yaxis_title="Avg rating (out of 5)",
                margin=dict(t=60, b=100, l=10, r=10),
            )
            st.plotly_chart(fig_rating, use_container_width=True)

        _spacer(40)
        st.divider()

        # 5. Category diagnostic chart ---------------------------------------------
        st.markdown("#### 🩺 Category Diagnostic — Recommended vs Actually Purchased")
        if not recs.empty:
            rec_cat_pct = (recs["category"].value_counts(normalize=True) * 100).rename("pct").reset_index()
            rec_cat_pct.columns = ["category", "pct"]
            rec_cat_pct["metric"] = "% of Recommendations"

            if not category_affinity.empty:
                purch_cat_pct = category_affinity[["category", "purchase_pct"]].rename(columns={"purchase_pct": "pct"})
                purch_cat_pct["metric"] = "% of Past Purchases"
            else:
                purch_cat_pct = pd.DataFrame(columns=["category", "pct", "metric"])

            diag_df = pd.concat([rec_cat_pct, purch_cat_pct], ignore_index=True)
            fig_diag = px.bar(
                diag_df, x="category", y="pct", color="metric", barmode="group",
                color_discrete_map={"% of Recommendations": PRIMARY, "% of Past Purchases": PALETTE[1]},
                height=420, template="plotly_dark",
            )
            fig_diag.update_layout(
                title="Recommended-Category Mix vs Customer's Real Purchase Mix",
                xaxis_title="", yaxis_title="% share", legend_title="",
                margin=dict(t=60, b=60, l=10, r=10),
            )
            st.plotly_chart(fig_diag, use_container_width=True)
            st.caption("Large gaps between the two bars for a category flag a potential mismatch between what's "
                      "recommended and what this customer actually buys.")
        else:
            st.info("No recommendations to compare against purchase history.")
    else:
        st.info("Select a customer and click **Generate Recommendations** to view the full breakdown.")


# ─── Tab 2: Buying Assistant ─────────────────────────────────────────────────
with tab2:
    st.subheader("🤝 Personalised Buying Assistant")
    st.caption("Conversational AI parses your request and suggests matching products")

    col1, col2 = st.columns([2, 1])
    with col1:
        sel_key2 = st.selectbox("Select Customer", list(customer_options.keys()), key="assist_cust")
        customer_id2 = customer_options.get(sel_key2, "")
    with col2:
        st.write("")

    message = st.text_area("Your message",
        value="Show me women's ethnic wear under ₹2000 from FabIndia",
        height=80)

    if st.button("💬 Ask Assistant", type="primary"):
        with st.spinner("Processing intent…"):
            result = api_post("/api/v1/customer-experience/buying-assistant",
                              {"customer_id": customer_id2, "message": message, "session_id": "ui"})
        if result:
            st.markdown(f"**🤖 Nexa:** {result['response']}")

            col1, col2, col3 = st.columns(3)
            col1.metric("Intent", result.get("intent","—").replace("_"," ").title())
            col2.metric("Category", result.get("detected_category") or "—")
            col3.metric("Max Price", f"₹{result['max_price']:,}" if result.get("max_price") else "—")

            st.subheader("🛍️ Suggestions")
            prods = pd.DataFrame(result.get("product_suggestions", []))
            if not prods.empty:
                fig_assist = px.bar(
                    prods.sort_values("price"), x="product_name", y="price", color="brand",
                    title="Matched Products by Price", height=350,
                    template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Vivid,
                )
                fig_assist.update_layout(xaxis_tickangle=-30, xaxis_title="", yaxis_title="Price (₹)")
                st.plotly_chart(fig_assist, use_container_width=True)
                st.dataframe(prods, use_container_width=True, hide_index=True)
            else:
                st.info("No matching products found for this request.")


# ─── Tab 3: Next Best Offer ───────────────────────────────────────────────────
with tab3:
    st.subheader("🎁 Next Best Offer")
    st.caption("Identifies the single most impactful promotional offer for a customer")

    sel_key3 = st.selectbox("Select Customer", list(customer_options.keys()), key="nbo_cust")
    customer_id3 = customer_options.get(sel_key3, "")

    if st.button("🎯 Get Best Offer", type="primary"):
        with st.spinner("Scoring promotions…"):
            result = api_get("/api/v1/customer-experience/next-best-offer",
                             {"customer_id": customer_id3})
        if result and "error" not in result:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Promo Type",     result.get("promo_type","—"))
            col2.metric("Discount",       f"{result.get('discount_pct',0):.1f}%")
            col3.metric("Predicted Uplift", f"{result.get('predicted_uplift',0):.1f}%")
            col4.metric("Confidence",     f"{result.get('confidence',0)*100:.1f}%")

            st.success(f"📨 **Action:** {result.get('message','')}")
            st.json(result)


# ─── Tab 4: Communication Timing ─────────────────────────────────────────────
with tab4:
    st.subheader("⏰ Predictive Customer Communication")
    st.caption("ML-powered optimal send time & channel prediction based on behaviour")

    sel_key4 = st.selectbox("Select Customer", list(customer_options.keys()), key="comm_cust")
    customer_id4 = customer_options.get(sel_key4, "")

    if st.button("📊 Predict Best Timing", type="primary"):
        with st.spinner("Analysing activity patterns…"):
            result = api_get("/api/v1/customer-experience/communication-timing",
                             {"customer_id": customer_id4})
        if result and "error" not in result:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Best Time",       result.get("best_send_hour_label","—"))
            col2.metric("Best Day",        result.get("best_day_of_week","—"))
            col3.metric("Channel",         result.get("recommended_channel","—"))
            col4.metric("Est. Open Rate",  f"{result.get('predicted_open_rate',0)*100:.1f}%")

            # Activity heatmap
            hourly = result.get("hourly_activity", {})
            if hourly:
                hours = list(range(24))
                values = [hourly.get(str(h), 0) for h in hours]
                fig = go.Figure(go.Bar(
                    x=[f"{h:02d}:00" for h in hours], y=values,
                    marker_color="rgba(99,102,241,0.8)",
                    name="Activity %"
                ))
                fig.update_layout(
                    title="Hourly Activity Distribution",
                    template="plotly_dark", height=300,
                    xaxis_tickangle=-45,
                )
                st.plotly_chart(fig, use_container_width=True)
