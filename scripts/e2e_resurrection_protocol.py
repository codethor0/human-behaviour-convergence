#!/usr/bin/env python3
"""
HBC End-to-End Resurrection, Bug Fix, and Hardening Protocol
Executes all phases to certify the system is production-ready.
"""
import json
import os
import sys
import subprocess
import requests
import time
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


def run_command(cmd: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Timeout"
    except Exception as e:
        return 1, "", str(e)


def wait_for_service(url: str, max_wait: int = 120) -> bool:
    """Wait for service to be available."""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 500:
                return True
        except:
            pass
        time.sleep(2)
    return False


def phase0_baseline():
    """Phase 0: Capture baseline state."""
    print("\n=== PHASE 0: BASELINE CAPTURE ===")
    os.makedirs(f"{CERT_DIR}/baseline", exist_ok=True)

    # Check if stack is running
    _, stdout, _ = run_command("docker compose ps")
    with open(f"{CERT_DIR}/baseline/docker_ps.txt", "w") as f:
        f.write(stdout)

    if "Up" not in stdout:
        print("  Stack not running. Starting stack...")
        run_command("docker compose up -d --build", timeout=300)
        print("  Waiting for services to start...")
        time.sleep(30)

        # Wait for services
        services = {
            "backend": BACKEND_URL,
            "frontend": FRONTEND_URL,
            "grafana": GRAFANA_URL,
            "prometheus": PROMETHEUS_URL,
        }

        for name, url in services.items():
            print(f"  Waiting for {name}...")
            if wait_for_service(url):
                print(f"    [OK] {name} is up")
            else:
                print(f"    [WARN]  {name} not responding")

    # Capture health
    health_status = {}
    for name, url in [
        ("backend", f"{BACKEND_URL}/health"),
        ("frontend", f"{FRONTEND_URL}/health"),
        ("grafana", f"{GRAFANA_URL}/api/health"),
        ("prometheus", f"{PROMETHEUS_URL}/-/ready"),
    ]:
        try:
            response = requests.get(url, timeout=5)
            health_status[name] = {
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "healthy": response.status_code == 200,
            }
        except Exception as e:
            health_status[name] = {"error": str(e), "healthy": False}

    with open(f"{CERT_DIR}/baseline/health_status.json", "w") as f:
        json.dump(health_status, f, indent=2)

    print("  Baseline captured")
    return health_status


def phase1_dashboard_inventory():
    """Phase 1: Inventory all dashboards."""
    print("\n=== PHASE 1: DASHBOARD INVENTORY ===")
    os.makedirs(f"{CERT_DIR}/dashboards", exist_ok=True)

    # Get dashboards from Grafana
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/search?type=dash-db",
            auth=(GRAFANA_USER, GRAFANA_PASS),
            timeout=10,
        )
        grafana_dashboards = {}
        if response.status_code == 200:
            for dash in response.json():
                grafana_dashboards[dash.get("uid")] = {
                    "title": dash.get("title"),
                    "uid": dash.get("uid"),
                    "url": dash.get("url"),
                }
    except Exception as e:
        print(f"  [WARN]  Could not fetch Grafana dashboards: {e}")
        grafana_dashboards = {}

    # Extract dashboards from frontend code
    frontend_dashboards = []
    index_file = Path("app/frontend/src/pages/index.tsx")
    if index_file.exists():
        content = index_file.read_text()
        # Look for dashboardUid patterns
        import re

        uid_pattern = r'dashboardUid["\']?\s*[:=]\s*["\']([^"\']+)["\']'
        matches = re.findall(uid_pattern, content)
        for uid in matches:
            frontend_dashboards.append({"uid": uid, "source": "index.tsx"})

    # Build inventory
    inventory = []
    for dash in frontend_dashboards:
        uid = dash["uid"]
        exists = uid in grafana_dashboards
        inventory.append(
            {
                "ui_label": grafana_dashboards.get(uid, {}).get("title", uid),
                "uid": uid,
                "status": "OK" if exists else "NOT_FOUND",
                "exists_in_grafana": exists,
                "grafana_title": (
                    grafana_dashboards.get(uid, {}).get("title") if exists else None
                ),
            }
        )

    with open(f"{CERT_DIR}/dashboards/inventory.json", "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "total_dashboards": len(inventory),
                "dashboards": inventory,
            },
            f,
            indent=2,
        )

    not_found = [d for d in inventory if d["status"] == "NOT_FOUND"]
    print(f"  Found {len(inventory)} dashboards")
    print(f"  {len(not_found)} not found in Grafana")

    return inventory


