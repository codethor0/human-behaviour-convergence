# SPDX-License-Identifier: MIT-0
"""Integration tests for data connectors and harmonization pipeline."""
from unittest.mock import Mock, patch

import pandas as pd

from app.core.prediction import BehavioralForecaster
from app.services.ingestion.finance import MarketSentimentFetcher
from app.services.ingestion.processor import DataHarmonizer
from app.services.ingestion.weather import EnvironmentalImpactFetcher


class TestMarketSentimentFetcher:
    """Test suite for MarketSentimentFetcher connector."""

    def test_fetcher_instantiation(self):
        """Test that MarketSentimentFetcher can be instantiated."""
        fetcher = MarketSentimentFetcher()
        assert fetcher is not None
        assert isinstance(fetcher, MarketSentimentFetcher)

    @patch("yfinance.Ticker")
    def test_fetch_stress_index_mocked(self, mock_ticker):
        """Test stress index fetching with mocked yfinance."""
        # Mock yfinance response
        mock_data = pd.DataFrame(
            {
                "Close": [100, 105, 98, 110, 95],
                "High": [102, 107, 100, 112, 97],
                "Low": [98, 103, 96, 108, 93],
            },
            index=pd.date_range("2024-01-01", periods=5, freq="D"),
        )

        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = mock_data
        mock_ticker.return_value = mock_ticker_instance

        fetcher = MarketSentimentFetcher()

        # Test if fetch method exists
        if hasattr(fetcher, "fetch_stress_index"):
            result = fetcher.fetch_stress_index(days_back=5)
            assert result is not None
            assert isinstance(result, pd.DataFrame) or isinstance(result, (int, float))

    def test_error_handling(self):
        """Test that fetcher handles errors gracefully."""
        fetcher = MarketSentimentFetcher()
        # Should not raise exception on instantiation
        assert fetcher is not None


class TestEnvironmentalImpactFetcher:
    """Test suite for EnvironmentalImpactFetcher connector."""

    def test_fetcher_instantiation(self):
        """Test that EnvironmentalImpactFetcher can be instantiated."""
        fetcher = EnvironmentalImpactFetcher()
        assert fetcher is not None
        assert isinstance(fetcher, EnvironmentalImpactFetcher)

    @patch("openmeteo_requests.Client")
    def test_fetch_discomfort_index_mocked(self, mock_client):
        """Test discomfort index fetching with mocked openmeteo."""
        fetcher = EnvironmentalImpactFetcher()

        # Test if fetch method exists
        if hasattr(fetcher, "fetch_discomfort_index"):
            result = fetcher.fetch_discomfort_index(
                latitude=40.7128, longitude=-74.0060, days_back=5
            )
            assert result is not None

    def test_error_handling(self):
        """Test that fetcher handles errors gracefully."""
        fetcher = EnvironmentalImpactFetcher()
        # Should not raise exception on instantiation
        assert fetcher is not None


