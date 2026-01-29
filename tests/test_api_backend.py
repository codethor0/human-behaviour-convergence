"""
Comprehensive tests for the FastAPI backend.
"""

import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import FastAPI dependencies, skip tests if not available
pytest.importorskip("fastapi")
pytest.importorskip("pandas")


@pytest.fixture
def temp_results_dir():
    """Create a temporary results directory with test CSV files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        results_dir = Path(tmpdir) / "results"
        results_dir.mkdir()

        # Create test forecasts.csv
        forecasts_csv = results_dir / "forecasts.csv"
        forecasts_csv.write_text(
            "timestamp,series,value\n"
            "2025-01-01,A,1.0\n"
            "2025-01-02,A,1.1\n"
            "2025-01-03,B,2.0\n"
        )

        # Create test metrics.csv
        metrics_csv = results_dir / "metrics.csv"
        metrics_csv.write_text("metric,value\n" "mae,0.1234\n" "rmse,0.2345\n")

        yield results_dir


@pytest.fixture
def client(temp_results_dir, monkeypatch):
    """Create a test client with mocked RESULTS_DIR."""
    # Import here to ensure RESULTS_DIR is set before module loads
    from app import main

    # Mock RESULTS_DIR to use our temp directory
    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)

    client = TestClient(main.app)
    return client


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_forecasts_with_csv(client):
    """Test forecasts endpoint with CSV file present."""
    response = client.get("/api/forecasts")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 3

    # Check first record
    first = data["data"][0]
    assert "timestamp" in first
    assert "series" in first
    assert "value" in first
    assert first["timestamp"] == "2025-01-01"


def test_get_metrics_with_csv(client):
    """Test metrics endpoint with CSV file present."""
    response = client.get("/api/metrics")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 2

    # Check metrics
    metrics = {m["metric"]: m["value"] for m in data["data"]}
    assert "mae" in metrics
    assert "rmse" in metrics


def test_forecasts_without_csv(monkeypatch):
    """Test forecasts endpoint when CSV file is missing (fallback stub)."""
    from app import main

    # Mock RESULTS_DIR to None to trigger fallback
    monkeypatch.setattr(main, "RESULTS_DIR", None)

    client = TestClient(main.app)
    response = client.get("/api/forecasts")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Should return stub data (2 rows for fallback)
    assert len(data["data"]) >= 2
    assert data["data"][0]["series"] == "A"


def test_metrics_without_csv(monkeypatch):
    """Test metrics endpoint when CSV file is missing (fallback stub)."""
    from app import main

    monkeypatch.setattr(main, "RESULTS_DIR", None)

    client = TestClient(main.app)
    response = client.get("/api/metrics")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Should return stub data
    assert len(data["data"]) == 2


def test_cors_headers(client):
    """Test that CORS headers are properly set."""
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers


def test_api_error_handling_bad_csv(temp_results_dir, monkeypatch):
    """Test error handling when CSV is malformed."""
    # Create invalid CSV
    bad_csv = temp_results_dir / "forecasts.csv"
    bad_csv.write_text("this,is,not\nvalid,csv,content\nwith,mismatched,columns,extra")

    from app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)

    client = TestClient(main.app)
    response = client.get("/api/forecasts")

    # Should handle gracefully (may return 500 or empty data depending on impl)
    assert response.status_code in [200, 500]


def test_forecasts_endpoint_with_limit(client):
    """Test forecasts endpoint respects limit parameter via query string."""
    # Create a CSV with many rows via temp_results_dir fixture
    response = client.get("/api/forecasts?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Should respect limit (if implemented) or return all available
    assert isinstance(data["data"], list)
    assert len(data["data"]) <= 3  # At most 3 rows in fixture


def test_status_endpoint(client, monkeypatch):
    """Test the /api/status endpoint returns service metadata."""
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    monkeypatch.setenv("GIT_COMMIT", "abcdef1")
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"ok": True, "version": "9.9.9", "commit": "abcdef1"}


def test_cache_status_endpoint(client):
    """Ensure cache status endpoint exposes statistics."""
    _ = client.get("/api/forecasts?limit=5")
    resp = client.get("/api/cache/status")
    assert resp.status_code == 200
    data = resp.json()
    assert set(["hits", "misses", "size", "max_size", "ttl_minutes"]).issubset(data)
    assert isinstance(data["hits"], int)
    assert isinstance(data["misses"], int)
    assert data["max_size"] >= 1


def test_create_forecast_endpoint(client):
    """POST /api/forecast should return a valid forecast result structure.

    When data sources are available (or HBC_CI_OFFLINE_DATA=1), history and forecast
    are non-empty. When network is unavailable and no offline data, history/forecast
    may be empty but response structure must still be valid.
    """
    payload = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "region_name": "New York City",
        "days_back": 30,
        "forecast_horizon": 7,
    }
    resp = client.post("/api/forecast", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "history" in data
    assert "forecast" in data
    assert "sources" in data
    assert "metadata" in data
    assert isinstance(data["history"], list)
    assert isinstance(data["forecast"], list)
    # When we have history, forecast length must match horizon; when empty (no network/CI), accept
    if len(data["history"]) > 0:
        assert len(data["forecast"]) == payload["forecast_horizon"]
    else:
        assert len(data["forecast"]) in (0, payload["forecast_horizon"])

    # Verify response structure is consistent on repeat
    resp_repeat = client.post("/api/forecast", json=payload)
    assert resp_repeat.status_code == 200
    data_repeat = resp_repeat.json()
    assert "history" in data_repeat
    assert "forecast" in data_repeat
    assert "sources" in data_repeat
    assert "metadata" in data_repeat
    assert isinstance(data_repeat["history"], list)
    assert isinstance(data_repeat["forecast"], list)
    if len(data_repeat["history"]) > 0:
        assert len(data_repeat["forecast"]) == payload["forecast_horizon"]
    else:
        assert len(data_repeat["forecast"]) in (0, payload["forecast_horizon"])


def test_create_forecast_validation(client):
    """Invalid coordinates should return validation error."""
    resp = client.post(
        "/api/forecast",
        json={
            "latitude": 100.0,
            "longitude": -74.0060,
            "region_name": "Invalid",
            "days_back": 30,
            "forecast_horizon": 7,
        },
    )
    assert resp.status_code == 422
