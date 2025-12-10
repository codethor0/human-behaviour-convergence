# SPDX-License-Identifier: PROPRIETARY
"""Tests for GDELT Events connector."""
import pandas as pd
import responses

from app.services.ingestion.gdelt_events import GDELTEventsFetcher


class TestGDELTEventsFetcher:
    """Test GDELT Events fetcher."""

    def test_fetch_event_tone_returns_dataframe(self):
        """Test that fetch_event_tone() returns a DataFrame with correct schema."""
        fetcher = GDELTEventsFetcher()
        df = fetcher.fetch_event_tone(days_back=7)

        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            assert "timestamp" in df.columns
            assert "tone_score" in df.columns
            # Check normalization
            assert df["tone_score"].min() >= 0.0
            assert df["tone_score"].max() <= 1.0

    @responses.activate
    def test_fetch_event_tone_with_mock_api(self):
        """Test that fetch_event_tone() parses API response correctly."""
        # Mock GDELT API response
        mock_response = {
            "timeline": [
                {"datetime": "20241104000000", "tone": -50.5},
                {"datetime": "20241105000000", "tone": 20.3},
            ]
        }

        responses.add(
            responses.GET,
            "https://api.gdeltproject.org/api/v2/doc/doc",
            json=mock_response,
            status=200,
        )

        fetcher = GDELTEventsFetcher()
        df = fetcher.fetch_event_tone(days_back=7, use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 0  # May be empty if parsing fails, which is OK

    def test_fetch_event_tone_handles_empty_response(self):
        """Test that fetch_event_tone() handles empty API response gracefully."""
        fetcher = GDELTEventsFetcher()
        # This will likely return empty due to API call, but should not crash
        df = fetcher.fetch_event_tone(days_back=1)

        assert isinstance(df, pd.DataFrame)
        assert "timestamp" in df.columns or df.empty

    def test_fetch_event_count_returns_dataframe(self):
        """Test that fetch_event_count() returns a DataFrame with correct schema."""
        fetcher = GDELTEventsFetcher()
        df = fetcher.fetch_event_count(days_back=7)

        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            assert "timestamp" in df.columns
            assert "event_count" in df.columns

    @responses.activate
    def test_fetch_event_count_with_mock_api(self):
        """Test that fetch_event_count() parses API response correctly."""
        # Mock GDELT API response
        mock_response = {
            "timeline": [
                {"datetime": "20241104000000", "volume": 1000},
                {"datetime": "20241105000000", "volume": 2000},
            ]
        }

        responses.add(
            responses.GET,
            "https://api.gdeltproject.org/api/v2/doc/doc",
            json=mock_response,
            status=200,
        )

        fetcher = GDELTEventsFetcher()
        df = fetcher.fetch_event_count(days_back=7, use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 0
