# SPDX-License-Identifier: PROPRIETARY
from __future__ import annotations

import asyncio
import os
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import structlog
from fastapi import FastAPI, HTTPException, Query

logger = structlog.get_logger("backend.main")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from app.core.behavior_index import BehaviorIndexComputer
from app.core.explanations import generate_explanation
from app.core.live_monitor import get_live_monitor
from app.core.prediction import BehavioralForecaster
from app.core.regions import get_region_by_id
from app.storage import ForecastDB

# Use relative import to ensure package-local router resolution
from .routers import forecasting, live, playground, public

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

# Configure structlog for consistent logging across the app
# Only configure once to avoid duplicate handlers
if not structlog.is_configured():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if os.getenv("LOG_FORMAT", "text") == "json"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

logger = structlog.get_logger("backend.main")


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
app.include_router(forecasting.router)
app.include_router(playground.router)
app.include_router(live.router)

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


# Background refresh for live monitoring
_refresh_thread: Optional[threading.Thread] = None
_refresh_stop_event = threading.Event()


def _background_refresh_loop() -> None:
    """Background thread that periodically refreshes live monitoring data."""
    monitor = get_live_monitor()
    refresh_interval = monitor.refresh_interval_minutes * 60  # Convert to seconds

    while not _refresh_stop_event.is_set():
        try:
            logger.info("Starting background refresh of live monitoring data")
            monitor.refresh_all_regions()
        except Exception as e:
            logger.error("Error in background refresh", error=str(e), exc_info=True)

        # Wait for refresh interval or until stop event
        if _refresh_stop_event.wait(timeout=refresh_interval):
            break  # Stop event was set


@app.on_event("startup")
def startup_event() -> None:
    """Start background refresh thread on application startup."""
    global _refresh_thread
    if _refresh_thread is None or not _refresh_thread.is_alive():
        _refresh_stop_event.clear()
        _refresh_thread = threading.Thread(target=_background_refresh_loop, daemon=True)
        _refresh_thread.start()
        logger.info("Started background refresh thread for live monitoring")


@app.on_event("shutdown")
def shutdown_event() -> None:
    """Stop background refresh thread on application shutdown."""
    global _refresh_thread
    _refresh_stop_event.set()
    if _refresh_thread and _refresh_thread.is_alive():
        _refresh_thread.join(timeout=5.0)
        logger.info("Stopped background refresh thread for live monitoring")


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
            f"[cache-debug] pre-ensure name={name} limit={limit} "
            f"marker={results_marker} context={_cache_context_marker} "
            f"cache_keys={list(_cache.keys())} max_cache={MAX_CACHE_SIZE} "
            f"id={id(globals())}"
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
                    "cache stats",
                    hits=_cache_hits,
                    misses=_cache_misses,
                    size=len(_cache),
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
                    f"[cache-debug] inserting key={cache_key} "
                    f"size_before={len(_cache)} limit={MAX_CACHE_SIZE} "
                    f"globals_id={id(globals())}"
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
            logger.warning("Failed to read CSV", name=name, error=str(e))
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
        # Prevent recursion by checking if we're already setting this attribute
        # Use object.__getattribute__ to bypass our own __setattr__ method
        try:
            setting_flag = object.__getattribute__(self, "_setting_attr")
            if setting_flag:
                # Already in the middle of setting, bypass hooks
                return ModuleType.__setattr__(self, name, value)
        except AttributeError:
            # Flag doesn't exist yet, that's fine
            pass

        # Mark that we're setting an attribute to prevent recursion
        # Use object.__setattr__ to bypass our own __setattr__ method
        object.__setattr__(self, "_setting_attr", True)
        try:
            # Update the module's namespace first
            ModuleType.__setattr__(self, name, value)
            # Then trigger hooks if needed
            if name == "RESULTS_DIR":
                _on_results_dir_updated(value)
            elif name == "MAX_CACHE_SIZE":
                _on_cache_size_updated(value)
        finally:
            # Always clear the flag using object.__delattr__ to bypass __setattr__
            try:
                object.__delattr__(self, "_setting_attr")
            except AttributeError:
                pass


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


class ForecastCSVItem(BaseModel):
    timestamp: str
    series: str
    value: float


class MetricItem(BaseModel):
    metric: str
    value: float


