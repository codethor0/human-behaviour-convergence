# SPDX-License-Identifier: PROPRIETARY
"""Environmental data ingestion using Open-Meteo API for weather impact analysis."""
from datetime import datetime, timedelta
from typing import Optional

import openmeteo_requests
import pandas as pd
import requests_cache
import structlog

logger = structlog.get_logger("ingestion.weather")


class EnvironmentalImpactFetcher:
    """
    Fetch and calculate environmental discomfort scores from Open-Meteo weather data.

    Calculates a discomfort score based on temperature deviation from 20C ideal,
    precipitation, and wind speed. Higher discomfort score = less comfortable weather.
    """

    def __init__(self, cache_duration_minutes: int = 30):
        """
        Initialize the environmental impact fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses (default: 30 minutes)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: Optional[pd.DataFrame] = None
        self._cache_key: Optional[str] = None
        self._cache_timestamp: Optional[datetime] = None

        # Setup requests session with caching
        self.session = requests_cache.CachedSession(
            ".cache/weather_cache",
            expire_after=timedelta(minutes=cache_duration_minutes),
        )
        self.openmeteo = openmeteo_requests.Client(session=self.session)

    def fetch_regional_comfort(
        self,
        latitude: float,
        longitude: float,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch weather data and calculate regional comfort/discomfort score.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'temperature', 'precipitation',
                'windspeed', 'discomfort_score']
            discomfort_score is normalized to 0.0-1.0 where 1.0 = maximum discomfort
        """
        # Validate coordinates
        if not (-90 <= latitude <= 90):
            raise ValueError(
                f"Invalid latitude: {latitude} (must be between -90 and 90)"
            )
        if not (-180 <= longitude <= 180):
            raise ValueError(
                f"Invalid longitude: {longitude} (must be between -180 and 180)"
            )

        cache_key = f"{latitude:.4f},{longitude:.4f},{days_back}"

        # Check cache validity
        if (
            use_cache
            and self._cache is not None
            and self._cache_key == cache_key
            and self._cache_timestamp is not None
        ):
            age_minutes = (datetime.now() - self._cache_timestamp).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info(
                    "Using cached weather data",
                    age_minutes=age_minutes,
                    cache_key=cache_key,
                )
                return self._cache.copy()

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            logger.info(
                "Fetching weather data",
                latitude=latitude,
                longitude=longitude,
                start_date=start_date.date().isoformat(),
                end_date=end_date.date().isoformat(),
            )

            # Open-Meteo API URL and parameters
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date.date().isoformat(),
                "end_date": end_date.date().isoformat(),
                "hourly": ["temperature_2m", "precipitation", "windspeed_10m"],
                "timezone": "UTC",
            }

            # Make API request
            responses = self.openmeteo.weather_api(url, params=params)

            if not responses or len(responses) == 0:
                logger.warning("Empty response from Open-Meteo API")
                return pd.DataFrame(
                    columns=[
                        "timestamp",
                        "temperature",
                        "precipitation",
                        "windspeed",
                        "discomfort_score",
                    ],
                    dtype=float,
                )

            response = responses[0]

            # Extract hourly data
            hourly = response.Hourly()
            hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
            hourly_precipitation = hourly.Variables(1).ValuesAsNumpy()
            hourly_windspeed_10m = hourly.Variables(2).ValuesAsNumpy()

            # Generate timestamps (UTC-aware, then normalize to naive UTC)
            date_range = pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            )
            # Normalize to timezone-naive UTC (remove timezone info for consistency)
            date_range = date_range.tz_localize(None)

            # Create DataFrame
            df = pd.DataFrame(
                {
                    "timestamp": date_range[: len(hourly_temperature_2m)],
                    "temperature": hourly_temperature_2m,
                    "precipitation": hourly_precipitation,
                    "windspeed": hourly_windspeed_10m,
                }
            )

            # Drop any NaN values
            df = df.dropna()

            if df.empty:
                logger.warning("No valid weather data returned from Open-Meteo API")
                return pd.DataFrame(
                    columns=[
                        "timestamp",
                        "temperature",
                        "precipitation",
                        "windspeed",
                        "discomfort_score",
                    ],
                    dtype=float,
                )

            # Calculate discomfort score
            # Ideal temperature: 20C
            ideal_temp = 20.0
            temp_deviation = abs(df["temperature"] - ideal_temp)
            # Normalize temperature deviation (assuming max deviation of 30C)
            temp_score = (temp_deviation / 30.0).clip(0.0, 1.0)

            # Normalize precipitation (mm per hour, max reasonable value ~50mm/hour)
            precip_score = (df["precipitation"] / 50.0).clip(0.0, 1.0)

            # Normalize wind speed (m/s, max reasonable value ~30 m/s)
            wind_score = (df["windspeed"] / 30.0).clip(0.0, 1.0)

            # Combined discomfort score: weighted average
            # Temperature deviation weighted most, then precipitation, then wind
            discomfort_score = (
                (temp_score * 0.5) + (precip_score * 0.3) + (wind_score * 0.2)
            )

            # Add discomfort_score column
            df["discomfort_score"] = discomfort_score.clip(0.0, 1.0)

            # Convert timestamp to date for aggregation (daily aggregation)
            df["date"] = pd.to_datetime(df["timestamp"]).dt.date

            # Aggregate to daily averages
            daily_df = (
                df.groupby("date")
                .agg(
                    {
                        "temperature": "mean",
                        "precipitation": "sum",  # Total daily precipitation
                        "windspeed": "mean",
                        "discomfort_score": "mean",
                    }
                )
                .reset_index()
            )

            # Rename date to timestamp
            daily_df["timestamp"] = pd.to_datetime(daily_df["date"])
            daily_df = daily_df.drop(columns=["date"])

            # Sort by timestamp
            daily_df = daily_df.sort_values("timestamp").reset_index(drop=True)

            # Update cache
            self._cache = daily_df.copy()
            self._cache_key = cache_key
            self._cache_timestamp = datetime.now()

            logger.info(
                "Weather data fetched successfully",
                rows=len(daily_df),
                discomfort_score_range=(
                    daily_df["discomfort_score"].min(),
                    daily_df["discomfort_score"].max(),
                ),
            )

            return daily_df

        except Exception as e:
            logger.error(
                "Error fetching weather data",
                error=str(e),
                latitude=latitude,
                longitude=longitude,
                exc_info=True,
            )
            # Return empty DataFrame with correct structure on error
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "temperature",
                    "precipitation",
                    "windspeed",
                    "discomfort_score",
                ],
                dtype=float,
            )
