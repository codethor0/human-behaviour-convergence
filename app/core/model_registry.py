# SPDX-License-Identifier: PROPRIETARY
"""Model registry for forecasting models."""
from abc import ABC, abstractmethod
from typing import Dict, Optional

import pandas as pd
import structlog

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    ExponentialSmoothing = None

try:
    from statsmodels.tsa.arima.model import ARIMA

    HAS_ARIMA = True
except ImportError:
    HAS_ARIMA = False
    ARIMA = None

logger = structlog.get_logger("core.model_registry")


class BaseModel(ABC):
    """Base interface for all forecasting models."""

    def __init__(self, name: str):
        """
        Initialize model.

        Args:
            name: Model identifier (e.g., "naive", "exponential_smoothing")
        """
        self.name = name

    @abstractmethod
    def forecast(self, history: pd.Series, horizon: int, **kwargs) -> Dict[str, any]:
        """
        Generate forecast from historical data.

        Args:
            history: Historical time series (indexed by timestamp)
            horizon: Number of steps to forecast ahead
            **kwargs: Model-specific parameters

        Returns:
            Dictionary with:
            - prediction: pd.Series of forecast values
            - lower_bound: pd.Series of lower interval bounds (optional)
            - upper_bound: pd.Series of upper interval bounds (optional)
            - std_error: Standard error estimate (optional)
            - metadata: Dict with model-specific metadata
        """
        pass

    def get_name(self) -> str:
        """Get model identifier."""
        return self.name


class NaiveModel(BaseModel):
    """Naive model: returns last observed value for all forecast steps."""

    def __init__(self):
        super().__init__("naive")

    def forecast(self, history: pd.Series, horizon: int, **kwargs) -> Dict[str, any]:
        """Generate naive forecast (last value repeated)."""
        if len(history) == 0:
            logger.warning("Empty history for naive model, using default")
            last_val = 0.5
        else:
            last_val = float(history.iloc[-1])
            if pd.isna(last_val):
                last_val = 0.5

        # Generate forecast dates
        if isinstance(history.index, pd.DatetimeIndex) and len(history.index) > 0:
            last_date = history.index.max()
            forecast_dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D"
            )
        else:
            forecast_dates = pd.date_range(
                start=pd.Timestamp.now(), periods=horizon, freq="D"
            )

        prediction = pd.Series([last_val] * horizon, index=forecast_dates)

        # Simple confidence intervals (10% of value)
        std_error = abs(last_val * 0.1) if last_val != 0 else 0.1
        lower_bound = pd.Series(
            [max(0.0, last_val - 1.96 * std_error)] * horizon, index=forecast_dates
        )
        upper_bound = pd.Series(
            [min(1.0, last_val + 1.96 * std_error)] * horizon, index=forecast_dates
        )

        return {
            "prediction": prediction,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "std_error": std_error,
            "metadata": {
                "model": self.name,
                "last_value": last_val,
                "horizon": horizon,
            },
        }


class SeasonalNaiveModel(BaseModel):
    """Seasonal naive model: returns value from same period in previous season."""

    def __init__(self, seasonal_period: int = 7):
        """
        Initialize seasonal naive model.

        Args:
            seasonal_period: Period of seasonality (default: 7 for weekly)
        """
        super().__init__("seasonal_naive")
        self.seasonal_period = seasonal_period

    def forecast(self, history: pd.Series, horizon: int, **kwargs) -> Dict[str, any]:
        """Generate seasonal naive forecast."""
        if len(history) < self.seasonal_period:
            logger.warning(
                "Insufficient history for seasonal naive, falling back to naive",
                history_len=len(history),
                seasonal_period=self.seasonal_period,
            )
            # Fallback to naive model
            naive = NaiveModel()
            return naive.forecast(history, horizon, **kwargs)

        # Extract seasonal pattern from last season
        seasonal_values = history.iloc[-self.seasonal_period :].values

        # Generate forecast dates
        if isinstance(history.index, pd.DatetimeIndex) and len(history.index) > 0:
            last_date = history.index.max()
            forecast_dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D"
            )
        else:
            forecast_dates = pd.date_range(
                start=pd.Timestamp.now(), periods=horizon, freq="D"
            )

        # Repeat seasonal pattern
        prediction_values = []
        for i in range(horizon):
            idx = i % self.seasonal_period
            prediction_values.append(seasonal_values[idx])

        prediction = pd.Series(prediction_values, index=forecast_dates)

        # Confidence intervals based on historical variance
        if len(history) > 1:
            std_error = float(history.std())
            if pd.isna(std_error) or std_error <= 0:
                std_error = 0.1
        else:
            std_error = 0.1

        std_error = max(0.01, min(0.5, std_error))

        lower_bound = pd.Series(
            [max(0.0, v - 1.96 * std_error) for v in prediction_values],
            index=forecast_dates,
        )
        upper_bound = pd.Series(
            [min(1.0, v + 1.96 * std_error) for v in prediction_values],
            index=forecast_dates,
        )

        return {
            "prediction": prediction,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "std_error": std_error,
            "metadata": {
                "model": self.name,
                "seasonal_period": self.seasonal_period,
                "horizon": horizon,
            },
        }


