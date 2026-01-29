#!/usr/bin/env python3
"""
HBC Comprehensive Bug Hunt & Forensic Registry
Executes all phases of the bug hunt protocol with full forensic evidence collection.
"""
import json
import os
import sys
import subprocess
import requests
import time
import ast
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

BUG_DIR = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8100")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3100")


def run_command(cmd: str, output_file: Optional[str] = None) -> tuple[int, str, str]:
    """Run command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        if output_file:
            with open(output_file, "w") as f:
                f.write(f"Command: {cmd}\n")
                f.write(f"Exit Code: {result.returncode}\n")
                f.write(f"STDOUT:\n{result.stdout}\n")
                if result.stderr:
                    f.write(f"STDERR:\n{result.stderr}\n")
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        if output_file:
            with open(output_file, "w") as f:
                f.write(f"Command: {cmd}\n")
                f.write("ERROR: Command timed out after 30 seconds\n")
        return 1, "", "Timeout"
    except Exception as e:
        if output_file:
            with open(output_file, "w") as f:
                f.write(f"Command: {cmd}\n")
                f.write(f"ERROR: {str(e)}\n")
        return 1, "", str(e)


def phase0_environmental_forensics() -> List[Dict]:
    """Phase 0: Environmental Forensics"""
    print("\n=== PHASE 0: ENVIRONMENTAL FORENSICS ===")
    bugs = []

    os.makedirs(f"{BUG_DIR}/baseline", exist_ok=True)

    # Capture Docker state
    print("Capturing Docker state...")
    run_command("docker compose ps", f"{BUG_DIR}/baseline/docker_ps.txt")
    run_command("docker stats --no-stream", f"{BUG_DIR}/baseline/docker_stats.txt")
    run_command("docker compose logs --tail=500", f"{BUG_DIR}/baseline/all_logs.txt")
    run_command("ps aux", f"{BUG_DIR}/baseline/processes.txt")
    run_command(
        "netstat -tuln 2>/dev/null || ss -tuln", f"{BUG_DIR}/baseline/ports.txt"
    )

    # Check service health
    print("Checking service health...")
    services = {
        "frontend": (FRONTEND_URL, "/health"),
        "backend": (BACKEND_URL, "/health"),
        "grafana": (GRAFANA_URL, "/api/health"),
        "prometheus": (PROMETHEUS_URL, "/-/healthy"),
    }

    for service, (base_url, endpoint) in services.items():
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code != 200:
                bugs.append(
                    {
                        "bug_id": f"HEALTH-{int(time.time())}-{service}",
                        "severity": "P1",
                        "category": "service_health",
                        "component": service,
                        "location": f"{base_url}{endpoint}",
                        "symptom": f"{service} health endpoint returned {response.status_code}",
                        "root_cause": "Service may be misconfigured or unhealthy",
                        "evidence": {
                            "url": f"{base_url}{endpoint}",
                            "status_code": response.status_code,
                            "response_body": response.text[:500],
                        },
                        "fix_suggestion": f"Check {service} logs and configuration",
                        "reproduction_steps": f"curl -v {base_url}{endpoint}",
                        "verification_method": f"curl {base_url}{endpoint} should return 200",
                    }
                )
        except Exception as e:
            bugs.append(
                {
                    "bug_id": f"HEALTH-{int(time.time())}-{service}",
                    "severity": "P0",
                    "category": "service_unreachable",
                    "component": service,
                    "location": f"{base_url}{endpoint}",
                    "symptom": f"{service} is unreachable: {str(e)}",
                    "root_cause": "Service may be down or network issue",
                    "evidence": {"url": f"{base_url}{endpoint}", "error": str(e)},
                    "fix_suggestion": f"Check if {service} is running: docker compose ps",
                    "reproduction_steps": f"curl {base_url}{endpoint}",
                    "verification_method": f"Service should respond at {base_url}{endpoint}",
                }
            )

    print(f"  Found {len(bugs)} health issues")
    return bugs


def phase1_data_integrity() -> List[Dict]:
    """Phase 1: Data Integrity Bugs"""
    print("\n=== PHASE 1: DATA INTEGRITY BUGS ===")
    bugs = []

    metrics_to_check = [
        ("behavior_index", 5),
        ("parent_subindex_value", 5),
        ("child_subindex_value", 5),
        ("forecast_points_generated", 3),
    ]

    print("Checking metric integrity...")
    for metric, min_expected in metrics_to_check:
        try:
            query = f"count(count by (region) ({metric}))"
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("result", [])
                if results:
                    count = int(float(results[0]["value"][1]))
                    if count < min_expected:
                        bugs.append(
                            {
                                "bug_id": f"DATA-{int(time.time())}-{hash(metric) % 10000}",
                                "severity": "P0",
                                "category": "missing_data",
                                "component": "prometheus",
                                "location": f"metric: {metric}",
                                "symptom": f"Only {count} regions have {metric} data, expected >= {min_expected}",
                                "root_cause": "Backend not emitting metric for all regions or Prometheus not scraping",
                                "evidence": {
                                    "prometheus_query": query,
                                    "prometheus_response": data,
                                    "curl_command": f"curl -s '{PROMETHEUS_URL}/api/v1/query?query={query}'",
                                },
                                "fix_suggestion": "1. Check backend /metrics endpoint. 2. Verify Prometheus scrape config. 3. Force data generation for missing regions.",
                                "reproduction_steps": f"curl -s '{PROMETHEUS_URL}/api/v1/query?query={query}'",
                                "verification_method": f"Query should return count >= {min_expected}",
                            }
                        )
                        print(
                            f"  [FAIL] {metric}: {count} regions (expected >= {min_expected})"
                        )
                    else:
                        print(f"  [OK] {metric}: {count} regions")
                else:
                    bugs.append(
                        {
                            "bug_id": f"DATA-{int(time.time())}-{hash(metric) % 10000}",
                            "severity": "P0",
                            "category": "missing_data",
                            "component": "prometheus",
                            "location": f"metric: {metric}",
                            "symptom": f"No data found for {metric}",
                            "root_cause": "Metric not being emitted or scraped",
                            "evidence": {
                                "prometheus_query": query,
                                "prometheus_response": data,
                            },
                            "fix_suggestion": "Check backend metrics emission and Prometheus scrape config",
                            "reproduction_steps": f"curl -s '{PROMETHEUS_URL}/api/v1/query?query={query}'",
                        }
                    )
                    print(f"  [FAIL] {metric}: No data")
        except Exception as e:
            print(f"  [WARN]  {metric}: Error - {str(e)}")

    # Check staleness
    print("\nChecking data staleness...")
    for metric in ["behavior_index", "forecast_last_updated_timestamp_seconds"]:
        try:
            query = f"{metric}"
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("result", [])
                if results:
                    latest_timestamp = int(float(results[0]["value"][0]))
                    current_time = int(time.time())
                    age = current_time - latest_timestamp
                    max_age = 7200  # 2 hours

                    if age > max_age:
                        bugs.append(
                            {
                                "bug_id": f"STALE-{int(time.time())}-{hash(metric) % 10000}",
                                "severity": "P1",
                                "category": "stale_data",
                                "component": "prometheus",
                                "location": f"metric: {metric}",
                                "symptom": f"{metric} data is {age} seconds old (max: {max_age})",
                                "root_cause": "Backend stopped emitting or Prometheus stopped scraping",
                                "evidence": {
                                    "prometheus_query": query,
                                    "latest_timestamp": latest_timestamp,
                                    "current_time": current_time,
                                    "age_seconds": age,
                                    "curl_command": f"curl -s '{PROMETHEUS_URL}/api/v1/query?query={query}'",
                                },
                                "fix_suggestion": "1. Check backend health. 2. Check Prometheus targets. 3. Check scrape interval.",
                                "reproduction_steps": f"Check timestamp of latest {metric} value",
                                "verification_method": f"Data should be < {max_age} seconds old",
                            }
                        )
                        print(f"  [FAIL] {metric}: {age}s old")
                    else:
                        print(f"  [OK] {metric}: {age}s old (fresh)")
        except Exception as e:
            print(f"  [WARN]  {metric}: Error - {str(e)}")

    print(f"\n  Found {len(bugs)} data integrity bugs")
    return bugs


def phase2_visualization() -> List[Dict]:
    """Phase 2: Visualization Bugs (No Data Panels)"""
    print("\n=== PHASE 2: VISUALIZATION BUGS ===")
    bugs = []

    # Try to fetch frontend HTML and check for dashboard UIDs
    try:
        response = requests.get(FRONTEND_URL, timeout=10)
        if response.status_code == 200:
            html = response.text

            # Extract dashboard UIDs from iframe sources
            import re

            dashboard_uids = re.findall(r"/d/([a-zA-Z0-9_-]+)", html)

            print(f"  Found {len(set(dashboard_uids))} unique dashboard UIDs in HTML")

            # Check each dashboard exists in Grafana
            for uid in set(dashboard_uids):
                try:
                    grafana_response = requests.get(
                        f"{GRAFANA_URL}/api/dashboards/uid/{uid}",
                        auth=("admin", os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")),
                        timeout=5,
                    )
                    if grafana_response.status_code != 200:
                        bugs.append(
                            {
                                "bug_id": f"VISUAL-{int(time.time())}-{hash(uid) % 10000}",
                                "severity": "P1",
                                "category": "dashboard_not_found",
                                "component": "frontend/grafana",
                                "location": f"dashboard UID: {uid}",
                                "symptom": f"Dashboard {uid} referenced in frontend but not found in Grafana",
                                "root_cause": "Dashboard may have been deleted or UID mismatch",
                                "evidence": {
                                    "dashboard_uid": uid,
                                    "grafana_status": grafana_response.status_code,
                                    "grafana_response": grafana_response.text[:500],
                                    "frontend_url": FRONTEND_URL,
                                },
                                "fix_suggestion": "1. Verify dashboard exists in Grafana. 2. Check UID in frontend code. 3. Recreate dashboard if missing.",
                                "reproduction_steps": f"1. Visit {FRONTEND_URL}. 2. Check for dashboard {uid}",
                                "verification_method": f"curl -u admin:admin {GRAFANA_URL}/api/dashboards/uid/{uid} should return 200",
                            }
                        )
                        print(f"  [FAIL] Dashboard {uid}: Not found in Grafana")
                    else:
                        print(f"  [OK] Dashboard {uid}: Found")
                except Exception as e:
                    print(f"  [WARN]  Dashboard {uid}: Error checking - {str(e)}")
        else:
            print(f"  [WARN]  Frontend returned {response.status_code}")
    except Exception as e:
        print(f"  [WARN]  Could not check frontend: {str(e)}")

    print(f"\n  Found {len(bugs)} visualization bugs")
    return bugs


def phase3_mathematical() -> List[Dict]:
    """Phase 3: Mathematical Bugs"""
    print("\n=== PHASE 3: MATHEMATICAL BUGS ===")
    bugs = []

    class MathBugFinder(ast.NodeVisitor):
        def __init__(self, file_path):
            self.file_path = file_path
            self.bugs = []

        def visit_BinOp(self, node):
            if isinstance(node.op, ast.Div):
                self.check_division_by_zero(node)
            self.generic_visit(node)

        def check_division_by_zero(self, node):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.bugs.append(
                    {
                        "type": "division_by_zero",
                        "line": node.lineno,
                        "critical": True,
                        "snippet": "Division by literal zero",
                    }
                )
            elif isinstance(node.right, ast.Name):
                self.bugs.append(
                    {
                        "type": "potential_division_by_zero",
                        "line": node.lineno,
                        "variable": node.right.id,
                        "critical": False,
                        "snippet": f"Division by variable '{node.right.id}' that might be zero",
                    }
                )

    scan_paths = [
        Path("app"),
        Path("tests"),
        Path("hbc"),
        Path("connectors"),
        Path("predictors"),
    ]
    files_scanned = 0

    for scan_path in scan_paths:
        if not scan_path.exists():
            continue

        for py_file in scan_path.rglob("*.py"):
            if any(
                skip in str(py_file)
                for skip in [".venv", "__pycache__", "node_modules"]
            ):
                continue

            try:
                with open(py_file, "r") as f:
                    content = f.read()

                try:
                    tree = ast.parse(content, filename=str(py_file))
                    finder = MathBugFinder(str(py_file))
                    finder.visit(tree)

                    if finder.bugs:
                        for bug in finder.bugs:
                            # Read context around the line
                            lines = content.split("\n")
                            context_start = max(0, bug["line"] - 3)
                            context_end = min(len(lines), bug["line"] + 2)
                            context = "\n".join(lines[context_start:context_end])

                            bugs.append(
                                {
                                    "bug_id": f"MATH-{hash(str(py_file) + str(bug['line'])) % 100000}",
                                    "severity": "P0" if bug.get("critical") else "P2",
                                    "category": "mathematical",
                                    "component": str(py_file),
                                    "location": f"line {bug['line']}",
                                    "symptom": bug.get(
                                        "snippet", bug.get("type", "Unknown")
                                    ),
                                    "root_cause": bug.get("type", "Unknown"),
                                    "evidence": {
                                        "file": str(py_file),
                                        "line": bug["line"],
                                        "code_context": context,
                                        "variable": bug.get("variable"),
                                    },
                                    "fix_suggestion": (
                                        "Add zero-check before division"
                                        if "division" in bug.get("type", "")
                                        else "Review mathematical operation"
                                    ),
                                    "reproduction_steps": f"Examine line {bug['line']} in {py_file}",
                                    "verification_method": f"Add unit test with zero value for {bug.get('variable', 'denominator')}",
                                }
                            )

                    files_scanned += 1
                except SyntaxError:
                    pass
            except Exception:
                pass

    print(f"  Scanned {files_scanned} Python files")
    print(f"  Found {len(bugs)} potential mathematical bugs")

    return bugs


def phase4_integration() -> List[Dict]:
    """Phase 4: Integration Bugs"""
    print("\n=== PHASE 4: INTEGRATION BUGS ===")
    bugs = []

    # Check API endpoints
    endpoints = [
        (f"{BACKEND_URL}/health", 200),
        (f"{BACKEND_URL}/metrics", 200),
        (f"{BACKEND_URL}/api/forecasting/models", 200),
        (f"{PROMETHEUS_URL}/-/healthy", 200),
        (f"{GRAFANA_URL}/api/health", 200),
    ]

    print("Validating API endpoints...")
    for endpoint, expected_status in endpoints:
        try:
            response = requests.get(endpoint, timeout=5)
            if response.status_code != expected_status:
                bugs.append(
                    {
                        "bug_id": f"API-{int(time.time())}-{hash(endpoint) % 10000}",
                        "severity": "P0",
                        "category": "api_contract",
                        "component": (
                            endpoint.split("/")[2]
                            if len(endpoint.split("/")) > 2
                            else "unknown"
                        ),
                        "location": endpoint,
                        "symptom": f"Endpoint returned {response.status_code}, expected {expected_status}",
                        "root_cause": "API contract violation",
                        "evidence": {
                            "endpoint": endpoint,
                            "expected_status": expected_status,
                            "actual_status": response.status_code,
                            "response_body": response.text[:500],
                            "curl_command": f"curl -v {endpoint}",
                        },
                        "fix_suggestion": "Fix backend route handler to return correct status code",
                        "reproduction_steps": f"curl -v {endpoint}",
                        "verification_method": f"Endpoint should return {expected_status}",
                    }
                )
                print(
                    f"  [FAIL] {endpoint}: {response.status_code} (expected {expected_status})"
                )
            else:
                print(f"  [OK] {endpoint}: {response.status_code}")
        except Exception as e:
            bugs.append(
                {
                    "bug_id": f"API-{int(time.time())}-{hash(endpoint) % 10000}",
                    "severity": "P0",
                    "category": "api_unreachable",
                    "component": (
                        endpoint.split("/")[2]
                        if len(endpoint.split("/")) > 2
                        else "unknown"
                    ),
                    "location": endpoint,
                    "symptom": f"Endpoint unreachable: {str(e)}",
                    "root_cause": "Service may be down",
                    "evidence": {"endpoint": endpoint, "error": str(e)},
                    "fix_suggestion": "Check if service is running",
                    "reproduction_steps": f"curl {endpoint}",
                    "verification_method": "Endpoint should be reachable",
                }
            )
            print(f"  [FAIL] {endpoint}: Unreachable")

    # Check Prometheus targets
    print("\nChecking Prometheus scrape targets...")
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/targets", timeout=10)
        if response.status_code == 200:
            data = response.json()
            targets = data.get("data", {}).get("activeTargets", [])
            down_targets = [t for t in targets if t.get("health") != "up"]

            if down_targets:
                bugs.append(
                    {
                        "bug_id": f"SCRAPE-{int(time.time())}",
                        "severity": "P0",
                        "category": "prometheus_scrape",
                        "component": "prometheus",
                        "location": "Prometheus scrape targets",
                        "symptom": f"{len(down_targets)} Prometheus targets are down",
                        "root_cause": "Target endpoints may be unreachable or misconfigured",
                        "evidence": {
                            "down_targets": down_targets,
                            "prometheus_query": f"{PROMETHEUS_URL}/api/v1/targets",
                            "curl_command": f"curl -s {PROMETHEUS_URL}/api/v1/targets | jq '.data.activeTargets[] | select(.health != \"up\")'",
                        },
                        "fix_suggestion": "Check target endpoints, restart Prometheus, verify network connectivity",
                        "reproduction_steps": f"curl -s {PROMETHEUS_URL}/api/v1/targets | jq '.data.activeTargets[] | select(.health != \"up\")'",
                        "verification_method": "All targets should have health='up'",
                    }
                )
                print(f"  [FAIL] {len(down_targets)} targets down")
            else:
                print("  [OK] All targets up")
    except Exception as e:
        print(f"  [WARN]  Error checking targets: {str(e)}")

    print(f"\n  Found {len(bugs)} integration bugs")
    return bugs


def phase5_frontend() -> List[Dict]:
    """Phase 5: Frontend Bugs"""
    print("\n=== PHASE 5: FRONTEND BUGS ===")
    bugs = []

    # Check frontend HTML for errors
    try:
        response = requests.get(FRONTEND_URL, timeout=10)
        if response.status_code == 200:
            html = response.text

            # Check for error patterns
            error_patterns = [
                ("Error:", "error_message"),
                ("Exception:", "exception"),
                ("Failed to", "failure_message"),
            ]

            for pattern, error_type in error_patterns:
                if pattern.lower() in html.lower():
                    bugs.append(
                        {
                            "bug_id": f"FRONTEND-{int(time.time())}-{hash(pattern) % 10000}",
                            "severity": "P1",
                            "category": "frontend_error",
                            "component": "frontend",
                            "location": FRONTEND_URL,
                            "symptom": f"Error pattern '{pattern}' found in HTML",
                            "root_cause": "Frontend may be rendering errors",
                            "evidence": {
                                "url": FRONTEND_URL,
                                "error_pattern": pattern,
                                "html_snippet": html[
                                    html.lower()
                                    .find(pattern.lower()) : html.lower()
                                    .find(pattern.lower())
                                    + 200
                                ],
                            },
                            "fix_suggestion": "Check frontend logs and error handling",
                            "reproduction_steps": f"Visit {FRONTEND_URL} and inspect HTML",
                            "verification_method": "HTML should not contain error messages",
                        }
                    )

            # Check for missing resources (simplified)
            if "404" in html or "Not Found" in html:
                bugs.append(
                    {
                        "bug_id": f"FRONTEND-{int(time.time())}-404",
                        "severity": "P2",
                        "category": "missing_resource",
                        "component": "frontend",
                        "location": FRONTEND_URL,
                        "symptom": "404 or 'Not Found' text in HTML",
                        "root_cause": "Missing resources or broken links",
                        "evidence": {"url": FRONTEND_URL, "html_snippet": html[:1000]},
                        "fix_suggestion": "Check for missing assets or broken links",
                        "reproduction_steps": f"Visit {FRONTEND_URL}",
                        "verification_method": "No 404 errors in HTML",
                    }
                )
    except Exception as e:
        print(f"  [WARN]  Error checking frontend: {str(e)}")

    print(f"  Found {len(bugs)} frontend bugs")
    return bugs


def phase6_performance() -> List[Dict]:
    """Phase 6: Performance Bugs"""
    print("\n=== PHASE 6: PERFORMANCE BUGS ===")
    bugs = []

    # Test Prometheus query performance
    queries = [
        "behavior_index",
        "count(count by (region) (behavior_index))",
        "parent_subindex_value",
    ]

    print("Testing Prometheus query performance...")
    for query in queries:
        try:
            start = time.time()
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10
            )
            duration = (time.time() - start) * 1000  # ms

            if duration > 1000:  # > 1 second
                bugs.append(
                    {
                        "bug_id": f"SLOW-{int(time.time())}-{hash(query) % 10000}",
                        "severity": "P1",
                        "category": "slow_query",
                        "component": "prometheus",
                        "location": f"query: {query}",
                        "symptom": f"Query took {duration:.0f}ms (threshold: 1000ms)",
                        "root_cause": "Query may be inefficient or data too large",
                        "evidence": {
                            "query": query,
                            "duration_ms": duration,
                            "prometheus_url": PROMETHEUS_URL,
                            "curl_command": f"time curl -s '{PROMETHEUS_URL}/api/v1/query?query={query}'",
                        },
                        "fix_suggestion": "Add index to metric, reduce time range, or pre-aggregate",
                        "reproduction_steps": f"curl -w '@-' -o /dev/null -s '{PROMETHEUS_URL}/api/v1/query?query={query}'",
                        "verification_method": "Query should complete in < 1000ms",
                    }
                )
                print(f"  [FAIL] {query}: {duration:.0f}ms")
            else:
                print(f"  [OK] {query}: {duration:.0f}ms")
        except Exception as e:
            print(f"  [WARN]  {query}: Error - {str(e)}")

    # Test API endpoint performance
    endpoints = [
        f"{BACKEND_URL}/health",
        f"{BACKEND_URL}/metrics",
    ]

    print("\nTesting API endpoint performance...")
    for endpoint in endpoints:
        try:
            start = time.time()
            response = requests.get(endpoint, timeout=5)
            duration = (time.time() - start) * 1000  # ms

            if duration > 500:  # > 500ms
                bugs.append(
                    {
                        "bug_id": f"SLOW-API-{int(time.time())}-{hash(endpoint) % 10000}",
                        "severity": "P2",
                        "category": "slow_endpoint",
                        "component": (
                            endpoint.split("/")[2]
                            if len(endpoint.split("/")) > 2
                            else "unknown"
                        ),
                        "location": endpoint,
                        "symptom": f"Endpoint took {duration:.0f}ms (threshold: 500ms)",
                        "root_cause": "Endpoint may be doing expensive operations",
                        "evidence": {
                            "endpoint": endpoint,
                            "duration_ms": duration,
                            "status_code": response.status_code,
                            "curl_command": f"time curl -s {endpoint}",
                        },
                        "fix_suggestion": "Optimize endpoint or add caching",
                        "reproduction_steps": f"time curl -s {endpoint}",
                        "verification_method": "Endpoint should respond in < 500ms",
                    }
                )
                print(f"  [FAIL] {endpoint}: {duration:.0f}ms")
            else:
                print(f"  [OK] {endpoint}: {duration:.0f}ms")
        except Exception as e:
            print(f"  [WARN]  {endpoint}: Error - {str(e)}")

    print(f"\n  Found {len(bugs)} performance bugs")
    return bugs


def phase7_security() -> List[Dict]:
    """Phase 7: Security Bugs"""
    print("\n=== PHASE 7: SECURITY BUGS ===")
    bugs = []

    # Scan for hardcoded secrets
    print("Scanning for hardcoded secrets...")
    secret_patterns = [
        (r'API_KEY\s*=\s*["\'][^"\']{8,}["\']', "api_key"),
        (r'SECRET\s*=\s*["\'][^"\']{8,}["\']', "secret"),
        (r'TOKEN\s*=\s*["\'][^"\']{8,}["\']', "token"),
        (r'PASSWORD\s*=\s*["\'][^"\']{8,}["\']', "password"),
    ]

    import re

    scan_paths = [Path("app"), Path("scripts"), Path("tests"), Path("connectors")]

    for scan_path in scan_paths:
        if not scan_path.exists():
            continue

        for py_file in scan_path.rglob("*.py"):
            if any(
                skip in str(py_file)
                for skip in [".venv", "__pycache__", "node_modules"]
            ):
                continue

            try:
                with open(py_file, "r") as f:
                    content = f.read()
                    lines = content.split("\n")

                for pattern, secret_type in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[: match.start()].count("\n") + 1
                        line_content = (
                            lines[line_num - 1] if line_num <= len(lines) else ""
                        )

                        # Skip test files and known false positives
                        if any(
                            skip in str(py_file)
                            for skip in ["test_", "conftest", "fixtures"]
                        ):
                            continue
                        if (
                            "test_key" in line_content.lower()
                            or "mock" in line_content.lower()
                        ):
                            continue

                        bugs.append(
                            {
                                "bug_id": f"SECRET-{hash(str(py_file) + str(line_num)) % 100000}",
                                "severity": "P0",
                                "category": "secret_exposure",
                                "component": str(py_file),
                                "location": f"line {line_num}",
                                "symptom": f"Hardcoded {secret_type} found",
                                "root_cause": "Secret hardcoded in source code",
                                "evidence": {
                                    "file": str(py_file),
                                    "line": line_num,
                                    "line_content": line_content.strip(),
                                    "pattern": pattern,
                                    "match": match.group(),
                                },
                                "fix_suggestion": "Move to environment variables, use vault, rotate exposed secrets",
                                "reproduction_steps": f"grep -n '{pattern}' {py_file}",
                                "verification_method": "No hardcoded secrets in source code",
                            }
                        )
            except Exception:
                pass

    # Check Python dependencies
    print("Checking Python dependencies...")
    try:
        result = subprocess.run(
            ["pip-audit", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            try:
                audit_data = json.loads(result.stdout)
                vulns = audit_data.get("vulnerabilities", [])
                critical_vulns = [
                    v for v in vulns if v.get("severity", "").lower() == "critical"
                ]

                if critical_vulns:
                    bugs.append(
                        {
                            "bug_id": f"VULN-{int(time.time())}",
                            "severity": "P0",
                            "category": "dependency_vulnerability",
                            "component": "python_dependencies",
                            "location": "requirements.txt",
                            "symptom": f"{len(critical_vulns)} critical vulnerabilities found",
                            "root_cause": "Outdated or vulnerable dependencies",
                            "evidence": {
                                "vulnerabilities": critical_vulns[:10],  # First 10
                                "pip_audit_output": result.stdout[:1000],
                            },
                            "fix_suggestion": "Update vulnerable packages: pip-audit --fix",
                            "reproduction_steps": "pip-audit --format json",
                            "verification_method": "pip-audit should report no critical vulnerabilities",
                        }
                    )
                    print(f"  [FAIL] {len(critical_vulns)} critical vulnerabilities")
                else:
                    print("  [OK] No critical vulnerabilities")
            except json.JSONDecodeError:
                pass
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  [WARN]  pip-audit not available")

    print(f"\n  Found {len(bugs)} security bugs")
    return bugs


def consolidate_registry(all_bugs: List[Dict]) -> Dict:
    """Phase 9: Consolidate all bugs into master registry"""
    print("\n=== PHASE 9: BUG REGISTRY CONSOLIDATION ===")

    # Categorize bugs
    bugs_by_category = {
        "data_integrity": [],
        "visualization": [],
        "mathematical": [],
        "integration": [],
        "frontend": [],
        "performance": [],
        "security": [],
        "concurrency": [],
        "configuration": [],
        "service_health": [],
    }

    bugs_by_severity = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}

    for bug in all_bugs:
        category = bug.get("category", "unknown")
        if category in bugs_by_category:
            bugs_by_category[category].append(bug)
        else:
            bugs_by_category["configuration"].append(bug)

        severity = bug.get("severity", "P3")
        bugs_by_severity[severity] = bugs_by_severity.get(severity, 0) + 1

    registry = {
        "audit_timestamp": datetime.utcnow().isoformat() + "Z",
        "total_bugs": len(all_bugs),
        "bugs_by_severity": bugs_by_severity,
        "bugs_by_category": bugs_by_category,
    }

    return registry


def main():
    os.makedirs(f"{BUG_DIR}/registry", exist_ok=True)

    print("=" * 60)
    print("HBC COMPREHENSIVE BUG HUNT & FORENSIC REGISTRY")
    print("=" * 60)
    print(f"Bug Directory: {BUG_DIR}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")

    all_bugs = []

    # Execute all phases
    all_bugs.extend(phase0_environmental_forensics())
    all_bugs.extend(phase1_data_integrity())
    all_bugs.extend(phase2_visualization())
    all_bugs.extend(phase3_mathematical())
    all_bugs.extend(phase4_integration())
    all_bugs.extend(phase5_frontend())
    all_bugs.extend(phase6_performance())
    all_bugs.extend(phase7_security())

    # Consolidate
    registry = consolidate_registry(all_bugs)

    # Save master registry
    with open(f"{BUG_DIR}/registry/MASTER_BUG_REGISTRY.json", "w") as f:
        json.dump(registry, f, indent=2)

    # Generate triage report
    print("\n=== PHASE 10: BUG TRIAGE & PRIORITIZATION ===")
    print("=" * 60)
    print("HBC BUG TRIAGE REPORT")
    print("=" * 60)
    print(f"Total Bugs: {registry['total_bugs']}")
    print("\nBy Severity:")
    for sev, count in registry["bugs_by_severity"].items():
        print(f"  {sev}: {count}")

    print("\nBy Category:")
    for cat, bugs in registry["bugs_by_category"].items():
        if bugs:
            print(f"  {cat}: {len(bugs)}")

    print("\n[WARN]  P0 BUGS (Fix Immediately):")
    for category, bugs in registry["bugs_by_category"].items():
        for bug in bugs:
            if bug.get("severity") == "P0":
                print(f"  - {bug['bug_id']}: {bug.get('symptom', 'Unknown')}")

    # Save triage report
    with open(f"{BUG_DIR}/BUG_TRIAGE_REPORT.txt", "w") as f:
        f.write("=" * 60 + "\n")
        f.write("HBC BUG TRIAGE REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Audit Date: {registry['audit_timestamp']}\n")
        f.write(f"Total Bugs: {registry['total_bugs']}\n\n")
        f.write("By Severity:\n")
        for sev, count in registry["bugs_by_severity"].items():
            f.write(f"  {sev}: {count}\n")
        f.write("\nBy Category:\n")
        for cat, bugs in registry["bugs_by_category"].items():
            if bugs:
                f.write(f"  {cat}: {len(bugs)}\n")

    print(f"\n[OK] Master registry saved: {BUG_DIR}/registry/MASTER_BUG_REGISTRY.json")
    print(f"[OK] Triage report saved: {BUG_DIR}/BUG_TRIAGE_REPORT.txt")

    return 0 if registry["total_bugs"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
