"""
CalRetail — Shared Streamlit utilities
Handles all API calls to the FastAPI backend.
"""
import sys
import os
from pathlib import Path

# Always ensure CalRetail root is on sys.path so backend is importable if needed
_root = Path(__file__).parent.parent.parent  # frontend/components/utils.py → CalRetail/
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import requests
import streamlit as st
import pandas as pd

API_BASE = "http://127.0.0.1:8000"


def api_get(path: str, params: dict = None) -> "dict | list | None":
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=30, proxies={"http": None, "https": None})
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend not running. Start it with: `python -m uvicorn backend.main:app --port 8000 --reload`")
        return None
    except Exception as e:
        st.warning(f"API error on {path}: {e}")
        return None


def api_post(path: str, payload: dict) -> "dict | list | None":
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=30, proxies={"http": None, "https": None})
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend not running.")
        return None
    except Exception as e:
        st.warning(f"API error on {path}: {e}")
        return None


def page_header(title: str, subtitle: str, icon: str = "🤖"):
    st.markdown(f"""
<div style='padding: 1.5rem 0 1rem 0;'>
  <h1 style='margin:0; font-size:2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 60%, #f093fb 100%);
             -webkit-background-clip:text; -webkit-text-fill-color:transparent; font-weight:800;'>
    {icon} {title}
  </h1>
  <p style='color:#94a3b8; margin:0.3rem 0 0 0; font-size:0.95rem;'>{subtitle}</p>
</div>
""", unsafe_allow_html=True)
    st.divider()


def confidence_bar(value: float, label: str = "Confidence"):
    st.metric(label, f"{value*100:.1f}%")
    st.progress(min(1.0, max(0.0, float(value))))


def export_button(df: pd.DataFrame, filename: str = "export.csv"):
    if df is not None and not df.empty:
        csv = df.to_csv(index=False).encode()
        st.download_button("📥 Export CSV", data=csv, file_name=filename, mime="text/csv",
                           key=f"export_{filename}_{len(df)}")


def module_card_css():
    return """
<style>
.calretail-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border: 1px solid rgba(100, 116, 255, 0.3);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    transition: all 0.3s ease;
}
.calretail-card:hover {
    border-color: rgba(100, 116, 255, 0.8);
    box-shadow: 0 8px 30px rgba(100, 116, 255, 0.3);
    transform: translateY(-2px);
}
.card-title { font-size: 1.2rem; font-weight: 700; color: #e2e8f0; margin-bottom: 0.3rem; }
.card-desc  { font-size: 0.85rem; color: #94a3b8; }
.badge {
    display: inline-block; padding: 2px 10px;
    border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-right: 6px;
}
.badge-blue   { background: rgba(59,130,246,0.2);  color: #60a5fa; border: 1px solid rgba(59,130,246,0.4); }
.badge-purple { background: rgba(139,92,246,0.2);  color: #a78bfa; border: 1px solid rgba(139,92,246,0.4); }
.badge-green  { background: rgba(16,185,129,0.2);  color: #34d399; border: 1px solid rgba(16,185,129,0.4); }
.badge-orange { background: rgba(245,158,11,0.2);  color: #fbbf24; border: 1px solid rgba(245,158,11,0.4); }
.badge-red    { background: rgba(239,68,68,0.2);   color: #f87171; border: 1px solid rgba(239,68,68,0.4); }
</style>
"""
