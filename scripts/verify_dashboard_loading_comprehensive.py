#!/usr/bin/env python3
"""Comprehensive Dashboard Loading Verification"""
import json
import os
import sys
import requests
import re

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3100")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")


def extract_dashboard_uids_from_html(html: str) -> set:
    """Extract all dashboard UIDs from HTML."""
    pattern = r'/d/([^?"&\s]+)'
    matches = re.findall(pattern, html)
    return set(matches)


def check_dashboard_exists(uid: str) -> dict:
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


def check_html_for_errors(html: str) -> list:
    """Check HTML for error messages."""
    errors = []
    error_patterns = [
        r"Dashboard not found",
        r"cannot find this dashboard",
        r"404",
        r"Error loading dashboard",
    ]

    for pattern in error_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            errors.extend(matches)

    return list(set(errors))


def main():
    eradicate_dir = os.getenv("ERADICATE_DIR", "/tmp/hbc_eradicate_default")
    os.makedirs(f"{eradicate_dir}/proofs", exist_ok=True)

    print("=== COMPREHENSIVE DASHBOARD LOADING VERIFICATION ===\n")

    # Fetch rendered HTML
    print("Fetching rendered page HTML...")
    try:
        response = requests.get(FRONTEND_URL, timeout=30)
        html = response.text
    except Exception as e:
        print(f"ERROR: Could not fetch frontend: {e}")
        return 1

    # Save HTML
    with open(f"{eradicate_dir}/proofs/rendered_page.html", "w") as f:
        f.write(html)

    # Check for error messages
    print("Checking HTML for error messages...")
    html_errors = check_html_for_errors(html)
    if html_errors:
        print(f"  [WARN]  Found {len(html_errors)} potential error indicators")
        for error in html_errors:
            print(f"    - {error}")
    else:
        print("  [OK] No error messages found in HTML")

    # Extract dashboard UIDs
    print("\nExtracting dashboard UIDs from HTML...")
    uids = extract_dashboard_uids_from_html(html)
    print(f"Found {len(uids)} unique dashboard UIDs\n")

    # Verify each dashboard
    print("Verifying each dashboard...")
    results = {}
    dead_dashboards = []

    for uid in sorted(uids):
        print(f"  {uid}...", end=" ", flush=True)
        result = check_dashboard_exists(uid)
        results[uid] = result

        if result["status"] == "alive":
            print(f"[OK] ALIVE - {result.get('title', '')[:50]}")
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

    print("\n=== SUMMARY ===")
    print(f"Total dashboards in HTML: {len(uids)}")
    print(f"[OK] Alive: {alive_count}")
    print(f"[FAIL] Dead: {dead_count}")
    print(f"[WARN]  Errors: {error_count}")
    print(f"HTML errors found: {len(html_errors)}")

    # Save results
    report = {
        "timestamp": os.popen('date -u +"%Y-%m-%dT%H:%M:%SZ"').read().strip(),
        "frontend_url": FRONTEND_URL,
        "grafana_url": GRAFANA_URL,
        "total_dashboards": len(uids),
        "alive": alive_count,
        "dead": dead_count,
        "errors": error_count,
        "html_errors": html_errors,
        "dead_dashboards": dead_dashboards,
        "all_results": results,
    }

    report_path = f"{eradicate_dir}/proofs/comprehensive_verification.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved: {report_path}")

    if dead_dashboards or html_errors:
        print("\n[FAIL] VERIFICATION FAILED")
        if dead_dashboards:
            print(f"   Dead dashboards: {len(dead_dashboards)}")
        if html_errors:
            print(f"   HTML errors: {len(html_errors)}")
        return 1
    else:
        print("\n[OK] VERIFICATION PASSED - All dashboards loading correctly")
        return 0


if __name__ == "__main__":
    sys.exit(main())
