"""Static contract test for Grafana embed configuration."""
import json
from pathlib import Path


def test_dashboard_uids_exist_in_repo():
    """Verify all dashboard UIDs referenced in frontend exist in repo."""
    # Expected UIDs from forecast.tsx
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
    
    # Load dashboard JSONs
    dashboards_dir = Path("infra/grafana/dashboards")
    existing_uids = set()
    
    for json_file in dashboards_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)
                uid = data.get("uid")
                if uid:
                    existing_uids.add(uid)
        except Exception:
            continue
    
    # Verify all expected UIDs exist
    missing = set(expected_uids) - existing_uids
    assert not missing, f"Missing dashboard UIDs: {missing}"


def test_grafana_config_allows_embedding():
    """Verify docker-compose.yml has embedding enabled."""
    compose_file = Path("docker-compose.yml")
    assert compose_file.exists(), "docker-compose.yml not found"
    
    with open(compose_file) as f:
        content = f.read()
    
    assert "GF_SECURITY_ALLOW_EMBEDDING=true" in content, "GF_SECURITY_ALLOW_EMBEDDING not set"
    assert "GF_AUTH_ANONYMOUS_ENABLED=true" in content, "GF_AUTH_ANONYMOUS_ENABLED not set"


def test_grafana_dashboard_files_exist():
    """Verify dashboard JSON files exist in provisioning directory."""
    dashboards_dir = Path("infra/grafana/dashboards")
    assert dashboards_dir.exists(), "Dashboard directory not found"
    
    json_files = list(dashboards_dir.glob("*.json"))
    assert len(json_files) > 0, "No dashboard JSON files found"
    
    # Verify at least expected dashboards exist
    expected_files = [
        "forecast_summary.json",
        "global_behavior_index.json",
        "subindex_deep_dive.json",
    ]
    
    existing_files = {f.name for f in json_files}
    missing_files = [f for f in expected_files if f not in existing_files]
    
    assert not missing_files, f"Missing dashboard files: {missing_files}"
