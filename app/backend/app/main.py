from __future__ import annotations

import logging
import os
import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CSV caching structures and TTL configuration
# Cache key is a tuple of (filename, limit) to avoid string collision issues
# Using OrderedDict for LRU cache implementation
_cache: OrderedDict[tuple, List[Dict]] = OrderedDict()
_cache_ttl: Dict[tuple, datetime] = {}
_cache_lock = threading.RLock()  # Thread-safe cache operations
CACHE_DURATION = timedelta(minutes=5)
MAX_CACHE_SIZE = 100  # Prevent unbounded cache growth
MAX_LIMIT = 10000  # Maximum rows that can be requested


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

# SECURITY: Load allowed origins from environment variable
# In production, set ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # No wildcard - security fix
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],  # Only allow needed methods
    allow_headers=["Content-Type", "Authorization"],  # Whitelist headers
    max_age=3600,  # Cache preflight requests for 1 hour
)


@app.get("/health")
def health() -> Dict[str, str]:
    """Health check endpoint returning a simple ok status."""
    return {"status": "ok"}


def _read_csv(name: str, limit: int = 1000) -> List[Dict]:
    """
    Read a CSV from results/ if available; otherwise return a small stub.
    Implements a 5-minute LRU cache to reduce repeated disk I/O.

    Args:
        name: CSV filename to read (e.g., 'forecasts.csv').
        limit: Maximum number of rows to return (default 1000). Must be 0 <= limit <= 10000.

    Returns:
        A list of dictionaries representing rows from the CSV (or a stub).

    Raises:
        ValueError: If limit is negative or exceeds maximum.
    """
    # Validate limit parameter to prevent DoS
    if limit < 0:
        raise ValueError(f"limit must be non-negative, got {limit}")
    if limit > MAX_LIMIT:
        raise ValueError(f"limit must not exceed {MAX_LIMIT}, got {limit}")

    cache_key = (name, limit)
    now = datetime.now()

    # Thread-safe cache check with LRU ordering
    with _cache_lock:
        # Clean up expired entries periodically (every 10th access)
        if len(_cache) > 0 and len(_cache) % 10 == 0:
            expired_keys = [k for k, ttl in _cache_ttl.items() if now >= ttl]
            for k in expired_keys:
                _cache.pop(k, None)
                _cache_ttl.pop(k, None)
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        # Check if cached and not expired
        if cache_key in _cache and cache_key in _cache_ttl:
            if now < _cache_ttl[cache_key]:
                # Move to end (most recently used) for LRU
                _cache.move_to_end(cache_key)
                logger.debug(f"Cache hit: {cache_key}")
                return _cache[cache_key]
            else:
                # Expired - remove it
                del _cache[cache_key]
                del _cache_ttl[cache_key]
                logger.debug(f"Removed expired entry: {cache_key}")

    # Cache miss - perform I/O without holding lock
    logger.info(f"Cache miss: {name}, limit={limit}")
    result = _read_csv_uncached(name, limit)
    logger.info(f"Loaded {len(result)} rows from {name}")

    # Atomic cache update with LRU eviction
    with _cache_lock:
        # Evict least recently used entry if cache is full
        if len(_cache) >= MAX_CACHE_SIZE:
            lru_key = next(iter(_cache))  # First item is LRU in OrderedDict
            del _cache[lru_key]
            del _cache_ttl[lru_key]
            logger.debug(f"Evicted LRU entry: {lru_key}")

        # Add new entry
        _cache[cache_key] = result
        _cache_ttl[cache_key] = now + CACHE_DURATION

    return result


