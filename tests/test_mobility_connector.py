# SPDX-License-Identifier: PROPRIETARY
"""Tests for MobilityFetcher connector."""
from unittest.mock import Mock, patch

import pandas as pd

from app.services.ingestion.mobility import MobilityFetcher


class TestMobilityFetcher:
    """Test suite for MobilityFetcher connector."""

    def test_fetcher_instantiation(self):
        """Test that MobilityFetcher can be instantiated."""
        fetcher = MobilityFetcher()
        assert fetcher is not None
        assert isinstance(fetcher, MobilityFetcher)

    def test_fetch_mobility_index_no_config(self):
        """Test that fetcher returns empty DataFrame when API not configured."""
        fetcher = MobilityFetcher()
        result = fetcher.fetch_mobility_index(days_back=30)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert "mobility_index" in result.columns
        assert result.empty  # Should be empty when API not configured

    @patch("os.getenv")
    @patch("requests_cache.CachedSession")
    def test_fetch_mobility_index_mocked(self, mock_session_class, mock_getenv):
        """Test mobility index fetching with mocked API."""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default: {
            "MOBILITY_API_ENDPOINT": "https://api.example.com/mobility",
            "MOBILITY_API_KEY": "test-key",
        }.get(key, default)

        # Mock session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"timestamp": "2024-01-01", "activity_level": 0.3},
                {"timestamp": "2024-01-02", "activity_level": 0.6},
                {"timestamp": "2024-01-03", "activity_level": 0.9},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        fetcher = MobilityFetcher()
        fetcher.session = mock_session

        result = fetcher.fetch_mobility_index(days_back=3, use_cache=False)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert "mobility_index" in result.columns
        assert len(result) > 0
        # Check normalization
        assert result["mobility_index"].min() >= 0.0
        assert result["mobility_index"].max() <= 1.0

    def test_error_handling(self):
        """Test that fetcher handles errors gracefully."""
        fetcher = MobilityFetcher()
        # Should not raise exception on instantiation
        assert fetcher is not None

    def test_fetch_mobility_index_with_coordinates(self):
        """Test that fetcher accepts latitude and longitude parameters."""
        fetcher = MobilityFetcher()
        result = fetcher.fetch_mobility_index(
            latitude=40.7128, longitude=-74.0060, days_back=30
        )

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert "mobility_index" in result.columns
