# SPDX-License-Identifier: PROPRIETARY
"""Tests for model registry."""
import pandas as pd
import pytest

from app.core.model_registry import (
    ARIMAModel,
    BaseModel,
    ExponentialSmoothingModel,
    ModelRegistry,
    NaiveModel,
    SeasonalNaiveModel,
    get_registry,
)


class TestModelRegistry:
    """Test model registry functionality."""

    def test_registry_initializes_with_defaults(self):
        """Test that registry initializes with default models."""
        registry = ModelRegistry()

        # Naive and seasonal naive should always be available
        assert "naive" in registry.list()
        assert "seasonal_naive" in registry.list()

        # Exponential smoothing should be available if statsmodels is installed
        # (we can't test this deterministically, but we can check it's registered if available)

    def test_naive_model_forecast(self):
        """Test naive model produces correct forecast."""
        model = NaiveModel()

        # Create simple history
        history = pd.Series(
            [0.5, 0.6, 0.7, 0.65, 0.7],
            index=pd.date_range("2025-01-01", periods=5, freq="D"),
        )

        result = model.forecast(history, horizon=3)

        assert "prediction" in result
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert "std_error" in result
        assert "metadata" in result

        # Prediction should be last value repeated
        assert len(result["prediction"]) == 3
        assert all(result["prediction"] == history.iloc[-1])

        # Metadata should contain model name
        assert result["metadata"]["model"] == "naive"

    def test_naive_model_with_empty_history(self):
        """Test naive model handles empty history gracefully."""
        model = NaiveModel()
        history = pd.Series([], dtype=float)

        result = model.forecast(history, horizon=3)

        # Should still produce forecast with default value
        assert len(result["prediction"]) == 3
        assert result["metadata"]["model"] == "naive"

    def test_seasonal_naive_model_forecast(self):
        """Test seasonal naive model produces correct forecast."""
        model = SeasonalNaiveModel(seasonal_period=7)

        # Create history with weekly pattern
        history = pd.Series(
            [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.4],  # One week
            index=pd.date_range("2025-01-01", periods=7, freq="D"),
        )

        result = model.forecast(history, horizon=7)

        assert len(result["prediction"]) == 7
        assert result["metadata"]["model"] == "seasonal_naive"
        assert result["metadata"]["seasonal_period"] == 7

        # First forecast should match first value of last season
        assert result["prediction"].iloc[0] == history.iloc[0]

    def test_seasonal_naive_fallback_to_naive(self):
        """Test seasonal naive falls back to naive with insufficient history."""
        model = SeasonalNaiveModel(seasonal_period=7)

        # History shorter than seasonal period
        history = pd.Series(
            [0.5, 0.6, 0.7], index=pd.date_range("2025-01-01", periods=3, freq="D")
        )

        result = model.forecast(history, horizon=3)

        # Should fall back to naive (last value)
        assert len(result["prediction"]) == 3
        assert all(result["prediction"] == history.iloc[-1])

    def test_exponential_smoothing_model_if_available(self):
        """Test exponential smoothing model if statsmodels is available."""
        try:
            model = ExponentialSmoothingModel()
        except ImportError:
            pytest.skip("statsmodels not available")

        history = pd.Series(
            [0.5, 0.6, 0.7, 0.65, 0.7, 0.75, 0.7] * 5,  # 35 days
            index=pd.date_range("2025-01-01", periods=35, freq="D"),
        )

        result = model.forecast(history, horizon=7)

        assert len(result["prediction"]) == 7
        assert result["metadata"]["model"] == "exponential_smoothing"
        assert "trend" in result["metadata"]

    def test_arima_model_if_available(self):
        """Test ARIMA model if statsmodels is available."""
        try:
            model = ARIMAModel()
        except ImportError:
            pytest.skip("statsmodels ARIMA not available")

        history = pd.Series(
            [0.5, 0.6, 0.7, 0.65, 0.7, 0.75, 0.7] * 5,  # 35 days
            index=pd.date_range("2025-01-01", periods=35, freq="D"),
        )

        result = model.forecast(history, horizon=7, order=(1, 1, 1))

        assert len(result["prediction"]) == 7
        assert result["metadata"]["model"] == "arima"
        assert result["metadata"]["order"] == (1, 1, 1)

    def test_registry_get_model(self):
        """Test getting models from registry."""
        registry = ModelRegistry()

        naive = registry.get("naive")
        assert naive is not None
        assert isinstance(naive, NaiveModel)

        # Non-existent model should return None
        assert registry.get("nonexistent") is None

    def test_registry_get_default(self):
        """Test getting default model from registry."""
        registry = ModelRegistry()

        default = registry.get_default()
        assert default is not None
        assert isinstance(default, BaseModel)

    def test_global_registry_singleton(self):
        """Test that global registry is a singleton."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_registry_register_custom_model(self):
        """Test registering a custom model."""
        registry = ModelRegistry()

        # Create a simple custom model
        class CustomModel(BaseModel):
            def forecast(self, history, horizon, **kwargs):
                return {
                    "prediction": pd.Series([0.5] * horizon),
                    "lower_bound": pd.Series([0.4] * horizon),
                    "upper_bound": pd.Series([0.6] * horizon),
                    "std_error": 0.1,
                    "metadata": {"model": "custom"},
                }

        custom = CustomModel("custom")
        registry.register(custom)

        assert "custom" in registry.list()
        assert registry.get("custom") is custom

    def test_all_models_produce_valid_forecasts(self):
        """Test that all registered models produce valid forecasts."""
        registry = ModelRegistry()

        history = pd.Series(
            [0.5, 0.6, 0.7, 0.65, 0.7, 0.75, 0.7] * 5,
            index=pd.date_range("2025-01-01", periods=35, freq="D"),
        )

        for model_name in registry.list():
            model = registry.get(model_name)
            result = model.forecast(history, horizon=7)

            # Verify structure
            assert "prediction" in result
            assert "lower_bound" in result
            assert "upper_bound" in result
            assert "std_error" in result
            assert "metadata" in result

            # Verify lengths
            assert len(result["prediction"]) == 7
            assert len(result["lower_bound"]) == 7
            assert len(result["upper_bound"]) == 7

            # Verify values are in valid range [0, 1]
            assert all(result["prediction"] >= 0.0)
            assert all(result["prediction"] <= 1.0)
            assert all(result["lower_bound"] >= 0.0)
            assert all(result["lower_bound"] <= 1.0)
            assert all(result["upper_bound"] >= 0.0)
            assert all(result["upper_bound"] <= 1.0)

            # Verify intervals are valid
            assert all(result["lower_bound"] <= result["prediction"])
            assert all(result["upper_bound"] >= result["prediction"])
