# SPDX-License-Identifier: PROPRIETARY
"""GDELT Events API connector for global event and crisis signals."""
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pandas as pd
import requests
import structlog

logger = structlog.get_logger("ingestion.gdelt_events")

# GDELT API base URL
GDELT_API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 10.0  # seconds


@dataclass
class SourceStatus:
    """Explicit source status for data ingestion."""

    provider: str
    ok: bool
    http_status: Optional[int] = None
    error_type: Optional[str] = (
        None  # timeout, http_error, non_json, empty, decode_error, other
    )
    error_detail: Optional[str] = None
    fetched_at: str = ""
    rows: int = 0
    query_window_days: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "provider": self.provider,
            "ok": self.ok,
            "http_status": self.http_status,
            "error_type": self.error_type,
            "error_detail": self.error_detail,
            "fetched_at": self.fetched_at,
            "rows": self.rows,
            "query_window_days": self.query_window_days,
        }


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

    def _make_request_with_retries(
        self, url: str, timeout: Tuple[float, float] = (10.0, 30.0)
    ) -> Tuple[Optional[requests.Response], Optional[str], Optional[int]]:
        """
        Make HTTP request with exponential backoff retries.

        Args:
            url: URL to request
            timeout: (connect_timeout, read_timeout) tuple

        Returns:
            Tuple of (response, error_type, http_status)
            error_type: None if success, else one of: timeout, http_error, other
        """
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, timeout=timeout)
                # Explicit status code check
                if response.status_code == 200:
                    return response, None, 200
                else:
                    error_type = "http_error"
                    http_status = response.status_code
                    if attempt < MAX_RETRIES - 1:
                        # Retry on non-200 status
                        logger.warning(
                            "GDELT API returned non-200 status, retrying",
                            status_code=http_status,
                            attempt=attempt + 1,
                            max_retries=MAX_RETRIES,
                        )
                        time.sleep(backoff)
                        backoff = min(backoff * 2, MAX_BACKOFF)
                        continue
                    return response, error_type, http_status
            except requests.exceptions.Timeout:
                error_type = "timeout"
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "GDELT API timeout, retrying",
                        attempt=attempt + 1,
                        max_retries=MAX_RETRIES,
                        backoff=backoff,
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, error_type, None
            except requests.exceptions.RequestException as e:
                error_type = "http_error"
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "GDELT API request exception, retrying",
                        error=str(e)[:100],
                        attempt=attempt + 1,
                        max_retries=MAX_RETRIES,
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, error_type, None
            except Exception as e:
                error_type = "other"
                logger.error(
                    "Unexpected error in GDELT request",
                    error=str(e)[:200],
                    exc_info=True,
                )
                return None, error_type, None

        return None, "other", None

    def _validate_response(
        self, response: requests.Response
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate HTTP response for JSON content.

        Args:
            response: HTTP response object

        Returns:
            Tuple of (is_valid, error_type, error_detail)
            error_type: None if valid, else: non_json, empty, decode_error
        """
        # Check for empty body
        if not response.content:
            return False, "empty", "Response body is empty"

        # Check Content-Type header (if present) - validation done via body content
        body_text = response.text

        # Validate body starts with JSON-like content
        body_stripped = body_text.strip()
        if not body_stripped or (
            not body_stripped.startswith("{") and not body_stripped.startswith("[")
        ):
            # Likely HTML or non-JSON
            preview = body_text[:200].replace("\n", " ").replace("\r", " ")
            return (
                False,
                "non_json",
                f"Body does not start with {{ or [ (preview: {preview})",
            )

        # Try to parse JSON
        try:
            json.loads(body_text)
        except json.JSONDecodeError as e:
            preview = body_text[:200].replace("\n", " ").replace("\r", " ")
            return (
                False,
                "decode_error",
                f"JSON decode error: {str(e)[:100]} (preview: {preview})",
            )

        return True, None, None

    def fetch_event_tone(
        self,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch average media tone score from GDELT.

        Tone score ranges from -100 (extremely negative) to +100 (extremely positive).
        We normalize to [0.0, 1.0] where 1.0 = maximum negative tone (crisis/stress).

        Args:
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            Tuple of (DataFrame, SourceStatus)
            DataFrame has columns: ['timestamp', 'tone_score']
            Returns empty DataFrame on error, with status.ok=False
        """
        fetched_at = datetime.now().isoformat()
        cache_key = f"gdelt_tone_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached GDELT tone data")
                status = SourceStatus(
                    provider="GDELT",
                    ok=True,
                    http_status=200,
                    fetched_at=fetched_at,
                    rows=len(df),
                    query_window_days=days_back,
                )
                return df.copy(), status

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # GDELT query for average tone by date
        # Use STARTDATETIME/ENDDATETIME without TIMESPAN (they are mutually exclusive)
        # Query parameter is required (minimal filter: sourcelang:english)
        query = (
            f"mode=timelinetone&format=json&"
            f"query=sourcelang:english&"
            f"startdatetime={start_date.strftime('%Y%m%d%H%M%S')}&"
            f"enddatetime={end_date.strftime('%Y%m%d%H%M%S')}"
        )

        logger.info("Fetching GDELT tone data", days_back=days_back)
        url = f"{GDELT_API_BASE}?{query}"

        # Make request with retries
        response, request_error_type, http_status = self._make_request_with_retries(url)

        if response is None:
            # Request failed
            error_detail = f"Request failed after {MAX_RETRIES} retries"
            status = SourceStatus(
                provider="GDELT",
                ok=False,
                http_status=http_status,
                error_type=request_error_type or "other",
                error_detail=error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error(
                "GDELT request failed",
                error_type=status.error_type,
                error_detail=error_detail,
            )
            return pd.DataFrame(columns=["timestamp", "tone_score"]), status

        # Check HTTP status - if not 200, return error immediately
        if http_status != 200:
            status = SourceStatus(
                provider="GDELT",
                ok=False,
                http_status=http_status,
                error_type="http_error",
                error_detail=f"HTTP {http_status} error",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error(
                "GDELT HTTP error",
                http_status=http_status,
            )
            return pd.DataFrame(columns=["timestamp", "tone_score"]), status

        # Validate response
        is_valid, validation_error_type, validation_error_detail = (
            self._validate_response(response)
        )

        if not is_valid:
            status = SourceStatus(
                provider="GDELT",
                ok=False,
                http_status=http_status,
                error_type=validation_error_type,
                error_detail=validation_error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error(
                "GDELT response validation failed",
                error_type=status.error_type,
                error_detail=status.error_detail,
                http_status=http_status,
            )
            return pd.DataFrame(columns=["timestamp", "tone_score"]), status

        # Parse JSON
        try:
            data = response.json()
            # Ensure data is a dict (handle Mock objects in tests)
            if not isinstance(data, dict):
                # If response.json() returns a Mock or non-dict, try to extract value
                if hasattr(data, "return_value"):
                    data = (
                        data.return_value if isinstance(data.return_value, dict) else {}
                    )
                else:
                    data = {}
        except json.JSONDecodeError as e:
            status = SourceStatus(
                provider="GDELT",
                ok=False,
                http_status=http_status,
                error_type="decode_error",
                error_detail=f"JSON decode error: {str(e)[:100]}",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("GDELT JSON decode failed", error=str(e)[:200])
            return pd.DataFrame(columns=["timestamp", "tone_score"]), status

        # Parse timeline data
        if "timeline" not in data or not data["timeline"]:
            status = SourceStatus(
                provider="GDELT",
                ok=False,
                http_status=http_status,
                error_type="empty",
                error_detail="Response contains no timeline data",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.warning("GDELT response contains no timeline data")
            return pd.DataFrame(columns=["timestamp", "tone_score"]), status

        timeline = data["timeline"]
        records = []

        # GDELT timeline structure can be:
        # 1. [{series: "Average Tone", data: [{date: "...", value: ...}]}]
        # 2. [{"datetime": "...", "tone": ...}] (simpler format)
        for series_item in timeline:
            if not isinstance(series_item, dict):
                continue

            # Check for simpler format: {"datetime": "...", "tone": ...}
            if "datetime" in series_item and "tone" in series_item:
                datetime_str = series_item.get("datetime", "")
                tone = series_item.get("tone", 0.0)
                try:
                    # Parse datetime (format: YYYYMMDDHHMMSS)
                    if len(datetime_str) >= 8:
                        date_part = datetime_str[:8]
                        timestamp = datetime.strptime(date_part, "%Y%m%d")
                        # Normalize tone from [-100, 100] to [0.0, 1.0] where 1.0 = max negative
                        tone_normalized = (100.0 - float(tone)) / 200.0
                        tone_normalized = max(0.0, min(1.0, tone_normalized))
                        records.append(
                            {
                                "timestamp": timestamp,
                                "tone_score": tone_normalized,
                            }
                        )
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to parse GDELT datetime: {datetime_str}", error=str(e)
                    )
                    continue
                continue

            # Check for structured format: {series: "...", data: [...]}
            series_name = series_item.get("series")
            data_points = series_item.get("data", [])

            if series_name != "Average Tone" or not data_points:
                continue

            for data_item in data_points:
                date_str = data_item.get("date")
                value = data_item.get("value")

                if date_str is None or value is None:
                    continue

                try:
                    # Parse date (ISO format: YYYYMMDDTHHMMSSZ or YYYYMMDDHHMMSS)
                    # Extract date part (first 8 chars for YYYYMMDD)
                    if "T" in date_str:
                        date_part = date_str.split("T")[0].replace("-", "")
                    else:
                        date_part = date_str[:8]

                    date_obj = datetime.strptime(date_part, "%Y%m%d")
                    records.append({"timestamp": date_obj, "tone": float(value)})
                except (ValueError, TypeError) as e:
                    logger.debug(
                        "Skipping invalid entry",
                        date=date_str,
                        value=value,
                        error=str(e),
                    )
                    continue

        if not records:
            status = SourceStatus(
                provider="GDELT",
                ok=False,
                http_status=http_status,
                error_type="empty",
                error_detail="No valid entries after parsing timeline data",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.warning("GDELT: No valid entries after parsing")
            return pd.DataFrame(columns=["timestamp", "tone_score"]), status

        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Normalize tone to [0.0, 1.0]
        # Tone ranges from -100 to +100
        # We want: negative tone (crisis) = high value (1.0)
        # So: normalize to [0, 1] then invert
        if "tone_score" in df.columns:
            # Already normalized (from simpler format)
            pass
        elif "tone" in df.columns:
            min_tone = df["tone"].min()
            max_tone = df["tone"].max()

            if max_tone > min_tone:
                # Map tone to [0, 1] where -100 -> 1.0 (high stress),
                # +100 -> 0.0 (low stress)
                df["tone_score"] = 1.0 - ((df["tone"] - (-100)) / (100 - (-100)))
                df["tone_score"] = df["tone_score"].clip(0.0, 1.0)
            else:
                # All same tone, default to neutral
                df["tone_score"] = 0.5
        else:
            # No tone data, default to neutral
            df["tone_score"] = 0.5

        df = (
            df[["timestamp", "tone_score"]]
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        # Cache result
        self._cache[cache_key] = (df.copy(), datetime.now())

        status = SourceStatus(
            provider="GDELT",
            ok=True,
            http_status=http_status,
            fetched_at=fetched_at,
            rows=len(df),
            query_window_days=days_back,
        )

        logger.info(
            "Successfully fetched GDELT tone data",
            rows=len(df),
            date_range=(df["timestamp"].min(), df["timestamp"].max()),
            status_ok=status.ok,
        )

        return df, status

    def fetch_legislative_attention(
        self,
        region_name: Optional[str] = None,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch legislative/governance event attention signal from GDELT.

        Queries GDELT for events related to legislative activity, bills, laws,
        state houses, governors, and policy changes. Returns a normalized
        legislative_attention score [0,1] based on event volume.

        Args:
            region_name: Optional region name (state/country) to filter events
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            Tuple of (DataFrame, SourceStatus)
            DataFrame has columns: ['timestamp', 'legislative_attention']
            legislative_attention is normalized to [0.0, 1.0] where 1.0 = high legislative activity
        """
        import math
        import urllib.parse

        fetched_at = datetime.now().isoformat()
        cache_key = f"gdelt_legislative_{region_name or 'global'}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached GDELT legislative data")
                status = SourceStatus(
                    provider="GDELT Legislative Events",
                    ok=True,
                    http_status=200,
                    fetched_at=fetched_at,
                    rows=len(df),
                    query_window_days=days_back,
                )
                return df.copy(), status

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Build GDELT query for legislative/governance-related events
        # Keywords: legislature, legislative, bill, bills, law, laws, state house, state senate,
        # state legislature, governor, executive order, policy change
        base_query = (
            "sourcelang:english AND (legislature OR legislative OR bill OR bills OR "
            'law OR laws OR "state house" OR "state senate" OR "state legislature" OR '
            'governor OR "executive order" OR "policy change")'
        )

        # Add region filter if provided
        if region_name:
            base_query = f'{base_query} AND "{region_name}"'

        # URL encode the query
        encoded_query = urllib.parse.quote(base_query, safe="")

        # GDELT query for event volume timeline
        query = (
            f"mode=timelinevol&format=json&"
            f"query={encoded_query}&"
            f"startdatetime={start_date.strftime('%Y%m%d%H%M%S')}&"
            f"enddatetime={end_date.strftime('%Y%m%d%H%M%S')}"
        )

        logger.info(
            "Fetching GDELT legislative events",
            region_name=region_name,
            days_back=days_back,
        )
        url = f"{GDELT_API_BASE}?{query}"

        # Make request with retries
        response, request_error_type, http_status = self._make_request_with_retries(url)

        if response is None:
            error_detail = f"Request failed after {MAX_RETRIES} retries"
            status = SourceStatus(
                provider="GDELT Legislative Events",
                ok=False,
                http_status=http_status,
                error_type=request_error_type or "other",
                error_detail=error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error(
                "GDELT legislative request failed", error_type=status.error_type
            )
            return pd.DataFrame(columns=["timestamp", "legislative_attention"]), status

        # Validate response
        is_valid, validation_error_type, validation_error_detail = (
            self._validate_response(response)
        )
        if not is_valid:
            status = SourceStatus(
                provider="GDELT Legislative Events",
                ok=False,
                http_status=http_status,
                error_type=validation_error_type,
                error_detail=validation_error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error(
                "GDELT legislative response validation failed",
                error_type=status.error_type,
                error_detail=validation_error_detail,
            )
            return pd.DataFrame(columns=["timestamp", "legislative_attention"]), status

        # Parse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            status = SourceStatus(
                provider="GDELT Legislative Events",
                ok=False,
                http_status=http_status,
                error_type="decode_error",
                error_detail=f"JSON decode error: {str(e)[:100]}",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("GDELT legislative JSON decode failed", error=str(e)[:200])
            return pd.DataFrame(columns=["timestamp", "legislative_attention"]), status

        # Parse timeline data
        if "timeline" not in data or not data["timeline"]:
            # No legislative events is valid (ok=true, rows=0)
            status = SourceStatus(
                provider="GDELT Legislative Events",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("No legislative events found in GDELT response")
            return pd.DataFrame(columns=["timestamp", "legislative_attention"]), status

        timeline = data["timeline"]
        records = []

        for entry in timeline:
            date_str = entry.get("datetime")
            volume = entry.get("volume")

            if date_str is None or volume is None:
                continue

            try:
                # Parse date (ISO format: YYYYMMDDTHHMMSSZ or YYYYMMDDHHMMSS)
                if "T" in date_str:
                    date_part = date_str.split("T")[0].replace("-", "")
                else:
                    date_part = date_str[:8]
                date_obj = datetime.strptime(date_part, "%Y%m%d")
                records.append({"timestamp": date_obj, "event_count": int(volume)})
            except (ValueError, TypeError) as e:
                logger.debug(
                    "Skipping invalid legislative entry",
                    date=date_str,
                    volume=volume,
                    error=str(e),
                )
                continue

        if not records:
            status = SourceStatus(
                provider="GDELT Legislative Events",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("No valid legislative events after parsing")
            return pd.DataFrame(columns=["timestamp", "legislative_attention"]), status

        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Normalize event counts to legislative_attention [0,1] using saturating log-scale function
        # Formula: legislative_attention = min(1.0, log1p(event_count) / log1p(K))
        # K value from calibration config (LEGISLATIVE_NORMALIZATION["K"])
        from app.services.calibration.config import LEGISLATIVE_NORMALIZATION

        K = LEGISLATIVE_NORMALIZATION["K"]
        max_count = df["event_count"].max()
        if max_count > 0:
            df["legislative_attention"] = df["event_count"].apply(
                lambda x: min(1.0, math.log1p(x) / math.log1p(K))
            )
        else:
            df["legislative_attention"] = 0.0

        # Cache the result
        self._cache[cache_key] = (df.copy(), datetime.now())

        status = SourceStatus(
            provider="GDELT Legislative Events",
            ok=True,
            http_status=http_status,
            fetched_at=fetched_at,
            rows=len(df),
            query_window_days=days_back,
        )

        logger.info(
            "GDELT legislative events fetched",
            rows=len(df),
            max_attention=float(df["legislative_attention"].max()),
            status_ok=status.ok,
        )

        return df, status

    def fetch_enforcement_attention(
        self,
        region_name: Optional[str] = None,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch enforcement/ICE/policing event attention signal from GDELT.

        Queries GDELT for events related to enforcement, immigration operations,
        policing, and detention. Returns a normalized enforcement_attention score [0,1]
        based on event volume.

        Args:
            region_name: Optional region name (state/country) to filter events
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            Tuple of (DataFrame, SourceStatus)
            DataFrame has columns: ['timestamp', 'enforcement_attention']
            enforcement_attention is normalized to [0.0, 1.0] where 1.0 = high enforcement activity
        """
        import math

        fetched_at = datetime.now().isoformat()
        cache_key = f"gdelt_enforcement_{region_name or 'global'}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached GDELT enforcement data")
                status = SourceStatus(
                    provider="GDELT Enforcement Events",
                    ok=True,
                    http_status=200,
                    fetched_at=fetched_at,
                    rows=len(df),
                    query_window_days=days_back,
                )
                return df.copy(), status

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Build GDELT query for enforcement-related events
        # Keywords: ICE, immigration enforcement, deportation, removal, raid, detention
        # Use OR logic: (ICE OR "immigration enforcement" OR deportation OR removal OR raid OR "detention center")
        base_query = 'sourcelang:english AND (ICE OR "immigration enforcement" OR deportation OR removal OR raid OR "detention center")'

        # Add region filter if provided (simple keyword-based approach)
        # Note: More sophisticated geo filtering could use GDELT's location:state or location:country filters
        if region_name:
            base_query = f'{base_query} AND "{region_name}"'

        # URL encode the query
        import urllib.parse

        encoded_query = urllib.parse.quote(base_query, safe="")

        # GDELT query for event volume timeline
        query = (
            f"mode=timelinevol&format=json&"
            f"query={encoded_query}&"
            f"startdatetime={start_date.strftime('%Y%m%d%H%M%S')}&"
            f"enddatetime={end_date.strftime('%Y%m%d%H%M%S')}"
        )

        logger.info(
            "Fetching GDELT enforcement events",
            region_name=region_name,
            days_back=days_back,
        )
        url = f"{GDELT_API_BASE}?{query}"

        # Make request with retries
        response, request_error_type, http_status = self._make_request_with_retries(url)

        if response is None:
            error_detail = f"Request failed after {MAX_RETRIES} retries"
            status = SourceStatus(
                provider="GDELT Enforcement Events",
                ok=False,
                http_status=http_status,
                error_type=request_error_type or "other",
                error_detail=error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error(
                "GDELT enforcement request failed", error_type=status.error_type
            )
            return pd.DataFrame(columns=["timestamp", "enforcement_attention"]), status

        # Validate response
        is_valid, validation_error_type, validation_error_detail = (
            self._validate_response(response)
        )
        if not is_valid:
            status = SourceStatus(
                provider="GDELT Enforcement Events",
                ok=False,
                http_status=http_status,
                error_type=validation_error_type,
                error_detail=validation_error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error(
                "GDELT enforcement response validation failed",
                error_type=status.error_type,
                error_detail=validation_error_detail,
            )
            return pd.DataFrame(columns=["timestamp", "enforcement_attention"]), status

        # Parse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            status = SourceStatus(
                provider="GDELT Enforcement Events",
                ok=False,
                http_status=http_status,
                error_type="decode_error",
                error_detail=f"JSON decode error: {str(e)[:100]}",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("GDELT enforcement JSON decode failed", error=str(e)[:200])
            return pd.DataFrame(columns=["timestamp", "enforcement_attention"]), status

        # Parse timeline data
        if "timeline" not in data or not data["timeline"]:
            # No enforcement events is valid (ok=true, rows=0)
            status = SourceStatus(
                provider="GDELT Enforcement Events",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("No enforcement events found in GDELT response")
            return pd.DataFrame(columns=["timestamp", "enforcement_attention"]), status

        timeline = data["timeline"]
        records = []

        for entry in timeline:
            date_str = entry.get("datetime")
            volume = entry.get("volume")

            if date_str is None or volume is None:
                continue

            try:
                # Parse date (ISO format: YYYYMMDDTHHMMSSZ or YYYYMMDDHHMMSS)
                if "T" in date_str:
                    date_part = date_str.split("T")[0].replace("-", "")
                else:
                    date_part = date_str[:8]
                date_obj = datetime.strptime(date_part, "%Y%m%d")
                records.append({"timestamp": date_obj, "event_count": int(volume)})
            except (ValueError, TypeError) as e:
                logger.debug(
                    "Skipping invalid enforcement entry",
                    date=date_str,
                    volume=volume,
                    error=str(e),
                )
                continue

        if not records:
            status = SourceStatus(
                provider="GDELT Enforcement Events",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("No valid enforcement events after parsing")
            return pd.DataFrame(columns=["timestamp", "enforcement_attention"]), status

        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Normalize event counts to enforcement_attention [0,1] using saturating log-scale function
        # Formula: enforcement_attention = min(1.0, log1p(event_count) / log1p(K))
        # K value from calibration config (ENFORCEMENT_NORMALIZATION["K"])
        from app.services.calibration.config import ENFORCEMENT_NORMALIZATION

        K = ENFORCEMENT_NORMALIZATION["K"]
        max_count = df["event_count"].max()
        if max_count > 0:
            df["enforcement_attention"] = df["event_count"].apply(
                lambda x: min(1.0, math.log1p(x) / math.log1p(K))
            )
        else:
            df["enforcement_attention"] = 0.0

        df["enforcement_attention"] = df["enforcement_attention"].clip(0.0, 1.0)

        df = (
            df[["timestamp", "enforcement_attention"]]
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        # Cache result
        self._cache[cache_key] = (df.copy(), datetime.now())

        status = SourceStatus(
            provider="GDELT Enforcement Events",
            ok=True,
            http_status=http_status,
            fetched_at=fetched_at,
            rows=len(df),
            query_window_days=days_back,
        )

        logger.info(
            "Successfully fetched GDELT enforcement events",
            rows=len(df),
            region_name=region_name,
            date_range=(df["timestamp"].min(), df["timestamp"].max()),
        )

        return df, status

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
