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
                     data/calretail.db  (SQLite, 31 tables)
                                  ▲
                                  │ backend/utils/db.py
                                  ▼
                    Jupyter Capability Notebooks (16 modules)
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
source of truth for capability logic.

All data lives in one **SQLite database**, `data/calretail.db` — 31 tables, 38
indexes, ~68 MB. It is committed, so a clone runs immediately and the Hugging
Face Space deploys with no build step. Nothing reads CSVs any more.

---

## Tech Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Database | SQLite | `data/calretail.db` — committed, read-only at runtime |
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
├── data/
│   └── calretail.db                # ← the database (committed, ~68 MB)
├── backend/
│   ├── main.py                     # FastAPI entry point, warms the notebook cache
│   ├── utils/
│   │   ├── db.py                   # SQLite engine: connections, pushdown, caching
│   │   ├── notebook_loader.py      # executes .ipynb cells into a live module
│   │   ├── llm_service.py          # provider detection + LangChain wrappers
│   │   └── data_loader.py          # table accessors + indexed lookups
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
├── notebooks/
│   ├── capabilities/               # the 16 capability notebooks
│   ├── generate_data.py            # seeded synthetic generator (stage 1)
│   ├── clean_data.py               # cleaning rules (stage 2)
│   ├── feature_engineering.py      # feature_* tables (stage 3)
│   ├── pipeline_io.py              # build-time SQLite reads/writes
│   └── build_db.py                 # runs all three, indexes, VACUUMs
└── tests/test_notebooks.py
```

---

## Capability Domains

Sixteen capabilities across four domains. **Every one is served by a real
endpoint reading the database** — there is no seeded or illustrative data left
in the console.

| # | Domain | Capabilities | Live |
|---|--------|--------------|------|
| 01 | Customer Experience | Hyper-personalized Recommendations · Personalized Buying Assistants · Next-Best-Offer Engines · Communication Timing Optimiser | 4/4 |
| 02 | Merchandising | Demand Forecasting · Dynamic Pricing Engines · Promotion Optimization · Competitor Price Monitoring | 4/4 |
| 03 | Operational Efficiency | Smart Inventory Management · Automated Replenishment · Warehouse Optimization · Logistics, Route & Fleet Optimization | 4/4 |
| 04 | Customer Support | 24x7 AI Chatbots · Intelligent Ticket Triage · Agent Assist · Voice of Customer | 4/4 |

Each card carries the deck's own **Impact / Data / Speed** qualifiers and its
deployment **Wave** badge.

### Names, not identifiers

Nothing in the console shows a raw `C00001` / `P00489` / `W002`. Identifiers are
resolved to names in the **backend**, by [`backend/utils/naming.py`](backend/utils/naming.py),
so every consumer of an endpoint gets the name for free rather than each card
re-implementing its own lookup:

```python
from backend.utils import naming

naming.customer("C00001")     # 'Niharika Bhatti'
naming.warehouse("W002")      # 'Bengaluru DC 2'
naming.annotate(rows)         # adds *_name beside every known *_id
naming.location_label(row)    # store or warehouse, whichever the row has
```

`annotate` never overwrites a name a notebook already supplied — the notebook's
is the more specific one. Maps are built once per process from the database and
memoised, so resolution is a dict hit, not a query per row.

---

## Quick Start

> **`PYTHONUTF8=1` is required.** Python 3.14 still defaults to cp1252 on Windows,
> and a notebook cell prints `≈`. Without UTF-8 mode that cell raises
> `'charmap' codec can't encode character`, and `notebook_loader` silently skips
> it — so the capability degrades with no visible error.

The database is committed, so there is no data step. Install and run:

```bash
pip install -r requirements.txt
```

### 1. Backend API — port 8000
```bash
PYTHONUTF8=1 python -m uvicorn backend.main:app --port 8000
```

### 2. Dash console — port 8050
```bash
PYTHONUTF8=1 python frontend_dash/app.py
```

PowerShell equivalent:
```powershell
$env:PYTHONUTF8 = "1"
python -m uvicorn backend.main:app --port 8000
python frontend_dash\app.py
```

### 3. Open
- **Console** — <http://127.0.0.1:8050>
- **Swagger** — <http://127.0.0.1:8000/docs>

Set `DASH_DEBUG=1` for hot reload and the callback graph. It's off by default
because the dev-tools widget overlays the last card in the grid.

---

## The Database

`data/calretail.db` holds all 31 tables and is the only data artifact. The app
opens it **read-only**, one connection per thread, so a request can never mutate
the demo data.

### Rebuilding

```bash
python -m notebooks.build_db                # demo scale — what is committed
python -m notebooks.build_db --scale full   # full fidelity: 3.9M rows, 528 MB
python -m notebooks.build_db --scale 0.5    # anything in between
```

The pipeline runs `generate_data → clean_data → feature_engineering`, then
indexes and VACUUMs. The generator is seeded (`random.seed(42)`), so a given
scale always produces the same database.

Stop the backend and console first — Windows will not let the builder replace a
file those processes hold open.

### What `--scale` does

Scale multiplies **event-log** tables only. Customers (10,000), products
(5,000), stores, warehouses, suppliers and inventory (25,000) are always
generated at full size, so a demo build still shows a complete catalogue and
customer base — only the behavioural history behind them is thinner.

Every customer is guaranteed at least one transaction and one order at any
scale. Sampling customers independently would leave ~9% of them with no history
at demo scale, which makes the recommendation and chatbot cards look broken
rather than sparse.

### Why demo scale is the committed default

A full-fidelity build is 528 MB, which exceeds GitHub's 100 MB per-file limit
and cannot be deployed to a Hugging Face Space without LFS. The demo build is
68 MB: it commits normally, clones fast, and the Space boots straight into a
warm dataset with no build step.

To run against a full build without touching the committed one:

```bash
CALRETAIL_DB=/path/to/full.db python -m notebooks.build_db --scale full
CALRETAIL_DB=/path/to/full.db python -m uvicorn backend.main:app --port 8000
```

### Reading from it

```python
from backend.utils import db, data_loader as dl

dl.get_customers()                 # whole table, memoised (what services use)
dl.customer_transactions("C00001") # indexed lookup, ~2 ms
db.query("SELECT category, COUNT(*) FROM products GROUP BY category")
```

`load_df` parses date columns to datetimes; `load_table` (used by the capability
notebooks) leaves them as ISO-8601 strings, which is the contract those
notebooks were written against when they read CSVs.

---

## Running Tests

```bash
PYTHONUTF8=1 python -m pytest tests/ -q
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
- **Notebook cell errors are silent.** `notebook_loader` catches per-cell
  exceptions, so a broken cell shows up much later as a missing attribute
  (`module '12_route_optimisation' has no attribute 'solve_delivery_route'`)
  rather than at load. When a capability 500s with an `AttributeError`, execute
  the notebook's cells directly — the real error is in one of them.
- **Rebuilding while the app runs** fails on Windows with `PermissionError`
  (`WinError 32`): uvicorn holds the database open. `build_db` detects this and
  tells you to stop the processes.
- **LLM responses.** In langchain-core 1.x, Gemini returns `content` as a list of
  blocks, not a string. `llm_service._response_text()` normalises both shapes —
  without it every call silently fell through to the rule-based engine while
  still logging `LLM: Gemini ✅`.
- **No API key?** Everything still runs; LLM-backed cards report
  `powered_by: Rule-Based Engine`.
