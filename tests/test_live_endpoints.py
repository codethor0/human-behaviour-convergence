# SPDX-License-Identifier: PROPRIETARY
"""Tests for live monitoring API endpoints."""
from fastapi.testclient import TestClient

from app.backend.app.main import app

client = TestClient(app)


class TestLiveEndpoints:
    """Test suite for live monitoring endpoints."""

    def test_live_summary_no_regions(self):
        """Test live summary endpoint with no regions specified."""
        response = client.get("/api/live/summary")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "regions" in data

    def test_live_summary_with_regions(self):
        """Test live summary endpoint with specific regions."""
        response = client.get(
            "/api/live/summary",
            params={"regions": ["us_dc", "us_mn"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "regions" in data

    def test_live_summary_time_window(self):
        """Test live summary endpoint with time window parameter."""
        response = client.get(
            "/api/live/summary",
            params={"time_window_minutes": 120},
        )
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data

    def test_live_summary_invalid_time_window(self):
        """Test live summary endpoint with invalid time window."""
        response = client.get(
            "/api/live/summary",
            params={"time_window_minutes": 0},  # Below minimum
        )
        assert response.status_code == 422  # Validation error

    def test_live_refresh_no_regions(self):
        """Test live refresh endpoint with no regions specified."""
        response = client.post("/api/live/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "results" in data

    def test_live_refresh_with_regions(self):
        """Test live refresh endpoint with specific regions."""
        response = client.post(
            "/api/live/refresh",
            params={"regions": ["us_dc"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "results" in data
        assert "us_dc" in data["results"]