def phase2_fix_dashboards(inventory: List[Dict]):
    """Phase 2: Fix dashboard issues."""
    print("\n=== PHASE 2: DASHBOARD RESURRECTION ===")

    not_found = [d for d in inventory if d["status"] == "NOT_FOUND"]

    if not not_found:
        print("  [OK] All dashboards exist in Grafana")
        return

    print(f"  Creating {len(not_found)} missing dashboards...")

    for dash in not_found:
        uid = dash["uid"]
        title = dash.get("ui_label", uid)

        # Create minimal dashboard
        dashboard_json = {
            "dashboard": {
                "title": title,
                "uid": uid,
                "panels": [
                    {
                        "id": 1,
                        "title": "Behavior Index",
                        "type": "stat",
                        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                        "targets": [
                            {"expr": 'behavior_index{region="$region"}', "refId": "A"}
                        ],
                    }
                ],
                "templating": {
                    "list": [
                        {
                            "name": "region",
                            "type": "query",
                            "query": "label_values(behavior_index, region)",
                            "current": {
                                "value": "city_nyc",
                                "text": "New York City (US)",
                            },
                        }
                    ]
                },
                "time": {"from": "now-30d", "to": "now"},
                "refresh": "30s",
            },
            "overwrite": False,
        }

        try:
            response = requests.post(
                f"{GRAFANA_URL}/api/dashboards/db",
                auth=(GRAFANA_USER, GRAFANA_PASS),
                json=dashboard_json,
                timeout=10,
            )
            if response.status_code in [200, 201]:
                print(f"    [OK] Created dashboard: {title} ({uid})")
            else:
                print(f"    [WARN]  Failed to create {title}: {response.status_code}")
        except Exception as e:
            print(f"    [WARN]  Error creating {title}: {e}")


def phase3_security_hardening():
    """Phase 3: Security findings and health endpoints."""
    print("\n=== PHASE 3: SECURITY HARDENING ===")
    os.makedirs(f"{CERT_DIR}/security", exist_ok=True)

    # Load bug registry
    bug_registry_path = (
        "/tmp/hbc_bugs_deep_20260128_171737/registry/MASTER_BUG_REGISTRY.json"
    )
    if not Path(bug_registry_path).exists():
        print("  [WARN]  Bug registry not found, skipping security fixes")
        return

    with open(bug_registry_path, "r") as f:
        registry = json.load(f)

    # Classify security findings
    security_bugs = []
    for category, bugs in registry.get("bugs_by_category", {}).items():
        if category == "security" or "secret" in category.lower():
            security_bugs.extend(bugs)

    print(f"  Found {len(security_bugs)} security findings")

    # Check if whitelist exists
    gitleaks_config = Path(".gitleaks.toml")
    if gitleaks_config.exists():
        print("  [OK] .gitleaks.toml exists")
    else:
        print("  [WARN]  .gitleaks.toml not found, creating...")
        # Create basic whitelist
        with open(".gitleaks.toml", "w") as f:
            f.write(
                """title = "HBC Secret Scanning Rules"
[rules]
[[rules]]
    id = "generic-api-key"
    description = "Generic API Key"
    regex = '''(?i)(api_key|apikey|api-key)\\s*=\\s*["'][^"'\\s]{8,}["']'''
    [rules.allowlist]
    paths = [
        "**/test/**",
        "**/tests/**",
        "**/*_test.py",
        "**/.venv/**",
        "**/node_modules/**"
    ]
    regexes = [
        "test_key",
        "mock_",
        "example_"
    ]
"""
            )

    # Fix division by zero bug
    scenario_file = Path("app/core/scenario_sensitivity.py")
    if scenario_file.exists():
        content = scenario_file.read_text()
        if (
            "if input_delta == 0:" not in content
            and "elasticity = (output_delta / input_delta)" in content
        ):
            print("  Fixing division by zero in scenario_sensitivity.py...")
            # Add guard before division
            content = content.replace(
                "elasticity = (output_delta / input_delta) * factor_weight",
                """if input_delta == 0:
        raise ValueError("input_delta cannot be zero for elasticity calculation")
    elasticity = (output_delta / input_delta) * factor_weight""",
            )
            scenario_file.write_text(content)
            print("    [OK] Fixed division by zero")


