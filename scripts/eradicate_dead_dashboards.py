#!/usr/bin/env python3
"""Dashboard Eradication Protocol - Triage Phase"""
import json
import os
import re
from pathlib import Path
from typing import Set


# Extract all dashboard UIDs from frontend code
def extract_dashboard_uids_from_frontend() -> Set[str]:
    """Extract all dashboard UIDs referenced in frontend code."""
    frontend_dir = Path("app/frontend/src")
    uids = set()

    # Pattern to match dashboardUid="..."
    pattern = r'dashboardUid=["\']([^"\']+)["\']'

    for file_path in frontend_dir.rglob("*.tsx"):
        content = file_path.read_text()
        matches = re.findall(pattern, content)
        uids.update(matches)

    # Also check for dashboard.uid in ops.tsx
    ops_file = frontend_dir / "pages" / "ops.tsx"
    if ops_file.exists():
        content = ops_file.read_text()
        # Look for dashboard objects
        uid_matches = re.findall(r'"uid":\s*["\']([^"\']+)["\']', content)
        uids.update(uid_matches)

    return uids


# Get all existing dashboard UIDs from Grafana JSON files
def get_existing_dashboard_uids() -> Set[str]:
    """Get all dashboard UIDs from Grafana JSON files."""
    dashboards_dir = Path("infra/grafana/dashboards")
    uids = set()

    for json_file in dashboards_dir.glob("*.json"):
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                if "uid" in data:
                    uids.add(data["uid"])
        except Exception as e:
            print(f"Error reading {json_file}: {e}")

    return uids


# Main triage
def main():
    eradicate_dir = (
        f"/tmp/hbc_eradicate_{os.popen('date +%Y%m%d_%H%M%S').read().strip()}"
    )
    os.makedirs(f"{eradicate_dir}/triage", exist_ok=True)

    print("=== PHASE 0: TRIAGE - IDENTIFYING DEAD DASHBOARDS ===\n")

    # Extract UIDs from frontend
    frontend_uids = extract_dashboard_uids_from_frontend()
    print(f"Found {len(frontend_uids)} unique dashboard UIDs in frontend:")
    for uid in sorted(frontend_uids):
        print(f"  - {uid}")

    # Get existing UIDs from Grafana
    existing_uids = get_existing_dashboard_uids()
    print(f"\nFound {len(existing_uids)} existing dashboard UIDs in Grafana:")
    for uid in sorted(existing_uids):
        print(f"  - {uid}")

    # Find missing dashboards
    missing_uids = frontend_uids - existing_uids
    print(f"\n=== MISSING DASHBOARDS ({len(missing_uids)}) ===")
    for uid in sorted(missing_uids):
        print(f"  [FAIL] {uid}")

    # Find dashboards that exist but aren't used
    unused_uids = existing_uids - frontend_uids
    if unused_uids:
        print(f"\n=== UNUSED DASHBOARDS ({len(unused_uids)}) ===")
        for uid in sorted(unused_uids):
            print(f"  [WARN]  {uid} (exists but not referenced in frontend)")

    # Save triage report
    triage_report = {
        "frontend_uids": sorted(list(frontend_uids)),
        "existing_uids": sorted(list(existing_uids)),
        "missing_uids": sorted(list(missing_uids)),
        "unused_uids": sorted(list(unused_uids)),
    }

    report_path = f"{eradicate_dir}/triage/dead_dashboards.json"
    with open(report_path, "w") as f:
        json.dump(triage_report, f, indent=2)

    print(f"\nTriage report saved to: {report_path}")

    if missing_uids:
        print(
            f"\n[WARN]  ACTION REQUIRED: {len(missing_uids)} dashboards need to be created"
        )
        return sorted(list(missing_uids))
    else:
        print("\n[OK] NO DEAD DASHBOARDS FOUND - All frontend UIDs exist in Grafana")
        return []


if __name__ == "__main__":
    missing = main()
    if missing:
        exit(1)
    else:
        exit(0)
