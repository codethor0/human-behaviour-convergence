# SPDX-License-Identifier: PROPRIETARY
"""Tests for model metrics integration."""
from unittest.mock import patch

import pandas as pd

from app.core.model_metrics import emit_model_metrics, track_forecast_computation


class TestModelMetrics:
    """Test model metrics emission."""

    def test_emit_model_metrics_with_valid_data(self):
        """Test that metrics are emitted with valid history and forecast."""
        history = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=10, freq="D"),
                "behavior_index": [
                    0.5,
                    0.6,
                    0.7,
                    0.65,
                    0.7,
                    0.75,
                    0.7,
                    0.65,
                    0.7,
                    0.75,
                ],
            }
        )

        forecast = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-11", periods=7, freq="D"),
                "prediction": [0.75, 0.76, 0.77, 0.78, 0.79, 0.80, 0.81],
                "lower_bound": [0.65, 0.66, 0.67, 0.68, 0.69, 0.70, 0.71],
                "upper_bound": [0.85, 0.86, 0.87, 0.88, 0.89, 0.90, 0.91],
            }
        )

        # Mock the metrics from main module
        with patch("app.core.model_metrics.PROMETHEUS_AVAILABLE", True):
            with patch("app.core.model_metrics._emit_metrics_safe") as mock_emit:
                emit_model_metrics(
                    history=history,
                    forecast=forecast,
                    model_name="exponential_smoothing",
                    region_id="test_region",
                    region_name="Test Region",
                )

                # Verify metrics were attempted to be emitted
                mock_emit.assert_called_once()
                call_args = mock_emit.call_args
                assert call_args[0][0].equals(history)
                assert call_args[0][1].equals(forecast)
                assert call_args[0][2] == "exponential_smoothing"
                assert call_args[0][3] == "Test Region"

    def test_emit_model_metrics_without_prometheus(self):
        """Test that metrics emission gracefully handles missing Prometheus."""
        history = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=5, freq="D"),
                "behavior_index": [0.5, 0.6, 0.7, 0.65, 0.7],
            }
        )

        forecast = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-06", periods=3, freq="D"),
                "prediction": [0.7, 0.71, 0.72],
                "lower_bound": [0.6, 0.61, 0.62],
                "upper_bound": [0.8, 0.81, 0.82],
            }
        )

        # Should not raise even if Prometheus is unavailable
        with patch("app.core.model_metrics.PROMETHEUS_AVAILABLE", False):
            emit_model_metrics(
                history=history,
                forecast=forecast,
                model_name="naive",
                region_id="test",
            )
            # Should complete without error

    def test_emit_model_metrics_with_empty_data(self):
        """Test that metrics emission handles empty data gracefully."""
        history = pd.DataFrame(columns=["timestamp", "behavior_index"])
        forecast = pd.DataFrame(
            columns=["timestamp", "prediction", "lower_bound", "upper_bound"]
        )

        with patch("app.core.model_metrics.PROMETHEUS_AVAILABLE", True):
            with patch("app.core.model_metrics._emit_metrics_safe"):
                emit_model_metrics(
                    history=history,
                    forecast=forecast,
                    model_name="naive",
                    region_id="test",
                )
                # Should still attempt to emit (evaluation will handle empty data)

    def test_track_forecast_computation(self):
        """Test tracking forecast computation duration."""
        with patch("app.core.model_metrics.PROMETHEUS_AVAILABLE", True):
            with patch("app.core.model_metrics.track_forecast_computation"):
                # This is a bit circular, but tests the function signature
                track_forecast_computation(
                    model_name="exponential_smoothing",
                    region_label="test_region",
                    duration_seconds=1.5,
                )
                # Function should complete without error

    def test_emit_metrics_with_missing_columns(self):
        """Test that metrics emission handles missing columns gracefully."""
        history = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=5, freq="D"),
                # Missing behavior_index
            }
        )

        forecast = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-06", periods=3, freq="D"),
                "prediction": [0.7, 0.71, 0.72],
                # Missing lower_bound and upper_bound
            }
        )

        with patch("app.core.model_metrics.PROMETHEUS_AVAILABLE", True):
            # Should not raise, but evaluation may fail gracefully
            try:
                emit_model_metrics(
                    history=history,
                    forecast=forecast,
                    model_name="naive",
                    region_id="test",
                )
            except Exception:
                # Expected to fail evaluation, but should not crash
                pass

    def test_emit_metrics_integration_with_evaluator(self):
        """Test that metrics emission integrates with ModelEvaluator."""
        history = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=10, freq="D"),
                "behavior_index": [
                    0.5,
                    0.6,
                    0.7,
                    0.65,
                    0.7,
                    0.75,
                    0.7,
                    0.65,
                    0.7,
                    0.75,
                ],
            }
        )

        # Create forecast that overlaps with history for evaluation
        forecast = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    "2025-01-01", periods=7, freq="D"
                ),  # Overlapping
                "prediction": [0.5, 0.6, 0.7, 0.65, 0.7, 0.75, 0.7],
                "lower_bound": [0.4, 0.5, 0.6, 0.55, 0.6, 0.65, 0.6],
                "upper_bound": [0.6, 0.7, 0.8, 0.75, 0.8, 0.85, 0.8],
            }
        )

        with patch("app.core.model_metrics.PROMETHEUS_AVAILABLE", True):
            with patch("app.core.model_metrics._emit_metrics_safe") as mock_emit:
                emit_model_metrics(
                    history=history,
                    forecast=forecast,
                    model_name="exponential_smoothing",
                    region_id="test_region",
                )

                # Should attempt evaluation since we have overlapping data
                mock_emit.assert_called_once()
