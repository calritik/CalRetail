# 🛍️ CalRetail — Enterprise Retail AI Intelligence Platform

> **30 AI Capabilities · 5 Domains · 33 REST APIs · Dash Console**
> A retail AI platform for fashion retail, built on Python, FastAPI, Dash and 20
> Jupyter-based AI capability notebooks. The console implements slides 4-8 of the
> Calsoft *Retail AI Solutions* deck.

---

## 📋 Table of Contents
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Capability Domains](#capability-domains)
- [Quick Start](#quick-start)
- [Running Tests](#running-tests)
- [Notes & Gotchas](#notes--gotchas)

---

## Architecture Overview

```
                    Jupyter Capability Notebooks (20 modules)
                                  ▲
                                  │ dynamic import via notebook_loader.py
                                  ▼
                       FastAPI backend  (port 8000)
                                  ▲
                                  │ HTTP JSON
                                  ▼
                       Dash console     (port 8050)
```

CalRetail uses a **notebook-delegated architecture**: rather than duplicating
logic, the FastAPI backend imports and executes `.ipynb` code cells as live
Python modules, cached in memory after first load. The notebooks stay the single
source of truth.

---

## Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Backend API | FastAPI + Uvicorn | Async, Pydantic-validated |
| Console | Dash (Plotly) | `frontend_dash/` — the current UI |
| Legacy UI | Streamlit | `frontend/` — superseded, kept for reference |
| ML & Analytics | pandas, NumPy, scikit-learn, XGBoost | cosine similarity, K-Means, ABC slotting, routing, forecasting |
| LLM | LangChain (Gemini / Groq / OpenAI) | falls back to a rule-based engine with no key |
| Tests | pytest | regression over all 20 notebooks |

---

## Project Structure

```
CalRetail/
├── backend/
│   ├── main.py                     # FastAPI entry point, warms the notebook cache
│   ├── utils/
│   │   ├── notebook_loader.py      # executes .ipynb cells into a live module
│   │   ├── llm_service.py          # provider detection + LangChain wrappers
│   │   └── data_loader.py          # LRU-cached CSV loaders
│   ├── services/                   # thin proxies onto the notebooks
│   └── routers/                    # 33 REST routes
├── frontend_dash/                  # ← the console
│   ├── app.py                      # shell, routing, pre-paint theme bootstrap
│   ├── assets/
│   │   ├── style.css               # design system (tokens, cards, nav, dark mode)
│   │   ├── theme.js                # light/dark toggle + persistence
│   │   └── chart_theme.js          # keeps Plotly figures in step with the theme
│   ├── components/
│   │   ├── cards.py                # card / kpi / pill / bar / table / money
│   │   └── layout.py               # right-hand nav rail + page header
│   ├── services/
│   │   ├── api.py                  # cached FastAPI client (never raises)
│   │   ├── capabilities.py         # the 30 deck capabilities + their qualifiers
│   │   └── demo.py                 # seeded data for capabilities without endpoints
│   ├── theme/                      # colors.py + Plotly chart theme
│   └── pages/                      # home, 5 domains, AI assistant
├── notebooks/capabilities/         # the 20 capability notebooks
├── data/processed/                 # cleaned CSVs, cached at startup
└── tests/test_notebooks.py
```

---

## Capability Domains

Thirty capabilities from the deck. **20 are served by real endpoints**; the other
10 have no backend yet and render seeded, clearly-labelled illustrative data.

| # | Domain | Capabilities | Live |
|---|--------|--------------|------|
| 01 | Customer Experience | Recommendations · Buying Assistant · Next-Best-Offer · Visual Search · AR Try-on · Churn Propensity | 3/6 |
| 02 | Merchandising | Dynamic Pricing · Competitor Monitoring · Promotion Optimization · Assortment Planning · Demand Forecasting · Digital Shelf | 4/6 |
| 03 | Operational Efficiency | Smart Inventory · Automated Replenishment · Warehouse Optimization · Omnichannel OMS · Route Optimization · Store Vision AI | 4/6 |
| 04 | Customer Support | 24×7 Chatbots · L0-L2 Copilots · Ticket Triage · Agent-Assist · Voice-of-Customer · Feedback Analytics | 5/6 |
| 05 | First-Party Data | Retail Media Networks · Supplier Insights · Media-ROI Propensity · Audience Segments · Buying Intent · CLV & Retention | 4/6 |

Each card carries the deck's own **Impact / Data / Speed** qualifiers and its
deployment **Wave** badge.

---

## Quick Start

> **`PYTHONUTF8=1` is required.** Python 3.14 still defaults to cp1252 on Windows,
> and a notebook cell prints `≈`. Without UTF-8 mode that cell raises
> `'charmap' codec can't encode character`, and `notebook_loader` silently skips
> it — so the capability degrades with no visible error.

### 1. Backend API — port 8000
```bash
PYTHONUTF8=1 myenv/Scripts/python.exe -m uvicorn backend.main:app --port 8000
```

### 2. Dash console — port 8050
```bash
PYTHONUTF8=1 myenv/Scripts/python.exe frontend_dash/app.py
```

PowerShell equivalent:
```powershell
$env:PYTHONUTF8 = "1"
myenv\Scripts\python.exe -m uvicorn backend.main:app --port 8000
myenv\Scripts\python.exe frontend_dash\app.py
```

### 3. Open
- **Console** — <http://127.0.0.1:8050>
- **Swagger** — <http://127.0.0.1:8000/docs>

Set `DASH_DEBUG=1` for hot reload and the callback graph. It's off by default
because the dev-tools widget overlays the last card in the grid.

---

## Running Tests

```bash
PYTHONUTF8=1 myenv/Scripts/python.exe -m pytest tests/ -q
```

---

## Notes & Gotchas

- **Dependencies.** `requirements.txt` pins with `>=`, so a fresh install
  resolves to current majors (pandas 3.x, langchain-core 1.x). Two things that
  follow from that are already handled in code, but worth knowing if you re-pin.
- **`jupyter` metapackage.** Not installed — JupyterLab's asset filenames exceed
  the Windows 260-character path limit under this directory depth. Nothing needs
  it: `notebook_loader.py` parses `.ipynb` with plain `json`. `ipykernel` +
  `nbformat` are installed, so VS Code notebooks work.
- **`matplotlib`** is imported by `05_demand_forecasting.ipynb` but missing from
  `requirements.txt`. It is installed in `myenv`; add it if you rebuild the env.
- **LLM responses.** In langchain-core 1.x, Gemini returns `content` as a list of
  blocks, not a string. `llm_service._response_text()` normalises both shapes —
  without it every call silently fell through to the rule-based engine while
  still logging `LLM: Gemini ✅`.
- **No API key?** Everything still runs; LLM-backed cards report
  `powered_by: Rule-Based Engine`.
