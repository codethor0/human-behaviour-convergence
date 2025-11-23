# SPDX-License-Identifier: MIT-0
"""Public health data ingestion using public APIs for health indicator analysis."""
from datetime import datetime, timedelta
from typing import Optional

import os
import pandas as pd
import requests
import requests_cache
import structlog

logger = structlog.get_logger("ingestion.public_health")


class PublicHealthFetcher:
    """
    Fetch and normalize public health indicators from public health APIs.

    Provides time-series signals for public health conditions using aggregated,
    public data only (no individual-level records). Calculates normalized health
    risk indices (0.0-1.0) where high scores indicate elevated health concerns.
    """

    def __init__(self, cache_duration_minutes: int = 1440):
        """
        Initialize the public health fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses (default: 1440 minutes = 24 hours)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: Optional[pd.DataFrame] = None
        self._cache_key: Optional[str] = None
        self._cache_timestamp: Optional[datetime] = None

        # Setup requests session with caching
        self.session = requests_cache.CachedSession(
            ".cache/public_health_cache",
            expire_after=timedelta(minutes=cache_duration_minutes),
        )

    def fetch_health_risk_index(
        self,
        region_code: Optional[str] = None,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch public health risk index time-series data.

        Args:
            region_code: Optional standardized region identifier (ISO country/region code)
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'health_risk_index']
            health_risk_index is normalized to 0.0-1.0 where 1.0 = maximum health risk
        """
        # Check cache validity
        cache_key = f"{region_code or 'default'},{days_back}"
        if (
            use_cache
            and self._cache is not None
            and self._cache_key == cache_key
            and self._cache_timestamp is not None
        ):
            age_minutes = (datetime.now() - self._cache_timestamp).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info(
                    "Using cached public health data",
                    age_minutes=age_minutes,
                    region_code=region_code,
                )
                return self._cache.copy()

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            logger.info(
                "Fetching public health data",
                region_code=region_code,
                start_date=start_date.date().isoformat(),
                end_date=end_date.date().isoformat(),
            )

            # Placeholder implementation using public health API
            # This is a generic abstraction that can be configured via environment variables
            api_endpoint = os.getenv("PUBLIC_HEALTH_API_ENDPOINT", "")
            api_key = os.getenv("PUBLIC_HEALTH_API_KEY", "")

            if not api_endpoint or not api_key:
                logger.warning(
                    "Public health API not configured, returning empty DataFrame",
                    region_code=region_code,
                )
                # Return empty DataFrame with correct structure
                return pd.DataFrame(
                    columns=["timestamp", "health_risk_index"],
                    dtype=float,
                )

            # Make API request (placeholder - replace with actual API call)
            # This is a generic structure that can work with various public health APIs
            params = {
                "start_date": start_date.date().isoformat(),
                "end_date": end_date.date().isoformat(),
                "api_key": api_key,
            }
            if region_code:
                params["region_code"] = region_code

            response = self.session.get(api_endpoint, params=params, timeout=30)
            response.raise_for_status()

            # Parse response (placeholder - adapt to actual API format)
            data = response.json()

            # Transform to DataFrame (adapt based on actual API response format)
            if "data" in data and len(data["data"]) > 0:
                df = pd.DataFrame(data["data"])
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp").reset_index(drop=True)

                # Normalize health_risk_index to [0.0, 1.0]
                # This could be based on case counts, hospitalization rates, etc.
                if "risk_level" in df.columns:
                    max_risk = df["risk_level"].max() if len(df) > 0 else 1.0
                    if max_risk > 0:
                        df["health_risk_index"] = df["risk_level"] / max_risk
                    else:
                        df["health_risk_index"] = 0.0
                elif "case_count" in df.columns:
                    # Normalize case counts relative to population or historical max
                    max_cases = df["case_count"].max() if len(df) > 0 else 1.0
                    if max_cases > 0:
                        df["health_risk_index"] = df["case_count"] / max_cases
                    else:
                        df["health_risk_index"] = 0.0
                else:
                    df["health_risk_index"] = 0.5  # Default neutral score

                # Ensure health_risk_index is in [0.0, 1.0]
                df["health_risk_index"] = df["health_risk_index"].clip(0.0, 1.0)

                # Select only required columns
                result = df[["timestamp", "health_risk_index"]].copy()

                # Update cache
                self._cache = result.copy()
                self._cache_key = cache_key
                self._cache_timestamp = datetime.now()

                logger.info(
                    "Successfully fetched public health data",
                    region_code=region_code,
                    rows=len(result),
                )
                return result
            else:
                logger.warning(
                    "No public health data returned", region_code=region_code
                )
                return pd.DataFrame(
                    columns=["timestamp", "health_risk_index"],
                    dtype=float,
                )

        except Exception as e:
            logger.error(
                "Error fetching public health data",
                region_code=region_code,
                error=str(e),
                exc_info=True,
            )
            # Return empty DataFrame with correct structure
            return pd.DataFrame(
                columns=["timestamp", "health_risk_index"],
                dtype=float,
            )
