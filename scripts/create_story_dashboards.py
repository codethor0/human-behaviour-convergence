#!/usr/bin/env python3
"""
Create storytelling dashboards in Grafana.
Pushes dashboard JSON files to Grafana via API.
"""
import json
import os
import sys
import requests
from pathlib import Path

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
GRAFANA_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_PASS = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")


def create_dashboard(dashboard_path: Path) -> bool:
    """Create a dashboard in Grafana from JSON file."""
    try:
        with open(dashboard_path, "r") as f:
            dashboard_json = json.load(f)

        # Check if dashboard already exists
        uid = dashboard_json.get("uid")
        if uid:
            check_response = requests.get(
                f"{GRAFANA_URL}/api/dashboards/uid/{uid}",
                auth=(GRAFANA_USER, GRAFANA_PASS),
                timeout=10,
            )
            if check_response.status_code == 200:
                existing = check_response.json()
                dashboard_json["version"] = existing["dashboard"].get("version", 0) + 1

        # Wrap in Grafana API format
        payload = {
            "dashboard": dashboard_json,
            "overwrite": True,  # Allow overwrite for updates
        }

        response = requests.post(
            f"{GRAFANA_URL}/api/dashboards/db",
            auth=(GRAFANA_USER, GRAFANA_PASS),
            json=payload,
            timeout=10,
        )

        if response.status_code in [200, 201]:
            print(
                f"  [OK] Created/Updated: {dashboard_json.get('title', dashboard_path.name)}"
            )
            return True
        else:
            print(
                f"  [FAIL] Failed: {dashboard_json.get('title', dashboard_path.name)} - {response.status_code}"
            )
            print(f"     Error: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  [FAIL] Error creating {dashboard_path}: {e}")
        return False


def main():
    dashboards_dir = Path("infra/grafana/dashboards")

    # New story dashboards to create
    story_dashboards = [
        "executive_storyboard.json",
        "shock_recovery_timeline.json",
        "regional_comparison_storyboard.json",
        "forecast_performance_storybook.json",
    ]

    print("=" * 60)
    print("CREATING STORYTELLING DASHBOARDS")
    print("=" * 60)

    created = 0
    failed = 0

    for dashboard_file in story_dashboards:
        dashboard_path = dashboards_dir / dashboard_file
        if dashboard_path.exists():
            print(f"\nCreating {dashboard_file}...")
            if create_dashboard(dashboard_path):
                created += 1
            else:
                failed += 1
        else:
            print(f"  [WARN]  Not found: {dashboard_path}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"SUMMARY: {created} created, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
