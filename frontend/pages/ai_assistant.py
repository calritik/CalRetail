"""
CalRetail — AI Assistant Page (Natural Language Interface)
"""
import sys
from pathlib import Path
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import streamlit as st
from frontend.components.utils import api_get, api_post, page_header

st.set_page_config(page_title="AI Assistant | CalRetail", page_icon="🤖", layout="wide")

page_header("Retail AI Assistant", "Ask any question about customers, products, inventory, or sales", "🤖")

st.caption("The assistant will route your question to the most relevant AI capability. Example queries below.")

st.info("""
💡 **Try asking:**
• *"Show recommendations for customer CUST-001"*  
• *"What's the inventory health for Footwear in Store S-01?"*  
• *"Forecast demand for product P-001 for 30 days"*  
• *"Triage this ticket: My delivery is 5 days late"*  
• *"Show me the buying intent for customer CUST-002 on product P-005"*
""")

if "assistant_history" not in st.session_state:
    st.session_state.assistant_history = []

for msg in st.session_state.assistant_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

query = st.chat_input("Ask anything about your retail business…")

QUICK_ACTIONS = {
    "📧 Get Communication Timing": lambda: ("comm_timing",),
    "📦 Check Inventory Health":   lambda: ("inventory",),
    "🎯 Score Buying Intent":      lambda: ("buying_intent",),
    "🎤 Analyse Customer Voice":   lambda: ("voc",),
}

col1, col2, col3, col4 = st.columns(4)
for col, (label, _) in zip([col1, col2, col3, col4], QUICK_ACTIONS.items()):
    with col:
        if st.button(label, use_container_width=True):
            query = label.split(" ", 1)[-1]

if query:
    st.session_state.assistant_history.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    q = query.lower()

    # Route to correct capability
    with st.chat_message("assistant"):
        with st.spinner("Routing to AI capability…"):
            # Pure LangChain Routing: query FastAPI's /api/v1/support/assistant-router
            result = api_post("/api/v1/support/assistant-router", {"query": query})
            
            if result:
                action = result.get("action", "general_chat")
                cid = result.get("customer_id") or "CUST-0001"
                pid = result.get("product_id") or "P-0484"
                llm_resp = result.get("response")

                if action == "recommendations":
                    rec_res = api_post("/api/v1/customer-experience/recommendations",
                                      {"customer_id": cid, "top_n": 5})
                    if rec_res:
                        recs  = rec_res.get("recommendations", [])
                        names = ", ".join([r["product_name"] for r in recs[:3]])
                        response = f"🎯 Top picks for **{cid}**: **{names}** — and {max(0, len(recs)-3)} more."
                    else:
                        response = f"I couldn't fetch recommendations for {cid} right now."

                elif action == "inventory_health":
                    inv_res = api_get("/api/v1/operations/inventory-health", {"top_n": 5})
                    if inv_res:
                        items = inv_res.get("results", inv_res) if isinstance(inv_res, dict) else inv_res
                        df_items = items[:3] if items else []
                        lines = "\n".join([f"• {i.get('product_name','—')}: stock={i.get('stock_qty','?')}, risk={i.get('risk_label','?')}" for i in df_items])
                        response = f"📦 **Inventory snapshot (top 3):**\n{lines}"
                    else:
                        response = "Couldn't load inventory data."

                elif action == "demand_forecast":
                    fore_res = api_get("/api/v1/merchandising/demand-forecast",
                                     {"product_id": pid, "days": 14})
                    if fore_res:
                        response = (f"📈 Demand forecast for **{pid}**: "
                                    f"~{fore_res.get('avg_daily_demand','?')} units/day "
                                    f"({fore_res.get('total_forecast','?')} total over 14 days, "
                                    f"MAPE={fore_res.get('mape_estimate','?')}%)")
                    else:
                        response = f"Couldn't run demand forecast for {pid}."

                elif action == "ticket_triage":
                    triage_res = api_post("/api/v1/support/ticket-triage",
                                      {"ticket_description": query, "customer_id": cid})
                    if triage_res:
                        response = (f"🎫 Ticket classified as **{triage_res.get('predicted_category','—')}** "
                                    f"with **{triage_res.get('predicted_priority','—')}** priority. "
                                    f"Route to: **{triage_res.get('recommended_team','—')}**.")
                    else:
                        response = "Couldn't triage the ticket."

                elif action == "buying_intent":
                    intent_res = api_post("/api/v1/monetization/buying-intent",
                                      {"customer_id": cid, "product_id": pid})
                    if intent_res:
                        response = (f"🎯 Buying intent for **{cid}** × **{pid}**: "
                                    f"**{intent_res.get('intent_level','—')}** "
                                    f"({intent_res.get('intent_score',0) or intent_res.get('purchase_probability',0)*100:.1f}/100). "
                                    f"💡 {intent_res.get('recommended_nudge','No recommended action.')}")
                    else:
                        response = f"Couldn't score buying intent for customer {cid} on product {pid}."

                elif action == "voice_of_customer":
                    voc_res = api_get("/api/v1/support/voice-of-customer", {"product_id": pid})
                    if voc_res and "message" not in voc_res:
                        response = (f"🎤 VOC Summary for **{pid}** — **{voc_res.get('total_reviews',0):,} reviews**, "
                                    f"avg rating: **{voc_res.get('avg_rating',0)}★**, "
                                    f"sentiment: {voc_res.get('sentiment_distribution',{})}")
                    else:
                        response = f"No Voice of Customer reviews found for {pid}."

                else:
                    response = llm_resp or (
                        "I can help you with:\n"
                        "• **Personalised Recommendations** — ask for a customer ID\n"
                        "• **Demand Forecasting** — ask for a product ID\n"
                        "• **Inventory Health** — ask about stock levels\n"
                        "• **Ticket Triage** — describe a customer complaint\n"
                        "• **Buying Intent** — ask for customer + product pair\n"
                        "• **Voice of Customer** — ask about reviews or sentiment\n\n"
                        "Try: *'Show recommendations for CUST-0001'*"
                    )
            else:
                response = "Unable to process request via AI router."

        st.markdown(response)
        st.session_state.assistant_history.append({"role": "assistant", "content": response})
