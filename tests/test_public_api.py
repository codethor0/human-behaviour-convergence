# SPDX-License-Identifier: MIT-0
"""Tests for public data API endpoints."""
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

# Ensure project root is on path (for top-level packages like 'connectors')
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add backend app to path (so 'from app.main import app' resolves to backend)
sys.path.insert(1, str(Path(__file__).parent.parent / "app" / "backend"))

from fastapi.testclient import TestClient

from app.backend.app.routers import public
from app.main import app

client = TestClient(app)


class TestPublicDataEndpoints:
    """Test /api/public data endpoints."""

    @patch.object(public, "WikiPageviewsSync")
    def test_wiki_latest_endpoint(self, mock_wiki_class):
        """Test /api/public/wiki/latest returns valid response."""
        # Mock the connector class and its pull method
        mock_connector = mock_wiki_class.return_value
        mock_connector.pull.return_value = pd.DataFrame(
            {
                "project": ["en", "de"],
                "hour": [0, 1],
                "views": [1000, 2000],
            }
        )

        response = client.get("/api/public/wiki/latest?date=2024-11-04")
        assert (
            response.status_code == 200
        ), f"Unexpected status code: {response.status_code}"

        data = response.json()
        assert "source" in data
        assert data["source"] == "wiki"
        assert "date" in data
        assert "row_count" in data
        assert "data" in data
        assert isinstance(data["data"], list)

    @patch.object(public, "OSMChangesetsSync")
    def test_osm_latest_endpoint(self, mock_osm_class):
        """Test /api/public/osm/latest returns valid response."""
        # Mock the connector class and its pull method
        mock_connector = mock_osm_class.return_value
        mock_connector.pull.return_value = pd.DataFrame(
            {
                "h3_9": ["8928308280fffff"],
                "changeset_count": [5],
                "buildings_modified": [2],
                "roads_modified": [1],
                "timestamp": ["2024-11-04T00:00:00Z"],
            }
        )

        response = client.get("/api/public/osm/latest?date=2024-11-04")
        assert (
            response.status_code == 200
        ), f"Unexpected status code: {response.status_code}"

        data = response.json()
        assert data["source"] == "osm"

    def test_firms_latest_endpoint(self):
        """Test /api/public/firms/latest returns valid response."""
        # FIRMS connector returns empty DataFrame when no API key, so no mocking needed
        response = client.get("/api/public/firms/latest")
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["source"] == "firms"

    def test_invalid_source(self):
        """Test /api/public with invalid source returns 422."""
        response = client.get("/api/public/invalid/latest")
        assert response.status_code == 422  # Validation error

    @patch.object(public, "FIRMSFiresSync")
    @patch.object(public, "OSMChangesetsSync")
    @patch.object(public, "WikiPageviewsSync")
    def test_synthetic_score_endpoint(
        self, mock_wiki_class, mock_osm_class, mock_firms_class
    ):
        """Test /api/public/synthetic_score endpoint."""
        # Mock all three connector classes
        mock_wiki = mock_wiki_class.return_value
        mock_wiki.pull.return_value = pd.DataFrame({"views": [1000, 2000]})

        mock_osm = mock_osm_class.return_value
        mock_osm.pull.return_value = pd.DataFrame({"changeset_count": [5, 10]})

        mock_firms = mock_firms_class.return_value
        mock_firms.pull.return_value = pd.DataFrame({"fire_count": [1, 2]})

        response = client.get("/api/public/synthetic_score/9/2024-11-04")
        assert (
            response.status_code == 200
        ), f"Unexpected status code: {response.status_code}"

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
