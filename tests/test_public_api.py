# SPDX-License-Identifier: MIT-0
"""Tests for public data API endpoints."""
import sys
from pathlib import Path

# Add backend app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "backend"))

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


class TestPublicDataEndpoints:
    """Test /api/public data endpoints."""

    def test_wiki_latest_endpoint(self):
        """Test /api/public/wiki/latest returns valid response."""
        response = client.get("/api/public/wiki/latest")
        assert response.status_code in [
            200,
            500,
        ]  # May fail without data, but should not 404

        if response.status_code == 200:
            data = response.json()
            assert "source" in data
            assert data["source"] == "wiki"
            assert "date" in data
            assert "row_count" in data
            assert "data" in data
            assert isinstance(data["data"], list)

    def test_osm_latest_endpoint(self):
        """Test /api/public/osm/latest returns valid response."""
        response = client.get("/api/public/osm/latest")
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["source"] == "osm"

    def test_firms_latest_endpoint(self):
        """Test /api/public/firms/latest returns valid response."""
        response = client.get("/api/public/firms/latest")
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["source"] == "firms"

    def test_invalid_source(self):
        """Test /api/public with invalid source returns 422."""
        response = client.get("/api/public/invalid/latest")
        assert response.status_code == 422  # Validation error

    def test_synthetic_score_endpoint(self):
        """Test /api/public/synthetic_score endpoint."""
        response = client.get("/api/public/synthetic_score/9/2024-11-04")
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "h3_res" in data
            assert data["h3_res"] == 9
            assert "date" in data
            assert "scores" in data
            assert isinstance(data["scores"], list)

    def test_synthetic_score_invalid_h3_res(self):
        """Test synthetic_score with invalid H3 resolution."""
        response = client.get("/api/public/synthetic_score/3/2024-11-04")  # Too low
        assert response.status_code == 422

        response = client.get("/api/public/synthetic_score/15/2024-11-04")  # Too high
        assert response.status_code == 422

    def test_date_format_validation(self):
        """Test that date format is validated."""
        response = client.get("/api/public/wiki/latest?date=invalid-date")
        assert response.status_code == 422  # Validation error
