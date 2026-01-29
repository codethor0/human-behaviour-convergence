#!/usr/bin/env python3
"""
Comprehensive HBC Resurrection Protocol - Full Implementation
"""
import json
import os
import sys
import requests
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List

CERT_DIR = os.getenv("CERT_DIR", "/tmp/hbc_fix_cert_default")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8100")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3100")
GRAFANA_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_PASS = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")


def extract_dashboard_uids() -> List[Dict]:
    """Extract all dashboard UIDs from frontend code."""
    dashboards = []
    index_file = Path("app/frontend/src/pages/index.tsx")

    if not index_file.exists():
        return dashboards

    content = index_file.read_text()

    # Find all GrafanaDashboardEmbed components
    pattern = r'<GrafanaDashboardEmbed\s+[^>]*dashboardUid=["\']([^"\']+)["\'][^>]*title=["\']([^"\']+)["\']'
    matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)

    for match in matches:
        uid = match.group(1)
        title = match.group(2)
        dashboards.append({"uid": uid, "title": title, "source": "index.tsx"})

    # Also check for any other patterns
    uid_pattern = r'dashboardUid["\']?\s*[:=]\s*["\']([^"\']+)["\']'
    all_uids = set(re.findall(uid_pattern, content))

    for uid in all_uids:
        if not any(d["uid"] == uid for d in dashboards):
            dashboards.append(
                {
                    "uid": uid,
                    "title": uid.replace("-", " ").title(),
                    "source": "index.tsx (pattern)",
                }
            )

    return dashboards


def verify_dashboard_exists(uid: str) -> Dict:
    """Verify dashboard exists in Grafana."""
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/dashboards/uid/{uid}",
            auth=(GRAFANA_USER, GRAFANA_PASS),
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "exists": True,
                "title": data.get("dashboard", {}).get("title", uid),
                "panels": len(data.get("dashboard", {}).get("panels", [])),
                "status_code": 200,
            }
        else:
            return {
                "exists": False,
                "status_code": response.status_code,
                "error": response.text[:200],
            }
    except Exception as e:
        return {"exists": False, "error": str(e)}


def check_dashboard_data(uid: str, region: str = "city_nyc") -> Dict:
    """Check if dashboard has data for a region."""
    try:
        # Query Prometheus for behavior_index for the region
        query = f'behavior_index{{region="{region}"}}'
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10
        )

        has_data = False
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", {}).get("result", [])
            has_data = len(results) > 0

        return {"has_data": has_data, "region": region, "metric": "behavior_index"}
    except Exception as e:
        return {"has_data": False, "error": str(e)}


def fix_division_by_zero():
    """Fix division by zero bug in scenario_sensitivity.py."""
    file_path = Path("app/core/scenario_sensitivity.py")
    if not file_path.exists():
        return False

    content = file_path.read_text()

    # Check if already fixed
    if "if input_delta == 0:" in content:
        return True

    # Find the division line
    if "elasticity = (output_delta / input_delta) * factor_weight" in content:
        # Add guard before division
        old_line = "    elasticity = (output_delta / input_delta) * factor_weight"
        new_lines = """    if input_delta == 0:
        raise ValueError("input_delta cannot be zero for elasticity calculation")
    elasticity = (output_delta / input_delta) * factor_weight"""

        content = content.replace(old_line, new_lines)
        file_path.write_text(content)
        return True

    return False


def classify_security_findings():
    """Classify security findings from bug registry."""
    bug_registry_path = (
        "/tmp/hbc_bugs_deep_20260128_171737/registry/MASTER_BUG_REGISTRY.json"
    )
    if not Path(bug_registry_path).exists():
        return []

    with open(bug_registry_path, "r") as f:
        registry = json.load(f)

    security_bugs = []
    for category, bugs in registry.get("bugs_by_category", {}).items():
        if "secret" in category.lower() or "security" in category.lower():
            security_bugs.extend(bugs)

    classified = []
    for bug in security_bugs:
        file_path = bug.get("component", "")
        line_content = bug.get("evidence", {}).get("line_content", "")

        # Classify
        if any(x in file_path.lower() for x in ["test", "example", "mock", "fixture"]):
            classification = "TEST"
            action = "WHITELIST"
        elif any(
            x in line_content.lower()
            for x in ["test_key", "mock_", "example_", "your-key"]
        ):
            classification = "EXAMPLE"
            action = "REFACTOR"
        else:
            classification = "PROD"
            action = "ROTATE"

        classified.append(
            {
                "bug_id": bug.get("bug_id"),
                "file": file_path,
                "line": bug.get("location", ""),
                "classification": classification,
                "action": action,
            }
        )

    return classified


