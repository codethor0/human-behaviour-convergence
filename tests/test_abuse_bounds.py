# SPDX-License-Identifier: PROPRIETARY
"""Tests for abuse and DoS protection bounds."""
from fastapi.testclient import TestClient

from app.backend.app.main import app

client = TestClient(app)


class TestForecastBounds:
    """Test bounds on forecast endpoint parameters."""

    def test_days_back_minimum(self):
        """Test that days_back < 7 is rejected."""
        payload = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "region_name": "Test",
            "days_back": 6,  # Below minimum
            "forecast_horizon": 7,
        }
        response = client.post("/api/forecast", json=payload)
        assert response.status_code == 422  # Validation error

    def test_days_back_maximum(self):
        """Test that days_back > 365 is rejected."""
        payload = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "region_name": "Test",
            "days_back": 366,  # Above maximum
            "forecast_horizon": 7,
        }
        response = client.post("/api/forecast", json=payload)
        assert response.status_code == 422  # Validation error

    def test_forecast_horizon_maximum(self):
        """Test that forecast_horizon > 30 is rejected."""
        payload = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "region_name": "Test",
            "days_back": 30,
            "forecast_horizon": 31,  # Above maximum
        }
        response = client.post("/api/forecast", json=payload)
        assert response.status_code == 422  # Validation error

    def test_coordinate_bounds(self):
        """Test that invalid coordinates are rejected."""
        # Latitude > 90
        payload = {
            "latitude": 91.0,
            "longitude": -74.0060,
            "region_name": "Test",
            "days_back": 30,
            "forecast_horizon": 7,
        }
        response = client.post("/api/forecast", json=payload)
        assert response.status_code == 422  # Validation error

        # Longitude > 180
        payload = {
            "latitude": 40.7128,
            "longitude": 181.0,
            "region_name": "Test",
            "days_back": 30,
            "forecast_horizon": 7,
        }
        response = client.post("/api/forecast", json=payload)
        assert response.status_code == 422  # Validation error


class TestPlaygroundBounds:
    """Test bounds on playground compare endpoint."""

    def test_regions_maximum(self):
        """Test that > 10 regions is rejected."""
        payload = {
            "regions": [f"region_{i}" for i in range(11)],  # 11 regions
            "historical_days": 30,
            "forecast_horizon_days": 7,
        }
        response = client.post("/api/playground/compare", json=payload)
        assert response.status_code == 422  # Validation error

    def test_regions_minimum(self):
        """Test that empty regions list is rejected."""
        payload = {
            "regions": [],  # Empty list
            "historical_days": 30,
            "forecast_horizon_days": 7,
        }
        response = client.post("/api/playground/compare", json=payload)
        assert response.status_code == 422  # Validation error

    def test_historical_days_bounds(self):
        """Test that historical_days bounds are enforced."""
        # Below minimum
        payload = {
            "regions": ["us_dc"],
            "historical_days": 6,  # Below minimum
            "forecast_horizon_days": 7,
        }
        response = client.post("/api/playground/compare", json=payload)
        assert response.status_code == 422  # Validation error

        # Above maximum
        payload = {
            "regions": ["us_dc"],
            "historical_days": 366,  # Above maximum
            "forecast_horizon_days": 7,
        }
        response = client.post("/api/playground/compare", json=payload)
        assert response.status_code == 422  # Validation error


class TestCSVReadBounds:
    """Test bounds on CSV read endpoints."""

    def test_forecasts_limit_maximum(self):
        """Test that limit > 10000 is rejected."""
        response = client.get("/api/forecasts?limit=10001")
        assert response.status_code == 422  # Validation error

    def test_metrics_limit_maximum(self):
        """Test that limit > 10000 is rejected."""
        response = client.get("/api/metrics?limit=10001")
        assert response.status_code == 422  # Validation error

    def test_forecasts_limit_minimum(self):
        """Test that limit < 1 is rejected."""
        response = client.get("/api/forecasts?limit=0")
        assert response.status_code == 422  # Validation error


class TestPublicDataBounds:
    """Test bounds on public data endpoints."""

    def test_h3_res_bounds(self):
        """Test that h3_res bounds are enforced."""
        # Below minimum
        response = client.get("/api/public/synthetic_score/4/2024-01-01")
        assert response.status_code == 422  # Validation error

        # Above maximum
        response = client.get("/api/public/synthetic_score/10/2024-01-01")
        assert response.status_code == 422  # Validation error

    def test_date_format_validation(self):
        """Test that invalid date format is rejected."""
        response = client.get("/api/public/synthetic_score/9/invalid-date")
        assert response.status_code == 422  # Validation error


class TestLiveBounds:
    """Test bounds on live monitoring endpoints."""

    def test_time_window_minimum(self):
        """Test that time_window_minutes < 1 is rejected."""
        response = client.get("/api/live/summary?time_window_minutes=0")
        assert response.status_code == 422  # Validation error

    def test_time_window_maximum(self):
        """Test that time_window_minutes > 1440 is rejected."""
        response = client.get("/api/live/summary?time_window_minutes=1441")
        assert response.status_code == 422  # Validation error
