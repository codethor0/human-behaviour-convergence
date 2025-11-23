# SPDX-License-Identifier: MIT-0
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from app.core.prediction import BehavioralForecaster

# Use relative import to ensure package-local router resolution
from .routers import public

# CSV caching structures and TTL configuration
# Cache key is a tuple of (filename, limit) to avoid string collision issues
_cache: Dict[Tuple[str, int], List[Dict]] = {}
_cache_ttl: Dict[Tuple[str, int], datetime] = {}
_cache_context_marker: Optional[str] = None
_cache_lock: Lock = Lock()
_cache_hits: int = 0
_cache_misses: int = 0

# Configuration from environment with sensible defaults
MAX_CACHE_SIZE = int(
    os.getenv("CACHE_MAX_SIZE", "100")
)  # Prevent unbounded cache growth
CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "5"))
CACHE_DURATION = timedelta(minutes=CACHE_TTL_MINUTES)


# Structured logging: enable JSON format if LOG_FORMAT=json
LOG_FORMAT = os.getenv("LOG_FORMAT", "text")
logger = logging.getLogger(__name__)
if not logger.handlers:
    if LOG_FORMAT == "json":
        import json

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_record = {
                    "level": record.levelname,
                    "time": self.formatTime(record, self.datefmt),
                    "name": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info:
                    log_record["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_record)

        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    else:
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

app = FastAPI(title="Behavior Convergence API", version="0.1.0")

# Register routers
app.include_router(public.router)

# Configure CORS from environment (comma-separated)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
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
    global _cache_hits, _cache_misses

    # Defensively restrict allowed CSV names (unknown names return empty)
    allowed_names = {"forecasts.csv", "metrics.csv"}
    if name not in allowed_names:
        # Unknown names return empty (test expectation)
        return []

    # Use tuple for cache key to avoid string collision issues
    active_results_dir = _get_results_dir()
    results_marker = "None"
    if active_results_dir is not None:
        try:
            results_marker = str(active_results_dir.resolve())
        except (OSError, RuntimeError):
            results_marker = str(active_results_dir)

    if os.getenv("CACHE_DEBUG") == "1":
        print(
            f"[cache-debug] pre-ensure name={name} limit={limit} marker={results_marker} "
            f"context={_cache_context_marker} cache_keys={list(_cache.keys())} "
            f"max_cache={MAX_CACHE_SIZE} id={id(globals())}"
        )

    _ensure_cache_context(results_marker)

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
            _cache_hits += 1
            # Periodically log cache stats every 50 lookups
            total = _cache_hits + _cache_misses
            if total % 50 == 0:
                logger.info(
                    "cache stats: hits=%d misses=%d size=%d",
                    _cache_hits,
                    _cache_misses,
                    len(_cache),
                )
            return list(_cache[cache_key])

    # Cache miss/expired: perform I/O outside lock
    result = _read_csv_uncached(name, limit)

    # Thread-safe cache write with eviction
    with _cache_lock:
        _cache_misses += 1
        # Re-check validity in case another thread populated it
        if cache_key not in _cache or now >= _cache_ttl.get(cache_key, datetime.min):
            _enforce_cache_limit()
            if os.getenv("CACHE_DEBUG") == "1":
                print(
                    f"[cache-debug] inserting key={cache_key} size_before={len(_cache)} "
                    f"limit={MAX_CACHE_SIZE} globals_id={id(globals())}"
                )
            _cache[cache_key] = result
            _cache_ttl[cache_key] = now + CACHE_DURATION
    return result


async def _read_csv_async(name: str, limit: int = 1000) -> List[Dict]:
    """Async wrapper to avoid blocking the event loop during CSV I/O."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _read_csv(name, limit))


def _read_csv_uncached(name: str, limit: int = 1000) -> List[Dict]:
    """Read a CSV from results/ directory without caching, respecting limit."""
    active_results_dir = _get_results_dir()
    if active_results_dir is not None:
        csv_path = active_results_dir / name
        try:
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                if limit:
                    df = df.head(limit)
                records = df.to_dict(orient="records")
                return _normalize_records(name, records)
        except Exception as e:
            logger.warning("Failed to read CSV %s: %s", name, e)
    # mypy: strict

    # Fallback stubs
    if name == "forecasts.csv":
        return _normalize_records(
            name,
            [
                {"timestamp": "2025-01-01", "series": "A", "value": 1.0},
                {"timestamp": "2025-01-02", "series": "A", "value": 1.1},
            ],
        )
    if name == "metrics.csv":
        return _normalize_records(
            name,
            [
                {"metric": "mae", "value": 0.1234},
                {"metric": "rmse", "value": 0.2345},
            ],
        )
    return _normalize_records(name, [])


def _ensure_cache_context(marker: str) -> None:
    """Reset cache if the underlying results directory changes."""
    global _cache_context_marker
    with _cache_lock:
        if _cache_context_marker != marker:
            _cache.clear()
            _cache_ttl.clear()
            _cache_context_marker = marker


def _enforce_cache_limit() -> None:
    """Ensure cache does not exceed MAX_CACHE_SIZE entries."""
    limit = _get_cache_limit()
    # Treat non-positive limits as disabling caching
    if limit <= 0:
        _cache.clear()
        _cache_ttl.clear()
        return

    while len(_cache) >= limit:
        oldest_key = next(iter(_cache))
        _cache.pop(oldest_key, None)
        _cache_ttl.pop(oldest_key, None)


def _on_results_dir_updated(value: Optional[Path]) -> None:
    """Reset cache context when RESULTS_DIR is reassigned."""
    global _cache_context_marker
    with _cache_lock:
        _cache.clear()
        _cache_ttl.clear()
        _cache_context_marker = None
    if os.getenv("CACHE_DEBUG") == "1":
        print(f"[cache-debug] RESULTS_DIR updated -> {value}")


def _on_cache_size_updated(value: int) -> None:
    """Coerce cache size updates to int and enforce limits immediately."""
    global MAX_CACHE_SIZE
    try:
        MAX_CACHE_SIZE = int(value)
    except (TypeError, ValueError):
        MAX_CACHE_SIZE = 0
    with _cache_lock:
        _enforce_cache_limit()
    if os.getenv("CACHE_DEBUG") == "1":
        print(f"[cache-debug] MAX_CACHE_SIZE updated -> {MAX_CACHE_SIZE}")


class _MainModule(ModuleType):
    """Module subclass to intercept attribute updates from monkeypatch/tests."""

    def __setattr__(
        self, name: str, value: Any
    ) -> None:  # pragma: no cover - simple hook
        ModuleType.__setattr__(self, name, value)
        if name == "RESULTS_DIR":
            _on_results_dir_updated(value)
        elif name == "MAX_CACHE_SIZE":
            _on_cache_size_updated(value)


sys.modules[__name__].__class__ = _MainModule


def _get_results_dir() -> Optional[Path]:
    """Resolve current RESULTS_DIR, considering shims and overrides."""
    app_module = sys.modules.get("app")
    if app_module is not None:
        main_mod = getattr(app_module, "main", None)
        if main_mod is not None:
            namespace = vars(main_mod)
            if "RESULTS_DIR" in namespace:
                return namespace["RESULTS_DIR"]
    # Fallback to module-level variable (direct access, not globals().get())
    return RESULTS_DIR


def _get_cache_limit() -> int:
    """Resolve current MAX_CACHE_SIZE, considering shims and overrides."""
    app_module = sys.modules.get("app")
    if app_module is not None:
        main_mod = getattr(app_module, "main", None)
        if main_mod is not None:
            namespace = vars(main_mod)
            if "MAX_CACHE_SIZE" in namespace:
                try:
                    return int(namespace["MAX_CACHE_SIZE"])
                except (TypeError, ValueError):
                    return 0
    # Fallback to module-level variable (direct access, not globals().get())
    try:
        return int(MAX_CACHE_SIZE)
    except (TypeError, ValueError):
        return 0


def _get_version() -> str:
    return os.getenv("APP_VERSION", app.version)


def _get_commit() -> str:
    commit = os.getenv("GIT_COMMIT")
    if commit:
        return commit
    repo_root = Path(__file__).resolve().parents[3]
    git_dir = repo_root / ".git"
    if git_dir.exists():
        try:
            import subprocess

            return (
                subprocess.check_output(
                    ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"],
                    stderr=subprocess.DEVNULL,
                )
                .decode("utf-8")
                .strip()
            )
        except Exception:
            return "unknown"
    return "unknown"


def _normalize_records(
    name: str, records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Ensure records conform to API schemas irrespective of CSV column names."""
    if name == "forecasts.csv":
        return [_normalize_forecast_row(row) for row in records]
    if name == "metrics.csv":
        return [_normalize_metric_row(row) for row in records]
    return records


def _normalize_forecast_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single forecast record to required keys."""
    timestamp = row.get("timestamp")
    if timestamp is None:
        # Fall back to generic datetime string if missing
        timestamp = datetime.now().isoformat()
    else:
        timestamp = str(timestamp)

    series = row.get("series")
    if series is None:
        for candidate in ("location_id", "series_id", "region", "id"):
            if row.get(candidate) is not None:
                series = row[candidate]
                break
    if series is None:
        series = "unknown"
    series = str(series)

    value = row.get("value")
    if value is None:
        for candidate in (
            "forecast_mean",
            "forecast",
            "forecast_value",
            "forecast_median",
        ):
            if row.get(candidate) is not None:
                value = row[candidate]
                break
    if value is None:
        value = 0.0
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0

    return {"timestamp": timestamp, "series": series, "value": value}


def _normalize_metric_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a single metric record to required keys."""
    metric = row.get("metric")
    if metric is None:
        # Attempt to infer from other common column names
        for candidate in ("name", "label", "id"):
            if row.get(candidate) is not None:
                metric = row[candidate]
                break
    if metric is None:
        metric = "unknown"
    metric = str(metric)

    value = row.get("value")
    if value is None:
        for candidate in ("score", "metric_value", "mean"):
            if row.get(candidate) is not None:
                value = row[candidate]
                break
    if value is None:
        value = 0.0
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0

    return {"metric": metric, "value": value}


# ====== Response Models ======


class ForecastItem(BaseModel):
    timestamp: str
    series: str
    value: float


class MetricItem(BaseModel):
    metric: str
    value: float


class ForecastResponse(BaseModel):
    data: List[ForecastItem]


class MetricsResponse(BaseModel):
    data: List[MetricItem]


class CacheStatus(BaseModel):
    hits: int
    misses: int
    size: int
    max_size: int
    ttl_minutes: int


class StatusResponse(BaseModel):
    ok: bool = True
    version: str
    commit: str


class ForecastRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate (-90 to 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate (-180 to 180)")
    region_name: str = Field(..., description="Human-readable region name")
    days_back: int = Field(default=30, ge=7, le=365, description="Number of historical days to use")
    forecast_horizon: int = Field(default=7, ge=1, le=30, description="Number of days to forecast ahead")


class ForecastHistoryItem(BaseModel):
    timestamp: str
    behavior_index: float


class ForecastItem(BaseModel):
    timestamp: str
    prediction: float
    lower_bound: float
    upper_bound: float


class ForecastResult(BaseModel):
    history: List[ForecastHistoryItem]
    forecast: List[ForecastPredictionItem]
    sources: List[str]
    metadata: Dict[str, Any]


@app.get("/api/forecasts", response_model=ForecastResponse)
async def get_forecasts(
    limit: int = Query(
        default=1000, ge=1, le=10000, description="Maximum rows to return"
    )
) -> Dict[str, List[Dict]]:
    """Return forecast data read from CSV (or a stub if missing)."""
    try:
        data = await _read_csv_async("forecasts.csv", limit=limit)
        return {"data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Forecasts file not found") from e
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=500, detail="Invalid CSV format") from e
    except Exception as e:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics(
    limit: int = Query(
        default=1000, ge=1, le=10000, description="Maximum rows to return"
    )
) -> Dict[str, List[Dict]]:
    """Return metrics data read from CSV (or a stub if missing)."""
    try:
        data = await _read_csv_async("metrics.csv", limit=limit)
        return {"data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Metrics file not found") from e
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=500, detail="Invalid CSV format") from e
    except Exception as e:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/api/status", response_model=StatusResponse, tags=["meta"])
def get_status() -> StatusResponse:
    """Return service metadata."""
    return StatusResponse(version=_get_version(), commit=_get_commit())


@app.get("/api/cache/status", response_model=CacheStatus, tags=["meta"])
def get_cache_status() -> CacheStatus:
    """Return basic cache stats for observability."""
    with _cache_lock:
        # Access module-level variables directly (not globals().get())
        hits = _cache_hits
        misses = _cache_misses
        size = len(_cache)
    return CacheStatus(
        hits=hits,
        misses=misses,
        size=size,
        max_size=MAX_CACHE_SIZE,
        ttl_minutes=CACHE_TTL_MINUTES,
    )


@app.post("/api/forecast", response_model=ForecastResult, tags=["forecasting"])
def create_forecast(payload: ForecastRequest) -> ForecastResult:
    """
    Generate behavioral forecast using real-world public data.

    Uses economic (VIX/SPY) and environmental (weather) data to forecast
    human behavioral convergence using exponential smoothing model.

    Args:
        payload: ForecastRequest with latitude, longitude, region_name, etc.

    Returns:
        ForecastResult with history, forecast, sources, and metadata
    """
    forecaster = BehavioralForecaster()
    result = forecaster.forecast(
        latitude=payload.latitude,
        longitude=payload.longitude,
        region_name=payload.region_name,
        days_back=payload.days_back,
        forecast_horizon=payload.forecast_horizon,
    )
    return ForecastResult(**result)


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "app.backend.app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
