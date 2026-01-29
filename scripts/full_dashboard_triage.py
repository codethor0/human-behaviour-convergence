#!/usr/bin/env python3
"""Full Dashboard Triage - Check all pages for dashboard references"""
import json
import os
import re
import sys
import requests
from pathlib import Path
from typing import Dict, Set

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3100")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")

# All pages to check
PAGES_TO_CHECK = [
    "/",
    "/command-center",
    "/forecast",
    "/playground",
    "/live",
    "/history",
    "/advanced-visualizations",
]


def extract_dashboard_uids_from_html(html: str) -> Set[str]:
    """Extract all dashboard UIDs from HTML."""
    # Pattern: /d/DASHBOARD_UID?...
    pattern = r'/d/([^?"&\s]+)'
    matches = re.findall(pattern, html)
    return set(matches)


def extract_uids_from_code() -> Set[str]:
    """Extract dashboard UIDs from frontend code."""
    uids = set()
    frontend_dir = Path("app/frontend/src")

    # Search for dashboardUid, dashboard-uid, etc.
    patterns = [
        r'dashboardUid=["\']([^"\']+)["\']',
        r'dashboard-uid=["\']([^"\']+)["\']',
        r'dashboard_uid=["\']([^"\']+)["\']',
        r'uid=["\']([^"\']+)["\']',  # In GrafanaEmbed components
    ]

    for file_path in frontend_dir.rglob("*.tsx"):
        try:
            content = file_path.read_text()
            for pattern in patterns:
                matches = re.findall(pattern, content)
                uids.update(matches)
        except:
            pass

    return uids


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
    except Exception as e:
        return {
            "exists": False,
            "status": "error",
            "error": str(e),
        }


def main():
    eradicate_dir = os.getenv("ERADICATE_DIR", "/tmp/hbc_eradicate_default")
    os.makedirs(f"{eradicate_dir}/triage", exist_ok=True)

    print("=== FULL DASHBOARD TRIAGE ===\n")

    # Collect UIDs from all sources
    all_uids = set()
    page_results = {}

    # 1. Check rendered HTML from all pages
    print("Checking rendered HTML from all pages...")
    for page in PAGES_TO_CHECK:
        try:
            url = f"{FRONTEND_URL}{page}"
            print(f"  Fetching {url}...", end=" ", flush=True)
            response = requests.get(url, timeout=30)
            html = response.text

            uids = extract_dashboard_uids_from_html(html)
            all_uids.update(uids)
            page_results[page] = {
                "url": url,
                "uids": list(uids),
                "count": len(uids),
            }
            print(f"Found {len(uids)} UIDs")
        except Exception as e:
            print(f"ERROR: {e}")
            page_results[page] = {
                "url": url,
                "error": str(e),
            }

    # 2. Extract from code
    print("\nExtracting UIDs from frontend code...")
    code_uids = extract_uids_from_code()
    all_uids.update(code_uids)
    print(f"Found {len(code_uids)} UIDs in code")

    print(f"\nTotal unique dashboard UIDs found: {len(all_uids)}\n")

    # 3. Check each dashboard
    print("Checking each dashboard...")
    results = {}
    dead_dashboards = []

    for uid in sorted(all_uids):
        print(f"  {uid}...", end=" ", flush=True)
        result = check_dashboard_exists(uid)
        results[uid] = result

        if result["status"] == "alive":
            print("[OK] ALIVE")
        elif result["status"] == "dead":
            print("[FAIL] DEAD")
            dead_dashboards.append(uid)
        else:
            print(f"[WARN]  ERROR: {result.get('error', '')}")
            dead_dashboards.append(uid)

    # Summary
    alive_count = len([r for r in results.values() if r["status"] == "alive"])
    dead_count = len([r for r in results.values() if r["status"] == "dead"])
    error_count = len([r for r in results.values() if r["status"] == "error"])

    print("\n=== TRIAGE SUMMARY ===")
    print(f"Total unique UIDs found: {len(all_uids)}")
    print(f"[OK] Alive: {alive_count}")
    print(f"[FAIL] Dead: {dead_count}")
    print(f"[WARN]  Errors: {error_count}")

    # Save results
    report = {
        "total_uids": len(all_uids),
        "alive": alive_count,
        "dead": dead_count,
        "errors": error_count,
        "dead_dashboards": dead_dashboards,
        "page_results": page_results,
        "all_results": results,
    }

    report_path = f"{eradicate_dir}/triage/full_triage_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved: {report_path}")

    if dead_dashboards:
        print("\n[FAIL] DEAD DASHBOARDS FOUND:")
        for uid in dead_dashboards:
            print(f"  - {uid}: {results[uid].get('error', 'Unknown error')}")
        return 1
    else:
        print("\n[OK] NO DEAD DASHBOARDS FOUND")
        return 0


if __name__ == "__main__":
    sys.exit(main())
