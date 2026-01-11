"""Tests for GDELT Events connector."""

from unittest.mock import Mock, patch
import pandas as pd
import requests
from app.services.ingestion.gdelt_events import (
    GDELTEventsFetcher,
    SourceStatus,
)


class TestGDELTEventsFetcher:
    """Test GDELT Events fetcher."""

    def test_fetcher_initialization(self):
        """Test fetcher can be initialized."""
        fetcher = GDELTEventsFetcher()
        assert fetcher is not None
        assert fetcher.cache_duration_minutes == 60

    def test_fetch_event_tone_success(self, monkeypatch):
        """Test successful fetch of event tone data."""
        # Mock GDELT API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = (
            b'{"timeline": [{"datetime": "20240101000000", "tone": -10.5}]}'
        )
        mock_response.text = (
            '{"timeline": [{"datetime": "20240101000000", "tone": -10.5}]}'
        )
        mock_response.json.return_value = {
            "timeline": [{"datetime": "20240101000000", "tone": -10.5}]
        }

        def mock_get(*args, **kwargs):
            return mock_response

        with patch("requests.get", side_effect=mock_get):
            fetcher = GDELTEventsFetcher()
            df, status = fetcher.fetch_event_tone(days_back=7, use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "timestamp" in df.columns
        assert "tone_score" in df.columns
        assert status.ok is True
        assert status.http_status == 200
        assert status.rows > 0
        assert status.error_type is None

    def test_fetch_event_tone_empty_response(self, monkeypatch):
        """Test handling of empty response body."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b""
        mock_response.text = ""

        def mock_get(*args, **kwargs):
            return mock_response

        with patch("requests.get", side_effect=mock_get):
            fetcher = GDELTEventsFetcher()
            df, status = fetcher.fetch_event_tone(days_back=7, use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert status.ok is False
        assert status.error_type == "empty"
        assert status.http_status == 200
        assert status.rows == 0

    def test_fetch_event_tone_non_json_response(self, monkeypatch):
        """Test handling of HTML/non-JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.content = b"<html><body>Error</body></html>"
        mock_response.text = "<html><body>Error</body></html>"

        def mock_get(*args, **kwargs):
            return mock_response

        with patch("requests.get", side_effect=mock_get):
            fetcher = GDELTEventsFetcher()
            df, status = fetcher.fetch_event_tone(days_back=7, use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert status.ok is False
        assert status.error_type == "non_json"
        assert status.http_status == 200
        assert status.rows == 0
        assert "Error" in status.error_detail or "html" in status.error_detail.lower()

    def test_fetch_event_tone_http_error(self, monkeypatch):
        """Test handling of HTTP 500 error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"error": "Internal Server Error"}'
        mock_response.text = '{"error": "Internal Server Error"}'

        def mock_get(*args, **kwargs):
            return mock_response

        with patch("requests.get", side_effect=mock_get):
            fetcher = GDELTEventsFetcher()
            df, status = fetcher.fetch_event_tone(days_back=7, use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert status.ok is False
        assert status.error_type == "http_error"
        assert status.http_status == 500
        assert status.rows == 0

    def test_fetch_event_tone_timeout(self, monkeypatch):
        """Test handling of timeout error."""

        def mock_get(*args, **kwargs):
            raise requests.exceptions.Timeout("Request timed out")

        with patch("requests.get", side_effect=mock_get):
            fetcher = GDELTEventsFetcher()
            df, status = fetcher.fetch_event_tone(days_back=7, use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert status.ok is False
        assert status.error_type == "timeout"
        assert status.http_status is None
        assert status.rows == 0

    def test_fetch_event_tone_invalid_json(self, monkeypatch):
        """Test handling of invalid JSON (decode error)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"timeline": [{"datetime": invalid}'
        mock_response.text = '{"timeline": [{"datetime": invalid}'

        def mock_get(*args, **kwargs):
            return mock_response

        with patch("requests.get", side_effect=mock_get):
            fetcher = GDELTEventsFetcher()
            df, status = fetcher.fetch_event_tone(days_back=7, use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert status.ok is False
        assert status.error_type in ["decode_error", "non_json"]
        assert status.http_status == 200
        assert status.rows == 0

    def test_fetch_event_tone_empty_timeline(self, monkeypatch):
        """Test handling of response with empty timeline."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"timeline": []}'
        mock_response.text = '{"timeline": []}'
        mock_response.json.return_value = {"timeline": []}

        def mock_get(*args, **kwargs):
            return mock_response

        with patch("requests.get", side_effect=mock_get):
            fetcher = GDELTEventsFetcher()
            df, status = fetcher.fetch_event_tone(days_back=7, use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert status.ok is False
        assert status.error_type == "empty"
        assert status.http_status == 200
        assert status.rows == 0

    def test_source_status_to_dict(self):
        """Test SourceStatus serialization to dictionary."""
        status = SourceStatus(
            provider="GDELT",
            ok=True,
            http_status=200,
            fetched_at="2024-01-01T00:00:00",
            rows=10,
            query_window_days=7,
        )
        status_dict = status.to_dict()
        assert status_dict["provider"] == "GDELT"
        assert status_dict["ok"] is True
        assert status_dict["http_status"] == 200
        assert status_dict["rows"] == 10
        assert status_dict["query_window_days"] == 7
        assert status_dict["error_type"] is None

    def test_source_status_error_to_dict(self):
        """Test SourceStatus with error serialization."""
        status = SourceStatus(
            provider="GDELT",
            ok=False,
            http_status=500,
            error_type="http_error",
            error_detail="Internal Server Error",
            fetched_at="2024-01-01T00:00:00",
            rows=0,
            query_window_days=7,
        )
        status_dict = status.to_dict()
        assert status_dict["ok"] is False
        assert status_dict["error_type"] == "http_error"
        assert status_dict["error_detail"] == "Internal Server Error"

    def test_fetch_event_tone_retry_behavior(self, monkeypatch):
        """Test that retries are attempted on failure."""
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # First two calls fail with timeout
                raise requests.exceptions.Timeout("Timeout")
            # Third call succeeds
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.content = (
                b'{"timeline": [{"datetime": "20240101000000", "tone": -10.5}]}'
            )
            mock_response.text = (
                '{"timeline": [{"datetime": "20240101000000", "tone": -10.5}]}'
            )
            mock_response.json.return_value = {
                "timeline": [{"datetime": "20240101000000", "tone": -10.5}]
            }
            return mock_response

        with patch("requests.get", side_effect=mock_get), patch("time.sleep"):
            fetcher = GDELTEventsFetcher()
            df, status = fetcher.fetch_event_tone(days_back=7, use_cache=False)

        assert call_count == 3  # Should retry twice, then succeed
        assert status.ok is True
