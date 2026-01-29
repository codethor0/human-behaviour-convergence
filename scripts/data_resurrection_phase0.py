#!/usr/bin/env python3
"""Phase 0: Dashboard Inventory & Mapping"""
import os
import sys
import requests
import csv

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3100")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")


def get_grafana_dashboards():
    """Get all dashboards from Grafana."""
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/search?type=dash-db",
            auth=(GRAFANA_USER, GRAFANA_PASSWORD),
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"ERROR: Could not fetch Grafana dashboards: {e}")
        return []


def extract_ui_dashboards():
    """Extract dashboard references from UI."""
    # From the previous eradication protocol, we know these exist
    # Let's get them from the rendered HTML
    try:
        response = requests.get(FRONTEND_URL, timeout=30)
        html = response.text

        # Extract dashboard UIDs from iframe srcs
        import re

        pattern = r'/d/([^?"&\s]+)'
        uids = set(re.findall(pattern, html))

        return sorted(list(uids))
    except Exception as e:
        print(f"ERROR: Could not fetch frontend: {e}")
        return []


def main():
    resurrection_dir = os.getenv("RESURRECTION_DIR", "/tmp/hbc_resurrection_default")
    os.makedirs(f"{resurrection_dir}/inventory", exist_ok=True)

    print("=== PHASE 0: DASHBOARD INVENTORY & MAPPING ===\n")

    # Get Grafana dashboards
    print("Fetching dashboards from Grafana...")
    grafana_dashboards = get_grafana_dashboards()
    grafana_map = {d["uid"]: d["title"] for d in grafana_dashboards}
    print(f"Found {len(grafana_dashboards)} dashboards in Grafana\n")

    # Get UI dashboards
    print("Extracting dashboard UIDs from UI...")
    ui_uids = extract_ui_dashboards()
    print(f"Found {len(ui_uids)} dashboard UIDs in UI\n")

    # Create mapping
    print("Creating dashboard mapping...")
    mapping = []

    for uid in ui_uids:
        status = "EXISTS" if uid in grafana_map else "MISSING"
        title = grafana_map.get(uid, "Unknown")
        mapping.append(
            {
                "ui_label": title,
                "expected_uid": uid,
                "actual_uid": uid if uid in grafana_map else "",
                "status": status,
                "data_present": "UNKNOWN",
            }
        )

    # Save mapping CSV
    csv_path = f"{resurrection_dir}/inventory/dashboard_mapping.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ui_label",
                "expected_uid",
                "actual_uid",
                "status",
                "data_present",
            ],
        )
        writer.writeheader()
        writer.writerows(mapping)

    print(f"Mapping saved to: {csv_path}\n")

    # Save Grafana inventory
    grafana_path = f"{resurrection_dir}/inventory/grafana_actual.txt"
    with open(grafana_path, "w") as f:
        for d in grafana_dashboards:
            f.write(f"{d['uid']}|{d['title']}\n")

    print(f"Grafana inventory saved to: {grafana_path}\n")

    # Summary
    existing = len([m for m in mapping if m["status"] == "EXISTS"])
    missing = len([m for m in mapping if m["status"] == "MISSING"])

    print("=== SUMMARY ===")
    print(f"Total UI dashboards: {len(mapping)}")
    print(f"[OK] Existing in Grafana: {existing}")
    print(f"[FAIL] Missing from Grafana: {missing}")

    if missing > 0:
        print("\n[WARN]  WARNING: Some dashboards are missing from Grafana")
        for m in mapping:
            if m["status"] == "MISSING":
                print(f"  - {m['expected_uid']}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
