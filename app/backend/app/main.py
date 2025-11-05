from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Tuple

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# CSV caching structures and TTL configuration
# Cache key is a tuple of (filename, limit) to avoid string collision issues
_cache: Dict[Tuple[str, int], List[Dict]] = {}
_cache_ttl: Dict[Tuple[str, int], datetime] = {}
_cache_lock: Lock = Lock()

# Configuration from environment with sensible defaults
MAX_CACHE_SIZE = int(
    os.getenv("CACHE_MAX_SIZE", "100")
)  # Prevent unbounded cache growth
CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "5"))
CACHE_DURATION = timedelta(minutes=CACHE_TTL_MINUTES)

# Basic logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())


def _find_results_dir(start: Path) -> Optional[Path]:
    """Walk up from start and return the first directory that contains 'results'."""
    start = start.resolve()
    for p in [start] + list(start.parents):
        candidate = p / "results"
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


RESULTS_DIR = _find_results_dir(Path(__file__))

app = FastAPI(title="Behaviour Convergence API", version="0.1.0")

# Configure CORS from environment (comma-separated)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)

# Enable gzip compression for large responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/health")
def health() -> Dict[str, str]:
    """Health check endpoint returning a simple ok status."""
    return {"status": "ok"}


def _cleanup_expired_cache() -> None:
    """Remove expired entries from the cache in a thread-safe manner."""
    now = datetime.now()
    with _cache_lock:
        expired = [key for key, ttl in _cache_ttl.items() if now >= ttl]
        for key in expired:
            _cache.pop(key, None)
            _cache_ttl.pop(key, None)


def _read_csv(name: str, limit: int = 1000) -> List[Dict]:
    """
    Read a CSV from results/ if available; otherwise return a small stub.
    Implements a 5-minute in-memory cache to reduce repeated disk I/O.

    Args:
        name: CSV filename to read (e.g., 'forecasts.csv').
        limit: Maximum number of rows to return (default 1000). Must be >= 0.

    Returns:
        A list of dictionaries representing rows from the CSV (or a stub).

    Raises:
        ValueError: If limit is negative.
    """
    if limit < 0:
        raise ValueError(f"limit must be non-negative, got {limit}")

    # Use tuple for cache key to avoid string collision issues
    cache_key: Tuple[str, int] = (name, limit)
    now = datetime.now()

    # Periodically cleanup expired cache entries (every 10 touches)
    if len(_cache) % 10 == 0:
        _cleanup_expired_cache()

    # Thread-safe cache read
    with _cache_lock:
        if (
            cache_key in _cache
            and cache_key in _cache_ttl
            and now < _cache_ttl[cache_key]
        ):
            # Return a shallow copy to avoid external mutation of cached data
            return list(_cache[cache_key])

    # Cache miss/expired: perform I/O outside lock
    result = _read_csv_uncached(name, limit)

    # Thread-safe cache write with eviction
    with _cache_lock:
        # Re-check validity in case another thread populated it
        if cache_key not in _cache or now >= _cache_ttl.get(cache_key, datetime.min):
            # Implement simple cache eviction: remove oldest entry if cache is full
            if len(_cache) >= MAX_CACHE_SIZE:
                # Remove the oldest entry (first inserted, as dict maintains insertion order)
                oldest_key = next(iter(_cache))
                _cache.pop(oldest_key, None)
                _cache_ttl.pop(oldest_key, None)

            _cache[cache_key] = result
            _cache_ttl[cache_key] = now + CACHE_DURATION
    return result


def _read_csv_uncached(name: str, limit: int = 1000) -> List[Dict]:
    """Read a CSV from results/ directory without caching, respecting limit."""
    if RESULTS_DIR is not None:
        csv_path = RESULTS_DIR / name
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                if limit:
                    df = df.head(limit)
                return df.to_dict(orient="records")
            except pd.errors.EmptyDataError:
                # Empty CSV, return empty list
                return []
            except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as e:
                # CSV parse/encoding errors: log and fall back to stubs
                logger.warning("Failed to parse CSV %s: %s", name, e)
                # Fall through to stubs below

    # Fallback stubs
    if name == "forecasts.csv":
        return [
            {"timestamp": "2025-01-01", "series": "A", "value": 1.0},
            {"timestamp": "2025-01-02", "series": "A", "value": 1.1},
        ]
    if name == "metrics.csv":
        return [
            {"metric": "mae", "value": 0.1234},
            {"metric": "rmse", "value": 0.2345},
        ]
    return []


@app.get("/api/forecasts")
def get_forecasts(
    limit: int = Query(
        default=1000, ge=1, le=10000, description="Maximum rows to return"
    )
) -> Dict[str, List[Dict]]:
    """Return forecast data read from CSV (or a stub if missing)."""
    try:
        return {"data": _read_csv("forecasts.csv", limit=limit)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Forecasts file not found") from e
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=500, detail="Invalid CSV format") from e
    except Exception as e:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/api/metrics")
def get_metrics(
    limit: int = Query(
        default=1000, ge=1, le=10000, description="Maximum rows to return"
    )
) -> Dict[str, List[Dict]]:
    """Return metrics data read from CSV (or a stub if missing)."""
    try:
        return {"data": _read_csv("metrics.csv", limit=limit)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Metrics file not found") from e
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=500, detail="Invalid CSV format") from e
    except Exception as e:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail="Internal server error") from e


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
