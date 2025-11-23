# SPDX-License-Identifier: MIT-0
"""Tests for SearchTrendsFetcher connector."""
from unittest.mock import Mock, patch
from datetime import datetime

import pandas as pd
import pytest

from app.services.ingestion.search_trends import SearchTrendsFetcher


class TestSearchTrendsFetcher:
    """Test suite for SearchTrendsFetcher connector."""

    def test_fetcher_instantiation(self):
        """Test that SearchTrendsFetcher can be instantiated."""
        fetcher = SearchTrendsFetcher()
        assert fetcher is not None
        assert isinstance(fetcher, SearchTrendsFetcher)

    def test_fetch_search_interest_no_config(self):
        """Test that fetcher returns empty DataFrame when API not configured."""
        fetcher = SearchTrendsFetcher()
        result = fetcher.fetch_search_interest(query="test", days_back=30)
        
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert "search_interest_score" in result.columns
        assert result.empty  # Should be empty when API not configured

    @patch("os.getenv")
    @patch("requests_cache.CachedSession")
    def test_fetch_search_interest_mocked(self, mock_session_class, mock_getenv):
        """Test search interest fetching with mocked API."""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default: {
            "SEARCH_TRENDS_API_ENDPOINT": "https://api.example.com/search",
            "SEARCH_TRENDS_API_KEY": "test-key",
        }.get(key, default)

        # Mock session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"timestamp": "2024-01-01", "interest": 50},
                {"timestamp": "2024-01-02", "interest": 75},
                {"timestamp": "2024-01-03", "interest": 100},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        fetcher = SearchTrendsFetcher()
        fetcher.session = mock_session

        result = fetcher.fetch_search_interest(query="test", days_back=3, use_cache=False)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert "search_interest_score" in result.columns
        assert len(result) > 0
        # Check normalization
        assert result["search_interest_score"].min() >= 0.0
        assert result["search_interest_score"].max() <= 1.0

    def test_error_handling(self):
        """Test that fetcher handles errors gracefully."""
        fetcher = SearchTrendsFetcher()
        # Should not raise exception on instantiation
        assert fetcher is not None

    @patch("os.getenv")
    @patch("requests_cache.CachedSession")
    def test_fetch_search_interest_api_error(self, mock_session_class, mock_getenv):
        """Test that fetcher handles API errors gracefully."""
        mock_getenv.side_effect = lambda key, default: {
            "SEARCH_TRENDS_API_ENDPOINT": "https://api.example.com/search",
            "SEARCH_TRENDS_API_KEY": "test-key",
        }.get(key, default)

        mock_session = Mock()
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        fetcher = SearchTrendsFetcher()
        fetcher.session = mock_session

        result = fetcher.fetch_search_interest(query="test", days_back=3, use_cache=False)

        # Should return empty DataFrame with correct structure
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert "search_interest_score" in result.columns

