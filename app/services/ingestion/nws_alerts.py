# SPDX-License-Identifier: PROPRIETARY
"""NWS Weather Alerts API connector."""
from datetime import datetime, timedelta
from typing import Optional, Tuple

import json
import pandas as pd
import requests
import structlog
import time

from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.nws_alerts")

# NWS API base URLs
NWS_API_BASE = "https://api.weather.gov"
NWS_USER_AGENT = "HumanBehaviourConvergence/1.0 (contact: your-email@example.com)"

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 10.0  # seconds


class NWSAlertsFetcher:
    """
    Fetch weather alerts from NWS API.

    NWS provides active weather alerts (warnings, watches, advisories) by location.

    No authentication required (public API).
    Rate limits: Standard HTTP rate limits apply

    Source: https://www.weather.gov/documentation/services-web-api
    API Docs: https://api.weather.gov/
    """

    def __init__(self, cache_duration_minutes: int = 60):
        """
        Initialize NWS alerts fetcher.

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
        headers = {"User-Agent": NWS_USER_AGENT}

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
                            "NWS API returned non-200 status, retrying",
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
                        "NWS API timeout, retrying",
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
                        "NWS API request exception, retrying",
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
                    "Unexpected error in NWS request",
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
        if not response.content:
            return False, "empty", "Response body is empty"

        body_text = response.text
        body_stripped = body_text.strip()
        if not body_stripped or (
            not body_stripped.startswith("{") and not body_stripped.startswith("[")
        ):
            preview = body_text[:200].replace("\n", " ").replace("\r", " ")
            return (
                False,
                "non_json",
                f"Body does not start with {{ or [ (preview: {preview})",
            )

        return True, None, None

    def fetch_weather_alerts(
        self,
        latitude: float,
        longitude: float,
        days_back: int = 7,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch active weather alerts from NWS for a location.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            days_back: Number of days to look back (NWS returns active alerts, this is for filtering)
            use_cache: Whether to use cached data if available

        Returns:
            Tuple of (DataFrame, SourceStatus)
            DataFrame columns: timestamp, alert_count
            Returns empty DataFrame on error, with status.ok=False
        """
        fetched_at = datetime.now().isoformat()
        cache_key = f"nws_alerts_{latitude}_{longitude}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached NWS alerts data", age_minutes=age_minutes)
                status = SourceStatus(
                    provider="NWS",
                    ok=True,
                    http_status=200,
                    fetched_at=fetched_at,
                    rows=len(df),
                    query_window_days=days_back,
                )
                return df.copy(), status

        # NWS alerts endpoint: /alerts/active?point={lat},{lon}
        url = f"{NWS_API_BASE}/alerts/active?point={latitude},{longitude}"

        logger.info("Fetching NWS alerts", latitude=latitude, longitude=longitude)

        # Make request with retries
        response, request_error_type, http_status = self._make_request_with_retries(url)

        if response is None:
            error_detail = f"Request failed after {MAX_RETRIES} retries"
            status = SourceStatus(
                provider="NWS",
                ok=False,
                http_status=http_status,
                error_type=request_error_type or "other",
                error_detail=error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("NWS request failed", error_type=status.error_type)
            return pd.DataFrame(columns=["timestamp", "alert_count"]), status

        # Validate response
        is_valid, validation_error_type, validation_error_detail = (
            self._validate_response(response)
        )

        if not is_valid:
            status = SourceStatus(
                provider="NWS",
                ok=False,
                http_status=http_status,
                error_type=validation_error_type,
                error_detail=validation_error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error(
                "NWS response validation failed",
                error_type=status.error_type,
                error_detail=status.error_detail,
                http_status=http_status,
            )
            return pd.DataFrame(columns=["timestamp", "alert_count"]), status

        # Parse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            status = SourceStatus(
                provider="NWS",
                ok=False,
                http_status=http_status,
                error_type="decode_error",
                error_detail=f"JSON decode error: {str(e)[:100]}",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("NWS JSON decode failed", error=str(e)[:200])
            return pd.DataFrame(columns=["timestamp", "alert_count"]), status

        # NWS alerts response structure: { "@context": [...], "features": [...] }
        # Each feature has properties with sent, effective, expires, status, etc.
        features = data.get("features", [])
        if not features:
            # No alerts is valid (ok=true, rows=0)
            status = SourceStatus(
                provider="NWS",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("NWS returned no active alerts")
            return pd.DataFrame(columns=["timestamp", "alert_count"]), status

        # Aggregate alerts by date
        alert_counts = {}
        cutoff_date = datetime.now() - timedelta(days=days_back)

        for feature in features:
            props = feature.get("properties", {})
            # Use effective time if available, otherwise sent time
            time_str = props.get("effective", props.get("sent", ""))
            if time_str:
                try:
                    # Parse ISO 8601 datetime
                    alert_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    if alert_time >= cutoff_date:
                        date_key = alert_time.date()
                        alert_counts[date_key] = alert_counts.get(date_key, 0) + 1
                except (ValueError, TypeError):
                    continue

        if not alert_counts:
            status = SourceStatus(
                provider="NWS",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("NWS alerts found but none in query window")
            return pd.DataFrame(columns=["timestamp", "alert_count"]), status

        # Create DataFrame
        records = [
            {
                "timestamp": datetime.combine(date, datetime.min.time()),
                "alert_count": count,
            }
            for date, count in alert_counts.items()
        ]
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Cache result
        self._cache[cache_key] = (df.copy(), datetime.now())

        status = SourceStatus(
            provider="NWS",
            ok=True,
            http_status=http_status,
            fetched_at=fetched_at,
            rows=len(df),
            query_window_days=days_back,
        )

        logger.info(
            "Successfully fetched NWS alerts",
            rows=len(df),
            latitude=latitude,
            longitude=longitude,
        )

        return df, status
