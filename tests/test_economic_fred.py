# SPDX-License-Identifier: PROPRIETARY
"""Tests for FRED economic indicators connector."""
from unittest.mock import Mock, patch

import pandas as pd

from app.services.ingestion.economic_fred import FRED_SERIES, FREDEconomicFetcher


class TestFREDEconomicFetcher:
    """Test suite for FREDEconomicFetcher."""

    def test_fetcher_instantiation_without_key(self):
        """Test that fetcher can be instantiated without API key."""
        fetcher = FREDEconomicFetcher()
        assert fetcher is not None
        assert fetcher.api_key is None

    def test_fetcher_instantiation_with_key(self):
        """Test that fetcher can be instantiated with API key."""
        fetcher = FREDEconomicFetcher(api_key="test_key")
        assert fetcher is not None
        assert fetcher.api_key == "test_key"

    @patch("app.services.ingestion.economic_fred.requests.get")
    def test_fetch_series_success(self, mock_get):
        """Test successful FRED series fetch."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "observations": [
                {"date": "2025-01-01", "value": "100.5"},
                {"date": "2025-01-02", "value": "101.2"},
                {"date": "2025-01-03", "value": "."},  # Missing value
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = FREDEconomicFetcher(api_key="test_key")
        df = fetcher.fetch_series("UMCSENT", days_back=30)

        assert isinstance(df, pd.DataFrame)
        assert "timestamp" in df.columns
        assert "value" in df.columns
        assert len(df) == 2  # Missing value skipped
        assert mock_get.called

    @patch("app.services.ingestion.economic_fred.requests.get")
    def test_fetch_series_no_api_key(self, mock_get):
        """Test that fetch returns empty DataFrame when API key not set."""
        fetcher = FREDEconomicFetcher(api_key=None)
        df = fetcher.fetch_series("UMCSENT", days_back=30)

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert not mock_get.called

    @patch("app.services.ingestion.economic_fred.requests.get")
    def test_fetch_series_http_error(self, mock_get):
        """Test that HTTP errors are handled gracefully."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        fetcher = FREDEconomicFetcher(api_key="test_key")
        df = fetcher.fetch_series("UMCSENT", days_back=30)

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    @patch("app.services.ingestion.economic_fred.requests.get")
    def test_fetch_consumer_sentiment(self, mock_get):
        """Test consumer sentiment fetch and normalization."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "observations": [
                {"date": "2025-01-01", "value": "50.0"},
                {"date": "2025-01-02", "value": "100.0"},
                {"date": "2025-01-03", "value": "75.0"},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = FREDEconomicFetcher(api_key="test_key")
        df = fetcher.fetch_consumer_sentiment(days_back=30)

        assert isinstance(df, pd.DataFrame)
        assert "timestamp" in df.columns
        assert "consumer_sentiment" in df.columns
        assert all(0.0 <= val <= 1.0 for val in df["consumer_sentiment"])

    @patch("app.services.ingestion.economic_fred.requests.get")
    def test_fetch_unemployment_rate(self, mock_get):
        """Test unemployment rate fetch and normalization."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "observations": [
                {"date": "2025-01-01", "value": "3.5"},
                {"date": "2025-01-02", "value": "5.0"},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = FREDEconomicFetcher(api_key="test_key")
        df = fetcher.fetch_unemployment_rate(days_back=30)

        assert isinstance(df, pd.DataFrame)
        assert "timestamp" in df.columns
        assert "unemployment_rate" in df.columns
        assert all(0.0 <= val <= 1.0 for val in df["unemployment_rate"])

    @patch("app.services.ingestion.economic_fred.requests.get")
    def test_fetch_jobless_claims(self, mock_get):
        """Test jobless claims fetch and normalization."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "observations": [
                {"date": "2025-01-01", "value": "200000"},
                {"date": "2025-01-08", "value": "300000"},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = FREDEconomicFetcher(api_key="test_key")
        df = fetcher.fetch_jobless_claims(days_back=30)

        assert isinstance(df, pd.DataFrame)
        assert "timestamp" in df.columns
        assert "jobless_claims" in df.columns
        assert all(0.0 <= val <= 1.0 for val in df["jobless_claims"])

    def test_fred_series_constants(self):
        """Test that FRED series IDs are defined."""
        assert "consumer_sentiment" in FRED_SERIES
        assert "unemployment_rate" in FRED_SERIES
        assert "jobless_claims" in FRED_SERIES
        assert FRED_SERIES["consumer_sentiment"] == "UMCSENT"
        assert FRED_SERIES["unemployment_rate"] == "UNRATE"
        assert FRED_SERIES["jobless_claims"] == "ICSA"
