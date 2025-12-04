# SPDX-License-Identifier: PROPRIETARY
"""Tests for OWID health connector."""
import pandas as pd
import pytest
import responses

from app.services.ingestion.health_owid import OWIDHealthFetcher


class TestOWIDHealthFetcher:
    """Test OWID health fetcher."""

    def test_fetch_excess_mortality_returns_dataframe(self):
        """Test fetch_excess_mortality() returns DataFrame with correct schema."""
        fetcher = OWIDHealthFetcher()
        df = fetcher.fetch_excess_mortality(country="United States", days_back=30)

        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            assert "timestamp" in df.columns
            assert "excess_mortality" in df.columns
            # Check normalization
            assert df["excess_mortality"].min() >= 0.0
            assert df["excess_mortality"].max() <= 1.0

    def test_fetch_excess_mortality_handles_empty_response(self):
        """Test that fetch_excess_mortality() handles empty API response gracefully."""
        fetcher = OWIDHealthFetcher()
        # This will likely return empty due to API call, but should not crash
        df = fetcher.fetch_excess_mortality(country="TestCountry", days_back=1)

        assert isinstance(df, pd.DataFrame)
        assert "timestamp" in df.columns or df.empty

    def test_fetch_health_stress_index_returns_dataframe(self):
        """Test fetch_health_stress_index() returns DataFrame with correct schema."""
        fetcher = OWIDHealthFetcher()
        df = fetcher.fetch_health_stress_index(country="United States", days_back=30)

        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            assert "timestamp" in df.columns
            assert "health_stress_index" in df.columns