class ForecastResponse(BaseModel):
    data: List[ForecastCSVItem]


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
    latitude: Optional[float] = Field(
        None,
        ge=-90,
        le=90,
        description="Latitude coordinate (-90 to 90). Required if region_id not provided.",
    )
    longitude: Optional[float] = Field(
        None,
        ge=-180,
        le=180,
        description="Longitude coordinate (-180 to 180). Required if region_id not provided.",
    )
    region_name: str = Field(..., description="Human-readable region name")
    region_id: Optional[str] = Field(
        None,
        description="Region identifier (e.g., 'us_mn', 'city_nyc'). If provided, overrides latitude/longitude.",
    )
    days_back: int = Field(
        default=30, ge=7, le=365, description="Number of historical days to use"
    )
    forecast_horizon: int = Field(
        default=7, ge=1, le=30, description="Number of days to forecast ahead"
    )


class SubIndices(BaseModel):
    """Sub-indices breakdown for a behavior index value."""

    economic_stress: float
    environmental_stress: float
    mobility_activity: float
    digital_attention: float
    public_health_stress: float


class SubIndexContribution(BaseModel):
    """Contribution of a sub-index to the behavior index."""

    value: float
    weight: float
    contribution: float


class SubIndexContributions(BaseModel):
    """Contributions of all sub-indices to the behavior index."""

    economic_stress: SubIndexContribution
    environmental_stress: SubIndexContribution
    mobility_activity: SubIndexContribution
    digital_attention: SubIndexContribution
    public_health_stress: SubIndexContribution


class SubIndexComponent(BaseModel):
    """Component-level detail for a sub-index."""

    id: str
    label: str
    value: float
    weight: float
    source: str


class SubIndexDetailsItem(BaseModel):
    """Details for a single sub-index including components."""

    value: float
    components: List[SubIndexComponent]


class SubIndexDetails(BaseModel):
    """Component-level breakdown for all sub-indices."""

    economic_stress: SubIndexDetailsItem
    environmental_stress: SubIndexDetailsItem
    mobility_activity: SubIndexDetailsItem
    digital_attention: SubIndexDetailsItem
    public_health_stress: SubIndexDetailsItem


class ForecastHistoryItem(BaseModel):
    timestamp: str
    behavior_index: float
    sub_indices: Optional[SubIndices] = None
    subindex_contributions: Optional[SubIndexContributions] = None
    subindex_details: Optional[SubIndexDetails] = None


class ForecastItem(BaseModel):
    timestamp: str
    prediction: float
    lower_bound: float
    upper_bound: float
    sub_indices: Optional[SubIndices] = None
    subindex_contributions: Optional[SubIndexContributions] = None
    subindex_details: Optional[SubIndexDetails] = None


class ComponentExplanation(BaseModel):
    """Component-level explanation."""

    id: str
    label: str
    direction: str  # "up", "down", or "neutral"
    importance: str  # "high", "medium", or "low"
    explanation: str


class SubIndexExplanation(BaseModel):
    """Explanation for a single sub-index."""

    level: str  # "low", "moderate", or "high"
    reason: str
    components: List[ComponentExplanation]


class Explanations(BaseModel):
    """Structured explanations for a forecast."""

    summary: str
    subindices: Dict[str, SubIndexExplanation]


class ForecastResult(BaseModel):
    history: List[ForecastHistoryItem]
    forecast: List[ForecastItem]
    sources: List[str]
    metadata: Dict[str, Any]
    explanation: Optional[str] = None
    explanations: Optional[Explanations] = None


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


def _generate_explanation(
    behavior_index: float,
    sub_indices: Optional[SubIndices],
    sources: List[str],
) -> str:
    """
    Generate human-readable explanation of behavior index.

    Args:
        behavior_index: Current behavior index value (0.0-1.0)
        sub_indices: Sub-index breakdown if available
        sources: List of data sources used

    Returns:
        Human-readable explanation string
    """
    if behavior_index < 0.3:
        level = "low"
        interpretation = "stable, normal behavioral patterns"
    elif behavior_index < 0.6:
        level = "moderate"
        interpretation = "mixed signals or partial disruption"
    else:
        level = "high"
        interpretation = "significant behavioral stress or disruption"

    explanation = f"Behavior Index is {level} ({behavior_index:.2f}), indicating {interpretation}."

    if sub_indices:
        # Identify primary drivers
        drivers = []
        if sub_indices.economic_stress > 0.6:
            drivers.append("elevated economic stress")
        if sub_indices.environmental_stress > 0.6:
            drivers.append("environmental stress")
        if sub_indices.mobility_activity < 0.4:
            drivers.append("reduced mobility activity")
        if sub_indices.digital_attention > 0.6:
            drivers.append("high digital attention")
        if sub_indices.public_health_stress > 0.6:
            drivers.append("public health stress")

        if drivers:
            explanation += f" Primary drivers: {', '.join(drivers)}."
        else:
            explanation += " All sub-indices are within normal ranges."

    if sources:
        explanation += f" Data sources: {', '.join(sources)}."

    return explanation


