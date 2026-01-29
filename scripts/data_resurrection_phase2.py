#!/usr/bin/env python3
"""Phase 2: Panel-by-Panel Verification"""
import json
import os
import sys
import requests
import csv
import urllib.parse

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_PASSWORD", "admin")


def get_dashboard_json(uid: str):
    """Get dashboard JSON from Grafana."""
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/dashboards/uid/{uid}",
            auth=(GRAFANA_USER, GRAFANA_PASSWORD),
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"ERROR: Could not fetch dashboard {uid}: {e}")
        return None


def extract_panels(dashboard_json):
    """Extract panels and their queries from dashboard JSON."""
    panels = []
    dashboard = dashboard_json.get("dashboard", {})

    # Get all panels (including from rows)
    def extract_from_panel(panel):
        panel_id = panel.get("id", "unknown")
        title = panel.get("title", "Untitled")

        # Get targets (queries)
        targets = panel.get("targets", [])
        if not targets:
            # Some panels might have queries in different format
            expr = panel.get("expr") or panel.get("query") or "N/A"
            panels.append(
                {
                    "panel_id": panel_id,
                    "title": title,
                    "query": expr,
                    "type": panel.get("type", "unknown"),
                }
            )
        else:
            for target in targets:
                expr = target.get("expr") or target.get("query") or "N/A"
                panels.append(
                    {
                        "panel_id": panel_id,
                        "title": title,
                        "query": expr,
                        "type": panel.get("type", "unknown"),
                    }
                )

        # Check for row panels (which contain other panels)
        if panel.get("type") == "row":
            for p in panel.get("panels", []):
                extract_from_panel(p)

    for panel in dashboard.get("panels", []):
        extract_from_panel(panel)

    return panels


def test_query(query: str, region: str = "New York City (US)"):
    """Test a Prometheus query."""
    if query == "N/A" or not query or query == "null":
        return {"status": "NO_QUERY", "result_count": 0}

    # Substitute $region variable
    test_query = query.replace("$region", f'"{region}"')

    # URL encode
    encoded_query = urllib.parse.quote(test_query)

    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query", params={"query": test_query}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", {}).get("result", [])
            return {
                "status": "PASS" if len(results) > 0 else "FAIL",
                "result_count": len(results),
                "error": None,
            }
        else:
            return {
                "status": "ERROR",
                "result_count": 0,
                "error": f"HTTP {response.status_code}",
            }
    except Exception as e:
        return {"status": "ERROR", "result_count": 0, "error": str(e)}


def main():
    resurrection_dir = os.getenv("RESURRECTION_DIR", "/tmp/hbc_resurrection_default")
    os.makedirs(f"{resurrection_dir}/queries", exist_ok=True)

    print("=== PHASE 2: PANEL-BY-PANEL VERIFICATION ===\n")

    # Load dashboard mapping
    mapping_path = f"{resurrection_dir}/inventory/dashboard_mapping.csv"
    if not os.path.exists(mapping_path):
        print(f"ERROR: Dashboard mapping not found at {mapping_path}")
        return 1

    dashboards = []
    with open(mapping_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["status"] == "EXISTS":
                dashboards.append(row)

    print(f"Testing {len(dashboards)} dashboards...\n")

    all_results = []
    panel_summary = []

    for dash in dashboards:
        uid = dash["expected_uid"]
        title = dash["ui_label"]

        print(f"Processing: {title} ({uid})...")

        # Get dashboard JSON
        dashboard_json = get_dashboard_json(uid)
        if not dashboard_json:
            print("  [FAIL] Could not fetch dashboard")
            continue

        # Save dashboard JSON
        with open(f"{resurrection_dir}/queries/{uid}.json", "w") as f:
            json.dump(dashboard_json, f, indent=2)

        # Extract panels
        panels = extract_panels(dashboard_json)
        print(f"  Found {len(panels)} panels")

        panel_summary.append(
            {"dashboard": title, "uid": uid, "panel_count": len(panels)}
        )

        # Test each panel query
        for panel in panels:
            panel_id = panel["panel_id"]
            panel_title = panel["title"]
            query = panel["query"]

            result = test_query(query)

            all_results.append(
                {
                    "dashboard": title,
                    "dashboard_uid": uid,
                    "panel_id": panel_id,
                    "panel_title": panel_title,
                    "query": query,
                    "status": result["status"],
                    "result_count": result["result_count"],
                    "error": result.get("error"),
                }
            )

            status_icon = (
                "[OK]"
                if result["status"] == "PASS"
                else "[FAIL]" if result["status"] == "FAIL" else "[WARN]"
            )
            print(
                f"    {status_icon} Panel {panel_id} ({panel_title}): {result['status']} ({result['result_count']} results)"
            )

    # Save results
    results_path = f"{resurrection_dir}/queries/query_test_results.csv"
    with open(results_path, "w", newline="") as f:
        if all_results:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
            writer.writeheader()
            writer.writerows(all_results)

    # Summary
    total_panels = len(all_results)
    passing = len([r for r in all_results if r["status"] == "PASS"])
    failing = len([r for r in all_results if r["status"] == "FAIL"])
    no_query = len([r for r in all_results if r["status"] == "NO_QUERY"])
    errors = len([r for r in all_results if r["status"] == "ERROR"])

    print("\n=== SUMMARY ===")
    print(f"Total panels tested: {total_panels}")
    print(f"[OK] Passing: {passing}")
    print(f"[FAIL] Failing: {failing}")
    print(f"[WARN]  No query: {no_query}")
    print(f" Errors: {errors}")

    # Save panel summary
    summary_path = f"{resurrection_dir}/queries/panel_summary.csv"
    with open(summary_path, "w", newline="") as f:
        if panel_summary:
            writer = csv.DictWriter(f, fieldnames=panel_summary[0].keys())
            writer.writeheader()
            writer.writerows(panel_summary)

    if failing > 0 or errors > 0:
        print("\n[WARN]  PHASE 2 ISSUES FOUND:")
        print(f"   {failing} panels returning no data")
        print(f"   {errors} panels with query errors")
        print("   Proceeding to Phase 4 for auto-repair...")
        return 1
    else:
        print("\n[OK] PHASE 2 PASSED - All panels have data")
        return 0


if __name__ == "__main__":
    sys.exit(main())
