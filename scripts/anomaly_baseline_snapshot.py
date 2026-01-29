#!/usr/bin/env python3
"""
Phase 0: Pull baseline distribution snapshots from Prometheus for anomaly tuning.
Writes /tmp/hbc_anomaly_<ts>/baseline_stats.json (or env OUT_DIR).
"""
import json
import os
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("requests required: pip install requests")
    sys.exit(1)

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
OUT_DIR = os.getenv(
    "OUT_DIR", f"/tmp/hbc_anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
)
WINDOW = os.getenv("WINDOW", "30d")

METRICS = [
    "behavior_index",
    "parent_subindex_value",
    "forecast_points_generated",
    "hbc_data_source_last_success_timestamp_seconds",
]


def query_range(metric: str, window: str = WINDOW) -> list:
    end = datetime.utcnow().timestamp()
    # Approximate 30d in seconds
    step = 3600  # 1h
    start = end - (30 * 24 * 3600) if "30d" in window else end - (7 * 24 * 3600)
    url = f"{PROMETHEUS_URL}/api/v1/query_range"
    params = {
        "query": metric,
        "start": start,
        "end": end,
        "step": step,
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "success":
            return []
        return data.get("data", {}).get("result", [])
    except Exception as e:
        print(f"Query failed for {metric}: {e}")
        return []


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out = {"window": WINDOW, "prometheus": PROMETHEUS_URL, "metrics": {}}
    for name in METRICS:
        results = query_range(name)
        if not results:
            out["metrics"][name] = {"error": "no data or query failed"}
            continue
        values = []
        for series in results:
            for _, v in series.get("values", []):
                try:
                    values.append(float(v))
                except (TypeError, ValueError):
                    pass
        if not values:
            out["metrics"][name] = {"error": "no numeric values"}
            continue
        n = len(values)
        s = sorted(values)
        out["metrics"][name] = {
            "count": n,
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / n,
            "p50": s[int(0.5 * (n - 1))] if n else None,
            "p05": s[int(0.05 * (n - 1))] if n else None,
            "p95": s[int(0.95 * (n - 1))] if n else None,
        }
    path = os.path.join(OUT_DIR, "baseline_stats.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