def _read_csv_uncached(name: str, limit: int = 1000) -> List[Dict]:
    """
    Read a CSV from results/ directory without caching, respecting limit.

    SECURITY: Implements path traversal protection by validating filename.
    """
    # SECURITY: Sanitize filename to prevent path traversal attacks
    if not name:
        raise ValueError("Filename cannot be empty")

    # Remove any path components - only allow basename
    safe_name = Path(name).name

    # Validate filename is not empty or special dirs
    if not safe_name or safe_name in (".", ".."):
        raise ValueError("Invalid filename")

    # Check for path traversal attempts in original input
    if ".." in name or "/" in name or "\\" in name:
        raise ValueError(f"Path traversal detected in filename: {name}")

    # Validate file extension
    if not safe_name.endswith(".csv"):
        raise ValueError(f"Only CSV files are allowed, got: {safe_name}")

    if RESULTS_DIR is not None:
        csv_path = RESULTS_DIR / safe_name

        # SECURITY: Verify resolved path is still within RESULTS_DIR
        try:
            resolved_path = csv_path.resolve()
            resolved_results = RESULTS_DIR.resolve()

            # Check if resolved path is within results directory
            if not str(resolved_path).startswith(str(resolved_results)):
                raise ValueError(f"Access denied: path outside results directory")

        except (RuntimeError, OSError) as e:
            logger.warning(f"Path resolution error for {name}: {e}")
            raise ValueError(f"Invalid file path: {name}") from e

        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                if limit:
                    df = df.head(limit)
                return df.to_dict(orient="records")
            except pd.errors.EmptyDataError:
                # Empty CSV, return empty list
                logger.info(f"Empty CSV file: {safe_name}")
                return []
            except pd.errors.ParserError as e:
                # CSV parsing error - let it bubble up
                logger.error(f"CSV parsing error in {safe_name}: {e}")
                raise
            except Exception as e:
                # Any other error, fall through to stubs
                logger.warning(f"Error reading {safe_name}: {e}")
                pass

    # Fallback stubs
    logger.info(f"Returning fallback stub data for {name}")
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
        default=1000,
        ge=0,
        le=MAX_LIMIT,
        description=f"Maximum number of rows to return (0-{MAX_LIMIT})",
    )
) -> Dict[str, List[Dict]]:
    """
    Return forecast data read from CSV (or a stub if missing).

    Args:
        limit: Maximum rows to return (validated by FastAPI Query)

    Returns:
        JSON response with data array

    Raises:
        HTTPException: 400 for validation errors, 404 if file not found, 500 for server errors
    """
    try:
        return {"data": _read_csv("forecasts.csv", limit=limit)}
    except ValueError as e:
        # Validation errors (path traversal, invalid filename, etc.)
        logger.warning(f"Validation error in get_forecasts: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        logger.error(f"Forecasts file not found: {e}")
        raise HTTPException(status_code=404, detail="Forecasts file not found") from e
    except pd.errors.ParserError as e:
        logger.error(f"CSV parsing error: {e}")
        raise HTTPException(status_code=500, detail="Invalid CSV format") from e
    except Exception as e:  # pragma: no cover - safety net
        logger.exception(f"Unexpected error in get_forecasts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/api/metrics")
def get_metrics(
    limit: int = Query(
        default=1000,
        ge=0,
        le=MAX_LIMIT,
        description=f"Maximum number of rows to return (0-{MAX_LIMIT})",
    )
) -> Dict[str, List[Dict]]:
    """
    Return metrics data read from CSV (or a stub if missing).

    Args:
        limit: Maximum rows to return (validated by FastAPI Query)

    Returns:
        JSON response with data array

    Raises:
        HTTPException: 400 for validation errors, 404 if file not found, 500 for server errors
    """
    try:
        return {"data": _read_csv("metrics.csv", limit=limit)}
    except ValueError as e:
        # Validation errors (path traversal, invalid filename, etc.)
        logger.warning(f"Validation error in get_metrics: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        logger.error(f"Metrics file not found: {e}")
        raise HTTPException(status_code=404, detail="Metrics file not found") from e
    except pd.errors.ParserError as e:
        logger.error(f"CSV parsing error: {e}")
        raise HTTPException(status_code=500, detail="Invalid CSV format") from e
    except Exception as e:  # pragma: no cover - safety net
        logger.exception(f"Unexpected error in get_metrics: {e}")
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
