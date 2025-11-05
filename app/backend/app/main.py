from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# CSV caching structures and TTL configuration
_cache: Dict[str, List[Dict]] = {}
_cache_ttl: Dict[str, datetime] = {}
CACHE_DURATION = timedelta(minutes=5)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    """Health check endpoint returning a simple ok status."""
    return {"status": "ok"}


def _read_csv(name: str, limit: int = 1000) -> List[Dict]:
    """
    Read a CSV from results/ if available; otherwise return a small stub.
    Implements a 5-minute in-memory cache to reduce repeated disk I/O.

    Args:
        name: CSV filename to read (e.g., 'forecasts.csv').
        limit: Maximum number of rows to return (default 1000).

    Returns:
        A list of dictionaries representing rows from the CSV (or a stub).
    """
    cache_key = f"{name}:{limit}"
    now = datetime.now()
    if cache_key in _cache and cache_key in _cache_ttl and now < _cache_ttl[cache_key]:
        return _cache[cache_key]

    # Cache miss/expired
    result = _read_csv_uncached(name, limit)
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
            except Exception:
                # Any other error, fall through to stubs
                pass

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
def get_forecasts() -> Dict[str, List[Dict]]:
    """Return forecast data read from CSV (or a stub if missing)."""
    try:
        return {"data": _read_csv("forecasts.csv")}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Forecasts file not found") from e
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=500, detail="Invalid CSV format") from e
    except Exception as e:  # pragma: no cover - safety net
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/api/metrics")
def get_metrics() -> Dict[str, List[Dict]]:
    """Return metrics data read from CSV (or a stub if missing)."""
    try:
        return {"data": _read_csv("metrics.csv")}
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