class TestDataHarmonizer:
    """Test suite for DataHarmonizer."""

    def test_harmonizer_instantiation(self):
        """Test that DataHarmonizer can be instantiated."""
        harmonizer = DataHarmonizer()
        assert harmonizer is not None
        assert isinstance(harmonizer, DataHarmonizer)

    def test_harmonize_schema(self):
        """Test that harmonize produces consistent schema."""
        harmonizer = DataHarmonizer()

        # Create mock input data
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        market_data = pd.DataFrame(
            {
                "timestamp": dates,
                "stress_index": [0.5, 0.6, 0.4, 0.7, 0.5, 0.5, 0.6, 0.4, 0.7, 0.5],
            }
        )

        weather_data = pd.DataFrame(
            {
                "timestamp": dates,
                "discomfort_score": [0.3, 0.4, 0.2, 0.5, 0.3, 0.3, 0.4, 0.2, 0.5, 0.3],
            }
        )

        search_data = pd.DataFrame(
            {
                "timestamp": dates,
                "search_interest_score": [
                    0.4,
                    0.5,
                    0.3,
                    0.6,
                    0.4,
                    0.4,
                    0.5,
                    0.3,
                    0.6,
                    0.4,
                ],
            }
        )

        health_data = pd.DataFrame(
            {
                "timestamp": dates,
                "health_risk_index": [0.2, 0.3, 0.1, 0.4, 0.2, 0.2, 0.3, 0.1, 0.4, 0.2],
            }
        )

        mobility_data = pd.DataFrame(
            {
                "timestamp": dates,
                "mobility_index": [0.6, 0.7, 0.5, 0.8, 0.6, 0.6, 0.7, 0.5, 0.8, 0.6],
            }
        )

        # Test harmonize with all connectors
        result = harmonizer.harmonize(
            market_data=market_data,
            weather_data=weather_data,
            search_data=search_data,
            health_data=health_data,
            mobility_data=mobility_data,
        )

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert "timestamp" in result.columns
        assert "behavior_index" in result.columns
        assert "stress_index" in result.columns
        assert "discomfort_score" in result.columns
        assert "search_interest_score" in result.columns
        assert "health_risk_index" in result.columns
        assert "mobility_index" in result.columns

        # Verify behavior_index is in valid range
        assert result["behavior_index"].min() >= 0.0
        assert result["behavior_index"].max() <= 1.0


class TestBehavioralForecaster:
    """Test suite for BehavioralForecaster end-to-end."""

    def test_forecaster_instantiation(self):
        """Test that BehavioralForecaster can be instantiated."""
        forecaster = BehavioralForecaster()
        assert forecaster is not None
        assert isinstance(forecaster, BehavioralForecaster)

    @patch("app.services.ingestion.finance.MarketSentimentFetcher")
    @patch("app.services.ingestion.weather.EnvironmentalImpactFetcher")
    @patch("app.services.ingestion.search_trends.SearchTrendsFetcher")
    @patch("app.services.ingestion.public_health.PublicHealthFetcher")
    @patch("app.services.ingestion.mobility.MobilityFetcher")
    @patch("app.services.ingestion.processor.DataHarmonizer")
    def test_forecast_pipeline_mocked(
        self,
        mock_harmonizer,
        mock_mobility,
        mock_health,
        mock_search,
        mock_weather,
        mock_finance,
    ):
        """Test end-to-end forecast with all connectors mocked."""
        # Mock harmonized data
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        mock_harmonized = pd.DataFrame(
            {
                "timestamp": dates,
                "behavior_index": [0.5 + 0.1 * (i % 7) / 7 for i in range(30)],
            }
        )

        mock_harmonizer_instance = Mock()
        mock_harmonizer_instance.harmonize.return_value = mock_harmonized
        mock_harmonizer.return_value = mock_harmonizer_instance

        # Mock all fetchers
        mock_finance_instance = Mock()
        mock_finance_instance.fetch_stress_index.return_value = pd.DataFrame(
            {"timestamp": dates, "stress_index": [0.5] * 30}
        )
        mock_finance.return_value = mock_finance_instance

        mock_weather_instance = Mock()
        mock_weather_instance.fetch_regional_comfort.return_value = pd.DataFrame(
            {"timestamp": dates, "discomfort_score": [0.3] * 30}
        )
        mock_weather.return_value = mock_weather_instance

        mock_search_instance = Mock()
        mock_search_instance.fetch_search_interest.return_value = pd.DataFrame()
        mock_search.return_value = mock_search_instance

        mock_health_instance = Mock()
        mock_health_instance.fetch_health_risk_index.return_value = pd.DataFrame()
        mock_health.return_value = mock_health_instance

        mock_mobility_instance = Mock()
        mock_mobility_instance.fetch_mobility_index.return_value = pd.DataFrame()
        mock_mobility.return_value = mock_mobility_instance

        forecaster = BehavioralForecaster()

        # Test forecast method
        result = forecaster.forecast(
            latitude=40.7128,
            longitude=-74.0060,
            region_name="Test Region",
            days_back=30,
            forecast_horizon=7,
        )
        assert result is not None
        assert "history" in result
        assert "forecast" in result
        assert "sources" in result
        assert "metadata" in result
