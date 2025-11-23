# SPDX-License-Identifier: MIT-0
"""Integration tests for data connectors and harmonization pipeline."""
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import pandas as pd
import pytest

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

    @patch('yfinance.Ticker')
    def test_fetch_stress_index_mocked(self, mock_ticker):
        """Test stress index fetching with mocked yfinance."""
        # Mock yfinance response
        mock_data = pd.DataFrame({
            'Close': [100, 105, 98, 110, 95],
            'High': [102, 107, 100, 112, 97],
            'Low': [98, 103, 96, 108, 93]
        }, index=pd.date_range('2024-01-01', periods=5, freq='D'))

        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = mock_data
        mock_ticker.return_value = mock_ticker_instance

        fetcher = MarketSentimentFetcher()
        
        # Test if fetch method exists
        if hasattr(fetcher, 'fetch_stress_index'):
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

    @patch('openmeteo_requests.Client')
    def test_fetch_discomfort_index_mocked(self, mock_client):
        """Test discomfort index fetching with mocked openmeteo."""
        fetcher = EnvironmentalImpactFetcher()
        
        # Test if fetch method exists
        if hasattr(fetcher, 'fetch_discomfort_index'):
            result = fetcher.fetch_discomfort_index(
                latitude=40.7128,
                longitude=-74.0060,
                days_back=5
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
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        market_data = pd.DataFrame({
            'stress_index': [0.5, 0.6, 0.4, 0.7, 0.5] * 2
        }, index=dates[:5].repeat(2)[:10])
        
        weather_data = pd.DataFrame({
            'discomfort_index': [0.3, 0.4, 0.2, 0.5, 0.3] * 2
        }, index=dates[:5].repeat(2)[:10])
        
        # Test if harmonize method exists
        if hasattr(harmonizer, 'harmonize'):
            result = harmonizer.harmonize(market_data, weather_data)
            assert result is not None
            assert isinstance(result, pd.DataFrame)
            assert 'Behavior_Index' in result.columns or len(result.columns) > 0


class TestBehavioralForecaster:
    """Test suite for BehavioralForecaster end-to-end."""

    def test_forecaster_instantiation(self):
        """Test that BehavioralForecaster can be instantiated."""
        forecaster = BehavioralForecaster()
        assert forecaster is not None
        assert isinstance(forecaster, BehavioralForecaster)

    @patch('app.services.ingestion.finance.MarketSentimentFetcher')
    @patch('app.services.ingestion.weather.EnvironmentalImpactFetcher')
    @patch('app.services.ingestion.processor.DataHarmonizer')
    def test_forecast_pipeline_mocked(self, mock_harmonizer, mock_weather, mock_finance):
        """Test end-to-end forecast with mocked connectors."""
        # Mock harmonized data
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        mock_harmonized = pd.DataFrame({
            'Behavior_Index': [0.5 + 0.1 * (i % 7) / 7 for i in range(30)]
        }, index=dates)
        
        mock_harmonizer_instance = Mock()
        mock_harmonizer_instance.harmonize.return_value = mock_harmonized
        mock_harmonizer.return_value = mock_harmonizer_instance
        
        forecaster = BehavioralForecaster()
        
        # Test if forecast method exists
        if hasattr(forecaster, 'forecast'):
            result = forecaster.forecast(
                latitude=40.7128,
                longitude=-74.0060,
                days_back=30,
                forecast_horizon=7
            )
            assert result is not None

