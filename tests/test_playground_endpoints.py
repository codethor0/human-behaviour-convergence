# SPDX-License-Identifier: PROPRIETARY
"""Tests for playground API endpoints."""
from fastapi.testclient import TestClient

from app.backend.app.main import app

client = TestClient(app)


class TestPlaygroundEndpoints:
    """Test suite for playground endpoints."""

    def test_playground_compare_single_region(self):
        """Test playground compare with single region."""
        response = client.post(
            "/api/playground/compare",
            json={
                "regions": ["us_dc"],
                "historical_days": 30,
                "forecast_horizon_days": 7,
                "include_explanations": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "results" in data
        assert "errors" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["region_id"] == "us_dc"

    def test_playground_compare_multiple_regions(self):
        """Test playground compare with multiple regions."""
        response = client.post(
            "/api/playground/compare",
            json={
                "regions": ["us_dc", "us_mn"],
                "historical_days": 30,
                "forecast_horizon_days": 7,
                "include_explanations": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        region_ids = [r["region_id"] for r in data["results"]]
        assert "us_dc" in region_ids
        assert "us_mn" in region_ids

    def test_playground_compare_with_explanations(self):
        """Test playground compare with explanations enabled."""
        response = client.post(
            "/api/playground/compare",
            json={
                "regions": ["us_dc"],
                "historical_days": 30,
                "forecast_horizon_days": 7,
                "include_explanations": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["include_explanations"] is True

    def test_playground_compare_with_scenario(self):
        """Test playground compare with scenario adjustments."""
        response = client.post(
            "/api/playground/compare",
            json={
                "regions": ["us_dc"],
                "historical_days": 30,
                "forecast_horizon_days": 7,
                "include_explanations": False,
                "scenario": {
                    "digital_attention_offset": 0.1,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["scenario_applied"] is True

    def test_playground_compare_invalid_region(self):
        """Test playground compare with invalid region."""
        response = client.post(
            "/api/playground/compare",
            json={
                "regions": ["invalid_region_id"],
                "historical_days": 30,
                "forecast_horizon_days": 7,
            },
        )
        assert response.status_code == 200  # Should not fail, just return error
        data = response.json()
        assert len(data["results"]) == 0
        assert len(data["errors"]) == 1

    def test_playground_compare_empty_regions(self):
        """Test playground compare with empty regions list."""
        response = client.post(
            "/api/playground/compare",
            json={
                "regions": [],
                "historical_days": 30,
                "forecast_horizon_days": 7,
            },
        )
        assert response.status_code == 422  # Validation error

    def test_playground_compare_too_many_regions(self):
        """Test playground compare with too many regions."""
        response = client.post(
            "/api/playground/compare",
            json={
                "regions": [f"us_dc_{i}" for i in range(15)],  # More than max_items=10
                "historical_days": 30,
                "forecast_horizon_days": 7,
            },
        )
        assert response.status_code == 422  # Validation error

    def test_playground_compare_invalid_scenario_offset(self):
        """Test playground compare with invalid scenario offset."""
        response = client.post(
            "/api/playground/compare",
            json={
                "regions": ["us_dc"],
                "historical_days": 30,
                "forecast_horizon_days": 7,
                "scenario": {
                    "digital_attention_offset": 2.0,  # Exceeds max of 1.0
                },
            },
        )
        assert response.status_code == 422  # Validation error
