# 🛍️ CalRetail — Enterprise Retail AI Intelligence Platform

> **20 AI Capabilities · 5 Business Modules · 26 REST APIs · Streamlit Dashboard**  
> A production-grade retail AI platform built for fashion retail, powered by Python, FastAPI, Streamlit, and 20 Jupyter-based AI capability modules.

---

## 📋 Table of Contents
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [AI Modules & Notebooks](#ai-modules--notebooks)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Running Tests](#running-tests)

---

## Architecture Overview

```
                          Jupyter Capability Notebooks (20 modules)
                                      ▲
                                      │ (Dynamic import using notebook_loader.py)
                                      ▼
                          FastAPI backend (Port 8000)
                                      ▲
                                      │ HTTP JSON APIs
                                      ▼
                          Streamlit frontend (Port 8501)
```

The CalRetail platform utilizes a state-of-the-art **Notebook-Delegated Architecture**. Rather than replicating code, the FastAPI backend dynamically imports and executes Jupyter Notebooks (`.ipynb`) as live Python modules. The notebooks serve as the single, data-driven source of truth, loaded once and cached in memory for sub-millisecond execution times.

---

## Tech Stack

| Component | Technology | Description |
|-----------|-----------|-------------|
| Backend API | FastAPI + Uvicorn | Async web framework with Pydantic validations |
| Frontend | Streamlit | Pure-Python interactive UI |
| ML & Data Analytics | Pandas, NumPy, Scikit-learn | Algorithms: Cosine similarity, K-Means clustering, Dijkstra routing, statistical forecasting |
| Notebook Delegation | Custom Notebook Loader | Dynamically executes `.ipynb` code cells inside live Python namespaces |
| Test Suite | Pytest | Full regression checking for all 20 capability notebooks |

---

## Project Structure

```
CalRetail/
├── backend/
│   ├── main.py                  # FastAPI app entry point & startup warmed cache
│   ├── config/settings.py       # Pydantic-settings config
│   ├── utils/
│   │   ├── data_loader.py       # LRU-cached load functions for all processed CSVs
│   │   ├── notebook_loader.py   # Dynamic notebook-to-module loader utility
│   │   └── logger.py            # Loguru logger instance
│   ├── services/
│   │   ├── customer_experience.py   # Delegating thin proxy (capabilities 1-4)
│   │   ├── merchandising.py         # Delegating thin proxy (capabilities 5-8)
│   │   ├── operations.py            # Delegating thin proxy (capabilities 9-12)
│   │   ├── support_intelligence.py  # Delegating thin proxy (capabilities 13-16)
│   │   └── monetisation.py          # Delegating thin proxy (capabilities 17-20)
│   └── routers/
│       ├── customer_experience.py   # FastAPI routers
│       ├── merchandising.py
│       └── ops_support_monetise.py
├── frontend/
│   ├── app.py                       # Streamlit multi-page homepage
│   ├── components/utils.py          # API connector & CSS helper assets
│   └── pages/                       # Module dashboards (Customer Experience, Merchandising, Operations, Support, Monetisation)
├── notebooks/
│   └── capabilities/                # The 20 data-driven capability notebooks (source of truth)
├── data/
│   └── processed/                   # Cleaned CSV data tables cached at startup
└── tests/
    └── test_notebooks.py            # Automated notebook execution regression tests
```

---

## AI Modules & Notebooks

### 1. Customer Experience (`customer_experience.py`)
- `01_personalised_recommendations.ipynb` - User-Item Cosine Similarity recomendations.
- `02_conversational_buying_assistant.ipynb` - Natural language query filter extraction.
- `03_next_best_offer.ipynb` - Segment preference promotion boost scoring.
- `04_communication_timing.ipynb` - Best hour/day activity pattern optimization.

### 2. Merchandising Intelligence (`merchandising.py`)
- `05_demand_forecasting.ipynb` - Machine learning lag sales forecasting.
- `06_dynamic_pricing.ipynb` - Price elasticity rules & competitor matching.
- `07_promotion_optimization.ipynb` - Control-scaled uplift prediction.
- `08_competitor_price_monitoring.ipynb` - Z-score price gap alarms.

### 3. Operational Excellence (`operations.py`)
- `09_inventory_health_monitoring.ipynb` - Log-sigmoid stockout risk metrics.
- `10_automated_replenishment.ipynb` - safety stock and Economic Order Quantity (EOQ).
- `11_warehouse_slotting.ipynb` - ABC class frequency velocity slotting.
- `12_route_optimisation.ipynb` - Delivery routing solver.

### 4. Support Intelligence (`support_intelligence.py`)
- `13_ai_chatbot.ipynb` - Conversational customer care assistant.
- `14_ticket_triage.ipynb` - Automated ticket category and priority router.
- `15_agent_assist.ipynb` - Knowledge base TF-IDF recommendation engine.
- `16_voice_of_customer.ipynb` - Rating aggregation sentiment metrics.

### 5. First-Party Data Monetisation (`monetisation.py`)
- `17_retail_media_planner.ipynb` - CTR/CVR campaign budget builder.
- `18_audience_segmentation.ipynb` - RFM customer K-Means clustering.
- `19_buying_intent_scoring.ipynb` - Segment probability classification.
- `20_supplier_insights.ipynb` - Multidimensional scorecard rating.

---

## Quick Start

### 1. Launch the Backend API
Start the FastAPI server on port `8000` (using the system virtual environment):
```bash
myenv\Scripts\python.exe -m uvicorn backend.main:app --port 8000 --reload
```

### 2. Launch the Streamlit Frontend
Start the web dashboard on port `8501`:
```bash
myenv\Scripts\python.exe -m streamlit run frontend/app.py --server.port 8501
```

### 3. Open in Browser
- **Web Dashboard**: [http://localhost:8501](http://localhost:8501)
- **FastAPI API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Running Tests
To run full regression checking on all 20 capability notebooks and ensure compatibility:
```bash
myenv\Scripts\python.exe -m pytest tests/test_notebooks.py
```

