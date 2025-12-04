# SPDX-License-Identifier: PROPRIETARY
"""GDELT Events API connector for global event and crisis signals."""
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests
import structlog

logger = structlog.get_logger("ingestion.gdelt_events")

# GDELT API base URL
GDELT_API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTEventsFetcher:
    """
    Fetch global event and crisis signals from GDELT Events API.

    GDELT (Global Database of Events, Language, and Tone) provides
    real-time monitoring of global news and events.

    No authentication required for basic queries.
    Rate limits: Generous free tier (no documented strict limits)

    Source: https://www.gdeltproject.org/
    API Docs: https://blog.gdeltproject.org/gdelt-2-0-api-debuts/
    """

    def __init__(self, cache_duration_minutes: int = 60):
        """
        Initialize GDELT events fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses
                (default: 60 minutes)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

    def fetch_event_tone(
        self,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch average media tone score from GDELT.

        Tone score ranges from -100 (extremely negative) to +100 (extremely positive).
        We normalize to [0.0, 1.0] where 1.0 = maximum negative tone (crisis/stress).

        Args:
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'tone_score']
            Returns empty DataFrame on error
        """
        cache_key = f"gdelt_tone_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached GDELT tone data")
                return df.copy()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        try:
            # GDELT query for average tone by date
            # Using GDELT 2.0 API format
            query = (
                f"mode=timelinetone&format=json&timespan=1d&"
                f"startdatetime={start_date.strftime('%Y%m%d%H%M%S')}&"
                f"enddatetime={end_date.strftime('%Y%m%d%H%M%S')}"
            )

            logger.info("Fetching GDELT tone data", days_back=days_back)
            url = f"{GDELT_API_BASE}?{query}"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Parse timeline data
            if "timeline" not in data or not data["timeline"]:
                logger.warning("No timeline data in GDELT response")
                return pd.DataFrame(columns=["timestamp", "tone_score"])

            timeline = data["timeline"]
            records = []

            for entry in timeline:
                date_str = entry.get("datetime")
                tone = entry.get("tone")

                if date_str is None or tone is None:
                    continue

                try:
                    # Parse date (format: YYYYMMDDHHMMSS)
                    date_obj = datetime.strptime(date_str[:8], "%Y%m%d")
                    records.append({"timestamp": date_obj, "tone": float(tone)})
                except (ValueError, TypeError) as e:
                    logger.debug(
                        "Skipping invalid entry",
                        date=date_str,
                        tone=tone,
                        error=str(e),
                    )
                    continue

            if not records:
                logger.warning("No valid entries after parsing GDELT data")
                return pd.DataFrame(columns=["timestamp", "tone_score"])

            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Normalize tone to [0.0, 1.0]
            # Tone ranges from -100 to +100
            # We want: negative tone (crisis) = high value (1.0)
            # So: normalize to [0, 1] then invert
            min_tone = df["tone"].min()
            max_tone = df["tone"].max()

            if max_tone > min_tone:
                # Map tone to [0, 1] where -100 -> 1.0 (high stress),
                # +100 -> 0.0 (low stress)
                # Formula: 1.0 - ((tone - (-100)) / (100 - (-100)))
                # This maps -100 to 1.0 and +100 to 0.0
                df["tone_score"] = 1.0 - ((df["tone"] - (-100)) / (100 - (-100)))
                df["tone_score"] = df["tone_score"].clip(0.0, 1.0)
            else:
                # All same tone, default to neutral
                df["tone_score"] = 0.5

            df = (
                df[["timestamp", "tone_score"]]
                .sort_values("timestamp")
                .reset_index(drop=True)
            )

            # Cache result
            self._cache[cache_key] = (df.copy(), datetime.now())

            logger.info(
                "Successfully fetched GDELT tone data",
                rows=len(df),
                date_range=(df["timestamp"].min(), df["timestamp"].max()),
            )

            return df

        except requests.exceptions.RequestException as e:
            logger.error(
                "Error fetching GDELT data",
                error=str(e),
                exc_info=True,
            )
            return pd.DataFrame(columns=["timestamp", "tone_score"])

        except Exception as e:
            logger.error(
                "Unexpected error fetching GDELT data",
                error=str(e),
                exc_info=True,
            )
            return pd.DataFrame(columns=["timestamp", "tone_score"])

    def fetch_event_count(
        self,
        days_back: int = 30,
        event_type: str = "all",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch daily event counts from GDELT.

        Args:
            days_back: Number of days of historical data to fetch (default: 30)
            event_type: Event type filter ('all', 'conflict', 'protest', etc.)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'event_count']
            Returns empty DataFrame on error
        """
        cache_key = f"gdelt_events_{days_back}_{event_type}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached GDELT event count data")
                return df.copy()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        try:
            # GDELT query for event counts by date
            # Using simplified query (GDELT API can be complex)
            query = (
                f"mode=timelinevol&format=json&timespan=1d&"
                f"startdatetime={start_date.strftime('%Y%m%d%H%M%S')}&"
                f"enddatetime={end_date.strftime('%Y%m%d%H%M%S')}"
            )

            logger.info(
                "Fetching GDELT event count data",
                days_back=days_back,
                event_type=event_type,
            )
            url = f"{GDELT_API_BASE}?{query}"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Parse timeline data
            if "timeline" not in data or not data["timeline"]:
                logger.warning("No timeline data in GDELT response")
                return pd.DataFrame(columns=["timestamp", "event_count"])

            timeline = data["timeline"]
            records = []

            for entry in timeline:
                date_str = entry.get("datetime")
                volume = entry.get("volume")

                if date_str is None or volume is None:
                    continue

                try:
                    # Parse date
                    date_obj = datetime.strptime(date_str[:8], "%Y%m%d")
                    records.append({"timestamp": date_obj, "event_count": int(volume)})
                except (ValueError, TypeError) as e:
                    logger.debug(
                        "Skipping invalid entry",
                        date=date_str,
                        volume=volume,
                        error=str(e),
                    )
                    continue

            if not records:
                logger.warning("No valid entries after parsing GDELT data")
                return pd.DataFrame(columns=["timestamp", "event_count"])

            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Normalize event count to [0.0, 1.0]
            min_count = df["event_count"].min()
            max_count = df["event_count"].max()

            if max_count > min_count:
                df["event_count_normalized"] = (df["event_count"] - min_count) / (
                    max_count - min_count
                )
            else:
                df["event_count_normalized"] = 0.5

            # Keep both raw and normalized
            df = (
                df[["timestamp", "event_count", "event_count_normalized"]]
                .sort_values("timestamp")
                .reset_index(drop=True)
            )

            # Cache result
            self._cache[cache_key] = (df.copy(), datetime.now())

            logger.info(
                "Successfully fetched GDELT event count data",
                rows=len(df),
                date_range=(df["timestamp"].min(), df["timestamp"].max()),
            )

            return df

        except requests.exceptions.RequestException as e:
            logger.error(
                "Error fetching GDELT event count data",
                error=str(e),
                exc_info=True,
            )
            return pd.DataFrame(columns=["timestamp", "event_count"])

        except Exception as e:
            logger.error(
                "Unexpected error fetching GDELT event count data",
                error=str(e),
                exc_info=True,
            )
            return pd.DataFrame(columns=["timestamp", "event_count"])
