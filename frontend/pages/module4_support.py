"""
Module 4 — Customer Support Intelligence (Streamlit Page)
"""
import sys
from pathlib import Path
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import streamlit as st
import pandas as pd
import plotly.express as px
from frontend.components.utils import api_get, api_post, page_header, export_button

st.set_page_config(page_title="Support Intelligence | CalRetail", page_icon="💬", layout="wide")


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
    customers_df = load_customers()
except Exception:
    customers_df = pd.DataFrame()

try:
    products_df  = load_products()
except Exception:
    products_df  = pd.DataFrame()

if customers_df.empty or products_df.empty:
    st.warning("⚠️ Backend connection timed out or is not responding. Please check your backend status.")
    if st.button("🔄 Retry Connection", key="retry_conn"):
        st.cache_data.clear()
        st.rerun()
    st.stop()
customer_opts = (dict(zip(customers_df["customer_id"] + " — " + customers_df["name"],
                          customers_df["customer_id"])) if not customers_df.empty else {})

page_header("Support Intelligence", "24×7 AI chatbot, ticket triage, agent assist & voice of customer", "💬")

tab1, tab2, tab3, tab4 = st.tabs([
    "🤖 AI Chatbot",
    "🎫 Ticket Triage",
    "🧑‍💼 Agent Assist",
    "🎤 Voice of Customer",
])

# ─── Chat history state ────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with tab1:
    st.subheader("🤖 24×7 AI Chatbot — Nexa")
    col1, col2 = st.columns([3, 1])
    with col1:
        sel = st.selectbox("Customer", list(customer_opts.keys()), key="chat_cust")
        cid = customer_opts.get(sel, "")
    with col2:
        if st.button("Clear Chat"):
            st.session_state.chat_history = []

    # Render history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask Nexa anything…")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.spinner("Nexa is thinking…"):
            result = api_post("/api/v1/support/chatbot",
                              {"customer_id": cid, "message": prompt, "session_id": "ui"})
        if result:
            resp = result.get("response", "I'm sorry, I couldn't process that right now.")
            st.session_state.chat_history.append({"role": "assistant", "content": resp})
            with st.chat_message("assistant"):
                st.markdown(resp)
            if result.get("escalate"):
                st.error("🚨 This issue has been flagged for human escalation")
            col1, col2 = st.columns(2)
            col1.caption(f"Intent: **{result.get('intent','—')}**")
            col2.caption(f"Confidence: **{result.get('confidence',0)*100:.1f}%**")


with tab2:
    st.subheader("🎫 Intelligent Ticket Triage")
    st.caption("TF-IDF + Logistic Regression → category, priority, and team routing")

    sel2 = st.selectbox("Customer", list(customer_opts.keys()), key="triage_cust")
    cid2 = customer_opts.get(sel2, "")
    desc = st.text_area("Ticket Description",
        value="I received a completely wrong item. The package had someone else's order. Please help.",
        height=100)

    if st.button("🎫 Triage Ticket", type="primary"):
        with st.spinner("Classifying ticket…"):
            result = api_post("/api/v1/support/ticket-triage",
                              {"ticket_description": desc, "customer_id": cid2})
        if result:
            col1,col2,col3,col4 = st.columns(4)
            col1.metric("Category",  result.get("predicted_category","—"))
            col2.metric("Priority",  result.get("predicted_priority","—"))
            col3.metric("Team",      result.get("recommended_team","—"))
            col4.metric("Confidence", f"{result.get('overall_confidence',0)*100:.1f}%")

            priority_color = {
                "High":   "🔴", "Critical": "🚨",
                "Medium": "🟡", "Low": "🟢"
            }
            label = result.get("predicted_priority","—")
            st.info(f"{priority_color.get(label,'⚪')} Route to **{result.get('recommended_team','—')}** immediately")

            c1, c2 = st.columns(2)
            c1.progress(result.get("category_confidence",0), text=f"Category: {result.get('category_confidence',0)*100:.1f}%")
            c2.progress(result.get("priority_confidence",0), text=f"Priority: {result.get('priority_confidence',0)*100:.1f}%")

            conf_df = pd.DataFrame({
                "Model": ["Category Classifier", "Priority Classifier", "Overall"],
                "Confidence": [
                    result.get("category_confidence", 0) * 100,
                    result.get("priority_confidence", 0) * 100,
                    result.get("overall_confidence", 0) * 100,
                ],
            })
            fig_triage = px.bar(
                conf_df, x="Model", y="Confidence", color="Model", text_auto=".1f",
                title="Classifier Confidence Breakdown", height=320, template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Vivid,
            )
            fig_triage.update_layout(yaxis_title="Confidence (%)", yaxis_range=[0, 100], showlegend=False)
            st.plotly_chart(fig_triage, use_container_width=True)


