"""
CalRetail — Smart inventory health.

Ported from ``notebooks/capabilities/09_inventory_health_monitoring.ipynb``. The notebook remains the readable
narrative of the method; this module is what the API actually runs.

State is built lazily by :func:`_init` on the first call, so importing this
module is free and nothing is computed for a capability nobody asks for.
:func:`reset` drops it again, which is how the process stays inside a small
memory budget without re-executing a notebook.
"""
from __future__ import annotations

import sys
import numpy as np
import pandas as pd
from pathlib import Path
import json
import re
import math
from backend.utils.db import load_table
import warnings

warnings.filterwarnings('ignore')
from backend.capabilities import _registry

_READY = False
_BUILDING = False


def _init() -> None:
    """
    Build this capability's shared frames. Idempotent and cheap once warm.

    The _BUILDING guard matters: helpers lifted out of the setup block call
    _init() like every other function, and the setup itself calls those helpers.
    Without the guard that is unbounded recursion. Re-entering during the build
    simply returns, which leaves the helper reading the partially-built state —
    exactly what it saw when these were sequential notebook cells.
    """
    global _READY, _BUILDING, get_inventory_health_weights, inv, tx, suppliers, prod, max_date, recent_tx, velocity, product_supplier_map, supplier_reliability_map, DEFAULT_RELIABILITY, W_STOCKOUT, W_OVERSTOCK, W_RELIABILITY
    if _READY or _BUILDING:
        return
    _BUILDING = True
    try:
        from backend.utils.adaptive_thresholds import get_inventory_health_weights

        inv = load_table('inventory')
        tx = load_table('transactions')
        suppliers = load_table('suppliers')
        prod = load_table('products')

        # Compute daily velocity over 30 days
        tx['transaction_date'] = pd.to_datetime(tx['transaction_date'])
        max_date = tx['transaction_date'].max()
        recent_tx = tx[tx['transaction_date'] >= (max_date - pd.Timedelta(days=30))]

        velocity = recent_tx.groupby('product_id')['quantity'].sum().reset_index()
        velocity['daily_velocity'] = velocity['quantity'] / 30.0

        # Real supplier reliability per product (previously loaded but never used).
        product_supplier_map = dict(zip(prod['product_id'], prod['supplier_id']))
        supplier_reliability_map = dict(zip(suppliers['supplier_id'], suppliers['reliability_score']))
        DEFAULT_RELIABILITY = float(suppliers['reliability_score'].median())

        # PCA-derived composite weights for [stockout_risk, overstock_flag, supplier
        # reliability] — replaces a health score that only ever looked at stockout risk.
        W_STOCKOUT, W_OVERSTOCK, W_RELIABILITY = get_inventory_health_weights()

        print(f"Loaded stock information. Daily velocity calculated for {len(velocity)} products.")
        print(f"Composite health weights (data-derived): stockout={W_STOCKOUT:.2f}, overstock={W_OVERSTOCK:.2f}, reliability={W_RELIABILITY:.2f}")

        _READY = True
    finally:
        _BUILDING = False

    # Registering last bounds how many capabilities hold frames at once; the
    # coldest is reset when this one pushes the count over the limit.
    _registry.touch(__name__)


def __getattr__(name: str):
    """
    Build the state on first attribute access (PEP 562).

    Callers that reach past the public functions for a shared frame — the
    recommendations debug view reads the feedback matrix directly — would
    otherwise see an AttributeError, because nothing exists until _init() runs.
    This is only consulted for names *missing* from the module, so it costs
    nothing once warm.
    """
    if not name.startswith("__"):
        _init()
        if name in globals():
            return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def reset() -> None:
    """
    Release the cached frames so the next call rebuilds them.

    The names are *deleted*, not set to None. __getattr__ above only fires for
    names missing from the module, so leaving a None behind would hand a caller
    that None forever instead of triggering a rebuild — the frames would look
    released while every read of them silently broke.
    """
    global _READY
    _READY = False
    for _name in ('get_inventory_health_weights', 'inv', 'tx', 'suppliers', 'prod', 'max_date', 'recent_tx', 'velocity', 'product_supplier_map', 'supplier_reliability_map', 'DEFAULT_RELIABILITY', 'W_STOCKOUT', 'W_OVERSTOCK', 'W_RELIABILITY'):
        globals().pop(_name, None)


def compute_inventory_health():
    # Merge stock details with velocity
    _init()
    health_df = pd.merge(inv, velocity, on='product_id', how='left')
    health_df['daily_velocity'] = health_df['daily_velocity'].fillna(0.1) # default min
    
    # Calculate days cover
    health_df['days_cover'] = health_df['stock_qty'] / health_df['daily_velocity']
    
    # sigmoid risk: high risk when days_cover < reorder_point
    results = []
    for idx, row in health_df.iterrows():
        rop = row['reorder_point']
        cover = row['days_cover']
        
        # stockout risk function (sigmoid of difference)
        stockout_risk = 1.0 / (1.0 + np.exp((cover - rop) * 0.2))
        
        # Calculate overstock
        max_stk = row['max_stock'] if not pd.isna(row['max_stock']) else 9999.0
        overstock_flag = 1 if row['stock_qty'] > max_stk else 0

        # Real supplier reliability for this SKU's actual supplier
        supplier_id = product_supplier_map.get(row['product_id'])
        reliability = supplier_reliability_map.get(supplier_id, DEFAULT_RELIABILITY)

        # Genuine composite score: PCA-derived weights blending stockout risk,
        # overstock, and real supplier reliability (not stockout risk alone).
        health_score = float(np.clip(
            W_STOCKOUT * (1.0 - stockout_risk) +
            W_OVERSTOCK * (1.0 - overstock_flag) +
            W_RELIABILITY * reliability,
            0.0, 1.0
        ))
        
        label = "Healthy"
        if health_score < 0.4: label = "Critical"
        elif health_score < 0.7: label = "At Risk"
        
        results.append({
            "product_id": row['product_id'],
            "store_id": str(row['store_id']) if not pd.isna(row['store_id']) else "",
            "warehouse_id": str(row['warehouse_id']) if not pd.isna(row['warehouse_id']) else "",
            "location_type": str(row['location_type']) if not pd.isna(row['location_type']) else "",
            "stock_level": int(row['stock_qty']),
            "days_cover": round(float(cover), 1),
            "stockout_risk": round(float(stockout_risk), 3),
            "supplier_reliability": round(float(reliability), 3),
            "health_score": round(float(health_score), 2),
            "risk_label": label,
            "overstock_flag": overstock_flag
        })
    return results
