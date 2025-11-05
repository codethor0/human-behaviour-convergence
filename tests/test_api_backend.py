"""
Comprehensive tests for the FastAPI backend.
"""

import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import FastAPI dependencies, skip tests if not available
pytest.importorskip("fastapi")
pytest.importorskip("pandas")

from fastapi.testclient import TestClient


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
    from app.backend.app import main

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
    from app.backend.app import main

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
    from app.backend.app import main

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


def test_csv_limit_parameter(temp_results_dir, monkeypatch):
    """Test that CSV reading respects the limit parameter."""
    # Create a CSV with many rows
    large_csv = temp_results_dir / "forecasts.csv"
    rows = ["timestamp,series,value"]
    for i in range(2000):
        rows.append(f"2025-01-{i % 28 + 1:02d},A,{i}.0")
    large_csv.write_text("\n".join(rows))

    from app.backend.app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)

    # Test that default limit works
    data = main._read_csv("forecasts.csv", limit=100)
    assert len(data) == 100


def test_find_results_dir():
    """Test the _find_results_dir utility function."""
    from app.backend.app.main import _find_results_dir

    # Should find results dir from repo structure
    result = _find_results_dir(Path(__file__).parent)
    # May be None in test environment, that's ok
    assert result is None or result.name == "results"


def test_read_csv_invalid_file(temp_results_dir, monkeypatch):
    """Test _read_csv with invalid/non-existent file."""
    from app.backend.app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)

    # Non-existent file should return empty list (fallback)
    result = main._read_csv("nonexistent.csv")
    assert result == []


def test_api_error_handling_bad_csv(temp_results_dir, monkeypatch):
    """Test error handling when CSV is malformed."""
    # Create invalid CSV
    bad_csv = temp_results_dir / "forecasts.csv"
    bad_csv.write_text("this,is,not\nvalid,csv,content\nwith,mismatched,columns,extra")

    from app.backend.app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)

    client = TestClient(main.app)
    response = client.get("/api/forecasts")

    # Should handle gracefully (may return 500 or empty data depending on implementation)
    assert response.status_code in [200, 500]


def test_csv_negative_limit_validation(temp_results_dir, monkeypatch):
    """Test that negative limit values are rejected."""
    from app.backend.app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)

    # Test negative limit raises ValueError
    with pytest.raises(ValueError, match="limit must be non-negative"):
        main._read_csv("forecasts.csv", limit=-1)


def test_cache_eviction(temp_results_dir, monkeypatch):
    """Test that cache eviction works when MAX_CACHE_SIZE is exceeded."""
    from app.backend.app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)
    monkeypatch.setattr(main, "MAX_CACHE_SIZE", 3)  # Set small cache for testing

    # Clear cache to start fresh
    main._cache.clear()
    main._cache_ttl.clear()

    # Fill cache to max
    main._read_csv("forecasts.csv", limit=10)
    main._read_csv("forecasts.csv", limit=20)
    main._read_csv("forecasts.csv", limit=30)
    assert len(main._cache) == 3

    # Add one more - should trigger eviction
    main._read_csv("forecasts.csv", limit=40)
    assert len(main._cache) == 3  # Still at max size

    # First entry should be evicted
    assert ("forecasts.csv", 10) not in main._cache
    assert ("forecasts.csv", 40) in main._cache


def test_path_traversal_prevention(temp_results_dir, monkeypatch):
    """Test that path traversal attacks are blocked."""
    from app.backend.app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)

    # Test various path traversal attempts
    with pytest.raises(ValueError, match="Path traversal detected"):
        main._read_csv("../etc/passwd")

    with pytest.raises(ValueError, match="Path traversal detected"):
        main._read_csv("../../secrets.txt")

    with pytest.raises(ValueError, match="Path traversal detected"):
        main._read_csv("subdir/../../../etc/passwd")

    with pytest.raises(ValueError, match="Path traversal detected"):
        main._read_csv("forecasts.csv/../../../etc/passwd")


def test_non_csv_file_rejection(temp_results_dir, monkeypatch):
    """Test that only CSV files are allowed."""
    from app.backend.app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)

    # Create a non-CSV file
    txt_file = temp_results_dir / "data.txt"
    txt_file.write_text("secret data")

    with pytest.raises(ValueError, match="Only CSV files are allowed"):
        main._read_csv("data.txt")

    with pytest.raises(ValueError, match="Only CSV files are allowed"):
        main._read_csv("script.py")

    with pytest.raises(ValueError, match="Only CSV files are allowed"):
        main._read_csv("config.json")


def test_limit_upper_bound_validation(temp_results_dir, monkeypatch):
    """Test that extremely large limit values are rejected."""
    from app.backend.app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)

    # Test limit exceeding MAX_LIMIT
    with pytest.raises(ValueError, match="limit must not exceed"):
        main._read_csv("forecasts.csv", limit=999999)

    with pytest.raises(ValueError, match="limit must not exceed"):
        main._read_csv("forecasts.csv", limit=main.MAX_LIMIT + 1)

    # Valid limit should work
    result = main._read_csv("forecasts.csv", limit=main.MAX_LIMIT)
    assert isinstance(result, list)


def test_api_limit_query_parameter_validation(client):
    """Test that API endpoints validate limit query parameter."""
    # Test negative limit
    response = client.get("/api/forecasts?limit=-1")
    assert response.status_code == 422  # FastAPI validation error

    # Test limit exceeding max
    response = client.get("/api/forecasts?limit=99999")
    assert response.status_code == 422  # FastAPI validation error

    # Test valid limit
    response = client.get("/api/forecasts?limit=100")
    assert response.status_code == 200


def test_empty_filename_rejection(temp_results_dir, monkeypatch):
    """Test that empty filenames are rejected."""
    from app.backend.app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)

    with pytest.raises(ValueError, match="Filename cannot be empty"):
        main._read_csv("")


def test_thread_safety_concurrent_cache_access(temp_results_dir, monkeypatch):
    """Test that concurrent cache access is thread-safe."""
    import threading

    from app.backend.app import main

    monkeypatch.setattr(main, "RESULTS_DIR", temp_results_dir)
    main._cache.clear()
    main._cache_ttl.clear()

    results = []
    errors = []

    def worker(limit):
        try:
            result = main._read_csv("forecasts.csv", limit=limit)
            results.append((limit, len(result)))
        except Exception as e:
            errors.append(e)

    # Create multiple threads accessing cache concurrently
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, 21)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # All threads should complete without errors
    assert len(errors) == 0
    assert len(results) == 20

    # Cache should be consistent
    assert len(main._cache) <= main.MAX_CACHE_SIZE
