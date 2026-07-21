"""
CalRetail — Streamlit Homepage
Enterprise Retail AI Intelligence Platform
"""
import streamlit as st

st.set_page_config(
    page_title="CalRetail AI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: linear-gradient(135deg, #0a0a0f 0%, #0d1117 50%, #0a0f1a 100%); }

.hero-title {
    font-size: 3.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 30%, #f093fb 60%, #f5576c 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
    margin-bottom: 0.5rem;
}
.hero-subtitle {
    font-size: 1.15rem;
    color: #94a3b8;
    margin-bottom: 2rem;
    font-weight: 400;
}
.stat-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
}
.stat-number { font-size: 2rem; font-weight: 800; color: #a78bfa; }
.stat-label  { font-size: 0.8rem; color: #64748b; margin-top: 0.2rem; }

.module-card {
    background: linear-gradient(135deg, rgba(26,26,46,0.95) 0%, rgba(22,33,62,0.95) 100%);
    border: 1px solid rgba(100,116,255,0.25);
    border-radius: 20px;
    padding: 2rem 1.8rem;
    height: 280px;
    transition: all 0.3s ease;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}
.module-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent);
    border-radius: 20px 20px 0 0;
}
.module-card:hover {
    border-color: rgba(100,116,255,0.7);
    box-shadow: 0 20px 60px rgba(100,116,255,0.2);
    transform: translateY(-4px);
}
.module-icon   { font-size: 2.8rem; margin-bottom: 1rem; }
.module-title  { font-size: 1.2rem; font-weight: 700; color: #e2e8f0; margin-bottom: 0.5rem; }
.module-desc   { font-size: 0.82rem; color: #94a3b8; line-height: 1.5; }
.module-caps   { margin-top: 1rem; }
.cap-tag {
    display: inline-block;
    background: rgba(100,116,255,0.15);
    color: #818cf8;
    border: 1px solid rgba(100,116,255,0.3);
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.7rem;
    font-weight: 600;
    margin: 2px;
}
.section-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 0.3rem;
}
.section-sub { font-size: 0.9rem; color: #64748b; margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Hero section ──────────────────────────────────────────────────────────────
st.markdown("""
<div style='padding: 3rem 0 2rem 0; text-align: center;'>
  <div class='hero-title'> CalRetail</div>
  <div style='font-size:1.05rem; color:#6366f1; font-weight:600; letter-spacing:0.15em; margin-bottom:0.8rem;'>
    ENTERPRISE RETAIL AI INTELLIGENCE PLATFORM
  </div>
  <div class='hero-subtitle'>
    20 AI capabilities across 5 business modules — powering the next generation of fashion retail.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Stats ──────────────────────────────────────────────────────────────────────
s1, s2, s3, s4, s5 = st.columns(5)
stats = [
    ("20", "AI Capabilities"),
    ("5", "Business Modules"),
    ("25", "Datasets"),
    ("1.8M+", "Data Points"),
    ("10K", "Customers"),
]
for col, (num, lbl) in zip([s1, s2, s3, s4, s5], stats):
    with col:
        st.markdown(f"""
        <div class='stat-card'>
          <div class='stat-number'>{num}</div>
          <div class='stat-label'>{lbl}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.divider()

# ── Module cards ──────────────────────────────────────────────────────────────
st.markdown("""
<div class='section-title'>Business Modules</div>
<div class='section-sub'>Select a module to explore its AI capabilities</div>
""", unsafe_allow_html=True)

MODULES = [
    {
        "icon": "👤",
        "title": "Customer Experience",
        "accent": "#6366f1",
        "desc": "Hyper-personalised AI that understands each customer's preferences, behaviour, and intent.",
        "caps": ["Personalised Recommendations","Buying Assistant","Next Best Offer","Predictive Communication"],
        "page": "pages/module1_customer_experience.py",
    },
    {
        "icon": "📊",
        "title": "Merchandising Intelligence",
        "accent": "#10b981",
        "desc": "Real-time intelligence on demand, pricing, promotions, and competitive positioning.",
        "caps": ["Demand Forecasting","Dynamic Pricing","Promotion Optimisation","Competitor Monitoring"],
        "page": "pages/module2_merchandising.py",
    },
    {
        "icon": "⚙️",
        "title": "Operational Excellence",
        "accent": "#f59e0b",
        "desc": "AI-driven inventory, replenishment, warehouse slotting, and route optimisation.",
        "caps": ["Inventory Health","Auto Replenishment","Warehouse Optimisation","Route Optimisation"],
        "page": "pages/module3_operations.py",
    },
    {
        "icon": "💬",
        "title": "Support Intelligence",
        "accent": "#ec4899",
        "desc": "24×7 AI support — from chatbot to agent assist and voice-of-customer mining.",
        "caps": ["24×7 AI Chatbot","Ticket Triage","Agent Assist","Voice of Customer"],
        "page": "pages/module4_support.py",
    },
    {
        "icon": "💰",
        "title": "Data Monetisation",
        "accent": "#8b5cf6",
        "desc": "Monetise first-party data via retail media, audience segments, and supplier insights.",
        "caps": ["Retail Media","Audience Segmentation","Buying Intent","Supplier Insights"],
        "page": "pages/module5_monetisation.py",
    },
]

for row_start in range(0, len(MODULES), 3):
    cols = st.columns(min(3, len(MODULES) - row_start))
    for col, mod in zip(cols, MODULES[row_start:row_start+3]):
        with col:
            caps_html = "".join([f"<span class='cap-tag'>{c}</span>" for c in mod["caps"]])
            st.markdown(f"""
            <div class='module-card' style='--accent: {mod["accent"]}'>
              <div class='module-icon'>{mod["icon"]}</div>
              <div class='module-title'>{mod["title"]}</div>
              <div class='module-desc'>{mod["desc"]}</div>
              <div class='module-caps'>{caps_html}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Explore {mod['title']} →", key=mod["title"], use_container_width=True):
                st.switch_page(mod["page"])

st.divider()

# ── AI Assistant quick access ─────────────────────────────────────────────────
st.markdown("""
<div class='section-title'>🤖 AI Assistant</div>
<div class='section-sub'>Ask anything about your retail data in natural language</div>
""", unsafe_allow_html=True)
if st.button("Launch Retail AI Assistant →", type="primary", use_container_width=False):
    st.switch_page("pages/ai_assistant.py")

st.markdown("<br>", unsafe_allow_html=True)
st.caption("CalRetail v1.0 · Enterprise Retail AI · Built with FastAPI + Streamlit + Scikit-learn + XGBoost")
