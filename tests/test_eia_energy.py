# SPDX-License-Identifier: PROPRIETARY
"""Tests for EIAEnergyFetcher connector."""
import os
from unittest.mock import Mock, patch

import pandas as pd

from app.services.ingestion.eia_energy import EIAEnergyFetcher


class TestEIAEnergyFetcher:
    """Test suite for EIAEnergyFetcher connector."""

    def test_fetcher_instantiation(self):
        """Test that EIAEnergyFetcher can be instantiated."""
        fetcher = EIAEnergyFetcher()
        assert fetcher is not None
        assert isinstance(fetcher, EIAEnergyFetcher)

    def test_fetch_series_ci_offline_mode(self):
        """Test that fetcher returns synthetic data in CI offline mode."""
        with patch.dict(os.environ, {"HBC_CI_OFFLINE_DATA": "1"}):
            fetcher = EIAEnergyFetcher()
            df, status = fetcher.fetch_series("PET.RWTC.D", days_back=30)

            assert df is not None
            assert isinstance(df, pd.DataFrame)
            assert "timestamp" in df.columns
            assert "value" in df.columns
            assert len(df) > 0
            assert status.ok is True

    def test_fetch_series_no_api_key(self):
        """Test that fetcher handles missing API key gracefully."""
        fetcher = EIAEnergyFetcher(api_key=None)
        # Without API key, EIA public data should still work, but may return empty
        # This test verifies it doesn't crash
        df, status = fetcher.fetch_series("PET.RWTC.D", days_back=30, use_cache=False)

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert "timestamp" in df.columns or len(df) == 0  # May be empty without key

    @patch("requests.get")
    def test_fetch_series_mocked(self, mock_get):
        """Test EIA series fetching with mocked API."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": {
                "data": [
                    {"period": "2024-01-01", "value": 75.5},
                    {"period": "2024-01-02", "value": 76.0},
                ]
            }
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = EIAEnergyFetcher(api_key="test-key")
        df, status = fetcher.fetch_series("PET.RWTC.D", days_back=30, use_cache=False)

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert "timestamp" in df.columns
        assert "value" in df.columns
        assert len(df) == 2
        assert status.ok is True
