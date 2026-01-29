#!/usr/bin/env python3
"""Create missing dashboards via Grafana API"""
import json
import os
import sys
import requests
from pathlib import Path

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")

DEAD_DASHBOARDS = [
    "baselines",
    "classical-models",
    "cross-domain-correlation",
    "forecast-overview",
    "model-performance",
    "regional-signals",
]


def get_auth_token():
    """Get Grafana API token."""
    try:
        response = requests.post(
            f"{GRAFANA_URL}/api/auth/keys",
            json={"name": "dashboard_creator", "role": "Admin", "secondsToLive": 3600},
            auth=(GRAFANA_USER, GRAFANA_PASSWORD),
            timeout=5,
        )
        if response.status_code == 200:
            return response.json()["key"]
    except Exception as e:
        print(f"Warning: Could not get auth token: {e}")
    return None


def load_dashboard_json(uid: str) -> dict:
    """Load dashboard JSON file."""
    # Map UID to filename
    uid_to_file = {
        "baselines": "baselines.json",
        "classical-models": "classical_models.json",
        "cross-domain-correlation": "cross_domain_correlation.json",
        "forecast-overview": "forecast_overview.json",
        "model-performance": "model_performance.json",
        "regional-signals": "regional_signals.json",
    }

    filename = uid_to_file.get(uid)
    if not filename:
        return None

    filepath = Path(f"infra/grafana/dashboards/{filename}")
    if not filepath.exists():
        print(f"Error: Dashboard file not found: {filepath}")
        return None

    with open(filepath, "r") as f:
        return json.load(f)


def create_dashboard_via_api(dashboard_data: dict, auth_token: str = None) -> bool:
    """Create dashboard via Grafana API."""
    # Wrap in Grafana API format
    payload = {
        "dashboard": dashboard_data,
        "overwrite": True,  # Overwrite if exists
    }

    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
        auth = None
    else:
        auth = (GRAFANA_USER, GRAFANA_PASSWORD)

    try:
        response = requests.post(
            f"{GRAFANA_URL}/api/dashboards/db",
            json=payload,
            headers=headers,
            auth=auth,
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            print(
                f"  [OK] Created: {result.get('dashboard', {}).get('title', 'Unknown')} (UID: {result.get('dashboard', {}).get('uid', 'unknown')})"
            )
            return True
        else:
            print(f"  [FAIL] Failed: HTTP {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def main():
    print("=== PHASE 2: RESURRECTION - CREATING MISSING DASHBOARDS ===\n")
    print(f"Grafana URL: {GRAFANA_URL}\n")

    # Get auth token
    auth_token = get_auth_token()
    if auth_token:
        print("[OK] Got Grafana auth token\n")
    else:
        print("[WARN]  Using basic auth (token creation failed)\n")

    results = {}

    for uid in DEAD_DASHBOARDS:
        print(f"Processing: {uid}...")

        # Load dashboard JSON
        dashboard_data = load_dashboard_json(uid)
        if not dashboard_data:
            print("  [FAIL] Could not load dashboard JSON")
            results[uid] = {"status": "error", "message": "JSON file not found"}
            continue

        # Verify UID matches
        if dashboard_data.get("uid") != uid:
            print(
                f"  [WARN]  UID mismatch: JSON has '{dashboard_data.get('uid')}', expected '{uid}'"
            )
            dashboard_data["uid"] = uid  # Fix it

        # Create dashboard
        success = create_dashboard_via_api(dashboard_data, auth_token)
        results[uid] = {"status": "success" if success else "failed"}
        print()

    # Summary
    print("=== SUMMARY ===")
    successful = [uid for uid, r in results.items() if r.get("status") == "success"]
    failed = [uid for uid, r in results.items() if r.get("status") != "success"]

    print(f"Successfully created: {len(successful)}")
    for uid in successful:
        print(f"  [OK] {uid}")

    if failed:
        print(f"\nFailed: {len(failed)}")
        for uid in failed:
            print(f"  [FAIL] {uid}")

    # Save results
    eradicate_dir = (
        f"/tmp/hbc_eradicate_{os.popen('date +%Y%m%d_%H%M%S').read().strip()}"
    )
    os.makedirs(f"{eradicate_dir}/proofs", exist_ok=True)
    with open(f"{eradicate_dir}/proofs/resurrection_results.json", "w") as f:
        json.dump(results, f, indent=2)

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
