# SPDX-License-Identifier: MIT-0
"""Tests for forecasting API endpoints."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.backend.app.main import app

client = TestClient(app)


class TestForecastingEndpoints:
    """Test suite for forecasting-related endpoints."""

    def test_get_data_sources(self):
        """Test GET /api/forecasting/data-sources endpoint."""
        response = client.get("/api/forecasting/data-sources")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert all("name" in item for item in data)
        assert all("description" in item for item in data)
        assert all("status" in item for item in data)

    def test_get_models(self):
        """Test GET /api/forecasting/models endpoint."""
        response = client.get("/api/forecasting/models")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert all("name" in item for item in data)
        assert all("description" in item for item in data)
        assert all("type" in item for item in data)

    def test_get_forecasting_status(self):
        """Test GET /api/forecasting/status endpoint."""
        response = client.get("/api/forecasting/status")
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "data_sources" in data
        assert "models" in data
        assert data["system"] == "operational"

    def test_get_forecast_history_empty(self):
        """Test GET /api/forecasting/history endpoint returns empty list."""
        response = client.get("/api/forecasting/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_forecast_history_with_limit(self):
        """Test GET /api/forecasting/history with limit parameter."""
        response = client.get("/api/forecasting/history?limit=50")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_forecast_history_with_region_filter(self):
        """Test GET /api/forecasting/history with region filter."""
        response = client.get("/api/forecasting/history?region_name=New%20York")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch("app.backend.app.main.BehavioralForecaster")
    def test_create_forecast_success(self, mock_forecaster_class):
        """Test POST /api/forecast with valid request."""
        mock_forecaster = MagicMock()
        mock_result = {
            "history": [
                {"timestamp": "2025-01-01", "behavior_index": 0.5},
                {"timestamp": "2025-01-02", "behavior_index": 0.6},
            ],
            "forecast": [
                {
                    "timestamp": "2025-01-08",
                    "prediction": 0.65,
                    "lower_bound": 0.6,
                    "upper_bound": 0.7,
                }
            ],
            "sources": ["yfinance (VIX/SPY)", "openmeteo.com (Weather)"],
            "metadata": {
                "region_name": "New York City",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "forecast_date": "2025-01-07T00:00:00",
                "forecast_horizon": 7,
                "historical_data_points": 2,
                "model_type": "ExponentialSmoothing (Holt-Winters)",
            },
        }
        mock_forecaster.forecast.return_value = mock_result
        mock_forecaster_class.return_value = mock_forecaster

        response = client.post(
            "/api/forecast",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "region_name": "New York City",
                "days_back": 30,
                "forecast_horizon": 7,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert "forecast" in data
        assert "sources" in data
        assert "metadata" in data

    def test_create_forecast_invalid_latitude(self):
        """Test POST /api/forecast with invalid latitude."""
        response = client.post(
            "/api/forecast",
            json={
                "latitude": 100.0,
                "longitude": -74.0060,
                "region_name": "New York City",
                "days_back": 30,
                "forecast_horizon": 7,
            },
        )
        assert response.status_code == 422

    def test_create_forecast_invalid_longitude(self):
        """Test POST /api/forecast with invalid longitude."""
        response = client.post(
            "/api/forecast",
            json={
                "latitude": 40.7128,
                "longitude": 200.0,
                "region_name": "New York City",
                "days_back": 30,
                "forecast_horizon": 7,
            },
        )
        assert response.status_code == 422

    def test_create_forecast_missing_required_field(self):
        """Test POST /api/forecast with missing required field."""
        response = client.post(
            "/api/forecast",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "days_back": 30,
                "forecast_horizon": 7,
            },
        )
        assert response.status_code == 422

