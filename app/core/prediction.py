# SPDX-License-Identifier: MIT-0
"""Behavioral forecasting engine using real-world public data."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import structlog

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    ExponentialSmoothing = None

from app.services.ingestion import (
    DataHarmonizer,
    EnvironmentalImpactFetcher,
    MarketSentimentFetcher,
    MobilityFetcher,
    PublicHealthFetcher,
    SearchTrendsFetcher,
)

logger = structlog.get_logger("core.prediction")


class BehavioralForecaster:
    """
    Multi-vector behavioral forecasting engine.

    Uses economic (VIX/SPY) and environmental (weather) data to forecast
    human behavioral convergence using exponential smoothing (Holt-Winters) model.
    """

    def __init__(
        self,
        market_fetcher: Optional[MarketSentimentFetcher] = None,
        weather_fetcher: Optional[EnvironmentalImpactFetcher] = None,
        search_fetcher: Optional[SearchTrendsFetcher] = None,
        health_fetcher: Optional[PublicHealthFetcher] = None,
        mobility_fetcher: Optional[MobilityFetcher] = None,
        harmonizer: Optional[DataHarmonizer] = None,
    ):
        """
        Initialize the behavioral forecaster.

        Args:
            market_fetcher: Market sentiment fetcher instance (creates new if None)
            weather_fetcher: Environmental impact fetcher instance (creates new if None)
            search_fetcher: Search trends fetcher instance (creates new if None)
            health_fetcher: Public health fetcher instance (creates new if None)
            mobility_fetcher: Mobility fetcher instance (creates new if None)
            harmonizer: Data harmonizer instance (creates new if None)
        """
        self.market_fetcher = market_fetcher or MarketSentimentFetcher()
        self.weather_fetcher = weather_fetcher or EnvironmentalImpactFetcher()
        self.search_fetcher = search_fetcher or SearchTrendsFetcher()
        self.health_fetcher = health_fetcher or PublicHealthFetcher()
        self.mobility_fetcher = mobility_fetcher or MobilityFetcher()
        self.harmonizer = harmonizer or DataHarmonizer()
        self._cache: Dict[str, Tuple[pd.DataFrame, pd.DataFrame, Dict]] = {}

    def forecast(
        self,
        latitude: float,
        longitude: float,
        region_name: str,
        days_back: int = 30,
        forecast_horizon: int = 7,
    ) -> Dict:
        """
        Generate behavioral forecast for a given region.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
            region_name: Human-readable region name
            days_back: Number of historical days to use (default: 30)
            forecast_horizon: Number of days to forecast ahead (default: 7)

        Returns:
            Dictionary containing:
            - history: DataFrame with past behavior_index data
            - forecast: DataFrame with future predictions and confidence intervals
            - sources: List of public APIs used
            - metadata: Additional information about the forecast
        """
        cache_key = f"{latitude:.4f},{longitude:.4f},{region_name},{days_back},{forecast_horizon}"

        # Check cache
        if cache_key in self._cache:
            logger.info("Using cached forecast", cache_key=cache_key)
            history, forecast, metadata = self._cache[cache_key]
            return {
                "history": history.to_dict("records") if not history.empty else [],
                "forecast": forecast.to_dict("records") if not forecast.empty else [],
                "sources": metadata.get("sources", []),
                "metadata": metadata,
            }

        sources = []

        try:
            logger.info(
                "Generating behavioral forecast",
                latitude=latitude,
                longitude=longitude,
                region_name=region_name,
                days_back=days_back,
                forecast_horizon=forecast_horizon,
            )

            # Fetch market sentiment data
            market_data = self.market_fetcher.fetch_stress_index(days_back=days_back)
            if not market_data.empty:
                sources.append("yfinance (VIX/SPY)")

            # Fetch weather data
            weather_data = self.weather_fetcher.fetch_regional_comfort(
                latitude=latitude, longitude=longitude, days_back=days_back
            )
            if not weather_data.empty:
                sources.append("openmeteo.com (Weather)")

            # Harmonize data
            if market_data.empty and weather_data.empty:
                logger.warning("No data available for forecast")
                return {
                    "history": [],
                    "forecast": [],
                    "sources": [],
                    "metadata": {
                        "region_name": region_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "error": "No data available",
                    },
                }

            harmonized = self.harmonizer.harmonize(
                market_data=market_data,
                weather_data=weather_data,
                search_data=search_data,
                health_data=health_data,
                mobility_data=mobility_data,
            )

            if harmonized.empty or "behavior_index" not in harmonized.columns:
                logger.warning("Harmonized data is empty or missing behavior_index")
                return {
                    "history": [],
                    "forecast": [],
                    "sources": sources,
                    "metadata": {
                        "region_name": region_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "error": "Harmonized data is empty",
                    },
                }

            # Prepare history data
            history = harmonized[["timestamp", "behavior_index"]].copy()
            history["timestamp"] = pd.to_datetime(history["timestamp"])
            history = history.sort_values("timestamp").reset_index(drop=True)

            # Ensure we have enough data points for forecasting (minimum 7 days)
            if len(history) < 7:
                logger.warning(
                    "Insufficient historical data for forecasting",
                    data_points=len(history),
                )
                return {
                    "history": history.to_dict("records"),
                    "forecast": [],
                    "sources": sources,
                    "metadata": {
                        "region_name": region_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "warning": "Insufficient data for forecasting",
                        "data_points": len(history),
                    },
                }

            # Extract behavior_index time series
            behavior_ts = history.set_index("timestamp")["behavior_index"]

            # Fit Exponential Smoothing (Holt-Winters) model
            try:
                if not HAS_STATSMODELS:
                    logger.warning(
                        "statsmodels not available, using simple moving average forecast"
                    )
                    # Fallback to simple moving average if statsmodels not available
                    window_size = min(7, len(behavior_ts) // 2)
                    if window_size < 2:
                        window_size = 2
                    ma = behavior_ts.rolling(window=window_size, center=False).mean()
                    last_value = ma.iloc[-1] if not ma.empty else behavior_ts.iloc[-1]
                    trend = (
                        (behavior_ts.iloc[-1] - behavior_ts.iloc[0]) / len(behavior_ts)
                        if len(behavior_ts) > 1
                        else 0
                    )
                    forecast_result = pd.Series(
                        [
                            last_value + trend * i
                            for i in range(1, forecast_horizon + 1)
                        ],
                        index=pd.date_range(
                            start=behavior_ts.index[-1] + pd.Timedelta(days=1),
                            periods=forecast_horizon,
                            freq="D",
                        ),
                    )
                    std_error = behavior_ts.std() if len(behavior_ts) > 1 else 0.1
                else:
                    # Use additive seasonality with yearly period (365 days)
                    # For shorter series, use trend-only model
                    if len(behavior_ts) >= 30:
                        model = ExponentialSmoothing(
                            behavior_ts,
                            trend="add",
                            seasonal="add",
                            seasonal_periods=min(
                                7, len(behavior_ts) // 4
                            ),  # Weekly seasonality
                        ).fit(optimized=True)
                    else:
                        # Trend-only for shorter series
                        model = ExponentialSmoothing(behavior_ts, trend="add").fit(
                            optimized=True
                        )

                    # Generate forecast
                    forecast_result = model.forecast(steps=forecast_horizon)

                    # Calculate confidence intervals (approximate using model's fitted values variance)
                    fitted_values = model.fittedvalues
                    residuals = behavior_ts - fitted_values
                    std_error = residuals.std()

                # Generate forecast dates
                if (
                    isinstance(forecast_result, pd.Series)
                    and not forecast_result.index.empty
                ):
                    forecast_dates = forecast_result.index
                else:
                    last_date = behavior_ts.index.max()
                    forecast_dates = pd.date_range(
                        start=last_date + timedelta(days=1),
                        periods=forecast_horizon,
                        freq="D",
                    )

                # Create forecast DataFrame with confidence intervals
                forecast_df = pd.DataFrame(
                    {
                        "timestamp": forecast_dates,
                        "prediction": forecast_result.values,
                        "lower_bound": (forecast_result - 1.96 * std_error).values,
                        "upper_bound": (forecast_result + 1.96 * std_error).values,
                    }
                )

                # Clip values to valid range [0.0, 1.0]
                forecast_df["prediction"] = forecast_df["prediction"].clip(0.0, 1.0)
                forecast_df["lower_bound"] = forecast_df["lower_bound"].clip(0.0, 1.0)
                forecast_df["upper_bound"] = forecast_df["upper_bound"].clip(0.0, 1.0)

                # Reset index
                forecast_df = forecast_df.reset_index(drop=True)

                # Prepare metadata
                model_type = (
                    "Moving Average + Trend"
                    if not HAS_STATSMODELS
                    else "ExponentialSmoothing (Holt-Winters)"
                )
                metadata = {
                    "region_name": region_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "forecast_date": datetime.now().isoformat(),
                    "forecast_horizon": forecast_horizon,
                    "historical_data_points": len(history),
                    "model_type": model_type,
                    "confidence_level": 0.95,
                    "sources": sources,
                }

                # Cache result
                self._cache[cache_key] = (history, forecast_df, metadata)

                logger.info(
                    "Forecast generated successfully",
                    region_name=region_name,
                    forecast_points=len(forecast_df),
                    prediction_range=(
                        forecast_df["prediction"].min(),
                        forecast_df["prediction"].max(),
                    ),
                )

                return {
                    "history": history.to_dict("records"),
                    "forecast": forecast_df.to_dict("records"),
                    "sources": sources,
                    "metadata": metadata,
                }

            except Exception as e:
                logger.error(
                    "Error fitting forecasting model", error=str(e), exc_info=True
                )
                return {
                    "history": history.to_dict("records"),
                    "forecast": [],
                    "sources": sources,
                    "metadata": {
                        "region_name": region_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "error": f"Model fitting failed: {str(e)}",
                    },
                }

        except Exception as e:
            logger.error("Error generating forecast", error=str(e), exc_info=True)
            return {
                "history": [],
                "forecast": [],
                "sources": sources,
                "metadata": {
                    "region_name": region_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "error": str(e),
                },
            }
