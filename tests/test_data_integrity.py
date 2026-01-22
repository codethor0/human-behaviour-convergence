# SPDX-License-Identifier: PROPRIETARY
"""Data integrity checks - Great-Expectations-style validation."""
import os
from typing import Any, Dict, List, Optional

import pandas as pd
import pytest

from app.core.prediction import BehavioralForecaster
from app.services.ingestion.source_registry import get_all_sources


class TestIngestionSourceIntegrity:
    """Data integrity checks for each ingestion source."""

    def test_weather_source_schema_validation(self):
        """Schema validation: Weather data must have required fields."""
        from app.services.ingestion.weather import WeatherFetcher

        fetcher = WeatherFetcher()
        data = fetcher.fetch_regional_comfort(
            latitude=40.7128, longitude=-74.0060, days_back=7
        )

        if not data.empty:
            # Required fields
            assert "timestamp" in data.columns, "Weather data must have timestamp"
            assert (
                "discomfort_score" in data.columns
            ), "Weather data must have discomfort_score"

            # Type validation
            assert pd.api.types.is_datetime64_any_dtype(
                data["timestamp"]
            ), "timestamp must be datetime"
            assert pd.api.types.is_numeric_dtype(
                data["discomfort_score"]
            ), "discomfort_score must be numeric"

            # Range validation
            assert (
                data["discomfort_score"].min() >= 0.0
            ), "discomfort_score must be >= 0"
            assert (
                data["discomfort_score"].max() <= 1.0
            ), "discomfort_score must be <= 1"

    def test_mobility_source_freshness(self):
        """Freshness validation: Mobility data should be recent."""
        from app.services.ingestion.mobility import MobilityFetcher

        fetcher = MobilityFetcher()
        data, status = fetcher._fetch_mobility_index_with_status(
            latitude=40.7128, longitude=-74.0060, days_back=7
        )

        if not data.empty and status.ok:
            # Check data is recent (within days_back window)
            latest_timestamp = pd.to_datetime(data["timestamp"]).max()
            from datetime import datetime, timedelta

            max_age = datetime.now() - timedelta(days=8)  # Allow 1 day buffer
            assert (
                latest_timestamp >= max_age
            ), f"Mobility data too old: {latest_timestamp}"

    def test_economic_source_cardinality(self):
        """Cardinality validation: Economic data should have expected row count."""
        from app.services.ingestion.economic_fred import FREDEconomicFetcher

        fetcher = FREDEconomicFetcher()
        data = fetcher.fetch_consumer_sentiment(days_back=30)

        if not data.empty:
            # Economic data is monthly, so 30 days should give ~1-2 points
            # But allow for interpolation/forward-fill
            assert (
                len(data) >= 1
            ), "Economic data should have at least 1 data point for 30 days"

    def test_all_sources_handle_errors_gracefully(self):
        """Error handling: Sources must not crash on malformed inputs."""
        from app.services.ingestion.weather import WeatherFetcher

        fetcher = WeatherFetcher()

        # Invalid coordinates should raise ValueError, not crash
        with pytest.raises(ValueError):
            fetcher.fetch_regional_comfort(
                latitude=999.0, longitude=-74.0060, days_back=7
            )

        # Valid coordinates should not raise
        try:
            data = fetcher.fetch_regional_comfort(
                latitude=40.7128, longitude=-74.0060, days_back=7
            )
            # Should return DataFrame (may be empty, but not crash)
            assert isinstance(data, pd.DataFrame)
        except Exception as e:
            pytest.fail(f"Weather fetcher crashed on valid input: {e}")


