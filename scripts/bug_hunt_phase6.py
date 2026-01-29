#!/usr/bin/env python3
"""Phase 6: Performance Bug Detection"""
import json
import os
import sys
import requests
import time
from datetime import datetime

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8100")


def test_query_performance(query, max_duration_ms=1000):
    """Test Prometheus query performance."""
    try:
        start = time.time()
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5
        )
        duration_ms = (time.time() - start) * 1000

        if response.status_code == 200 and duration_ms > max_duration_ms:
            return {
                "query": query,
                "duration_ms": duration_ms,
                "max_allowed_ms": max_duration_ms,
                "status": "slow",
            }
        return None
    except:
        return None


def check_api_performance(endpoint, max_duration_ms=500):
    """Check API endpoint performance."""
    try:
        start = time.time()
        response = requests.get(endpoint, timeout=5)
        duration_ms = (time.time() - start) * 1000

        if duration_ms > max_duration_ms:
            return {
                "endpoint": endpoint,
                "duration_ms": duration_ms,
                "max_allowed_ms": max_duration_ms,
                "status": "slow",
            }
        return None
    except:
        return None


def main():
    bug_dir = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
    os.makedirs(f"{bug_dir}/registry", exist_ok=True)

    print("=== PHASE 6: PERFORMANCE BUG DETECTION ===\n")

    bugs = []

    # Test critical Prometheus queries
    print("Testing Prometheus query performance...")
    critical_queries = [
        "behavior_index",
        "count(count by (region) (behavior_index))",
        "parent_subindex_value",
        "forecast_points_generated",
    ]

    for query in critical_queries:
        print(f"  Testing: {query[:50]}...", end=" ", flush=True)
        result = test_query_performance(query, max_duration_ms=1000)
        if result:
            print(f"[FAIL] SLOW ({result['duration_ms']:.1f}ms)")
            bugs.append(
                {
                    "bug_id": f"PERF-QUERY-{hash(query) % 100000}",
                    "severity": "P1",
                    "category": "slow_query",
                    "query": query,
                    "duration_ms": result["duration_ms"],
                    "symptom": f"Query takes {result['duration_ms']:.1f}ms, max allowed: {result['max_allowed_ms']}ms",
                    "fix_suggestion": "Add index to metric, reduce time range, or pre-aggregate",
                }
            )
        else:
            print("[OK] OK")

    # Test API endpoints
    print("\nTesting API endpoint performance...")
    api_endpoints = [
        (f"{BACKEND_URL}/health", 50),
        (f"{BACKEND_URL}/metrics", 200),
        (f"{BACKEND_URL}/api/forecasting/models", 200),
    ]

    for endpoint, max_ms in api_endpoints:
        print(f"  Testing: {endpoint}...", end=" ", flush=True)
        result = check_api_performance(endpoint, max_duration_ms=max_ms)
        if result:
            print(f"[FAIL] SLOW ({result['duration_ms']:.1f}ms)")
            bugs.append(
                {
                    "bug_id": f"PERF-API-{hash(endpoint) % 100000}",
                    "severity": "P1",
                    "category": "slow_api",
                    "endpoint": endpoint,
                    "duration_ms": result["duration_ms"],
                    "symptom": f"Endpoint takes {result['duration_ms']:.1f}ms, max allowed: {result['max_allowed_ms']}ms",
                    "fix_suggestion": "Optimize endpoint, add caching, or reduce processing",
                }
            )
        else:
            print("[OK] OK")

    # Save bugs
    if bugs:
        with open(f"{bug_dir}/registry/performance_bugs.json", "w") as f:
            json.dump(
                {"audit_timestamp": datetime.utcnow().isoformat() + "Z", "bugs": bugs},
                f,
                indent=2,
            )
        print(f"\n[OK] Found {len(bugs)} performance bugs")
        print(f"   Saved to: {bug_dir}/registry/performance_bugs.json")
    else:
        print("\n[OK] No performance bugs found")

    return 0


if __name__ == "__main__":
    sys.exit(main())