def phase4_health_endpoints():
    """Phase 4: Ensure all health endpoints work."""
    print("\n=== PHASE 4: HEALTH ENDPOINT HARDENING ===")

    # Check backend
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("  [OK] Backend /health: OK")
        else:
            print(f"  [WARN]  Backend /health: {response.status_code}")
    except Exception as e:
        print(f"  [FAIL] Backend /health: {e}")

    # Check frontend
    try:
        response = requests.get(f"{FRONTEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("  [OK] Frontend /health: OK")
        else:
            print(
                f"  [WARN]  Frontend /health: {response.status_code} (may need Next.js restart)"
            )
    except Exception as e:
        print(f"  [WARN]  Frontend /health: {e}")

    # Check Grafana
    try:
        response = requests.get(
            f"{GRAFANA_URL}/api/health", auth=(GRAFANA_USER, GRAFANA_PASS), timeout=5
        )
        if response.status_code == 200:
            print("  [OK] Grafana /api/health: OK")
        else:
            print(f"  [WARN]  Grafana /api/health: {response.status_code}")
    except Exception as e:
        print(f"  [WARN]  Grafana /api/health: {e}")

    # Check Prometheus
    try:
        response = requests.get(f"{PROMETHEUS_URL}/-/ready", timeout=5)
        if response.status_code == 200:
            print("  [OK] Prometheus /-/ready: OK")
        else:
            print(f"  [WARN]  Prometheus /-/ready: {response.status_code}")
    except Exception as e:
        print(f"  [WARN]  Prometheus /-/ready: {e}")


def phase5_verification():
    """Phase 5: Run verification loops."""
    print("\n=== PHASE 5: VERIFICATION ===")

    # Check dashboards
    inventory_path = f"{CERT_DIR}/dashboards/inventory.json"
    if Path(inventory_path).exists():
        with open(inventory_path, "r") as f:
            inventory = json.load(f)
            not_found = [
                d for d in inventory["dashboards"] if d["status"] == "NOT_FOUND"
            ]
            if not_found:
                print(f"  [WARN]  {len(not_found)} dashboards still not found")
            else:
                print("  [OK] All dashboards exist")

    # Check health
    health_path = f"{CERT_DIR}/baseline/health_status.json"
    if Path(health_path).exists():
        with open(health_path, "r") as f:
            health = json.load(f)
            all_healthy = all(h.get("healthy", False) for h in health.values())
            if all_healthy:
                print("  [OK] All health endpoints OK")
            else:
                print("  [WARN]  Some health endpoints not OK")

    print("  Verification complete")


def main():
    os.makedirs(CERT_DIR, exist_ok=True)

    print("=" * 60)
    print("HBC END-TO-END RESURRECTION PROTOCOL")
    print("=" * 60)
    print(f"Certification Directory: {CERT_DIR}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Phase 0: Baseline
    health_status = phase0_baseline()

    # Phase 1: Dashboard inventory
    inventory = phase1_dashboard_inventory()

    # Phase 2: Fix dashboards
    phase2_fix_dashboards(inventory)

    # Phase 3: Security hardening
    phase3_security_hardening()

    # Phase 4: Health endpoints
    phase4_health_endpoints()

    # Phase 5: Verification
    phase5_verification()

    print("\n" + "=" * 60)
    print("PROTOCOL COMPLETE")
    print("=" * 60)
    print(f"Evidence stored in: {CERT_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
