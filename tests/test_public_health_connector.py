# SPDX-License-Identifier: MIT-0
"""Tests for PublicHealthFetcher connector."""
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from app.services.ingestion.public_health import PublicHealthFetcher


class TestPublicHealthFetcher:
    """Test suite for PublicHealthFetcher connector."""

    def test_fetcher_instantiation(self):
        """Test that PublicHealthFetcher can be instantiated."""
        fetcher = PublicHealthFetcher()
        assert fetcher is not None
        assert isinstance(fetcher, PublicHealthFetcher)

    def test_fetch_health_risk_index_no_config(self):
        """Test that fetcher returns empty DataFrame when API not configured."""
        fetcher = PublicHealthFetcher()
        result = fetcher.fetch_health_risk_index(days_back=30)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert "health_risk_index" in result.columns
        assert result.empty  # Should be empty when API not configured

    @patch("os.getenv")
    @patch("requests_cache.CachedSession")
    def test_fetch_health_risk_index_mocked(self, mock_session_class, mock_getenv):
        """Test health risk index fetching with mocked API."""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default: {
            "PUBLIC_HEALTH_API_ENDPOINT": "https://api.example.com/health",
            "PUBLIC_HEALTH_API_KEY": "test-key",
        }.get(key, default)

        # Mock session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"timestamp": "2024-01-01", "risk_level": 0.2},
                {"timestamp": "2024-01-02", "risk_level": 0.5},
                {"timestamp": "2024-01-03", "risk_level": 0.8},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        fetcher = PublicHealthFetcher()
        fetcher.session = mock_session

        result = fetcher.fetch_health_risk_index(days_back=3, use_cache=False)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert "health_risk_index" in result.columns
        assert len(result) > 0
        # Check normalization
        assert result["health_risk_index"].min() >= 0.0
        assert result["health_risk_index"].max() <= 1.0

    def test_error_handling(self):
        """Test that fetcher handles errors gracefully."""
        fetcher = PublicHealthFetcher()
        # Should not raise exception on instantiation
        assert fetcher is not None

    def test_fetch_health_risk_index_with_region(self):
        """Test that fetcher accepts region_code parameter."""
        fetcher = PublicHealthFetcher()
        result = fetcher.fetch_health_risk_index(region_code="US", days_back=30)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert "health_risk_index" in result.columns
