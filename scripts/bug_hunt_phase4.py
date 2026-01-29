#!/usr/bin/env python3
"""Phase 4: Integration Bug Detection"""
import json
import os
import sys
import requests
import time
from datetime import datetime

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8100")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")


def validate_api(endpoint, expected_status, bug_dir):
    """Validate API endpoint returns expected status."""
    try:
        response = requests.get(endpoint, timeout=10)
        status = response.status_code

        if status != expected_status:
            return {
                "bug_id": f"API-{int(time.time())}-{hash(endpoint) % 10000}",
                "severity": "P0",
                "category": "api_contract",
                "endpoint": endpoint,
                "expected_status": expected_status,
                "actual_status": status,
                "response_body": response.text[:500],
                "fix_suggestion": "Fix backend route handler",
            }
        return None
    except requests.exceptions.ConnectionError:
        return {
            "bug_id": f"API-CONN-{int(time.time())}",
            "severity": "P0",
            "category": "api_connection",
            "endpoint": endpoint,
            "symptom": "Cannot connect to endpoint",
            "fix_suggestion": "Check if service is running",
        }
    except Exception as e:
        return {
            "bug_id": f"API-ERROR-{int(time.time())}",
            "severity": "P1",
            "category": "api_error",
            "endpoint": endpoint,
            "error": str(e),
            "fix_suggestion": "Investigate endpoint error",
        }


def check_prometheus_targets(bug_dir):
    """Check Prometheus scrape targets."""
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets", timeout=10)
        if response.status_code == 200:
            data = response.json()
            targets = data.get("data", {}).get("activeTargets", [])

            down_targets = [t for t in targets if t.get("health") != "up"]

            if down_targets:
                return {
                    "bug_id": f"SCRAPE-{int(time.time())}",
                    "severity": "P0",
                    "category": "prometheus_scrape",
                    "symptom": f"{len(down_targets)} Prometheus targets are down",
                    "down_targets": down_targets,
                    "fix_suggestion": "Check target endpoints, restart Prometheus, verify network connectivity",
                }
        return None
    except Exception as e:
        return {
            "bug_id": f"SCRAPE-ERROR-{int(time.time())}",
            "severity": "P1",
            "category": "prometheus_check_error",
            "error": str(e),
        }


def main():
    bug_dir = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
    os.makedirs(f"{bug_dir}/registry", exist_ok=True)

    print("=== PHASE 4: INTEGRATION BUG DETECTION ===\n")

    bugs = []

    # Check API endpoints
    print("Validating API endpoints...")
    api_checks = [
        (f"{BACKEND_URL}/health", 200),
        (f"{BACKEND_URL}/metrics", 200),
        (f"{BACKEND_URL}/api/forecasting/models", 200),
        (f"{PROMETHEUS_URL}/-/healthy", 200),
        (f"{GRAFANA_URL}/api/health", 200),
    ]

    for endpoint, expected_status in api_checks:
        print(f"  Checking {endpoint}...", end=" ", flush=True)
        bug = validate_api(endpoint, expected_status, bug_dir)
        if bug:
            print("[FAIL] BUG FOUND")
            bugs.append(bug)
        else:
            print("[OK] OK")

    # Check Prometheus targets
    print("\nChecking Prometheus scrape targets...")
    bug = check_prometheus_targets(bug_dir)
    if bug:
        print(f"[FAIL] BUG FOUND: {bug['symptom']}")
        bugs.append(bug)
    else:
        print("[OK] All targets up")

    # Save bugs
    if bugs:
        with open(f"{bug_dir}/registry/integration_bugs.json", "w") as f:
            json.dump(
                {"audit_timestamp": datetime.utcnow().isoformat() + "Z", "bugs": bugs},
                f,
                indent=2,
            )
        print(f"\n[OK] Found {len(bugs)} integration bugs")
        print(f"   Saved to: {bug_dir}/registry/integration_bugs.json")
    else:
        print("\n[OK] No integration bugs found")

    return 0


if __name__ == "__main__":
    sys.exit(main())
