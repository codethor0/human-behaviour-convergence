# SPDX-License-Identifier: PROPRIETARY
"""Search trends data ingestion using public APIs for digital attention analysis."""
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests_cache
import structlog

logger = structlog.get_logger("ingestion.search_trends")


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
            cache_duration_minutes: Cache duration for API responses (default: 60 minutes)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: Optional[pd.DataFrame] = None
        self._cache_key: Optional[str] = None
        self._cache_timestamp: Optional[datetime] = None

        # Setup requests session with caching
        self.session = requests_cache.CachedSession(
            ".cache/search_trends_cache",
            expire_after=timedelta(minutes=cache_duration_minutes),
        )

    def fetch_search_interest(
        self, query: str, days_back: int = 30, use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch search interest time-series data for a given query.

        Args:
            query: Search query or topic (generic, not vendor-specific)
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'search_interest_score']
            search_interest_score is normalized to 0.0-1.0 where 1.0 = maximum interest
        """
        # Check cache validity
        cache_key = f"{query},{days_back}"
        if (
            use_cache
            and self._cache is not None
            and self._cache_key == cache_key
            and self._cache_timestamp is not None
        ):
            age_minutes = (datetime.now() - self._cache_timestamp).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info(
                    "Using cached search trends data",
                    age_minutes=age_minutes,
                    query=query,
                )
                return self._cache.copy()

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            logger.info(
                "Fetching search trends data",
                query=query,
                start_date=start_date.date().isoformat(),
                end_date=end_date.date().isoformat(),
            )

            # Placeholder implementation using public search trends API
            # This is a generic abstraction that can be configured via environment variables
            api_endpoint = os.getenv("SEARCH_TRENDS_API_ENDPOINT", "")
            api_key = os.getenv("SEARCH_TRENDS_API_KEY", "")

            if not api_endpoint or not api_key:
                logger.warning(
                    "Search trends API not configured, returning empty DataFrame",
                    query=query,
                )
                # Return empty DataFrame with correct structure
                return pd.DataFrame(
                    columns=["timestamp", "search_interest_score"],
                    dtype=float,
                )

            # Make API request (placeholder - replace with actual API call)
            # This is a generic structure that can work with various search trends APIs
            response = self.session.get(
                api_endpoint,
                params={
                    "query": query,
                    "start_date": start_date.date().isoformat(),
                    "end_date": end_date.date().isoformat(),
                    "api_key": api_key,
                },
                timeout=30,
            )
            response.raise_for_status()

            # Parse response (placeholder - adapt to actual API format)
            data = response.json()

            # Transform to DataFrame (adapt based on actual API response format)
            if "data" in data and len(data["data"]) > 0:
                df = pd.DataFrame(data["data"])
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp").reset_index(drop=True)

                # Normalize search_interest_score to [0.0, 1.0]
                if "interest" in df.columns:
                    max_interest = df["interest"].max() if len(df) > 0 else 1.0
                    if max_interest > 0:
                        df["search_interest_score"] = df["interest"] / max_interest
                    else:
                        df["search_interest_score"] = 0.0
                else:
                    df["search_interest_score"] = 0.5  # Default neutral score

                # Ensure search_interest_score is in [0.0, 1.0]
                df["search_interest_score"] = df["search_interest_score"].clip(0.0, 1.0)

                # Select only required columns
                result = df[["timestamp", "search_interest_score"]].copy()

                # Update cache
                self._cache = result.copy()
                self._cache_key = cache_key
                self._cache_timestamp = datetime.now()

                logger.info(
                    "Successfully fetched search trends data",
                    query=query,
                    rows=len(result),
                )
                return result
            else:
                logger.warning("No search trends data returned", query=query)
                return pd.DataFrame(
                    columns=["timestamp", "search_interest_score"],
                    dtype=float,
                )

        except Exception as e:
            logger.error(
                "Error fetching search trends data",
                query=query,
                error=str(e),
                exc_info=True,
            )
            # Return empty DataFrame with correct structure
            return pd.DataFrame(
                columns=["timestamp", "search_interest_score"],
                dtype=float,
            )
