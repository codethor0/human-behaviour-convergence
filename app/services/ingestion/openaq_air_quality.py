# SPDX-License-Identifier: PROPRIETARY
"""OpenAQ API connector for air quality data."""
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
import requests
import structlog

from app.services.ingestion.ci_offline_data import (
    is_ci_offline_mode,
    get_ci_air_quality_data,
)
from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.openaq_air_quality")

# OpenAQ API base URL (v2)
OPENAQ_API_BASE = "https://api.openaq.org/v2"

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 10.0


class OpenAQAirQualityFetcher:
    """
    Fetch air quality data from OpenAQ API.

    OpenAQ provides aggregated air quality measurements from global monitoring stations.
    No authentication required for basic queries.

    Source: https://openaq.org/
    API Docs: https://docs.openaq.org/
    Rate limits: 1000 requests per day (free tier)
    """

    def __init__(self, cache_duration_minutes: int = 60):
        """
        Initialize OpenAQ air quality fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses (default: 60 minutes)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}
        self.last_status: Optional[SourceStatus] = None

    def _make_request_with_retries(
        self, url: str, params: dict, timeout: Tuple[float, float] = (10.0, 30.0)
    ) -> Tuple[Optional[requests.Response], Optional[str], Optional[int]]:
        """
        Make HTTP request with exponential backoff retries.

        Args:
            url: URL to request
            params: Query parameters
            timeout: (connect_timeout, read_timeout) tuple

        Returns:
            Tuple of (response, error_type, http_status)
        """
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, params=params, timeout=timeout)
                if response.status_code == 200:
                    return response, None, 200
                elif response.status_code in [429, 503]:
                    # Rate limit or service unavailable - retry with backoff
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(backoff)
                        backoff = min(backoff * 2, MAX_BACKOFF)
                        continue
                    return response, "http_error", response.status_code
                else:
                    return response, "http_error", response.status_code
            except requests.exceptions.Timeout:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, "timeout", None
            except Exception as e:
                logger.warning(
                    "Unexpected error in OpenAQ request",
                    error=str(e),
                    attempt=attempt + 1,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, "other", None

        return None, "other", None

    def fetch_air_quality(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: int = 50,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch air quality measurements for a location.

        Args:
            latitude: Latitude coordinate (optional, for location-based queries)
            longitude: Longitude coordinate (optional, for location-based queries)
            radius_km: Search radius in kilometers (default: 50)
            days_back: Number of days of historical data (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            Tuple of (DataFrame with columns: ['timestamp', 'pm25', 'pm10', 'aqi'], SourceStatus)
            DataFrame is empty if no data available or on error
        """
        # CI offline mode: return synthetic deterministic data
        if is_ci_offline_mode():
            logger.info("Using CI offline mode for air quality data")
            df = get_ci_air_quality_data()
            if df is not None and not df.empty:
                status = SourceStatus(
                    provider="CI_Synthetic_OpenAQ",
                    ok=True,
                    http_status=200,
                    fetched_at=datetime.now().isoformat(),
                    rows=len(df),
                    query_window_days=days_back,
                )
                self.last_status = status
                return df, status

        cache_key = f"openaq_{latitude}_{longitude}_{radius_km}_{days_back}"
        now = datetime.now()

        # Check cache
        if use_cache and cache_key in self._cache:
            cached_df, cached_time = self._cache[cache_key]
            if (now - cached_time).total_seconds() < (
                self.cache_duration_minutes * 60
            ):
                logger.debug("Using cached OpenAQ data", cache_key=cache_key)
                status = SourceStatus(
                    provider="OpenAQ_Cached",
                    ok=True,
                    http_status=200,
                    fetched_at=cached_time.isoformat(),
                    rows=len(cached_df),
                    query_window_days=days_back,
                )
                self.last_status = status
                return cached_df, status

        try:
            # OpenAQ v2 API: /measurements endpoint for historical data
            # Note: v2 is deprecated but still functional; consider migrating to v3 in future
            url = f"{OPENAQ_API_BASE}/measurements"
            params = {
                "limit": 10000,  # Max allowed per request
                "parameter": "pm25,pm10",  # Focus on PM2.5 and PM10
            }

            if latitude is not None and longitude is not None:
                params["coordinates"] = f"{latitude},{longitude}"
                params["radius"] = radius_km * 1000  # Convert km to meters

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            params["date_from"] = start_date.isoformat() + "Z"
            params["date_to"] = end_date.isoformat() + "Z"

            logger.info(
                "Fetching OpenAQ air quality data",
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                days_back=days_back,
            )

            response, error_type, http_status = self._make_request_with_retries(
                url, params
            )

            if response is None or error_type:
                status = SourceStatus(
                    provider="OpenAQ",
                    ok=False,
                    http_status=http_status,
                    error_type=error_type or "unknown",
                    error_detail=f"Request failed: {error_type}",
                    fetched_at=datetime.now().isoformat(),
                    rows=0,
                    query_window_days=days_back,
                )
                self.last_status = status
                return pd.DataFrame(), status

            if http_status != 200:
                status = SourceStatus(
                    provider="OpenAQ",
                    ok=False,
                    http_status=http_status,
                    error_type="http_error",
                    error_detail=f"HTTP {http_status}",
                    fetched_at=datetime.now().isoformat(),
                    rows=0,
                    query_window_days=days_back,
                )
                self.last_status = status
                return pd.DataFrame(), status

            # Parse response
            data = response.json()
            results = data.get("results", [])

            if not results:
                logger.warning("No results in OpenAQ response")
                status = SourceStatus(
                    provider="OpenAQ",
                    ok=True,
                    http_status=200,
                    fetched_at=datetime.now().isoformat(),
                    rows=0,
                    query_window_days=days_back,
                )
                self.last_status = status
                return pd.DataFrame(), status

            # Transform to DataFrame
            # OpenAQ v2 /measurements returns flat list of measurement objects
            records = []
            for result in results:
                param = result.get("parameter")
                value = result.get("value")
                # OpenAQ v2 uses date.utc or date.local
                date_obj = result.get("date", {})
                date_utc = date_obj.get("utc") or date_obj.get("local")

                if date_utc and value is not None and param in ["pm25", "pm10"]:
                    records.append(
                        {
                            "timestamp": pd.to_datetime(date_utc),
                            "parameter": param,
                            "value": float(value),
                        }
                    )

            if not records:
                status = SourceStatus(
                    provider="OpenAQ",
                    ok=True,
                    http_status=200,
                    fetched_at=datetime.now().isoformat(),
                    rows=0,
                    query_window_days=days_back,
                )
                self.last_status = status
                return pd.DataFrame(), status

            df = pd.DataFrame(records)

            # Pivot to have pm25, pm10 as columns (group by timestamp, average values)
            if len(df) > 0:
                df_pivot = df.pivot_table(
                    index="timestamp",
                    columns="parameter",
                    values="value",
                    aggfunc="mean",
                ).reset_index()

                # Ensure pm25 and pm10 columns exist
                if "pm25" not in df_pivot.columns:
                    df_pivot["pm25"] = 0.0
                if "pm10" not in df_pivot.columns:
                    df_pivot["pm10"] = 0.0

                # Calculate AQI (simplified - using PM2.5 as primary)
                # US EPA AQI formula for PM2.5
                pm25 = df_pivot["pm25"].fillna(0.0)
                df_pivot["aqi"] = pd.cut(
                    pm25,
                    bins=[0, 12, 35.4, 55.4, 150.4, 250.4, float("inf")],
                    labels=[50, 100, 150, 200, 300, 400],
                    include_lowest=True,
                ).astype(float).fillna(50.0)  # Default to 50 (good) if out of range
            else:
                df_pivot = pd.DataFrame(columns=["timestamp", "pm25", "pm10", "aqi"])

            # Sort by timestamp
            df_pivot = df_pivot.sort_values("timestamp").reset_index(drop=True)

            # Filter to requested date range
            df_pivot = df_pivot[
                (df_pivot["timestamp"] >= start_date) & (df_pivot["timestamp"] <= end_date)
            ]

            # Cache result
            self._cache[cache_key] = (df_pivot, now)

            status = SourceStatus(
                provider="OpenAQ",
                ok=True,
                http_status=200,
                fetched_at=datetime.now().isoformat(),
                rows=len(df_pivot),
                query_window_days=days_back,
            )
            self.last_status = status

            logger.info(
                "Successfully fetched OpenAQ data",
                rows=len(df_pivot),
                parameters=list(df_pivot.columns),
            )

            return df_pivot, status

        except Exception as e:
            logger.error(
                "Error fetching OpenAQ air quality data",
                error=str(e),
                exc_info=True,
            )
            status = SourceStatus(
                provider="OpenAQ",
                ok=False,
                error_type="other",
                error_detail=str(e),
                fetched_at=datetime.now().isoformat(),
                rows=0,
                query_window_days=days_back,
            )
            self.last_status = status
            return pd.DataFrame(), status
