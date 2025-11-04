from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


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
    return {"status": "ok"}


def _read_csv(name: str, limit: int = 1000) -> List[Dict]:
    """Read a CSV from results/ if available; otherwise return a small stub.

    Returns at most 'limit' rows to keep payloads small.
    """
    # Attempt to read from results/
    if RESULTS_DIR is not None:
        csv_path = RESULTS_DIR / name
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            if limit:
                df = df.head(limit)
            return df.to_dict(orient="records")

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
    try:
        return {"data": _read_csv("forecasts.csv")}
    except Exception as e:  # pragma: no cover - quick dev safety
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics")
def get_metrics() -> Dict[str, List[Dict]]:
    try:
        return {"data": _read_csv("metrics.csv")}
    except Exception as e:  # pragma: no cover - quick dev safety
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
