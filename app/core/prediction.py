# SPDX-License-Identifier: PROPRIETARY
"""Behavioral forecasting engine using real-world public data."""
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pandas as pd
import structlog

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    ExponentialSmoothing = None

from app.services.ingestion import (
    CrimeSafetyStressFetcher,
    DataHarmonizer,
    EnvironmentalImpactFetcher,
    FREDEconomicFetcher,
    GDELTEventsFetcher,
    MarketSentimentFetcher,
    MisinformationStressFetcher,
    MobilityFetcher,
    OWIDHealthFetcher,
    PoliticalStressFetcher,
    PublicHealthFetcher,
    SearchTrendsFetcher,
    SocialCohesionStressFetcher,
    USGSEarthquakeFetcher,
)

logger = structlog.get_logger("core.prediction")


class BehavioralForecaster:
    """
    Multi-vector behavioral forecasting engine.

    Uses economic (VIX/SPY), environmental (weather), search trends,
    public health, and mobility data to forecast human behavioral
    convergence using exponential smoothing (Holt-Winters) model.
    """

    def __init__(
        self,
        market_fetcher: Optional[MarketSentimentFetcher] = None,
        fred_fetcher: Optional[FREDEconomicFetcher] = None,
        weather_fetcher: Optional[EnvironmentalImpactFetcher] = None,
        search_fetcher: Optional[SearchTrendsFetcher] = None,
        health_fetcher: Optional[PublicHealthFetcher] = None,
        mobility_fetcher: Optional[MobilityFetcher] = None,
        gdelt_fetcher: Optional[GDELTEventsFetcher] = None,
        owid_fetcher: Optional[OWIDHealthFetcher] = None,
        usgs_fetcher: Optional[USGSEarthquakeFetcher] = None,
        political_fetcher: Optional[PoliticalStressFetcher] = None,
        crime_fetcher: Optional[CrimeSafetyStressFetcher] = None,
        misinformation_fetcher: Optional[MisinformationStressFetcher] = None,
        social_cohesion_fetcher: Optional[SocialCohesionStressFetcher] = None,
        harmonizer: Optional[DataHarmonizer] = None,
    ):
        """
        Initialize the behavioral forecaster.

        Args:
            market_fetcher: Market sentiment fetcher instance (creates new if None)
            fred_fetcher: FRED economic indicators fetcher instance
                (creates new if None)
            weather_fetcher: Environmental impact fetcher instance (creates new if None)
            search_fetcher: Search trends fetcher instance (creates new if None)
            health_fetcher: Public health fetcher instance (creates new if None)
            mobility_fetcher: Mobility fetcher instance (creates new if None)
            gdelt_fetcher: GDELT events fetcher instance (creates new if None)
            owid_fetcher: OWID health fetcher instance (creates new if None)
            usgs_fetcher: USGS earthquake fetcher instance (creates new if None)
            political_fetcher: Political stress fetcher instance (creates new if None)
            crime_fetcher: Crime & public safety stress fetcher instance
                (creates new if None)
            misinformation_fetcher: Misinformation stress fetcher instance
                (creates new if None)
            social_cohesion_fetcher: Social cohesion stress fetcher instance
                (creates new if None)
            harmonizer: Data harmonizer instance (creates new if None)
        """
        self.market_fetcher = market_fetcher or MarketSentimentFetcher()
        self.fred_fetcher = fred_fetcher or FREDEconomicFetcher()
        self.weather_fetcher = weather_fetcher or EnvironmentalImpactFetcher()
        self.search_fetcher = search_fetcher or SearchTrendsFetcher()
        self.health_fetcher = health_fetcher or PublicHealthFetcher()
        self.mobility_fetcher = mobility_fetcher or MobilityFetcher()
        self.gdelt_fetcher = gdelt_fetcher or GDELTEventsFetcher()
        self.owid_fetcher = owid_fetcher or OWIDHealthFetcher()
        self.usgs_fetcher = usgs_fetcher or USGSEarthquakeFetcher()
        self.political_fetcher = political_fetcher or PoliticalStressFetcher()
        self.crime_fetcher = crime_fetcher or CrimeSafetyStressFetcher()
        self.misinformation_fetcher = (
            misinformation_fetcher or MisinformationStressFetcher()
        )
        self.social_cohesion_fetcher = (
            social_cohesion_fetcher or SocialCohesionStressFetcher()
        )
        self.harmonizer = harmonizer or DataHarmonizer()
        # Intelligence Layer components
        from app.services.analytics.correlation import CorrelationEngine
        from app.services.convergence.engine import ConvergenceEngine
        from app.services.forecast.monitor import ForecastMonitor
        from app.services.risk.classifier import RiskClassifier
        from app.services.shocks.detector import ShockDetector

        self.shock_detector = ShockDetector()
        self.convergence_engine = ConvergenceEngine()
        self.risk_classifier = RiskClassifier()
        self.forecast_monitor = ForecastMonitor()
        self.correlation_engine = CorrelationEngine()
        self._cache: Dict[str, Tuple[pd.DataFrame, pd.DataFrame, Dict]] = {}

    def _is_us_state(self, region_name: str) -> bool:
        """Check if region_name is a US state."""
        us_states = {
            "Alabama",
            "Alaska",
            "Arizona",
            "Arkansas",
            "California",
            "Colorado",
            "Connecticut",
            "Delaware",
            "Florida",
            "Georgia",
            "Hawaii",
            "Idaho",
            "Illinois",
            "Indiana",
            "Iowa",
            "Kansas",
            "Kentucky",
            "Louisiana",
            "Maine",
            "Maryland",
            "Massachusetts",
            "Michigan",
            "Minnesota",
            "Mississippi",
            "Missouri",
            "Montana",
            "Nebraska",
            "Nevada",
            "New Hampshire",
            "New Jersey",
            "New Mexico",
            "New York",
            "North Carolina",
            "North Dakota",
            "Ohio",
            "Oklahoma",
            "Oregon",
            "Pennsylvania",
            "Rhode Island",
            "South Carolina",
            "South Dakota",
            "Tennessee",
            "Texas",
            "Utah",
            "Vermont",
            "Virginia",
            "Washington",
            "West Virginia",
            "Wisconsin",
            "Wyoming",
            "District of Columbia",
        }
        # Also check for state abbreviations or common variations
        return region_name in us_states or any(
            region_name.startswith(state) for state in us_states
        )

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
        cache_key = (
            f"{latitude:.4f},{longitude:.4f},{region_name},"
            f"{days_back},{forecast_horizon}"
        )

        # Check cache
        if cache_key in self._cache:
            logger.info("Using cached forecast", cache_key=cache_key)
            history, forecast, metadata = self._cache[cache_key]
            # Convert timestamps to ISO strings for API response
            history_dict = history.copy()
            if not history.empty and "timestamp" in history_dict.columns:
                history_dict["timestamp"] = history_dict["timestamp"].dt.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
            forecast_dict = forecast.copy()
            if not forecast.empty and "timestamp" in forecast_dict.columns:
                forecast_dict["timestamp"] = forecast_dict["timestamp"].dt.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
            # Preserve harmonized_df in metadata for component extraction
            # (will be removed in API layer)
            return {
                "history": history_dict.to_dict("records") if not history.empty else [],
                "forecast": (
                    forecast_dict.to_dict("records") if not forecast.empty else []
                ),
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

            # Fetch FRED economic indicators (if API key available)
            fred_consumer_sentiment = self.fred_fetcher.fetch_consumer_sentiment(
                days_back=days_back
            )
            fred_unemployment = self.fred_fetcher.fetch_unemployment_rate(
                days_back=days_back
            )
            fred_jobless_claims = self.fred_fetcher.fetch_jobless_claims(
                days_back=days_back
            )
            if (
                not fred_consumer_sentiment.empty
                or not fred_unemployment.empty
                or not fred_jobless_claims.empty
            ):
                sources.append("FRED (Economic Indicators)")

            # Fetch weather data
            weather_data = self.weather_fetcher.fetch_regional_comfort(
                latitude=latitude, longitude=longitude, days_back=days_back
            )
            if not weather_data.empty:
                sources.append("openmeteo.com (Weather)")

            # Fetch search trends data
            search_data = self.search_fetcher.fetch_search_interest(
                query="behavioral patterns", days_back=days_back
            )
            if not search_data.empty:
                sources.append("search trends API")

            # Fetch public health data
            # Derive region code from coordinates if possible (placeholder)
            health_data = self.health_fetcher.fetch_health_risk_index(
                region_code=None, days_back=days_back
            )
            if not health_data.empty:
                sources.append("public health API")

            # Fetch mobility data
            mobility_data = self.mobility_fetcher.fetch_mobility_index(
                latitude=latitude, longitude=longitude, days_back=days_back
            )
            if not mobility_data.empty:
                sources.append("mobility API")

            # Fetch GDELT events data (digital attention)
            gdelt_tone, gdelt_status = self.gdelt_fetcher.fetch_event_tone(
                days_back=days_back
            )
            if gdelt_status.ok and not gdelt_tone.empty:
                sources.append("GDELT (Global Events)")
            # Always store GDELT status in metadata (even if failed)

            # Fetch OWID health data
            # Try to map region to country (simplified: use region_name
            # if it's a country)
            country_name = (
                region_name
                if region_name in ["United States", "USA"]
                else "United States"
            )
            owid_health = self.owid_fetcher.fetch_health_stress_index(
                country=country_name, days_back=days_back
            )
            if not owid_health.empty:
                sources.append("OWID (Public Health)")

            # Fetch USGS earthquake data (environmental hazard)
            usgs_earthquakes = self.usgs_fetcher.fetch_earthquake_intensity(
                days_back=days_back
            )
            if not usgs_earthquakes.empty:
                sources.append("USGS (Earthquakes)")

            # Fetch political stress data (for US states only)
            political_data = pd.DataFrame()
            crime_data = pd.DataFrame()
            misinformation_data = pd.DataFrame()
            social_cohesion_data = pd.DataFrame()

            is_us_state = self._is_us_state(region_name)
            if is_us_state:
                try:
                    political_data = self.political_fetcher.calculate_political_stress(
                        state_name=region_name, days_back=days_back
                    )
                    if (
                        not political_data.empty
                        and "political_stress" in political_data.columns
                    ):
                        political_data = political_data[
                            ["timestamp", "political_stress"]
                        ]
                        sources.append("political_ingestion")
                except Exception as e:
                    logger.warning("Failed to fetch political data", error=str(e))

                try:
                    crime_data = self.crime_fetcher.calculate_crime_stress(
                        region_name=region_name, days_back=days_back
                    )
                    if not crime_data.empty and "crime_stress" in crime_data.columns:
                        crime_data = crime_data[["timestamp", "crime_stress"]]
                        sources.append("crime_ingestion")
                except Exception as e:
                    logger.warning("Failed to fetch crime data", error=str(e))

                try:
                    misinformation_data = (
                        self.misinformation_fetcher.calculate_misinformation_stress(
                            region_name=region_name, days_back=days_back
                        )
                    )
                    if (
                        not misinformation_data.empty
                        and "misinformation_stress" in misinformation_data.columns
                    ):
                        misinformation_data = misinformation_data[
                            ["timestamp", "misinformation_stress"]
                        ]
                        sources.append("misinformation_ingestion")
                except Exception as e:
                    logger.warning("Failed to fetch misinformation data", error=str(e))

                try:
                    social_cohesion_data = (
                        self.social_cohesion_fetcher.calculate_social_cohesion_stress(
                            region_name=region_name, days_back=days_back
                        )
                    )
                    if (
                        not social_cohesion_data.empty
                        and "social_cohesion_stress" in social_cohesion_data.columns
                    ):
                        social_cohesion_data = social_cohesion_data[
                            ["timestamp", "social_cohesion_stress"]
                        ]
                        sources.append("social_cohesion_ingestion")
                except Exception as e:
                    logger.warning("Failed to fetch social cohesion data", error=str(e))

            # Harmonize data
            if (
                market_data.empty
                and weather_data.empty
                and search_data.empty
                and health_data.empty
                and mobility_data.empty
                and fred_consumer_sentiment.empty
                and fred_unemployment.empty
                and fred_jobless_claims.empty
                and gdelt_tone.empty
                and owid_health.empty
                and usgs_earthquakes.empty
                and political_data.empty
                and crime_data.empty
                and misinformation_data.empty
                and social_cohesion_data.empty
            ):
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
                        "sources_status": {
                            "gdelt": gdelt_status.to_dict(),
                        },
                    },
                }

            harmonized = self.harmonizer.harmonize(
                market_data=market_data,
                fred_consumer_sentiment=fred_consumer_sentiment,
                fred_unemployment=fred_unemployment,
                fred_jobless_claims=fred_jobless_claims,
                weather_data=weather_data,
                search_data=search_data,
                health_data=health_data,
                mobility_data=mobility_data,
                gdelt_tone=gdelt_tone,
                owid_health=owid_health,
                usgs_earthquakes=usgs_earthquakes,
                political_data=political_data,
                crime_data=crime_data,
                misinformation_data=misinformation_data,
                social_cohesion_data=social_cohesion_data,
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
                        "sources_status": {
                            "gdelt": gdelt_status.to_dict(),
                        },
                    },
                }

            # Prepare history data with sub-indices
            # Keep full harmonized DataFrame for component extraction
            # (store in metadata)
            # But extract only needed columns for history
            sub_index_cols = [
                "economic_stress",
                "environmental_stress",
                "mobility_activity",
                "digital_attention",
                "public_health_stress",
                "political_stress",
                "crime_stress",
                "misinformation_stress",
                "social_cohesion_stress",
            ]
            history_cols = ["timestamp", "behavior_index"] + [
                col for col in sub_index_cols if col in harmonized.columns
            ]
            history = harmonized[history_cols].copy()

            # Preserve the full harmonized DataFrame
            # (with component metadata in attrs) for API extraction
            # We'll attach it to metadata temporarily
            harmonized_for_details = harmonized.copy()
            # Normalize timestamps to timezone-naive UTC
            history["timestamp"] = pd.to_datetime(history["timestamp"], utc=True)
            if history["timestamp"].dt.tz is not None:
                history["timestamp"] = history["timestamp"].dt.tz_localize(None)
            history = history.sort_values("timestamp").reset_index(drop=True)

            # Ensure we have enough data points for forecasting (minimum 7 days)
            if len(history) < 7:
                logger.warning(
                    "Insufficient historical data for forecasting",
                    data_points=len(history),
                )
                # Convert timestamps to ISO strings for API response
                history_dict = history.copy()
                if "timestamp" in history_dict.columns:
                    history_dict["timestamp"] = history_dict["timestamp"].dt.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                return {
                    "history": history_dict.to_dict("records"),
                    "forecast": [],
                    "sources": sources,
                    "metadata": {
                        "region_name": region_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "warning": "Insufficient data for forecasting",
                        "data_points": len(history),
                        "sources_status": {
                            "gdelt": gdelt_status.to_dict(),
                        },
                    },
                }

            # Extract behavior_index time series
            if "behavior_index" not in history.columns:
                logger.warning(
                    "behavior_index column missing from history, using default 0.5"
                )
                history["behavior_index"] = 0.5

            # Ensure behavior_index values are valid
            history["behavior_index"] = pd.to_numeric(
                history["behavior_index"], errors="coerce"
            ).fillna(0.5)
            history["behavior_index"] = history["behavior_index"].clip(0.0, 1.0)

            behavior_ts = history.set_index("timestamp")["behavior_index"]

            # Validate time series
            if behavior_ts.empty:
                logger.warning(
                    "Empty behavior_index time series, returning empty forecast"
                )
                return {
                    "history": (
                        history_dict.to_dict("records") if not history.empty else []
                    ),
                    "forecast": [],
                    "sources": sources,
                    "metadata": {
                        "region_name": region_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "warning": "Empty time series",
                        "data_points": len(history),
                        "sources_status": {
                            "gdelt": gdelt_status.to_dict(),
                        },
                    },
                }

            # Fit Exponential Smoothing (Holt-Winters) model
            try:
                if not HAS_STATSMODELS:
                    logger.warning(
                        "statsmodels not available, using simple moving average"
                    )
                    # Fallback to simple moving average if statsmodels not available
                    window_size = min(7, len(behavior_ts) // 2)
                    if window_size < 2:
                        window_size = 2
                    ma = behavior_ts.rolling(window=window_size, center=False).mean()
                    if ma.empty or len(ma) == 0:
                        last_value = (
                            behavior_ts.iloc[-1] if len(behavior_ts) > 0 else 0.5
                        )
                    else:
                        last_value = (
                            float(ma.iloc[-1])
                            if pd.notna(ma.iloc[-1])
                            else (
                                float(behavior_ts.iloc[-1])
                                if len(behavior_ts) > 0
                                and pd.notna(behavior_ts.iloc[-1])
                                else 0.5
                            )
                        )

                    # Ensure last_value is valid
                    if pd.isna(last_value) or not isinstance(last_value, (int, float)):
                        last_value = 0.5
                    last_value = max(0.0, min(1.0, float(last_value)))

                    trend = (
                        (float(behavior_ts.iloc[-1]) - float(behavior_ts.iloc[0]))
                        / len(behavior_ts)
                        if len(behavior_ts) > 1
                        and pd.notna(behavior_ts.iloc[-1])
                        and pd.notna(behavior_ts.iloc[0])
                        else 0.0
                    )
                    # Clamp trend to reasonable bounds
                    trend = max(-0.1, min(0.1, float(trend)))
                    # Generate forecast dates safely
                    try:
                        last_date = behavior_ts.index[-1]
                        if not isinstance(last_date, pd.Timestamp):
                            last_date = pd.Timestamp(last_date)
                        forecast_dates = pd.date_range(
                            start=last_date + pd.Timedelta(days=1),
                            periods=forecast_horizon,
                            freq="D",
                            tz=None,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to generate forecast dates", error=str(e)
                        )
                        forecast_dates = pd.date_range(
                            start=pd.Timestamp.now(),
                            periods=forecast_horizon,
                            freq="D",
                            tz=None,
                        )

                    forecast_values = []
                    for i in range(1, forecast_horizon + 1):
                        value = last_value + trend * i
                        # Clamp to valid range
                        value = max(0.0, min(1.0, float(value)))
                        forecast_values.append(value)

                    forecast_result = pd.Series(forecast_values, index=forecast_dates)

                    # Calculate std_error safely
                    if len(behavior_ts) > 1:
                        std_error = float(behavior_ts.std())
                        if pd.isna(std_error):
                            std_error = 0.1
                        std_error = max(0.01, min(0.5, std_error))
                    else:
                        std_error = 0.1
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

                    # Generate forecast with error handling
                    try:
                        forecast_result = model.forecast(steps=forecast_horizon)
                    except Exception as e:
                        logger.warning(
                            "Model forecast failed, using fallback", error=str(e)
                        )
                        # Fallback: use last value with small trend
                        last_val = (
                            float(behavior_ts.iloc[-1])
                            if len(behavior_ts) > 0 and pd.notna(behavior_ts.iloc[-1])
                            else 0.5
                        )
                        forecast_result = pd.Series([last_val] * forecast_horizon)

                    # Validate forecast_result
                    if (
                        not isinstance(forecast_result, pd.Series)
                        or len(forecast_result) == 0
                    ):
                        logger.warning("Invalid forecast result, using fallback")
                        last_val = (
                            float(behavior_ts.iloc[-1])
                            if len(behavior_ts) > 0 and pd.notna(behavior_ts.iloc[-1])
                            else 0.5
                        )
                        forecast_result = pd.Series([last_val] * forecast_horizon)

                    # Ensure forecast values are valid
                    forecast_result = pd.to_numeric(
                        forecast_result, errors="coerce"
                    ).fillna(0.5)
                    forecast_result = forecast_result.clip(0.0, 1.0)

                    # Calculate confidence intervals
                    # (approximate using model's fitted values variance)
                    try:
                        fitted_values = model.fittedvalues
                        residuals = behavior_ts - fitted_values
                        std_error = float(residuals.std())
                        if pd.isna(std_error) or std_error <= 0:
                            std_error = 0.1
                        std_error = max(0.01, min(0.5, std_error))
                    except Exception as e:
                        logger.warning("Failed to calculate std_error", error=str(e))
                        std_error = 0.1

                # Generate forecast dates with error handling
                try:
                    if (
                        isinstance(forecast_result, pd.Series)
                        and not forecast_result.index.empty
                        and len(forecast_result) > 0
                    ):
                        forecast_dates = forecast_result.index
                    else:
                        last_date = behavior_ts.index.max()
                        if not isinstance(last_date, pd.Timestamp):
                            last_date = pd.Timestamp(last_date)
                        forecast_dates = pd.date_range(
                            start=last_date + timedelta(days=1),
                            periods=forecast_horizon,
                            freq="D",
                            tz=None,
                        )
                except Exception as e:
                    logger.warning("Failed to generate forecast dates", error=str(e))
                    forecast_dates = pd.date_range(
                        start=pd.Timestamp.now(),
                        periods=forecast_horizon,
                        freq="D",
                        tz=None,
                    )

                # Ensure forecast_result has correct length
                if len(forecast_result) != forecast_horizon:
                    logger.warning(
                        f"Forecast length mismatch: expected {forecast_horizon}, "
                        f"got {len(forecast_result)}"
                    )
                    if len(forecast_result) > forecast_horizon:
                        forecast_result = forecast_result[:forecast_horizon]
                    else:
                        last_val = (
                            float(forecast_result.iloc[-1])
                            if len(forecast_result) > 0
                            else 0.5
                        )
                        forecast_result = pd.concat(
                            [
                                forecast_result,
                                pd.Series(
                                    [last_val]
                                    * (forecast_horizon - len(forecast_result))
                                ),
                            ]
                        )

                # Create forecast DataFrame with confidence intervals
                try:
                    forecast_df = pd.DataFrame(
                        {
                            "timestamp": forecast_dates[: len(forecast_result)],
                            "prediction": forecast_result.values,
                            "lower_bound": (forecast_result - 1.96 * std_error).values,
                            "upper_bound": (forecast_result + 1.96 * std_error).values,
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to create forecast DataFrame", error=str(e))
                    # Fallback: create minimal forecast
                    forecast_df = pd.DataFrame(
                        {
                            "timestamp": forecast_dates[:forecast_horizon],
                            "prediction": [0.5] * forecast_horizon,
                            "lower_bound": [0.4] * forecast_horizon,
                            "upper_bound": [0.6] * forecast_horizon,
                        }
                    )

                # Clip values to valid range [0.0, 1.0] and ensure numeric
                forecast_df["prediction"] = (
                    pd.to_numeric(forecast_df["prediction"], errors="coerce")
                    .fillna(0.5)
                    .clip(0.0, 1.0)
                )
                forecast_df["lower_bound"] = (
                    pd.to_numeric(forecast_df["lower_bound"], errors="coerce")
                    .fillna(0.4)
                    .clip(0.0, 1.0)
                )
                forecast_df["upper_bound"] = (
                    pd.to_numeric(forecast_df["upper_bound"], errors="coerce")
                    .fillna(0.6)
                    .clip(0.0, 1.0)
                )

                # Ensure forecast is sorted by timestamp
                # (invariant: forecast arrays always sorted)
                forecast_df = forecast_df.sort_values("timestamp").reset_index(
                    drop=True
                )

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
                    "_harmonized_df": harmonized_for_details,  # Store for extraction
                }
                # Add source status metadata
                metadata["sources_status"] = {
                    "gdelt": gdelt_status.to_dict(),
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

                # Convert timestamps to ISO strings for API response
                history_dict = history.copy()
                history_dict["timestamp"] = history_dict["timestamp"].dt.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
                forecast_dict = forecast_df.copy()
                forecast_dict["timestamp"] = forecast_dict["timestamp"].dt.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )

                # Store harmonized DataFrame (with component metadata) for extraction
                # Attach to metadata so API can extract component details
                # Note: This will be removed in the API layer before JSON serialization
                metadata["_harmonized_df"] = harmonized_for_details

                # Intelligence Layer Analysis
                intelligence_data = self._analyze_intelligence(
                    history, harmonized_for_details
                )

                return {
                    "history": history_dict.to_dict("records"),
                    "forecast": forecast_dict.to_dict("records"),
                    "sources": sources,
                    "metadata": metadata,
                    **intelligence_data,  # Add intelligence layer data
                }

            except Exception as e:
                logger.error(
                    "Error fitting forecasting model", error=str(e), exc_info=True
                )
                # Convert timestamps to ISO strings for API response
                history_dict = history.copy()
                if "timestamp" in history_dict.columns:
                    history_dict["timestamp"] = history_dict["timestamp"].dt.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                return {
                    "history": history_dict.to_dict("records"),
                    "forecast": [],
                    "sources": sources,
                    "metadata": {
                        "region_name": region_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "error": f"Model fitting failed: {str(e)}",
                    },
                    **self._empty_intelligence_data(),  # Add empty intelligence data
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
                **self._empty_intelligence_data(),  # Add empty intelligence data
            }

    def _analyze_intelligence(
        self, history_df: pd.DataFrame, harmonized_df: pd.DataFrame
    ) -> Dict:
        """Run intelligence layer analysis on historical data."""
        try:
            # Convert history DataFrame if needed
            if (
                "timestamp" not in history_df.columns
                and history_df.index.name == "timestamp"
            ):
                history_df = history_df.reset_index()

            # Ensure timestamp is datetime
            history_df_work = history_df.copy()
            if "timestamp" in history_df_work.columns:
                history_df_work["timestamp"] = pd.to_datetime(
                    history_df_work["timestamp"]
                )
                # Set timestamp as index for shock detection
                history_df_indexed = history_df_work.set_index("timestamp")
            else:
                history_df_indexed = history_df_work

            # 1. Shock Detection (use indexed version)
            shock_events = self.shock_detector.detect_shocks(history_df_indexed)

            # 2. Convergence Analysis (use original with timestamp column)
            convergence_result = self.convergence_engine.analyze_convergence(history_df)

            # 3. Risk Classification
            if len(history_df) > 0 and "behavior_index" in history_df.columns:
                latest_bi = history_df["behavior_index"].iloc[-1]
                # Calculate trend direction
                if len(history_df) >= 7:
                    recent_trend = (
                        history_df["behavior_index"].tail(7).iloc[-1]
                        - history_df["behavior_index"].tail(7).iloc[0]
                    )
                    trend_direction = (
                        "increasing"
                        if recent_trend > 0.05
                        else "decreasing" if recent_trend < -0.05 else "stable"
                    )
                else:
                    trend_direction = "stable"

                risk_classification = self.risk_classifier.classify_risk(
                    behavior_index=float(latest_bi),
                    shock_events=shock_events,
                    convergence_score=convergence_result.get("score", 0.0),
                    trend_direction=trend_direction,
                )
            else:
                risk_classification = {
                    "tier": "stable",
                    "risk_score": 0.5,
                    "base_risk": 0.5,
                    "shock_adjustment": 0.0,
                    "convergence_adjustment": 0.0,
                    "trend_adjustment": 0.0,
                    "contributing_factors": [],
                }

            # 4. Forecast Confidence (use original with timestamp column)
            confidence_scores = self.forecast_monitor.calculate_confidence(history_df)

            # 5. Model Drift (use original with timestamp column)
            drift_scores = self.forecast_monitor.detect_drift(history_df)

            # 6. Correlation Analysis (use original with timestamp column)
            correlation_result = self.correlation_engine.calculate_correlations(
                history_df
            )

            return {
                "shock_events": shock_events,
                "convergence": {
                    "score": convergence_result.get("score", 0.0),
                    "reinforcing_signals": [
                        [sig[0], sig[1], sig[2]]
                        for sig in convergence_result.get("reinforcing_signals", [])
                    ],
                    "conflicting_signals": [
                        [sig[0], sig[1], sig[2]]
                        for sig in convergence_result.get("conflicting_signals", [])
                    ],
                    "patterns": convergence_result.get("patterns", []),
                },
                "risk_tier": risk_classification,
                "forecast_confidence": confidence_scores,
                "model_drift": drift_scores,
                "correlations": {
                    "correlations": correlation_result.get("correlations", {}),
                    "relationships": correlation_result.get("relationships", []),
                    "indices_analyzed": correlation_result.get("indices_analyzed", []),
                },
            }
        except Exception as e:
            logger.warning(
                "Intelligence layer analysis failed", error=str(e), exc_info=True
            )
            return self._empty_intelligence_data()

    def _empty_intelligence_data(self) -> Dict:
        """Return empty intelligence data structure."""
        return {
            "shock_events": [],
            "convergence": {
                "score": 0.0,
                "reinforcing_signals": [],
                "conflicting_signals": [],
                "patterns": [],
            },
            "risk_tier": {
                "tier": "stable",
                "risk_score": 0.5,
                "base_risk": 0.5,
                "shock_adjustment": 0.0,
                "convergence_adjustment": 0.0,
                "trend_adjustment": 0.0,
                "contributing_factors": [],
            },
            "forecast_confidence": {},
            "model_drift": {},
            "correlations": {
                "correlations": {},
                "relationships": [],
                "indices_analyzed": [],
            },
        }
