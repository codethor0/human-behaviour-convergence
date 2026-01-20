# SPDX-License-Identifier: PROPRIETARY
"""OpenStates Legislative Activity API connector."""
from datetime import datetime, timedelta
from typing import Optional, Tuple
import math

import os
import pandas as pd
import requests
import structlog
import time

from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.openstates")

# OpenStates API base URL
OPENSTATES_API_BASE = "https://v3.openstates.org"

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 10.0


class OpenStatesLegislativeFetcher:
    """
    Fetch legislative activity from OpenStates API.

    OpenStates provides state-level legislative data (bills, events, votes).

    Requires OPENSTATES_API_KEY environment variable.
    Rate limits: Varies by tier (free tier available)

    Source: https://openstates.org/
    API Docs: https://docs.openstates.org/
    """

    def __init__(self, cache_duration_minutes: int = 60):
        """
        Initialize OpenStates fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses
                (default: 60 minutes)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}
        self.api_key = os.getenv("OPENSTATES_API_KEY")

    def _make_request_with_retries(
        self, url: str, headers: dict, timeout: Tuple[float, float] = (10.0, 30.0)
    ) -> Tuple[Optional[requests.Response], Optional[str], Optional[int]]:
        """Make HTTP request with exponential backoff retries."""
        backoff = INITIAL_BACKOFF

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
                            "OpenStates API returned non-200 status, retrying",
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
                    logger.warning(
                        "OpenStates API timeout, retrying", attempt=attempt + 1
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, error_type, None
            except requests.exceptions.RequestException as e:
                error_type = "http_error"
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "OpenStates API request exception, retrying", error=str(e)[:100]
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, error_type, None
            except Exception as e:
                error_type = "other"
                logger.error(
                    "Unexpected error in OpenStates request",
                    error=str(e)[:200],
                    exc_info=True,
                )
                return None, error_type, None

        return None, "other", None

    def _map_region_to_state(self, region_name: Optional[str]) -> Optional[str]:
        """Map region name to US state abbreviation for OpenStates API."""
        if not region_name:
            return None

        # Simple mapping - could be extended
        state_map = {
            "minnesota": "mn",
            "new york": "ny",
            "new york city": "ny",  # NYC is in NY state
            "california": "ca",
            "texas": "tx",
            "florida": "fl",
            # Add more as needed
        }

        region_lower = region_name.lower()
        for key, abbrev in state_map.items():
            if key in region_lower:
                return abbrev.upper()

        return None

    def fetch_legislative_activity(
        self,
        region_name: Optional[str] = None,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch legislative activity data from OpenStates.

        Args:
            region_name: Region name (state name, optional)
            days_back: Number of days to look back
            use_cache: Whether to use cached data if available

        Returns:
            Tuple of (DataFrame, SourceStatus)
            DataFrame columns: timestamp, legislative_stress
            Returns empty DataFrame on error, with status.ok=False
        """
        fetched_at = datetime.now().isoformat()
        cache_key = f"openstates_{region_name or 'default'}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached OpenStates data", age_minutes=age_minutes)
                status = SourceStatus(
                    provider="OpenStates",
                    ok=True,
                    http_status=200,
                    fetched_at=fetched_at,
                    rows=len(df),
                    query_window_days=days_back,
                )
                return df.copy(), status

        # Check for API key
        if not self.api_key:
            status = SourceStatus(
                provider="OpenStates",
                ok=False,
                http_status=None,
                error_type="missing_key",
                error_detail="OPENSTATES_API_KEY environment variable not set",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.warning("OpenStates API key not configured")
            return pd.DataFrame(columns=["timestamp", "legislative_stress"]), status

        # Map region to state abbreviation
        state_abbrev = self._map_region_to_state(region_name)

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        try:
            # OpenStates v3 API: bills endpoint
            # Fetch bills updated in the date range
            headers = {"X-API-Key": self.api_key}

            # Build query params
            params = {
                "updated_since": start_date.date().isoformat(),
                "per_page": 50,  # Limit per request
            }
            if state_abbrev:
                params["jurisdiction"] = state_abbrev

            url = f"{OPENSTATES_API_BASE}/bills/"

            logger.info(
                "Fetching OpenStates legislative activity",
                state=state_abbrev,
                days_back=days_back,
            )

            # Make request with retries
            response, request_error_type, http_status = self._make_request_with_retries(
                url, headers=headers
            )

            if response is None:
                error_detail = f"Request failed after {MAX_RETRIES} retries"
                status = SourceStatus(
                    provider="OpenStates",
                    ok=False,
                    http_status=http_status,
                    error_type=request_error_type or "other",
                    error_detail=error_detail,
                    fetched_at=fetched_at,
                    rows=0,
                    query_window_days=days_back,
                )
                logger.error("OpenStates request failed", error_type=status.error_type)
                return pd.DataFrame(columns=["timestamp", "legislative_stress"]), status

            # Parse JSON response
            try:
                data = response.json()
            except Exception as e:
                status = SourceStatus(
                    provider="OpenStates",
                    ok=False,
                    http_status=http_status,
                    error_type="decode_error",
                    error_detail=f"JSON decode error: {str(e)[:100]}",
                    fetched_at=fetched_at,
                    rows=0,
                    query_window_days=days_back,
                )
                logger.error("OpenStates JSON decode failed", error=str(e)[:200])
                return pd.DataFrame(columns=["timestamp", "legislative_stress"]), status

            # OpenStates API returns: {"results": [...], "pagination": {...}}
            bills = data.get("results", [])
            if not bills:
                # No bills in window is valid (ok=true, rows=0)
                status = SourceStatus(
                    provider="OpenStates",
                    ok=True,
                    http_status=http_status,
                    fetched_at=fetched_at,
                    rows=0,
                    query_window_days=days_back,
                )
                logger.info("OpenStates returned no bills in query window")
                return pd.DataFrame(columns=["timestamp", "legislative_stress"]), status

            # Aggregate bills by date
            bill_counts_by_date = {}
            for bill in bills:
                # Use updated_at if available, else created_at
                date_str = bill.get("updated_at", bill.get("created_at", ""))
                if date_str:
                    try:
                        # Parse ISO format datetime
                        bill_date = datetime.fromisoformat(
                            date_str.replace("Z", "+00:00")
                        )
                        if start_date <= bill_date <= end_date:
                            date_key = bill_date.date()
                            bill_counts_by_date[date_key] = (
                                bill_counts_by_date.get(date_key, 0) + 1
                            )
                    except (ValueError, TypeError):
                        continue

            if not bill_counts_by_date:
                # No bills in date range is valid
                status = SourceStatus(
                    provider="OpenStates",
                    ok=True,
                    http_status=http_status,
                    fetched_at=fetched_at,
                    rows=0,
                    query_window_days=days_back,
                )
                logger.info("OpenStates bills found but none in date range")
                return pd.DataFrame(columns=["timestamp", "legislative_stress"]), status

            # Create DataFrame with date, count, and normalized legislative_stress
            # Use saturating normalization: legislative_stress = min(1.0, log(1 + count) / K)
            # K=5 gives reasonable scaling: log(1+1)/5 ≈ 0.14, log(1+10)/5 ≈ 0.46, log(1+50)/5 ≈ 0.78
            K = 5.0
            records = []
            for date, count in bill_counts_by_date.items():
                legislative_stress = min(1.0, math.log(1 + count) / K)
                records.append(
                    {
                        "timestamp": datetime.combine(date, datetime.min.time()),
                        "legislative_stress": legislative_stress,
                    }
                )

            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)

            # Cache result
            self._cache[cache_key] = (df.copy(), datetime.now())

            status = SourceStatus(
                provider="OpenStates",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=len(df),
                query_window_days=days_back,
            )

            logger.info(
                "Successfully fetched OpenStates legislative activity",
                rows=len(df),
                state=state_abbrev,
            )

            return df, status

        except Exception as e:
            status = SourceStatus(
                provider="OpenStates",
                ok=False,
                http_status=None,
                error_type="exception",
                error_detail=f"Unexpected error: {str(e)[:100]}",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("OpenStates fetch error", error=str(e)[:200], exc_info=True)
            return pd.DataFrame(columns=["timestamp", "legislative_stress"]), status