class ExponentialSmoothingModel(BaseModel):
    """Exponential smoothing (Holt-Winters) model."""

    def __init__(self):
        if not HAS_STATSMODELS:
            raise ImportError("statsmodels is required for ExponentialSmoothingModel")
        super().__init__("exponential_smoothing")

    def forecast(
        self,
        history: pd.Series,
        horizon: int,
        trend: str = "add",
        seasonal: Optional[str] = None,
        seasonal_periods: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, any]:
        """
        Generate exponential smoothing forecast.

        Args:
            history: Historical time series
            horizon: Forecast horizon
            trend: Trend component ("add" or "mul")
            seasonal: Seasonal component ("add", "mul", or None)
            seasonal_periods: Number of periods in a season
        """
        if len(history) == 0:
            logger.warning("Empty history for exponential smoothing, using fallback")
            naive = NaiveModel()
            return naive.forecast(history, horizon, **kwargs)

        # Auto-detect seasonality if not specified
        if seasonal is None:
            seasonal = "add" if len(history) >= 30 else None

        if seasonal_periods is None and seasonal is not None:
            seasonal_periods = min(7, len(history) // 4)  # Weekly seasonality

        try:
            # Build model
            if seasonal is not None and seasonal_periods is not None:
                model = ExponentialSmoothing(
                    history,
                    trend=trend,
                    seasonal=seasonal,
                    seasonal_periods=seasonal_periods,
                ).fit(optimized=True)
            else:
                model = ExponentialSmoothing(history, trend=trend).fit(optimized=True)

            # Generate forecast
            forecast_result = model.forecast(steps=horizon)

            # Generate forecast dates
            if isinstance(history.index, pd.DatetimeIndex) and len(history.index) > 0:
                last_date = history.index.max()
                forecast_dates = pd.date_range(
                    start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D"
                )
            else:
                forecast_dates = pd.date_range(
                    start=pd.Timestamp.now(), periods=horizon, freq="D"
                )

            # Ensure forecast_result is a Series with correct index
            if not isinstance(forecast_result, pd.Series):
                forecast_result = pd.Series(
                    forecast_result, index=forecast_dates[: len(forecast_result)]
                )
            else:
                forecast_result.index = forecast_dates[: len(forecast_result)]

            # Calculate confidence intervals from residuals
            try:
                fitted_values = model.fittedvalues
                residuals = history - fitted_values
                std_error = float(residuals.std())
                if pd.isna(std_error) or std_error <= 0:
                    std_error = 0.1
                std_error = max(0.01, min(0.5, std_error))
            except Exception:
                std_error = 0.1

            prediction = forecast_result.clip(0.0, 1.0)
            lower_bound = (prediction - 1.96 * std_error).clip(0.0, 1.0)
            upper_bound = (prediction + 1.96 * std_error).clip(0.0, 1.0)

            return {
                "prediction": prediction,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "std_error": std_error,
                "metadata": {
                    "model": self.name,
                    "trend": trend,
                    "seasonal": seasonal,
                    "seasonal_periods": seasonal_periods,
                    "horizon": horizon,
                },
            }
        except Exception as e:
            logger.warning(
                "Exponential smoothing forecast failed, using fallback", error=str(e)
            )
            # Fallback to naive
            naive = NaiveModel()
            return naive.forecast(history, horizon, **kwargs)


class ARIMAModel(BaseModel):
    """ARIMA model (if statsmodels available)."""

    def __init__(self):
        if not HAS_ARIMA:
            raise ImportError("statsmodels is required for ARIMAModel")
        super().__init__("arima")

    def forecast(
        self, history: pd.Series, horizon: int, order: tuple = (1, 1, 1), **kwargs
    ) -> Dict[str, any]:
        """
        Generate ARIMA forecast.

        Args:
            history: Historical time series
            horizon: Forecast horizon
            order: ARIMA order (p, d, q)
        """
        if len(history) < max(order) + 1:
            logger.warning("Insufficient history for ARIMA, using fallback")
            naive = NaiveModel()
            return naive.forecast(history, horizon, **kwargs)

        try:
            # Fit ARIMA model
            model = ARIMA(history, order=order).fit()

            # Generate forecast
            forecast_result = model.forecast(steps=horizon)
            conf_int = model.get_forecast(steps=horizon).conf_int()

            # Generate forecast dates
            if isinstance(history.index, pd.DatetimeIndex) and len(history.index) > 0:
                last_date = history.index.max()
                forecast_dates = pd.date_range(
                    start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D"
                )
            else:
                forecast_dates = pd.date_range(
                    start=pd.Timestamp.now(), periods=horizon, freq="D"
                )

            prediction = pd.Series(forecast_result, index=forecast_dates).clip(0.0, 1.0)

            # Use confidence intervals from model if available
            if conf_int is not None and len(conf_int) == horizon:
                lower_bound = pd.Series(
                    conf_int.iloc[:, 0].values, index=forecast_dates
                ).clip(0.0, 1.0)
                upper_bound = pd.Series(
                    conf_int.iloc[:, 1].values, index=forecast_dates
                ).clip(0.0, 1.0)
                std_error = float((upper_bound - lower_bound).mean() / (2 * 1.96))
            else:
                # Fallback: estimate from residuals
                residuals = model.resid
                std_error = float(residuals.std()) if len(residuals) > 0 else 0.1
                std_error = max(0.01, min(0.5, std_error))
                lower_bound = (prediction - 1.96 * std_error).clip(0.0, 1.0)
                upper_bound = (prediction + 1.96 * std_error).clip(0.0, 1.0)

            return {
                "prediction": prediction,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "std_error": std_error,
                "metadata": {
                    "model": self.name,
                    "order": order,
                    "horizon": horizon,
                },
            }
        except Exception as e:
            logger.warning("ARIMA forecast failed, using fallback", error=str(e))
            # Fallback to naive
            naive = NaiveModel()
            return naive.forecast(history, horizon, **kwargs)


class ModelRegistry:
    """Registry for forecasting models."""

    def __init__(self):
        self._models: Dict[str, BaseModel] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register default models."""
        # Always available
        self.register(NaiveModel())
        self.register(SeasonalNaiveModel())

        # Conditional models
        if HAS_STATSMODELS:
            try:
                self.register(ExponentialSmoothingModel())
            except Exception as e:
                logger.warning(
                    "Failed to register ExponentialSmoothingModel", error=str(e)
                )

        if HAS_ARIMA:
            try:
                self.register(ARIMAModel())
            except Exception as e:
                logger.warning("Failed to register ARIMAModel", error=str(e))

    def register(self, model: BaseModel):
        """Register a model."""
        self._models[model.get_name()] = model
        logger.info("Registered model", model_name=model.get_name())

    def get(self, name: str) -> Optional[BaseModel]:
        """Get a model by name."""
        return self._models.get(name)

    def list(self) -> list[str]:
        """List all registered model names."""
        return list(self._models.keys())

    def get_default(self) -> BaseModel:
        """Get default model (exponential smoothing if available, else naive)."""
        if "exponential_smoothing" in self._models:
            return self._models["exponential_smoothing"]
        return self._models["naive"]


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """Get global model registry instance."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
