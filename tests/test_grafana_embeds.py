"""
Test suite for Grafana dashboard embedding verification.
CI-safe: can run with or without Docker stack.
"""
import json
import os
import re
from pathlib import Path


def test_dashboard_manifest_exists():
    """Verify dashboard JSON files exist in provisioning directory."""
    dashboards_dir = Path("infra/grafana/dashboards")
    assert dashboards_dir.exists(), f"Dashboard directory not found: {dashboards_dir}"
    
    json_files = list(dashboards_dir.glob("*.json"))
    assert len(json_files) > 0, "No dashboard JSON files found"
    
    return json_files


def test_expected_dashboard_uids_present():
    """Verify expected dashboard UIDs are present in JSON files."""
    expected_uids = [
        "forecast-summary",
        "behavior-index-global",
        "subindex-deep-dive",
        "regional-variance-explorer",
        "forecast-quality-drift",
        "algorithm-model-comparison",
        "data-sources-health",
        "source-health-freshness",
    ]
    
    dashboards_dir = Path("infra/grafana/dashboards")
    found_uids = set()
    
    for json_file in dashboards_dir.glob("*.json"):
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                if "uid" in data:
                    found_uids.add(data["uid"])
        except (json.JSONDecodeError, KeyError):
            continue
    
    missing = set(expected_uids) - found_uids
    assert len(missing) == 0, f"Missing dashboard UIDs: {missing}"
    
    return found_uids


def test_frontend_embed_list_matches_manifest():
    """Verify frontend forecast page includes embeds for expected dashboards."""
    forecast_page = Path("app/frontend/src/pages/forecast.tsx")
    assert forecast_page.exists(), f"Forecast page not found: {forecast_page}"
    
    content = forecast_page.read_text()
    
    expected_dashboards = [
        "forecast-summary",
        "behavior-index-global",
        "subindex-deep-dive",
        "regional-variance-explorer",
        "forecast-quality-drift",
        "algorithm-model-comparison",
        "data-sources-health",
        "source-health-freshness",
    ]
    
    missing = []
    for uid in expected_dashboards:
        if f'dashboardUid="{uid}"' not in content and f"dashboardUid='{uid}'" not in content:
            missing.append(uid)
    
    assert len(missing) == 0, f"Frontend missing dashboard embeds: {missing}"
    
    return True


def test_grafana_embedding_config_static():
    """Verify Grafana embedding configuration in docker-compose.yml."""
    compose_file = Path("docker-compose.yml")
    assert compose_file.exists(), "docker-compose.yml not found"
    
    content = compose_file.read_text()
    
    assert 'GF_SECURITY_ALLOW_EMBEDDING=true' in content, "Grafana embedding not enabled"
    assert 'GF_AUTH_ANONYMOUS_ENABLED=true' in content, "Grafana anonymous access not enabled"
    
    return True


def test_grafana_health_reachable():
    """Verify Grafana health endpoint is reachable (requires running stack)."""
    import urllib.request
    import urllib.error
    
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3001")
    health_url = f"{grafana_url}/api/health"
    
    try:
        with urllib.request.urlopen(health_url, timeout=5) as response:
            assert response.status == 200, f"Grafana health returned {response.status}"
            return True
    except (urllib.error.URLError, OSError) as e:
        # CI-safe: skip if stack not running
        if os.getenv("CI") or os.getenv("SKIP_STACK_TESTS"):
            return True  # Skip in CI if stack not available
        raise AssertionError(f"Grafana health check failed: {e}")


if __name__ == "__main__":
    import sys
    
    tests = [
        test_dashboard_manifest_exists,
        test_expected_dashboard_uids_present,
        test_frontend_embed_list_matches_manifest,
        test_grafana_embedding_config_static,
        test_grafana_health_reachable,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = test()
            print(f"✓ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            failed += 1
    
    print(f"\nPassed: {passed}, Failed: {failed}")
    sys.exit(0 if failed == 0 else 1)
