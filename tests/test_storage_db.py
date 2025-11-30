# SPDX-License-Identifier: PROPRIETARY
"""Tests for ForecastDB storage."""
import os
import tempfile
from pathlib import Path

from app.storage.db import ForecastDB


class TestForecastDB:
    """Test suite for ForecastDB."""

    def test_db_initialization(self):
        """Test that ForecastDB can be initialized."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = ForecastDB(db_path=db_path)
            assert db is not None
            assert db.db_path == Path(db_path)
        finally:
            os.unlink(db_path)

    def test_db_initialization_default_path(self):
        """Test that ForecastDB uses default path when none provided."""
        db = ForecastDB()
        assert db is not None
        assert db.db_path is not None

    def test_save_forecast(self):
        """Test saving a forecast to the database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = ForecastDB(db_path=db_path)
            forecast_id = db.save_forecast(
                region_name="Test Region",
                latitude=40.7128,
                longitude=-74.0060,
                model_name="ExponentialSmoothing",
                behavior_index=0.65,
                sub_indices={
                    "economic_stress": 0.45,
                    "environmental_stress": 0.35,
                    "mobility_activity": 0.60,
                    "digital_attention": 0.50,
                    "public_health_stress": 0.40,
                },
                metadata={
                    "forecast_horizon": 7,
                    "sources": ["yfinance", "openmeteo.com"],
                },
            )

            assert forecast_id is not None
            assert isinstance(forecast_id, int)
            assert forecast_id > 0
        finally:
            os.unlink(db_path)

    def test_get_forecasts(self):
        """Test retrieving forecasts from the database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = ForecastDB(db_path=db_path)

            # Save multiple forecasts
            db.save_forecast(
                region_name="Region A",
                latitude=40.7128,
                longitude=-74.0060,
                model_name="ExponentialSmoothing",
                behavior_index=0.65,
            )
            db.save_forecast(
                region_name="Region B",
                latitude=51.5074,
                longitude=-0.1278,
                model_name="ExponentialSmoothing",
                behavior_index=0.55,
            )

            # Get all forecasts
            forecasts = db.get_forecasts(limit=10)
            assert len(forecasts) == 2
            assert forecasts[0]["region_name"] == "Region B"  # Most recent first
            assert forecasts[1]["region_name"] == "Region A"

            # Get forecasts for specific region
            region_forecasts = db.get_forecasts(region_name="Region A", limit=10)
            assert len(region_forecasts) == 1
            assert region_forecasts[0]["region_name"] == "Region A"
        finally:
            os.unlink(db_path)

    def test_get_forecasts_with_sub_indices(self):
        """Test that sub_indices are properly serialized and deserialized."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = ForecastDB(db_path=db_path)
            sub_indices = {
                "economic_stress": 0.45,
                "environmental_stress": 0.35,
                "mobility_activity": 0.60,
                "digital_attention": 0.50,
                "public_health_stress": 0.40,
            }

            db.save_forecast(
                region_name="Test Region",
                latitude=40.7128,
                longitude=-74.0060,
                model_name="ExponentialSmoothing",
                behavior_index=0.65,
                sub_indices=sub_indices,
            )

            forecasts = db.get_forecasts(limit=1)
            assert len(forecasts) == 1
            assert forecasts[0]["sub_indices"] == sub_indices
        finally:
            os.unlink(db_path)

    def test_save_metrics(self):
        """Test saving metrics for a forecast."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = ForecastDB(db_path=db_path)
            forecast_id = db.save_forecast(
                region_name="Test Region",
                latitude=40.7128,
                longitude=-74.0060,
                model_name="ExponentialSmoothing",
                behavior_index=0.65,
            )

            metrics = {
                "mae": 78.5,
                "rmse": 112.3,
                "mape": 0.95,
            }

            db.save_metrics(forecast_id, metrics)

            retrieved_metrics = db.get_metrics(forecast_id)
            assert retrieved_metrics["mae"] == 78.5
            assert retrieved_metrics["rmse"] == 112.3
            assert retrieved_metrics["mape"] == 0.95
        finally:
            os.unlink(db_path)

    def test_export_to_dataframe(self):
        """Test exporting forecasts to pandas DataFrame."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = ForecastDB(db_path=db_path)

            db.save_forecast(
                region_name="Test Region",
                latitude=40.7128,
                longitude=-74.0060,
                model_name="ExponentialSmoothing",
                behavior_index=0.65,
            )

            df = db.export_to_dataframe()
            assert len(df) == 1
            assert "region_name" in df.columns
            assert "behavior_index" in df.columns
            assert df.iloc[0]["region_name"] == "Test Region"
        finally:
            os.unlink(db_path)

    def test_empty_forecasts(self):
        """Test that get_forecasts returns empty list when no forecasts exist."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = ForecastDB(db_path=db_path)
            forecasts = db.get_forecasts()
            assert forecasts == []
        finally:
            os.unlink(db_path)

    def test_get_metrics_empty(self):
        """Test that get_metrics returns empty dict when no metrics exist."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            db = ForecastDB(db_path=db_path)
            db.save_forecast(
                region_name="Test Region",
                latitude=40.7128,
                longitude=-74.0060,
                model_name="ExponentialSmoothing",
                behavior_index=0.65,
            )

            # Get the most recent forecast ID
            forecasts = db.get_forecasts(limit=1)
            assert len(forecasts) > 0
            forecast_id = forecasts[0]["id"]

            metrics = db.get_metrics(forecast_id)
            assert metrics == {}
        finally:
            os.unlink(db_path)
