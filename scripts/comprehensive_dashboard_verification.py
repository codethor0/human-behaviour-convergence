#!/usr/bin/env python3
"""Comprehensive Dashboard Verification - Check all dashboards from rendered HTML"""
import json
import os
import re
import sys
import requests
from typing import Dict, Set

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3100")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")


def extract_dashboard_uids_from_html(html: str) -> Set[str]:
    """Extract all dashboard UIDs from rendered HTML."""
    # Pattern: /d/DASHBOARD_UID?...
    pattern = r'/d/([^?"&\s]+)'
    matches = re.findall(pattern, html)
    return set(matches)


def check_dashboard_exists(uid: str) -> Dict:
    """Check if dashboard exists in Grafana."""
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/dashboards/uid/{uid}",
            auth=(GRAFANA_USER, GRAFANA_PASSWORD),
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
                "error": f"HTTP {response.status_code}",
            }
    except requests.exceptions.ConnectionError:
        return {
            "exists": False,
            "status": "error",
            "error": "Cannot connect to Grafana",
        }
    except Exception as e:
        return {
            "exists": False,
            "status": "error",
            "error": str(e),
        }


def main():
    eradicate_dir = (
        f"/tmp/hbc_eradicate_visual_{os.popen('date +%Y%m%d_%H%M%S').read().strip()}"
    )
    os.makedirs(f"{eradicate_dir}/proofs", exist_ok=True)

    print("=== COMPREHENSIVE DASHBOARD VERIFICATION ===\n")
    print(f"Frontend URL: {FRONTEND_URL}")
    print(f"Grafana URL: {GRAFANA_URL}\n")

    # Fetch rendered HTML
    print("Fetching rendered page HTML...")
    try:
        response = requests.get(FRONTEND_URL, timeout=30)
        html = response.text
    except Exception as e:
        print(f"ERROR: Could not fetch frontend: {e}")
        return 1

    # Save HTML for analysis
    with open(f"{eradicate_dir}/proofs/rendered_page.html", "w") as f:
        f.write(html)

    # Extract dashboard UIDs
    print("Extracting dashboard UIDs from HTML...")
    uids = extract_dashboard_uids_from_html(html)
    print(f"Found {len(uids)} unique dashboard UIDs in rendered HTML\n")

    # Check each dashboard
    results = {}
    dead_dashboards = []

    for uid in sorted(uids):
        print(f"Checking: {uid}...", end=" ", flush=True)
        result = check_dashboard_exists(uid)
        results[uid] = result

        if result["status"] == "alive":
            print(f"[OK] ALIVE - {result.get('title', '')}")
        elif result["status"] == "dead":
            print(f"[FAIL] DEAD - {result.get('error', '')}")
            dead_dashboards.append(uid)
        else:
            print(f"[WARN]  ERROR - {result.get('error', '')}")
            dead_dashboards.append(uid)

    # Summary
    alive_count = len([r for r in results.values() if r["status"] == "alive"])
    dead_count = len([r for r in results.values() if r["status"] == "dead"])
    error_count = len([r for r in results.values() if r["status"] == "error"])

    print("\n=== SUMMARY ===")
    print(f"Total dashboards in rendered HTML: {len(uids)}")
    print(f"[OK] Alive: {alive_count}")
    print(f"[FAIL] Dead: {dead_count}")
    print(f"[WARN]  Errors: {error_count}")

    # Save results
    report = {
        "timestamp": os.popen('date -u +"%Y-%m-%dT%H:%M:%SZ"').read().strip(),
        "frontend_url": FRONTEND_URL,
        "grafana_url": GRAFANA_URL,
        "total_dashboards": len(uids),
        "alive": alive_count,
        "dead": dead_count,
        "errors": error_count,
        "dead_dashboards": dead_dashboards,
        "all_results": results,
    }

    report_path = f"{eradicate_dir}/proofs/comprehensive_verification.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved: {report_path}")

    if dead_dashboards:
        print("\n[FAIL] DEAD DASHBOARDS FOUND:")
        for uid in dead_dashboards:
            print(f"  - {uid}: {results[uid].get('error', 'Unknown error')}")
        return 1
    else:
        print("\n[OK] ALL DASHBOARDS ARE ALIVE - NO DEAD LINKS")
        return 0


if __name__ == "__main__":
    sys.exit(main())