def _extract_sub_indices(record: Dict[str, Any]) -> Optional[SubIndices]:
    """Extract sub-indices from a record if available."""
    sub_index_keys = [
        "economic_stress",
        "environmental_stress",
        "mobility_activity",
        "digital_attention",
        "public_health_stress",
    ]
    if all(key in record for key in sub_index_keys):
        return SubIndices(
            economic_stress=float(record["economic_stress"]),
            environmental_stress=float(record["environmental_stress"]),
            mobility_activity=float(record["mobility_activity"]),
            digital_attention=float(record["digital_attention"]),
            public_health_stress=float(record["public_health_stress"]),
        )
    return None


@app.post("/api/forecast", response_model=ForecastResult, tags=["forecasting"])
def create_forecast(payload: ForecastRequest) -> ForecastResult:
    """
    Generate behavioral forecast using real-world public data.

    Uses economic (VIX/SPY) and environmental (weather) data to forecast
    human behavioral convergence using exponential smoothing model.

    Args:
        payload: ForecastRequest with latitude/longitude or region_id, region_name, etc.

    Returns:
        ForecastResult with history, forecast, sources, and metadata
        Includes sub-indices breakdown for each history and forecast item if available.
    """
    # Resolve coordinates from region_id if provided
    latitude = payload.latitude
    longitude = payload.longitude

    if payload.region_id:
        region = get_region_by_id(payload.region_id)
        if region is None:
            raise HTTPException(
                status_code=404, detail=f"Region not found: {payload.region_id}"
            )
        latitude = region.latitude
        longitude = region.longitude
        # Optionally update region_name from region if not explicitly provided
        if not payload.region_name or payload.region_name == "":
            payload.region_name = region.name
    elif latitude is None or longitude is None:
        raise HTTPException(
            status_code=400,
            detail="Either region_id or both latitude and longitude must be provided",
        )

    forecaster = BehavioralForecaster()
    result = forecaster.forecast(
        latitude=latitude,
        longitude=longitude,
        region_name=payload.region_name,
        days_back=payload.days_back,
        forecast_horizon=payload.forecast_horizon,
    )

    # Get behavior index computer for contribution analysis and component details
    index_computer = BehaviorIndexComputer()

    # Get harmonized DataFrame from metadata if available (for component extraction)
    harmonized_df = None
    # Get a reference to the actual metadata dict (not a copy)
    if "metadata" in result:
        result_metadata = result["metadata"]
        if "_harmonized_df" in result_metadata:
            harmonized_df = result_metadata["_harmonized_df"]
            # Remove from metadata immediately (it's not JSON-serializable)
            del result_metadata["_harmonized_df"]
    else:
        result_metadata = {}

    # Enrich history and forecast with sub-indices, contributions, and component details
    history_records = []
    latest_behavior_index = 0.5
    latest_sub_indices = None

    for idx, record in enumerate(result.get("history", [])):
        sub_indices = _extract_sub_indices(record)
        # Compute contributions if we have sub-indices
        contributions = None
        subindex_details = None
        if sub_indices:
            import pandas as pd

            row = pd.Series(
                {
                    "behavior_index": float(record["behavior_index"]),
                    "economic_stress": sub_indices.economic_stress,
                    "environmental_stress": sub_indices.environmental_stress,
                    "mobility_activity": sub_indices.mobility_activity,
                    "digital_attention": sub_indices.digital_attention,
                    "public_health_stress": sub_indices.public_health_stress,
                }
            )
            contrib_dict = index_computer.get_contribution_analysis(row)
            contributions = SubIndexContributions(
                economic_stress=SubIndexContribution(**contrib_dict["economic_stress"]),
                environmental_stress=SubIndexContribution(
                    **contrib_dict["environmental_stress"]
                ),
                mobility_activity=SubIndexContribution(
                    **contrib_dict["mobility_activity"]
                ),
                digital_attention=SubIndexContribution(
                    **contrib_dict["digital_attention"]
                ),
                public_health_stress=SubIndexContribution(
                    **contrib_dict["public_health_stress"]
                ),
            )

            # Extract component details if harmonized DataFrame is available
            if harmonized_df is not None and len(harmonized_df) > idx:
                try:
                    details_dict = index_computer.get_subindex_details(
                        harmonized_df, idx
                    )
                    subindex_details = SubIndexDetails(
                        economic_stress=SubIndexDetailsItem(
                            value=details_dict["economic_stress"]["value"],
                            components=[
                                SubIndexComponent(**comp)
                                for comp in details_dict["economic_stress"][
                                    "components"
                                ]
                            ],
                        ),
                        environmental_stress=SubIndexDetailsItem(
                            value=details_dict["environmental_stress"]["value"],
                            components=[
                                SubIndexComponent(**comp)
                                for comp in details_dict["environmental_stress"][
                                    "components"
                                ]
                            ],
                        ),
                        mobility_activity=SubIndexDetailsItem(
                            value=details_dict["mobility_activity"]["value"],
                            components=[
                                SubIndexComponent(**comp)
                                for comp in details_dict["mobility_activity"][
                                    "components"
                                ]
                            ],
                        ),
                        digital_attention=SubIndexDetailsItem(
                            value=details_dict["digital_attention"]["value"],
                            components=[
                                SubIndexComponent(**comp)
                                for comp in details_dict["digital_attention"][
                                    "components"
                                ]
                            ],
                        ),
                        public_health_stress=SubIndexDetailsItem(
                            value=details_dict["public_health_stress"]["value"],
                            components=[
                                SubIndexComponent(**comp)
                                for comp in details_dict["public_health_stress"][
                                    "components"
                                ]
                            ],
                        ),
                    )
                except (IndexError, KeyError, AttributeError) as e:
                    # If extraction fails, log but don't break the response
                    logger.warning("Failed to extract subindex details", error=str(e))

        history_item = ForecastHistoryItem(
            timestamp=str(record["timestamp"]),
            behavior_index=float(record["behavior_index"]),
            sub_indices=sub_indices,
            subindex_contributions=contributions,
            subindex_details=subindex_details,
        )
        history_records.append(history_item)
        # Track latest values for explanation
        latest_behavior_index = float(record["behavior_index"])
        latest_sub_indices = history_item.sub_indices

    forecast_records = []
    for record in result.get("forecast", []):
        sub_indices = _extract_sub_indices(record)
        # Compute contributions for forecast items if we have sub-indices
        contributions = None
        if sub_indices:
            import pandas as pd

            # Use prediction as behavior_index for forecast items
            row = pd.Series(
                {
                    "behavior_index": float(
                        record.get("prediction", record.get("behavior_index", 0.5))
                    ),
                    "economic_stress": sub_indices.economic_stress,
                    "environmental_stress": sub_indices.environmental_stress,
                    "mobility_activity": sub_indices.mobility_activity,
                    "digital_attention": sub_indices.digital_attention,
                    "public_health_stress": sub_indices.public_health_stress,
                }
            )
            contrib_dict = index_computer.get_contribution_analysis(row)
            contributions = SubIndexContributions(
                economic_stress=SubIndexContribution(**contrib_dict["economic_stress"]),
                environmental_stress=SubIndexContribution(
                    **contrib_dict["environmental_stress"]
                ),
                mobility_activity=SubIndexContribution(
                    **contrib_dict["mobility_activity"]
                ),
                digital_attention=SubIndexContribution(
                    **contrib_dict["digital_attention"]
                ),
                public_health_stress=SubIndexContribution(
                    **contrib_dict["public_health_stress"]
                ),
            )

        forecast_item = ForecastItem(
            timestamp=str(record["timestamp"]),
            prediction=float(record["prediction"]),
            lower_bound=float(record["lower_bound"]),
            upper_bound=float(record["upper_bound"]),
            sub_indices=sub_indices,
            subindex_contributions=contributions,
        )
        forecast_records.append(forecast_item)

    # Generate structured explanations
    explanations_obj = None
    if latest_sub_indices:
        # Convert sub_indices to dict
        sub_indices_dict = {
            "economic_stress": latest_sub_indices.economic_stress,
            "environmental_stress": latest_sub_indices.environmental_stress,
            "mobility_activity": latest_sub_indices.mobility_activity,
            "digital_attention": latest_sub_indices.digital_attention,
            "public_health_stress": latest_sub_indices.public_health_stress,
        }

        # Get subindex details for latest record if available
        subindex_details_dict = None
        if history_records and history_records[-1].subindex_details:
            details = history_records[-1].subindex_details
            subindex_details_dict = {
                "economic_stress": {
                    "value": details.economic_stress.value,
                    "components": [
                        {
                            "id": c.id,
                            "label": c.label,
                            "value": c.value,
                            "weight": c.weight,
                            "source": c.source,
                        }
                        for c in details.economic_stress.components
                    ],
                },
                "environmental_stress": {
                    "value": details.environmental_stress.value,
                    "components": [
                        {
                            "id": c.id,
                            "label": c.label,
                            "value": c.value,
                            "weight": c.weight,
                            "source": c.source,
                        }
                        for c in details.environmental_stress.components
                    ],
                },
                "mobility_activity": {
                    "value": details.mobility_activity.value,
                    "components": [
                        {
                            "id": c.id,
                            "label": c.label,
                            "value": c.value,
                            "weight": c.weight,
                            "source": c.source,
                        }
                        for c in details.mobility_activity.components
                    ],
                },
                "digital_attention": {
                    "value": details.digital_attention.value,
                    "components": [
                        {
                            "id": c.id,
                            "label": c.label,
                            "value": c.value,
                            "weight": c.weight,
                            "source": c.source,
                        }
                        for c in details.digital_attention.components
                    ],
                },
                "public_health_stress": {
                    "value": details.public_health_stress.value,
                    "components": [
                        {
                            "id": c.id,
                            "label": c.label,
                            "value": c.value,
                            "weight": c.weight,
                            "source": c.source,
                        }
                        for c in details.public_health_stress.components
                    ],
                },
            }

        try:
            explanations_dict = generate_explanation(
                behavior_index=latest_behavior_index,
                sub_indices=sub_indices_dict,
                subindex_details=subindex_details_dict,
                region_name=payload.region_name,
            )

            # Convert to Pydantic models
            explanations_obj = Explanations(
                summary=explanations_dict["summary"],
                subindices={
                    key: SubIndexExplanation(
                        level=val["level"],
                        reason=val["reason"],
                        components=[
                            ComponentExplanation(**comp) for comp in val["components"]
                        ],
                    )
                    for key, val in explanations_dict["subindices"].items()
                },
            )
        except Exception as e:
            # If explanation generation fails, log but don't break the response
            logger.warning("Failed to generate explanations", error=str(e))

    # Generate legacy text explanation (for backward compatibility)
    explanation = _generate_explanation(
        latest_behavior_index, latest_sub_indices, result.get("sources", [])
    )

    # Prepare metadata for response (remove non-serializable items like DataFrames)
    # Use the already-cleaned metadata from result_metadata (DataFrame already removed)
    metadata = result_metadata.copy()
    metadata["explanation"] = explanation

    # Store forecast in database (if available)
    try:
        db = ForecastDB()
        db.save_forecast(
            region_name=payload.region_name,
            latitude=latitude,
            longitude=longitude,
            model_name=metadata.get("model_type", "ExponentialSmoothing"),
            behavior_index=latest_behavior_index,
            sub_indices=(
                {
                    "economic_stress": latest_sub_indices.economic_stress,
                    "environmental_stress": latest_sub_indices.environmental_stress,
                    "mobility_activity": latest_sub_indices.mobility_activity,
                    "digital_attention": latest_sub_indices.digital_attention,
                    "public_health_stress": latest_sub_indices.public_health_stress,
                }
                if latest_sub_indices
                else None
            ),
            metadata=metadata,
        )
    except Exception as e:
        # Database is optional, log but don't fail
        logger.warning("Failed to save forecast to database", error=str(e))

    return ForecastResult(
        history=history_records,
        forecast=forecast_records,
        sources=result.get("sources", []),
        metadata=metadata,
        explanation=explanation,
        explanations=explanations_obj,
    )


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "app.backend.app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
