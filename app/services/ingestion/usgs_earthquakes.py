# SPDX-License-Identifier: PROPRIETARY
"""USGS Earthquake feed connector for environmental hazard signals."""
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests
import structlog

logger = structlog.get_logger("ingestion.usgs_earthquakes")

# USGS Earthquake API base URL
USGS_API_BASE = "https://earthquake.usgs.gov/fdsnws/event/1/query"


class USGSEarthquakeFetcher:
    """
    Fetch earthquake data from USGS Earthquake API.

    Provides real-time and historical earthquake data globally.
    No authentication required.

    Source: https://earthquake.usgs.gov/fdsnws/event/1/
    """

    def __init__(self, cache_duration_minutes: int = 60):
        """
        Initialize USGS earthquake fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses
                (default: 60 minutes)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

    def fetch_earthquake_intensity(
        self,
        days_back: int = 30,
        min_magnitude: float = 4.0,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch daily earthquake intensity index from USGS.

        Aggregates earthquakes by date and computes normalized intensity score
        based on magnitude and frequency.

        Args:
            days_back: Number of days of historical data (default: 30)
            min_magnitude: Minimum earthquake magnitude to include (default: 4.0)
            use_cache: Whether to use cached data (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'earthquake_intensity']
            Values normalized to [0.0, 1.0] where 1.0 = maximum intensity
        """
        cache_key = f"usgs_earthquakes_{days_back}_{min_magnitude}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached USGS earthquake data")
                return df.copy()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        try:
            # USGS API query
            params = {
                "format": "geojson",
                "starttime": start_date.strftime("%Y-%m-%d"),
                "endtime": end_date.strftime("%Y-%m-%d"),
                "minmagnitude": min_magnitude,
                "orderby": "time",
            }

            logger.info(
                "Fetching USGS earthquake data",
                days_back=days_back,
                min_magnitude=min_magnitude,
            )

            response = requests.get(USGS_API_BASE, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Parse GeoJSON features
            if "features" not in data or not data["features"]:
                logger.warning("No features in USGS response")
                return pd.DataFrame(columns=["timestamp", "earthquake_intensity"])

            features = data["features"]
            records = []

            for feature in features:
                props = feature.get("properties", {})
                time_ms = props.get("time")
                magnitude = props.get("mag")

                if time_ms is None or magnitude is None:
                    continue

                try:
                    # Convert milliseconds to datetime
                    date_obj = datetime.fromtimestamp(time_ms / 1000.0)
                    date_obj = date_obj.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    records.append(
                        {
                            "timestamp": date_obj,
                            "magnitude": float(magnitude),
                        }
                    )
                except (ValueError, TypeError) as e:
                    logger.debug(
                        "Skipping invalid earthquake entry",
                        time=time_ms,
                        magnitude=magnitude,
                        error=str(e),
                    )
                    continue

            if not records:
                logger.warning("No valid earthquake entries after parsing")
                return pd.DataFrame(columns=["timestamp", "earthquake_intensity"])

            df = pd.DataFrame(records)

            # Aggregate by date: compute daily intensity
            # Intensity = weighted sum of magnitudes (higher magnitude = more weight)
            daily_intensity = (
                df.groupby("timestamp")["magnitude"]
                .apply(
                    lambda x: (x**2).sum()
                )  # Square magnitude for non-linear weighting
                .reset_index()
            )
            daily_intensity.columns = ["timestamp", "raw_intensity"]

            # Normalize to [0.0, 1.0]
            min_intensity = daily_intensity["raw_intensity"].min()
            max_intensity = daily_intensity["raw_intensity"].max()

            if max_intensity > min_intensity:
                daily_intensity["earthquake_intensity"] = (
                    daily_intensity["raw_intensity"] - min_intensity
                ) / (max_intensity - min_intensity)
            else:
                daily_intensity["earthquake_intensity"] = 0.0

            result_df = (
                daily_intensity[["timestamp", "earthquake_intensity"]]
                .sort_values("timestamp")
                .reset_index(drop=True)
            )

            # Cache result
            self._cache[cache_key] = (result_df.copy(), datetime.now())

            logger.info(
                "Successfully fetched USGS earthquake data",
                rows=len(result_df),
                date_range=(result_df["timestamp"].min(), result_df["timestamp"].max()),
            )

            return result_df

        except requests.exceptions.RequestException as e:
            logger.error(
                "Error fetching USGS earthquake data",
                error=str(e),
                exc_info=True,
            )
            return pd.DataFrame(columns=["timestamp", "earthquake_intensity"])

        except Exception as e:
            logger.error(
                "Unexpected error fetching USGS earthquake data",
                error=str(e),
                exc_info=True,
            )
            return pd.DataFrame(columns=["timestamp", "earthquake_intensity"])