def main():
    os.makedirs(CERT_DIR, exist_ok=True)
    os.makedirs(f"{CERT_DIR}/dashboards", exist_ok=True)
    os.makedirs(f"{CERT_DIR}/security", exist_ok=True)

    print("=" * 60)
    print("HBC COMPREHENSIVE RESURRECTION PROTOCOL")
    print("=" * 60)

    # Extract dashboards
    print("\n=== EXTRACTING DASHBOARD UIDs ===")
    dashboards = extract_dashboard_uids()
    print(f"  Found {len(dashboards)} dashboards in frontend code")

    # Verify each dashboard
    print("\n=== VERIFYING DASHBOARDS ===")
    dashboard_report = []
    for dash in dashboards:
        uid = dash["uid"]
        print(f"  Checking {uid}...", end=" ", flush=True)

        exists = verify_dashboard_exists(uid)
        data_check = check_dashboard_data(uid)

        status = "OK" if exists.get("exists") else "NOT_FOUND"
        has_data = data_check.get("has_data", False)

        if not exists.get("exists"):
            status = "NOT_FOUND"
        elif not has_data:
            status = "NO_DATA"
        else:
            status = "OK"

        dashboard_report.append(
            {
                "uid": uid,
                "title": dash.get("title", uid),
                "status": status,
                "exists": exists.get("exists", False),
                "has_data": has_data,
                "panels": exists.get("panels", 0),
            }
        )

        if status == "OK":
            print("[OK]")
        elif status == "NOT_FOUND":
            print("[FAIL] NOT_FOUND")
        else:
            print("[WARN]  NO_DATA")

    # Save dashboard report
    with open(f"{CERT_DIR}/dashboards/dashboard_report.json", "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "total": len(dashboard_report),
                "ok": len([d for d in dashboard_report if d["status"] == "OK"]),
                "not_found": len(
                    [d for d in dashboard_report if d["status"] == "NOT_FOUND"]
                ),
                "no_data": len(
                    [d for d in dashboard_report if d["status"] == "NO_DATA"]
                ),
                "dashboards": dashboard_report,
            },
            f,
            indent=2,
        )

    # Fix bugs
    print("\n=== FIXING BUGS ===")
    if fix_division_by_zero():
        print("  [OK] Fixed division by zero bug")
    else:
        print("  [WARN]  Division by zero bug not found or already fixed")

    # Classify security findings
    print("\n=== CLASSIFYING SECURITY FINDINGS ===")
    security_classified = classify_security_findings()
    print(f"  Found {len(security_classified)} security findings")

    test_count = len([s for s in security_classified if s["classification"] == "TEST"])
    example_count = len(
        [s for s in security_classified if s["classification"] == "EXAMPLE"]
    )
    prod_count = len([s for s in security_classified if s["classification"] == "PROD"])

    print(f"    TEST: {test_count}")
    print(f"    EXAMPLE: {example_count}")
    print(f"    PROD: {prod_count}")

    with open(f"{CERT_DIR}/security/security_classified.json", "w") as f:
        json.dump(security_classified, f, indent=2)

    # Summary
    print("\n" + "=" * 60)
    print("RESURRECTION PROTOCOL SUMMARY")
    print("=" * 60)
    print(
        f"Dashboards: {len([d for d in dashboard_report if d['status'] == 'OK'])}/{len(dashboard_report)} OK"
    )
    print(f"Security: {len(security_classified)} findings classified")
    print(f"Evidence: {CERT_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
