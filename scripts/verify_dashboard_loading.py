#!/usr/bin/env python3
"""Verify all dashboards load correctly via Grafana API"""
import json
import os
import sys
import requests
from pathlib import Path
from typing import Dict

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")


def get_grafana_auth():
    """Get Grafana auth token or use basic auth."""
    # Try to get auth token first
    try:
        response = requests.post(
            f"{GRAFANA_URL}/api/auth/keys",
            json={"name": "verify_script", "role": "Viewer"},
            auth=(GRAFANA_USER, GRAFANA_PASSWORD),
            timeout=5,
        )
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json()['key']}"}
    except:
        pass

    # Fallback to basic auth
    return (GRAFANA_USER, GRAFANA_PASSWORD)


def check_dashboard_exists(uid: str, auth) -> Dict:
    """Check if dashboard exists in Grafana."""
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/dashboards/uid/{uid}",
            headers=auth if isinstance(auth, dict) else None,
            auth=auth if not isinstance(auth, dict) else None,
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "exists": True,
                "status": "alive",
                "title": data.get("dashboard", {}).get("title", "Unknown"),
                "uid": data.get("dashboard", {}).get("uid", uid),
            }
        elif response.status_code == 404:
            return {
                "exists": False,
                "status": "dead",
                "error": "Dashboard not found",
            }
        else:
            return {
                "exists": False,
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }
    except requests.exceptions.ConnectionError:
        return {
            "exists": False,
            "status": "error",
            "error": "Cannot connect to Grafana. Is it running?",
        }
    except Exception as e:
        return {
            "exists": False,
            "status": "error",
            "error": str(e),
        }


def main():
    eradicate_dir = (
        f"/tmp/hbc_eradicate_{os.popen('date +%Y%m%d_%H%M%S').read().strip()}"
    )
    os.makedirs(f"{eradicate_dir}/proofs", exist_ok=True)

    print("=== PHASE 1: FORENSIC ANALYSIS - CHECKING DASHBOARD STATUS ===\n")
    print(f"Grafana URL: {GRAFANA_URL}\n")

    # Get auth
    auth = get_grafana_auth()

    # Load triage report
    triage_file = Path("/tmp/hbc_eradicate_*/triage/dead_dashboards.json")
    triage_files = list(
        Path("/tmp").glob("hbc_eradicate_*/triage/dead_dashboards.json")
    )

    if not triage_files:
        print("No triage report found. Running triage first...")
        os.system("python3 scripts/eradicate_dead_dashboards.py")
        triage_files = list(
            Path("/tmp").glob("hbc_eradicate_*/triage/dead_dashboards.json")
        )

    if triage_files:
        with open(triage_files[-1], "r") as f:
            triage = json.load(f)
        frontend_uids = triage["frontend_uids"]
    else:
        # Fallback: extract from frontend
        from eradicate_dead_dashboards import extract_dashboard_uids_from_frontend

        frontend_uids = list(extract_dashboard_uids_from_frontend())

    print(f"Checking {len(frontend_uids)} dashboards...\n")

    results = {}
    dead_dashboards = []

    for uid in sorted(frontend_uids):
        print(f"Checking: {uid}...", end=" ", flush=True)
        result = check_dashboard_exists(uid, auth)
        results[uid] = result

        if result["status"] == "alive":
            print(f"[OK] ALIVE - {result.get('title', '')}")
        elif result["status"] == "dead":
            print(f"[FAIL] DEAD - {result.get('error', '')}")
            dead_dashboards.append(uid)
        else:
            print(f"[WARN]  ERROR - {result.get('error', '')}")
            dead_dashboards.append(uid)

    # Save results
    results_file = f"{eradicate_dir}/proofs/dashboard_status.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== SUMMARY ===")
    print(f"Total dashboards checked: {len(frontend_uids)}")
    print(f"Alive: {len([r for r in results.values() if r['status'] == 'alive'])}")
    print(f"Dead: {len(dead_dashboards)}")
    print(f"Errors: {len([r for r in results.values() if r['status'] == 'error'])}")

    if dead_dashboards:
        print("\n[FAIL] DEAD DASHBOARDS FOUND:")
        for uid in dead_dashboards:
            print(f"  - {uid}: {results[uid].get('error', 'Unknown error')}")
        print(f"\nResults saved to: {results_file}")
        return dead_dashboards
    else:
        print("\n[OK] ALL DASHBOARDS ARE ALIVE")
        print(f"Results saved to: {results_file}")
        return []


if __name__ == "__main__":
    dead = main()
    if dead:
        sys.exit(1)
    else:
        sys.exit(0)
