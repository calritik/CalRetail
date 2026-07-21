"""
CalRetail — Data loader utility
Loads processed CSVs into memory for AI services (cached on startup).
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

from backend.config.settings import settings

PROC = Path(settings.DATA_PROCESSED_DIR)


DATE_COLS = {
    "transaction_date", "timestamp", "shipped_date", "delivered_date", 
    "start_date", "end_date", "review_date", "created_at", "updated_at", 
    "order_date", "delivery_date", "estimated_delivery", "effective_date"
}

@lru_cache(maxsize=None)
def load_df(name: str) -> pd.DataFrame:
    """Load a processed CSV and cache in memory."""
    path = PROC / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    for col in df.columns:
        if col in DATE_COLS:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def get_customers() -> pd.DataFrame:
    return load_df("customers")

def get_products() -> pd.DataFrame:
    return load_df("products")

def get_transactions() -> pd.DataFrame:
    return load_df("transactions")

def get_inventory() -> pd.DataFrame:
    return load_df("inventory")

def get_reviews() -> pd.DataFrame:
    return load_df("customer_reviews")

def get_tickets() -> pd.DataFrame:
    return load_df("support_tickets")

def get_browsing() -> pd.DataFrame:
    return load_df("browsing_history")

def get_pricing_history() -> pd.DataFrame:
    return load_df("pricing_history")

def get_competitor_pricing() -> pd.DataFrame:
    return load_df("competitor_pricing")

def get_promotions() -> pd.DataFrame:
    return load_df("promotions")

def get_campaigns() -> pd.DataFrame:
    return load_df("marketing_campaigns")

def get_orders() -> pd.DataFrame:
    return load_df("orders")

def get_stores() -> pd.DataFrame:
    return load_df("stores")

def get_warehouses() -> pd.DataFrame:
    return load_df("warehouses")

def get_suppliers() -> pd.DataFrame:
    return load_df("suppliers")

def get_shipments() -> pd.DataFrame:
    return load_df("shipments")

def get_returns() -> pd.DataFrame:
    return load_df("returns")

def get_inventory_movements() -> pd.DataFrame:
    return load_df("inventory_movements")

def get_wishlist() -> pd.DataFrame:
    return load_df("wishlist")

def get_feature_customers() -> pd.DataFrame:
    return load_df("feature_customers")

def get_feature_products() -> pd.DataFrame:
    return load_df("feature_products")

def get_feature_daily_sales() -> pd.DataFrame:
    return load_df("feature_daily_sales")

def get_feature_inventory_health() -> pd.DataFrame:
    return load_df("feature_inventory_health")

def get_feature_buying_intent() -> pd.DataFrame:
    return load_df("feature_buying_intent")

def get_feature_tickets() -> pd.DataFrame:
    return load_df("feature_tickets")