class TestForecastOutputIntegrity:
    """Data integrity checks for forecast outputs."""

    def test_forecast_output_schema(self):
        """Schema validation: Forecast output must have required fields."""
        forecaster = BehavioralForecaster()

        result = forecaster.forecast(
            latitude=40.7128,
            longitude=-74.0060,
            region_name="New York City",
            days_back=30,
            forecast_horizon=7,
        )

        # Required top-level fields
        assert "history" in result, "Forecast must have history"
        assert "forecast" in result, "Forecast must have forecast"
        assert "sources" in result, "Forecast must have sources"
        assert "metadata" in result, "Forecast must have metadata"

        # History structure
        history = result.get("history", [])
        if history:
            first = history[0] if isinstance(history, list) else None
            if isinstance(first, dict):
                assert "timestamp" in first, "History item must have timestamp"
                assert (
                    "behavior_index" in first
                ), "History item must have behavior_index"

        # Forecast structure
        forecast = result.get("forecast", [])
        if forecast:
            first = forecast[0] if isinstance(forecast, list) else None
            if isinstance(first, dict):
                assert "timestamp" in first, "Forecast item must have timestamp"
                assert "prediction" in first, "Forecast item must have prediction"

    def test_forecast_value_ranges(self):
        """Range validation: Forecast values must be in valid ranges."""
        forecaster = BehavioralForecaster()

        result = forecaster.forecast(
            latitude=40.7128,
            longitude=-74.0060,
            region_name="New York City",
            days_back=30,
            forecast_horizon=7,
        )

        history = result.get("history", [])
        for item in history:
            if isinstance(item, dict):
                bi = item.get("behavior_index")
                if bi is not None:
                    assert (
                        0.0 <= bi <= 1.0
                    ), f"behavior_index must be in [0,1], got {bi}"

        forecast = result.get("forecast", [])
        for item in forecast:
            if isinstance(item, dict):
                pred = item.get("prediction")
                if pred is not None:
                    assert (
                        0.0 <= pred <= 1.0
                    ), f"forecast prediction must be in [0,1], got {pred}"

    def test_forecast_temporal_consistency(self):
        """Temporal validation: History and forecast timestamps must be sequential."""
        forecaster = BehavioralForecaster()

        result = forecaster.forecast(
            latitude=40.7128,
            longitude=-74.0060,
            region_name="New York City",
            days_back=30,
            forecast_horizon=7,
        )

        history = result.get("history", [])
        forecast = result.get("forecast", [])

        if history and forecast:
            # Get last history timestamp and first forecast timestamp
            last_history = history[-1] if isinstance(history, list) else None
            first_forecast = forecast[0] if isinstance(forecast, list) else None

            if isinstance(last_history, dict) and isinstance(first_forecast, dict):
                hist_ts = pd.to_datetime(last_history.get("timestamp"))
                fcst_ts = pd.to_datetime(first_forecast.get("timestamp"))

                # Forecast should start after history ends (or be continuous)
                assert (
                    fcst_ts >= hist_ts
                ), f"Forecast timestamp ({fcst_ts}) must be >= last history timestamp ({hist_ts})"


class TestSourceRegistryIntegrity:
    """Data integrity checks for source registry."""

    def test_all_sources_have_required_fields(self):
        """Schema validation: All sources in registry must have required fields."""
        sources = get_all_sources()

        for source_id, source_def in sources.items():
            assert source_id, f"Source {source_id} must have id"
            assert (
                source_def.display_name
            ), f"Source {source_id} must have display_name"
            assert (
                source_def.category
            ), f"Source {source_id} must have category"
            assert isinstance(
                source_def.requires_key, bool
            ), f"Source {source_id} requires_key must be bool"
            assert isinstance(
                source_def.can_run_without_key, bool
            ), f"Source {source_id} can_run_without_key must be bool"

    def test_source_status_classification(self):
        """Error classification: Distinguish 'source down' vs 'no data'."""
        from app.services.ingestion.source_registry import get_source_statuses

        statuses = get_source_statuses()

        for source_id, status in statuses.items():
            # Status must have required fields
            assert "status" in status, f"Source {source_id} status must have 'status'"
            assert "ok" in status, f"Source {source_id} status must have 'ok'"

            # Error classification
            if not status.get("ok"):
                error_type = status.get("error_type")
                # Should distinguish between:
                # - missing_key (source needs config)
                # - network_error (source down)
                # - no_data (source working but no data available)
                # - other (unknown error)
                assert error_type in [
                    "missing_key",
                    "network_error",
                    "no_data",
                    "other",
                    None,
                ], f"Invalid error_type: {error_type}"
