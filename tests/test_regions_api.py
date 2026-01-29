# SPDX-License-Identifier: PROPRIETARY
"""Tests for regions API endpoint."""
# Import app directly from backend to avoid shim recursion
# The shim in app/__init__.py can cause recursion during pytest collection
import sys

from fastapi.testclient import TestClient

from app.core.regions import get_all_regions, get_region_by_id

if "app.backend.app.main" not in sys.modules:
    from app.backend.app.main import app
else:
    app = sys.modules["app.backend.app.main"].app

client = TestClient(app)


class TestRegionsAPI:
    """Test suite for regions API endpoint."""

    def test_get_regions_endpoint(self):
        """Test GET /api/forecasting/regions returns all regions."""
        response = client.get("/api/forecasting/regions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least 62 regions (50 US states + DC + 3 original + 8 new)
        assert len(data) >= 62

    def test_regions_contains_us_states(self):
        """Test that regions endpoint includes US states."""
        response = client.get("/api/forecasting/regions")
        assert response.status_code == 200
        data = response.json()

        # Check for some known states
        state_ids = {r["id"] for r in data if r["region_type"] == "state"}
        assert "us_mn" in state_ids
        assert "us_ca" in state_ids
        assert "us_tx" in state_ids
        assert "us_ny" in state_ids

    def test_regions_contains_global_cities(self):
        """Test that regions endpoint includes global cities."""
        response = client.get("/api/forecasting/regions")
        assert response.status_code == 200
        data = response.json()

        # Check for known cities
        city_ids = {r["id"] for r in data if r["region_type"] == "city"}
        assert "city_nyc" in city_ids
        assert "city_london" in city_ids
        assert "city_tokyo" in city_ids
        # Check for new global cities
        assert "city_la" in city_ids
        assert "city_paris" in city_ids
        assert "city_sydney" in city_ids

    def test_region_structure(self):
        """Test that each region has required fields."""
        response = client.get("/api/forecasting/regions")
        assert response.status_code == 200
        data = response.json()

        for region in data:
            assert "id" in region
            assert "name" in region
            assert "country" in region
            assert "region_type" in region
            assert "latitude" in region
            assert "longitude" in region
            assert -90 <= region["latitude"] <= 90
            assert -180 <= region["longitude"] <= 180
            # region_group is optional but should be present for most regions
            if "region_group" in region:
                assert region["region_group"] in [
                    "GLOBAL_CITIES",
                    "US_STATES",
                    "EUROPE",
                    "ASIA_PACIFIC",
                    "LATAM",
                    "AFRICA",
                    None,
                ]

    def test_forecast_with_region_id(self):
        """Test forecast endpoint accepts region_id and returns valid structure."""
        response = client.post(
            "/api/forecast",
            json={
                "region_id": "us_mn",
                "region_name": "Minnesota",
                "days_back": 30,
                "forecast_horizon": 7,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert "forecast" in data
        assert isinstance(data["history"], list)
        assert isinstance(data["forecast"], list)
        if len(data["history"]) > 0:
            assert len(data["forecast"]) == 7

    def test_forecast_with_region_id_invalid(self):
        """Test forecast endpoint returns 404 for invalid region_id."""
        response = client.post(
            "/api/forecast",
            json={
                "region_id": "invalid_region",
                "region_name": "Invalid",
                "days_back": 30,
                "forecast_horizon": 7,
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_forecast_with_region_id_mn(self):
        """Test forecast for Minnesota state; structure when history present."""
        response = client.post(
            "/api/forecast",
            json={
                "region_id": "us_mn",
                "region_name": "Minnesota",
                "days_back": 30,
                "forecast_horizon": 7,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["history"], list)
        assert isinstance(data["forecast"], list)
        if len(data["history"]) > 0 and len(data["forecast"]) > 0:
            assert len(data["forecast"]) == 7
            forecast_item = data["forecast"][0]
            assert "timestamp" in forecast_item
            assert "prediction" in forecast_item
            assert "lower_bound" in forecast_item
            assert "upper_bound" in forecast_item

    def test_forecast_with_new_global_city(self):
        """Test forecast for a newly added global city; structure when data present."""
        response = client.post(
            "/api/forecast",
            json={
                "region_id": "city_paris",
                "region_name": "Paris",
                "days_back": 30,
                "forecast_horizon": 7,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["history"], list)
        assert isinstance(data["forecast"], list)
        if len(data["history"]) > 0:
            assert len(data["forecast"]) == 7


class TestRegionsModule:
    """Test suite for regions module functions."""

    def test_get_all_regions(self):
        """Test get_all_regions returns all regions."""
        regions = get_all_regions()
        assert len(regions) >= 62  # 50 states + DC + 3 original cities + 8 new cities
        assert all(r.region_type in ("city", "state", "country") for r in regions)
        # Check that region_group is assigned
        assert all(r.region_group is not None for r in regions)

    def test_get_region_by_id(self):
        """Test get_region_by_id finds regions."""
        region = get_region_by_id("us_mn")
        assert region is not None
        assert region.name == "Minnesota"
        assert region.region_type == "state"

        region = get_region_by_id("city_nyc")
        assert region is not None
        assert region.name == "New York City"
        assert region.region_type == "city"

    def test_get_region_by_id_not_found(self):
        """Test get_region_by_id returns None for invalid ID."""
        region = get_region_by_id("invalid_id")
        assert region is None
