# SPDX-License-Identifier: PROPRIETARY
"""OpenFEMA Emergency Management API connector for disaster declarations."""
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
import requests
import structlog

from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.openfema")

# OpenFEMA API base URL
OPENFEMA_API_BASE = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 10.0  # seconds


# State name to abbreviation mapping (common US states)
STATE_ABBREV_MAP = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC",
}


class OpenFEMAEmergencyManagementFetcher:
    """
    Fetch disaster declarations from OpenFEMA API.

    OpenFEMA provides public data on disaster declarations, emergency
    management events, and related FEMA program activity.

    No authentication required (public API).
    Rate limits: Standard HTTP rate limits apply

    Source: https://www.fema.gov/about/openfema/data-sets
    API Docs: https://www.fema.gov/api/open/v2/
    """

    def __init__(self, cache_duration_minutes: int = 60):
        """
        Initialize OpenFEMA fetcher.

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
                            "OpenFEMA API returned non-200 status, retrying",
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
                        "OpenFEMA API timeout, retrying",
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
                        "OpenFEMA API request exception, retrying",
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
                    "Unexpected error in OpenFEMA request",
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

    def _resolve_state_abbrev(self, region_name: str) -> Optional[str]:
        """
        Resolve state abbreviation from region name.

        Args:
            region_name: Region name (e.g., "Minnesota", "MN")

        Returns:
            State abbreviation (e.g., "MN") or None if not found
        """
        # Check if already an abbreviation (2 letters, uppercase)
        if len(region_name) == 2 and region_name.isupper():
            return region_name

        # Look up in mapping
        return STATE_ABBREV_MAP.get(region_name)

    def fetch_disaster_declarations(
        self,
        region_name: Optional[str] = None,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch disaster declarations from OpenFEMA API.

        Args:
            region_name: Region name (e.g., "Minnesota") or state abbrev (e.g., "MN")
            days_back: Number of days of historical data to consider (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            Tuple of (DataFrame, SourceStatus)
            DataFrame has columns: ['timestamp', 'declaration_count']
            Returns empty DataFrame on error, with status.ok=False
        """
        fetched_at = datetime.now().isoformat()
        cache_key = f"openfema_{region_name or 'national'}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached OpenFEMA data")
                status = SourceStatus(
                    provider="OpenFEMA",
                    ok=True,
                    http_status=200,
                    fetched_at=fetched_at,
                    rows=len(df),
                    query_window_days=days_back,
                )
                return df.copy(), status

        # Resolve state abbreviation
        state_abbrev = None
        if region_name:
            state_abbrev = self._resolve_state_abbrev(region_name)

        # Build URL with filters
        # OpenFEMA API uses $filter for query parameters
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        # Format dates as YYYY-MM-DD for API
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        # Build filter expression
        filter_parts = [
            f"declarationDate ge '{start_date_str}'",
            f"declarationDate le '{end_date_str}'",
        ]
        if state_abbrev:
            filter_parts.append(f"state eq '{state_abbrev}'")

        filter_expr = " and ".join(filter_parts)
        url = f"{OPENFEMA_API_BASE}?$filter={filter_expr}&$format=json"

        logger.info(
            "Fetching OpenFEMA disaster declarations",
            region_name=region_name,
            state_abbrev=state_abbrev,
            days_back=days_back,
        )

        # Make request with retries
        response, request_error_type, http_status = self._make_request_with_retries(url)

        if response is None:
            # Request failed
            error_detail = f"Request failed after {MAX_RETRIES} retries"
            status = SourceStatus(
                provider="OpenFEMA",
                ok=False,
                http_status=http_status,
                error_type=request_error_type or "other",
                error_detail=error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error(
                "OpenFEMA request failed",
                error_type=status.error_type,
                error_detail=error_detail,
            )
            return pd.DataFrame(columns=["timestamp", "declaration_count"]), status

        # Validate response
        is_valid, validation_error_type, validation_error_detail = (
            self._validate_response(response)
        )

        if not is_valid:
            status = SourceStatus(
                provider="OpenFEMA",
                ok=False,
                http_status=http_status,
                error_type=validation_error_type,
                error_detail=validation_error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error(
                "OpenFEMA response validation failed",
                error_type=status.error_type,
                error_detail=status.error_detail,
                http_status=http_status,
            )
            return pd.DataFrame(columns=["timestamp", "declaration_count"]), status

        # Parse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            status = SourceStatus(
                provider="OpenFEMA",
                ok=False,
                http_status=http_status,
                error_type="decode_error",
                error_detail=f"JSON decode error: {str(e)[:100]}",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("OpenFEMA JSON decode failed", error=str(e)[:200])
            return pd.DataFrame(columns=["timestamp", "declaration_count"]), status

        # Parse OpenFEMA response (may be array or object-wrapped array)
        records_array = None
        wrapper_key = None

        if isinstance(data, list):
            # Direct array format
            records_array = data
        elif isinstance(data, dict):
            # Object-wrapped format - try to extract array from common wrapper keys
            # Check common OpenFEMA patterns (ordered by likelihood)
            wrapper_candidates = [
                "DisasterDeclarationsSummaries",
                "results",
                "data",
                "items",
                "records",
            ]

            for candidate_key in wrapper_candidates:
                if candidate_key in data and isinstance(data[candidate_key], list):
                    records_array = data[candidate_key]
                    wrapper_key = candidate_key
                    break

            # If no known wrapper key found, try to find any list-valued field
            if records_array is None:
                for key, value in data.items():
                    if isinstance(value, list):
                        records_array = value
                        wrapper_key = key
                        logger.info(
                            "OpenFEMA: Using unknown wrapper key",
                            wrapper_key=wrapper_key,
                        )
                        break

            if records_array is None:
                # No array found in object - schema mismatch
                status = SourceStatus(
                    provider="OpenFEMA",
                    ok=False,
                    http_status=http_status,
                    error_type="schema_mismatch",
                    error_detail="Response is object but no array field found",
                    fetched_at=fetched_at,
                    rows=0,
                    query_window_days=days_back,
                )
                logger.warning(
                    "OpenFEMA response is object but no array field found",
                    object_keys=list(data.keys())[:10],  # Log first 10 keys
                )
                return pd.DataFrame(columns=["timestamp", "declaration_count"]), status
        else:
            # Neither list nor dict - invalid format
            status = SourceStatus(
                provider="OpenFEMA",
                ok=False,
                http_status=http_status,
                error_type="schema_mismatch",
                error_detail=f"Response is not array or object (type: {type(data).__name__})",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.warning(
                "OpenFEMA response is not array or object",
                response_type=type(data).__name__,
            )
            return pd.DataFrame(columns=["timestamp", "declaration_count"]), status

        # Log which format was used (if wrapper was detected)
        if wrapper_key:
            logger.info(
                "OpenFEMA: Extracted array from object wrapper",
                wrapper_key=wrapper_key,
                array_length=len(records_array),
            )

        data = records_array  # Use extracted array for rest of processing

        if not data:
            # Empty array is valid (no declarations in window)
            status = SourceStatus(
                provider="OpenFEMA",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info(
                "OpenFEMA returned empty result (no declarations in window)",
                wrapper_key=wrapper_key if wrapper_key else None,
            )
            return pd.DataFrame(columns=["timestamp", "declaration_count"]), status

        # Parse records
        records = []
        for record in data:
            declaration_date = record.get("declarationDate")
            if not declaration_date:
                continue

            try:
                # Parse date (format: YYYY-MM-DD)
                timestamp = datetime.strptime(declaration_date, "%Y-%m-%d").date()
                records.append(
                    {
                        "timestamp": timestamp,
                        "declaration_count": 1,
                    }
                )
            except (ValueError, TypeError) as e:
                logger.debug(
                    "Skipping invalid declaration entry",
                    declaration_date=declaration_date,
                    error=str(e),
                )
                continue

        if not records:
            status = SourceStatus(
                provider="OpenFEMA",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("OpenFEMA: No valid declarations after parsing")
            return pd.DataFrame(columns=["timestamp", "declaration_count"]), status

        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Aggregate by date (count declarations per day)
        df = df.groupby("timestamp")["declaration_count"].sum().reset_index()

        # Filter to days_back window (already filtered by API, but ensure)
        cutoff_date = datetime.now().date() - timedelta(days=days_back)
        df = df[df["timestamp"].dt.date >= cutoff_date]

        df = df.sort_values("timestamp").reset_index(drop=True)

        # Cache result
        self._cache[cache_key] = (df.copy(), datetime.now())

        status = SourceStatus(
            provider="OpenFEMA",
            ok=True,
            http_status=http_status,
            fetched_at=fetched_at,
            rows=len(df),
            query_window_days=days_back,
        )

        logger.info(
            "Successfully fetched OpenFEMA disaster declarations",
            rows=len(df),
            date_range=(
                (df["timestamp"].min(), df["timestamp"].max()) if not df.empty else None
            ),
            status_ok=status.ok,
        )

        return df, status