with tab3:
    st.subheader("🧑‍💼 Real-Time Agent Assist")
    st.caption("Retrieves similar resolved tickets and knowledge articles to help agents")

    sel3 = st.selectbox("Customer being served", list(customer_opts.keys()), key="assist_cust")
    cid3 = customer_opts.get(sel3, "")
    query = st.text_area("Customer complaint / query",
        value="Customer says package arrived damaged and wants immediate replacement",
        height=80)

    if st.button("💡 Get Agent Suggestions", type="primary"):
        with st.spinner("Searching knowledge base…"):
            result = api_post("/api/v1/support/agent-assist",
                              {"query_text": query, "customer_id": cid3})
        if result:
            suggestions = result.get("suggested_responses", [])
            if suggestions:
                sim_df = pd.DataFrame(suggestions)
                sim_df["similarity_pct"] = sim_df["similarity"] * 100
                sim_df["label"] = sim_df["ticket_id"] + " — " + sim_df["category"]
                fig_agent = px.bar(
                    sim_df.sort_values("similarity_pct"), x="similarity_pct", y="label",
                    orientation="h", color="category", text_auto=".1f",
                    title="Similarity to Retrieved Resolved Cases", height=320,
                    template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Vivid,
                )
                fig_agent.update_layout(xaxis_title="Similarity (%)", xaxis_range=[0, 100], yaxis_title="")
                st.plotly_chart(fig_agent, use_container_width=True)

            st.subheader("📚 Similar Resolved Cases")
            for s in suggestions:
                with st.expander(f"[Similarity: {s['similarity']*100:.1f}%] {s['description'][:80]}…"):
                    st.write(f"**Ticket ID:** {s['ticket_id']}")
                    st.write(f"**Category:** {s['category']}")
                    st.write(s["description"])
                    st.info(f"💡 **Suggested Action:** {s.get('suggested_reply', 'Investigate and resolve.')}")

            st.subheader("📖 Knowledge Articles")
            for art in result.get("knowledge_articles", []):
                st.markdown(f"• [{art['title']}]({art['url']})")


with tab4:
    st.subheader("🎤 Voice of Customer Mining")
    st.caption("Aspect-based sentiment analysis + topic extraction from review corpus")

    prod_opts = (dict(zip(products_df["product_id"] + " — " + products_df["product_name"],
                          products_df["product_id"])) if not products_df.empty else {})
    all_prods = {"All Products": ""}

    col1, col2, col3 = st.columns(3)
    with col1:
        sel_prod = st.selectbox("Product (optional)", list({**all_prods, **prod_opts}.keys()))
        pid = {**all_prods, **prod_opts}.get(sel_prod, "")
    with col2:
        date_from = st.date_input("From", value=None)
    with col3:
        date_to   = st.date_input("To",   value=None)

    params = {}
    if pid:         params["product_id"] = pid
    if date_from:   params["date_from"]  = str(date_from)
    if date_to:     params["date_to"]    = str(date_to)

    with st.spinner("Mining reviews…"):
        result = api_get("/api/v1/support/voice-of-customer", params)

    if result:
        if "message" in result:
            st.warning(result["message"])
        else:
            col1,col2,col3 = st.columns(3)
            col1.metric("Total Reviews", f"{result.get('total_reviews',0):,}")
            col2.metric("Avg Rating",    result.get("avg_rating",0))
            col3.metric("Alert",         "🚨 Low Rating!" if result.get("alert") else "✅ OK")

        # Sentiment distribution
        sent_dist = result.get("sentiment_distribution",{})
        if sent_dist:
            fig = px.pie(values=list(sent_dist.values()), names=list(sent_dist.keys()),
                         title="Sentiment Distribution",
                         color_discrete_map={"Positive":"#34d399","Neutral":"#60a5fa","Negative":"#f87171"},
                         template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        # Aspect analysis
        aspects = result.get("aspect_analysis",{})
        if aspects:
            asp_df = pd.DataFrame([
                {"Aspect": k, "Mentions": v["mention_count"],
                 "Avg Rating": v["avg_rating"], "% Positive": v["pct_positive"]}
                for k, v in aspects.items()
            ])
            fig2 = px.bar(asp_df, x="Aspect", y="% Positive",
                          color="Avg Rating", color_continuous_scale="RdYlGn",
                          title="Aspect Sentiment Analysis", template="plotly_dark")
            st.plotly_chart(fig2, use_container_width=True)

        # Monthly trend
        monthly = pd.DataFrame(result.get("monthly_trend", []))
        if not monthly.empty:
            fig3 = px.line(monthly, x="month", y="avg_rating",
                           title="Monthly Avg Rating Trend", markers=True, template="plotly_dark")
            st.plotly_chart(fig3, use_container_width=True)
