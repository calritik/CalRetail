"""
CalRetail Dash — shared FastAPI client.

Mirrors the old frontend/components/utils.py api_get/api_post, with a short
TTL cache standing in for Streamlit's st.cache_data(ttl=300).
"""
import time

import requests

API_BASE = "http://127.0.0.1:8000"
DEFAULT_TTL = 300  # seconds

_cache: dict = {}  # key -> (expires_at, value)


def _cache_key(method: str, path: str, payload: dict | None) -> str:
    return f"{method}:{path}:{sorted((payload or {}).items())}"


def api_get(path: str, params: dict | None = None, ttl: int = DEFAULT_TTL):
    """GET the FastAPI backend. Returns None (never raises) on any failure."""
    key = _cache_key("GET", path, params)
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=30,
                          proxies={"http": None, "https": None})
        r.raise_for_status()
        data = r.json()
        if ttl:
            _cache[key] = (time.time() + ttl, data)
        return data
    except Exception:
        return None


def api_post(path: str, payload: dict | None = None):
    """POST to the FastAPI backend. Not cached (mutating/compute call)."""
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=30,
                          proxies={"http": None, "https": None})
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def clear_cache():
    _cache.clear()


def backend_is_up() -> bool:
    return api_get("/health", ttl=5) is not None
