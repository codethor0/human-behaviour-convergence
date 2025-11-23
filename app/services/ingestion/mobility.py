# SPDX-License-Identifier: MIT-0
"""Mobility data ingestion using public APIs for activity pattern analysis."""
from datetime import datetime, timedelta
from typing import Optional

import os
import pandas as pd
import requests
import requests_cache
import structlog

logger = structlog.get_logger("ingestion.mobility")


class MobilityFetcher:
    """
    Fetch and normalize mobility/activity pattern data from public APIs.

    Provides time-series signals approximating mobility or activity patterns
    using aggregated, public data. Calculates normalized mobility indices
    (0.0-1.0) where high scores indicate high mobility/activity.
    """

    def __init__(self, cache_duration_minutes: int = 60):
        """
        Initialize the mobility fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses (default: 60 minutes)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: Optional[pd.DataFrame] = None
        self._cache_key: Optional[str] = None
        self._cache_timestamp: Optional[datetime] = None

        # Setup requests session with caching
        self.session = requests_cache.CachedSession(
            ".cache/mobility_cache", expire_after=timedelta(minutes=cache_duration_minutes)
        )

    def fetch_mobility_index(
        self,
        region_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch mobility/activity index time-series data.

        Args:
            region_code: Optional standardized region identifier (ISO country/region code)
            latitude: Optional latitude coordinate for geographic region
            longitude: Optional longitude coordinate for geographic region
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'mobility_index']
            mobility_index is normalized to 0.0-1.0 where 1.0 = maximum mobility/activity
        """
        # Check cache validity
        cache_key = f"{region_code or 'default'},{latitude or ''},{longitude or ''},{days_back}"
        if (
            use_cache
            and self._cache is not None
            and self._cache_key == cache_key
            and self._cache_timestamp is not None
        ):
            age_minutes = (datetime.now() - self._cache_timestamp).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info(
                    "Using cached mobility data",
                    age_minutes=age_minutes,
                    region_code=region_code,
                )
                return self._cache.copy()

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            logger.info(
                "Fetching mobility data",
                region_code=region_code,
                latitude=latitude,
                longitude=longitude,
                start_date=start_date.date().isoformat(),
                end_date=end_date.date().isoformat(),
            )

            # Placeholder implementation using public mobility API
            # This is a generic abstraction that can be configured via environment variables
            api_endpoint = os.getenv("MOBILITY_API_ENDPOINT", "")
            api_key = os.getenv("MOBILITY_API_KEY", "")

            if not api_endpoint or not api_key:
                logger.warning(
                    "Mobility API not configured, returning empty DataFrame",
                    region_code=region_code,
                )
                # Return empty DataFrame with correct structure
                return pd.DataFrame(
                    columns=["timestamp", "mobility_index"],
                    dtype=float,
                )

            # Make API request (placeholder - replace with actual API call)
            # This is a generic structure that can work with various mobility APIs
            params = {
                "start_date": start_date.date().isoformat(),
                "end_date": end_date.date().isoformat(),
                "api_key": api_key,
            }
            if region_code:
                params["region_code"] = region_code
            if latitude is not None:
                params["latitude"] = latitude
            if longitude is not None:
                params["longitude"] = longitude

            response = self.session.get(api_endpoint, params=params, timeout=30)
            response.raise_for_status()

            # Parse response (placeholder - adapt to actual API format)
            data = response.json()

            # Transform to DataFrame (adapt based on actual API response format)
            if "data" in data and len(data["data"]) > 0:
                df = pd.DataFrame(data["data"])
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp").reset_index(drop=True)

                # Normalize mobility_index to [0.0, 1.0]
                # This could be based on movement patterns, activity levels, etc.
                if "activity_level" in df.columns:
                    max_activity = df["activity_level"].max() if len(df) > 0 else 1.0
                    if max_activity > 0:
                        df["mobility_index"] = df["activity_level"] / max_activity
                    else:
                        df["mobility_index"] = 0.0
                elif "mobility_score" in df.columns:
                    # Already normalized
                    df["mobility_index"] = df["mobility_score"]
                else:
                    df["mobility_index"] = 0.5  # Default neutral score

                # Ensure mobility_index is in [0.0, 1.0]
                df["mobility_index"] = df["mobility_index"].clip(0.0, 1.0)

                # Select only required columns
                result = df[["timestamp", "mobility_index"]].copy()

                # Update cache
                self._cache = result.copy()
                self._cache_key = cache_key
                self._cache_timestamp = datetime.now()

                logger.info(
                    "Successfully fetched mobility data",
                    region_code=region_code,
                    rows=len(result),
                )
                return result
            else:
                logger.warning("No mobility data returned", region_code=region_code)
                return pd.DataFrame(
                    columns=["timestamp", "mobility_index"],
                    dtype=float,
                )

        except Exception as e:
            logger.error(
                "Error fetching mobility data",
                region_code=region_code,
                error=str(e),
                exc_info=True,
            )
            # Return empty DataFrame with correct structure
            return pd.DataFrame(
                columns=["timestamp", "mobility_index"],
                dtype=float,
            )

