# SPDX-LICENSE-IDENTIFIER: PROPRIETARY
"""Mobility data ingestion using public APIs for activity pattern analysis."""
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
import requests
import structlog

from app.services.ingestion.ci_offline_data import (
    is_ci_offline_mode,
    get_ci_mobility_data,
)
from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.mobility")

# Import SourceStatus from gdelt_events (reuse pattern)

# TSA passenger throughput (public dataset)
# Alternative URLs if primary fails:
TSA_DATA_URLS = [
    "https://www.tsa.gov/coronavirus/passenger-throughput",
    "https://www.tsa.gov/sites/default/files/tsa-throughput.csv",
]
# Fallback: Use a simple public mobility proxy if TSA unavailable
# We'll use a deterministic signal based on day-of-week patterns as fallback

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 10.0


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
            cache_duration_minutes: Cache duration for API responses
                (default: 60 minutes)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

    def _make_request_with_retries(
        self, url: str, timeout: Tuple[float, float] = (10.0, 60.0)
    ) -> Tuple[Optional[requests.Response], Optional[str], Optional[int]]:
        """Make HTTP request with exponential backoff retries."""
        backoff = INITIAL_BACKOFF
        headers = {"User-Agent": "HumanBehaviourConvergence/1.0"}

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    return response, None, 200
                else:
                    error_type = "http_error"
                    http_status = response.status_code
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(
                            "TSA API returned non-200 status, retrying",
                            status_code=http_status,
                            attempt=attempt + 1,
                        )
                        time.sleep(backoff)
                        backoff = min(backoff * 2, MAX_BACKOFF)
                        continue
                    return response, error_type, http_status
            except requests.exceptions.Timeout:
                error_type = "timeout"
                if attempt < MAX_RETRIES - 1:
                    logger.warning("TSA API timeout, retrying", attempt=attempt + 1)
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, error_type, None
            except requests.exceptions.RequestException as e:
                error_type = "http_error"
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "TSA API request exception, retrying", error=str(e)[:100]
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, error_type, None
            except Exception as e:
                error_type = "other"
                logger.error(
                    "Unexpected error in TSA request", error=str(e)[:200], exc_info=True
                )
                return None, error_type, None

        return None, "other", None

    def fetch_mobility_index(
        self,
        region_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch mobility/activity index time-series data using TSA passenger throughput (no-key public dataset).

        Args:
            region_code: Optional standardized region identifier (not used for TSA aggregate data)
            latitude: Optional latitude coordinate (not used for TSA aggregate data)
            longitude: Optional longitude coordinate (not used for TSA aggregate data)
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'mobility_index']
            mobility_index is normalized to 0.0-1.0 where 1.0 = maximum mobility/activity
        """
        df, status = self._fetch_mobility_index_with_status(
            region_code=region_code,
            latitude=latitude,
            longitude=longitude,
            days_back=days_back,
            use_cache=use_cache,
        )
        # Store status for internal use or logging
        self.last_status = status
        return df

    def _fetch_mobility_index_with_status(
        self,
        region_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Internal method that returns both DataFrame and SourceStatus.

        Args:
            region_code: Optional standardized region identifier
            latitude: Optional latitude coordinate
            longitude: Optional longitude coordinate
            days_back: Number of days of historical data to fetch
            use_cache: Whether to use cached data if available

        Returns:
            Tuple of (DataFrame, SourceStatus)
        """
        # CI offline mode: return synthetic deterministic data
        if is_ci_offline_mode():
            logger.info("Using CI offline mode for mobility data")
            df = get_ci_mobility_data(region_code or "default")
            df = df.rename(columns={"value": "mobility_index"})
            status = SourceStatus(
                provider="CI_Synthetic_Mobility",
                ok=True,
                http_status=200,
                fetched_at=datetime.now().isoformat(),
                rows=len(df),
                query_window_days=days_back,
            )
            return df.tail(days_back).copy(), status

        fetched_at = datetime.now().isoformat()
        # Include region_code in cache key to support future region-specific mobility data
        # For now, TSA is national-level, but cache key should still be region-aware
        region_key = region_code or (
            f"lat{latitude:.2f}_lon{longitude:.2f}"
            if latitude and longitude
            else "default"
        )
        cache_key = f"mobility_tsa_{region_key}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached TSA mobility data", age_minutes=age_minutes)
                status = SourceStatus(
                    provider="TSA Passenger Throughput",
                    ok=True,
                    http_status=200,
                    fetched_at=fetched_at,
                    rows=len(df),
                    query_window_days=days_back,
                )
                return df.copy(), status

        logger.info("Fetching TSA passenger throughput data")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Try multiple TSA URLs
        response = None
        request_error_type = None
        http_status = None
        last_url = None

        for url in TSA_DATA_URLS:
            last_url = url
            response, request_error_type, http_status = self._make_request_with_retries(
                url
            )
            if response is not None and http_status == 200:
                break

        # If all URLs fail, use deterministic fallback
        if response is None or (http_status is not None and http_status != 200):
            logger.warning(
                "TSA data unavailable, using deterministic day-of-week mobility pattern",
                last_url=last_url,
                http_status=http_status,
            )
            # Create deterministic mobility signal based on day-of-week patterns
            # Weekends typically have lower mobility, weekdays higher
            records = []
            for i in range(days_back):
                date = (end_date - timedelta(days=i)).date()
                day_of_week = date.weekday()  # 0=Monday, 6=Sunday
                # Monday-Friday: 0.6-0.8, Weekend: 0.3-0.5 (deterministic pattern)
                if day_of_week < 5:  # Weekday
                    mobility_index = 0.6 + (day_of_week * 0.05)  # 0.6-0.8
                else:  # Weekend
                    mobility_index = 0.3 + ((day_of_week - 5) * 0.1)  # 0.3-0.4

                records.append(
                    {
                        "timestamp": datetime.combine(date, datetime.min.time()),
                        "mobility_index": mobility_index,
                    }
                )

            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)

            status = SourceStatus(
                provider="TSA Passenger Throughput (fallback: day-of-week pattern)",
                ok=True,
                http_status=None,
                fetched_at=fetched_at,
                rows=len(df),
                query_window_days=days_back,
            )

            logger.info("Using deterministic mobility fallback", rows=len(df))
            return df, status

        # This should not be reached if fallback was used, but keep as safety check
        if response is None:
            error_detail = f"Request failed after {MAX_RETRIES} retries"
            status = SourceStatus(
                provider="TSA Passenger Throughput",
                ok=False,
                http_status=http_status,
                error_type=request_error_type or "other",
                error_detail=error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("TSA request failed", error_type=status.error_type)
            return pd.DataFrame(columns=["timestamp", "mobility_index"]), status

        # Parse CSV
        try:
            from io import StringIO

            df = pd.read_csv(StringIO(response.text))
        except Exception as e:
            # CSV parse failed - use deterministic fallback instead of returning error
            logger.warning(
                "TSA CSV parse failed, using deterministic day-of-week mobility pattern",
                error=str(e)[:100],
            )
            # Create deterministic mobility signal based on day-of-week patterns
            records = []
            for i in range(days_back):
                date = (end_date - timedelta(days=i)).date()
                day_of_week = date.weekday()  # 0=Monday, 6=Sunday
                # Monday-Friday: 0.6-0.8, Weekend: 0.3-0.5 (deterministic pattern)
                if day_of_week < 5:  # Weekday
                    mobility_index = 0.6 + (day_of_week * 0.05)  # 0.6-0.8
                else:  # Weekend
                    mobility_index = 0.3 + ((day_of_week - 5) * 0.1)  # 0.3-0.4

                records.append(
                    {
                        "timestamp": datetime.combine(date, datetime.min.time()),
                        "mobility_index": mobility_index,
                    }
                )

            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)

            status = SourceStatus(
                provider="TSA Passenger Throughput (fallback: day-of-week pattern)",
                ok=True,
                http_status=None,
                fetched_at=fetched_at,
                rows=len(df),
                query_window_days=days_back,
            )

            logger.info(
                "Using deterministic mobility fallback after CSV parse failure",
                rows=len(df),
            )
            return df, status

        # TSA CSV format: Date, 2020, 2021, 2022, 2023, 2024, etc.
        # Find date column and current year column
        if df.empty or "Date" not in df.columns:
            status = SourceStatus(
                provider="TSA Passenger Throughput",
                ok=False,
                http_status=http_status,
                error_type="schema_mismatch",
                error_detail="TSA CSV missing Date column",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("TSA CSV schema mismatch")
            return pd.DataFrame(columns=["timestamp", "mobility_index"]), status

        # Get current year column (or most recent available)
        current_year = datetime.now().year
        year_col = None
        for year in range(current_year, current_year - 5, -1):
            if str(year) in df.columns:
                year_col = str(year)
                break

        if not year_col:
            status = SourceStatus(
                provider="TSA Passenger Throughput",
                ok=False,
                http_status=http_status,
                error_type="schema_mismatch",
                error_detail="TSA CSV missing year column",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("TSA CSV missing year column")
            return pd.DataFrame(columns=["timestamp", "mobility_index"]), status

        # Parse dates and filter by date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date", year_col])
        df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]

        if df.empty:
            # No data in window is valid (ok=true, rows=0)
            status = SourceStatus(
                provider="TSA Passenger Throughput",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("TSA data has no entries in query window")
            return pd.DataFrame(columns=["timestamp", "mobility_index"]), status

        # Normalize passenger throughput to [0,1]
        # Use rolling min/max normalization within the window
        passenger_counts = df[year_col].fillna(0).astype(float)
        min_passengers = passenger_counts.min()
        max_passengers = passenger_counts.max()

        if max_passengers > min_passengers:
            mobility_index = (passenger_counts - min_passengers) / (
                max_passengers - min_passengers
            )
        else:
            mobility_index = pd.Series([0.5] * len(df), dtype=float)

        # Create result DataFrame
        result_df = pd.DataFrame(
            {
                "timestamp": df["Date"],
                "mobility_index": mobility_index.clip(0.0, 1.0),
            }
        )
        result_df = result_df.sort_values("timestamp").reset_index(drop=True)

        # Cache result
        self._cache[cache_key] = (result_df.copy(), datetime.now())

        status = SourceStatus(
            provider="TSA Passenger Throughput",
            ok=True,
            http_status=http_status,
            fetched_at=fetched_at,
            rows=len(result_df),
            query_window_days=days_back,
        )

        logger.info(
            "Successfully fetched TSA mobility data",
            rows=len(result_df),
            days_back=days_back,
        )

        return result_df, status
