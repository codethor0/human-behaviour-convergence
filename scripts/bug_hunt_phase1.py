#!/usr/bin/env python3
"""Phase 1: Data Integrity Bug Detection"""
import json
import os
import sys
import requests
import time
from datetime import datetime

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")


def check_metric_integrity(metric, min_expected, bug_dir):
    """Check if metric has data for minimum expected regions."""
    try:
        query = f"count(count by (region) ({metric}))"
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get("data", {}).get("result", [])
            if results:
                count = int(float(results[0]["value"][1]))
                if count < min_expected:
                    return {
                        "bug_id": f"DATA-{int(time.time())}-{hash(metric) % 10000}",
                        "severity": "P0",
                        "category": "missing_data",
                        "metric": metric,
                        "symptom": f"Only {count} regions have data, expected >= {min_expected}",
                        "evidence": {"prometheus_query": query, "result": data},
                        "root_cause": "Backend not emitting metric for all regions or Prometheus not scraping",
                        "fix_suggestion": "1. Check backend /metrics endpoint. 2. Verify Prometheus scrape config. 3. Force data generation for missing regions.",
                        "reproduction": f"curl -s '{PROMETHEUS_URL}/api/v1/query?query={query}'",
                    }
        return None
    except Exception as e:
        return {
            "bug_id": f"DATA-ERROR-{int(time.time())}",
            "severity": "P1",
            "category": "data_check_error",
            "metric": metric,
            "symptom": f"Could not check metric: {str(e)}",
            "fix_suggestion": "Check Prometheus connectivity",
        }


def check_staleness(metric, max_age_seconds, bug_dir):
    """Check if metric data is stale."""
    try:
        query = f"{metric}"
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get("data", {}).get("result", [])
            if results:
                latest_timestamp = int(float(results[0]["value"][0]))
                current_time = int(time.time())
                age = current_time - latest_timestamp

                if age > max_age_seconds:
                    return {
                        "bug_id": f"STALE-{int(time.time())}-{hash(metric) % 10000}",
                        "severity": "P1",
                        "category": "stale_data",
                        "metric": metric,
                        "symptom": f"Data is {age} seconds old, max allowed: {max_age_seconds}",
                        "root_cause": "Backend stopped emitting or Prometheus stopped scraping",
                        "fix_suggestion": "1. Check backend health. 2. Check Prometheus targets. 3. Check scrape interval.",
                        "reproduction": f"Check timestamp of latest {metric} value",
                    }
        return None
    except Exception:
        return None


def main():
    bug_dir = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
    os.makedirs(f"{bug_dir}/registry", exist_ok=True)

    print("=== PHASE 1: DATA INTEGRITY BUG DETECTION ===\n")

    bugs = []

    # Check critical metrics
    print("Checking metric integrity...")
    metrics_to_check = [
        ("behavior_index", 5),
        ("parent_subindex_value", 5),
        ("child_subindex_value", 5),
        ("forecast_points_generated", 3),
        ("forecast_last_updated_timestamp_seconds", 3),
    ]

    for metric, min_expected in metrics_to_check:
        print(f"  Checking {metric}...", end=" ", flush=True)
        bug = check_metric_integrity(metric, min_expected, bug_dir)
        if bug:
            print("[FAIL] BUG FOUND")
            bugs.append(bug)
        else:
            print("[OK] OK")

    # Check staleness
    print("\nChecking data staleness...")
    metrics_to_check_staleness = [
        ("behavior_index", 7200),  # 2 hours
        ("forecast_last_updated_timestamp_seconds", 3600),  # 1 hour
    ]

    for metric, max_age in metrics_to_check_staleness:
        print(f"  Checking {metric} freshness...", end=" ", flush=True)
        bug = check_staleness(metric, max_age, bug_dir)
        if bug:
            print("[FAIL] STALE")
            bugs.append(bug)
        else:
            print("[OK] FRESH")

    # Save bugs
    if bugs:
        with open(f"{bug_dir}/registry/data_bugs.json", "w") as f:
            json.dump(
                {"audit_timestamp": datetime.utcnow().isoformat() + "Z", "bugs": bugs},
                f,
                indent=2,
            )
        print(f"\n[OK] Found {len(bugs)} data integrity bugs")
        print(f"   Saved to: {bug_dir}/registry/data_bugs.json")
    else:
        print("\n[OK] No data integrity bugs found")

    return 0


if __name__ == "__main__":
    sys.exit(main())
