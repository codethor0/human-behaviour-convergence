# SPDX-LICENSE-IDENTIFIER: PROPRIETARY
"""Search trends data ingestion using public APIs for digital attention analysis."""
import math
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
import requests
import structlog

from app.services.ingestion.gdelt_events import SourceStatus
from app.services.ingestion.ci_offline_data import (
    is_ci_offline_mode,
    get_ci_search_trends_data,
)

logger = structlog.get_logger("ingestion.search_trends")

# Wikimedia Pageviews REST API (no key required)
WIKIMEDIA_PAGEVIEWS_API = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 10.0


class SearchTrendsFetcher:
    """
    Fetch and normalize search trends data representing digital attention.

    Uses public search trends APIs to calculate normalized search interest
    scores (0.0-1.0) where high scores indicate high digital attention.
    """

    def __init__(self, cache_duration_minutes: int = 60):
        """
        Initialize the search trends fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses
                (default: 60 minutes)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

    def _make_request_with_retries(
        self, url: str, timeout: Tuple[float, float] = (10.0, 30.0)
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
                            "Wikimedia API returned non-200 status, retrying",
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
                        "Wikimedia API timeout, retrying", attempt=attempt + 1
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, error_type, None
            except requests.exceptions.RequestException as e:
                error_type = "http_error"
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "Wikimedia API request exception, retrying", error=str(e)[:100]
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, error_type, None
            except Exception as e:
                error_type = "other"
                logger.error(
                    "Unexpected error in Wikimedia request",
                    error=str(e)[:200],
                    exc_info=True,
                )
                return None, error_type, None

        return None, "other", None

    def _get_region_keywords(self, region_name: Optional[str]) -> list[str]:
        """Get curated keyword set for a region."""
        if not region_name:
            return ["United_States", "Immigration", "Protest"]

        region_lower = region_name.lower()
        keywords = []

        # Add region-specific keywords
        if "minnesota" in region_lower or "minneapolis" in region_lower:
            keywords.extend(["Minnesota", "Minneapolis", "Immigration_Minnesota"])
        elif "new york" in region_lower or "nyc" in region_lower:
            keywords.extend(
                ["New_York_City", "New_York_(state)", "Immigration_New_York"]
            )
        else:
            # Generic fallback
            state_name = region_name.replace(" ", "_")
            keywords.append(state_name)

        # Add generic attention keywords
        keywords.extend(["Immigration", "Protest", "Policy"])

        return keywords[:5]  # Limit to 5 keywords

    def fetch_search_interest(
        self,
        query: str,
        days_back: int = 30,
        use_cache: bool = True,
        region_name: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch search interest time-series data using Wikipedia Pageviews (no-key public API).

        Args:
            query: Search query or topic (used for keyword selection if region_name not provided)
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)
            region_name: Optional region name to derive region-specific keywords

        Returns:
            Tuple of (DataFrame, SourceStatus)
            DataFrame columns: ['timestamp', 'search_attention_index']
            search_attention_index is normalized to 0.0-1.0 where 1.0 = maximum attention
        """
        # CI offline mode: return synthetic deterministic data
        if is_ci_offline_mode():
            logger.info("Using CI offline mode for search trends data")
            df = get_ci_search_trends_data(region_name or query)
            df = df.rename(columns={"value": "search_attention_index"})
            df_limited = df.tail(days_back).copy()
            status = SourceStatus(
                provider="CI_Synthetic_SearchTrends",
                ok=True,
                http_status=200,
                fetched_at=datetime.now().isoformat(),
                rows=len(df_limited),
                query_window_days=days_back,
            )
            return df_limited, status

        fetched_at = datetime.now().isoformat()
        cache_key = f"search_trends_{region_name or query}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached search trends data", age_minutes=age_minutes)
                status = SourceStatus(
                    provider="Wikimedia Pageviews",
                    ok=True,
                    http_status=200,
                    fetched_at=fetched_at,
                    rows=len(df),
                    query_window_days=days_back,
                )
                return df.copy(), status

        # Get region-specific keywords
        keywords = (
            self._get_region_keywords(region_name)
            if region_name
            else [query.replace(" ", "_")]
        )

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        logger.info(
            "Fetching search trends via Wikipedia Pageviews",
            keywords=keywords,
            days_back=days_back,
        )

        # Aggregate pageviews across keywords by date
        pageviews_by_date = {}

        for keyword in keywords:
            try:
                # Wikimedia Pageviews API: /per-article/{project}/{access}/{agent}/{article}/{granularity}/{start}/{end}
                # project: en.wikipedia (English Wikipedia)
                # access: all-access (desktop + mobile)
                # agent: all-agents (user + bot)
                # article: URL-encoded article title
                # granularity: daily
                url = f"{WIKIMEDIA_PAGEVIEWS_API}/en.wikipedia/all-access/all-agents/{keyword}/daily/{start_str}/{end_str}"

                # Make request with retries
                response, request_error_type, http_status = (
                    self._make_request_with_retries(url)
                )

                if response is None:
                    logger.warning(
                        f"Failed to fetch pageviews for {keyword}",
                        error_type=request_error_type,
                    )
                    continue

                # Parse JSON
                try:
                    data = response.json()
                except Exception as e:
                    logger.warning(
                        f"JSON decode failed for {keyword}", error=str(e)[:100]
                    )
                    continue

                # API returns: {"items": [{"timestamp": "2024010100", "views": 1234}, ...]}
                items = data.get("items", [])
                for item in items:
                    timestamp_str = item.get("timestamp", "")
                    views = item.get("views", 0)

                    if timestamp_str and len(timestamp_str) >= 8:
                        # Parse YYYYMMDD format
                        try:
                            date_obj = datetime.strptime(
                                timestamp_str[:8], "%Y%m%d"
                            ).date()
                            if start_date.date() <= date_obj <= end_date.date():
                                pageviews_by_date[date_obj] = (
                                    pageviews_by_date.get(date_obj, 0) + views
                                )
                        except ValueError:
                            continue

            except Exception as e:
                logger.warning(
                    f"Error fetching pageviews for {keyword}", error=str(e)[:100]
                )
                continue

        if not pageviews_by_date:
            # No pageviews is valid (ok=true, rows=0)
            status = SourceStatus(
                provider="Wikimedia Pageviews",
                ok=True,
                http_status=200,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("No Wikipedia pageviews found in query window")
            return pd.DataFrame(columns=["timestamp", "search_attention_index"]), status

        # Create DataFrame with date, total views, and normalized attention index
        # Use saturating normalization: attention = min(1.0, log(1 + views) / K)
        # K=10 gives reasonable scaling: log(1+100)/10 ≈ 0.46, log(1+1000)/10 ≈ 0.69, log(1+10000)/10 ≈ 0.92
        K = 10.0
        records = []
        for date, total_views in pageviews_by_date.items():
            search_attention_index = min(1.0, math.log(1 + total_views) / K)
            records.append(
                {
                    "timestamp": datetime.combine(date, datetime.min.time()),
                    "search_attention_index": search_attention_index,
                }
            )

        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Cache result
        self._cache[cache_key] = (df.copy(), datetime.now())

        status = SourceStatus(
            provider="Wikimedia Pageviews",
            ok=True,
            http_status=200,
            fetched_at=fetched_at,
            rows=len(df),
            query_window_days=days_back,
        )

        logger.info(
            "Successfully fetched search trends data",
            rows=len(df),
            keywords=keywords,
        )

        return df, status
