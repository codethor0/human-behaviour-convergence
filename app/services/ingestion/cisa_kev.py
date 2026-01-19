# SPDX-License-Identifier: PROPRIETARY
"""CISA KEV (Known Exploited Vulnerabilities) API connector."""
from datetime import datetime, timedelta
from typing import Optional, Tuple

import json
import pandas as pd
import requests
import structlog
import time

logger = structlog.get_logger("ingestion.cisa_kev")

# CISA KEV API
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 10.0

# Import SourceStatus from gdelt_events (reuse pattern)
from app.services.ingestion.gdelt_events import SourceStatus


class CISAKEVFetcher:
    """
    Fetch CISA KEV catalog data.

    CISA provides a public JSON catalog of known exploited vulnerabilities.
    No authentication required (public JSON file).

    Source: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
    """

    def __init__(self, cache_duration_minutes: int = 360):
        """
        Initialize CISA KEV fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses
                (default: 360 minutes = 6 hours)
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
                            "CISA KEV API returned non-200 status, retrying",
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
                        "CISA KEV API timeout, retrying", attempt=attempt + 1
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, error_type, None
            except requests.exceptions.RequestException as e:
                error_type = "http_error"
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "CISA KEV API request exception, retrying", error=str(e)[:100]
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue
                return None, error_type, None
            except Exception as e:
                error_type = "other"
                logger.error(
                    "Unexpected error in CISA KEV request",
                    error=str(e)[:200],
                    exc_info=True,
                )
                return None, error_type, None

        return None, "other", None

    def fetch_kev_catalog(
        self,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch CISA KEV catalog and compute signal.

        Args:
            days_back: Number of days to look back for added/updated KEVs
            use_cache: Whether to use cached data if available

        Returns:
            Tuple of (DataFrame, SourceStatus)
            DataFrame columns: timestamp, kev_count, signal (normalized 0-1)
            Returns empty DataFrame on error, with status.ok=False
        """
        fetched_at = datetime.now().isoformat()
        cache_key = f"cisa_kev_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached CISA KEV data", age_minutes=age_minutes)
                status = SourceStatus(
                    provider="CISA KEV",
                    ok=True,
                    http_status=200,
                    fetched_at=fetched_at,
                    rows=len(df),
                    query_window_days=days_back,
                )
                return df.copy(), status

        logger.info("Fetching CISA KEV catalog")

        # Make request with retries
        response, request_error_type, http_status = self._make_request_with_retries(
            CISA_KEV_URL
        )

        if response is None:
            error_detail = f"Request failed after {MAX_RETRIES} retries"
            status = SourceStatus(
                provider="CISA KEV",
                ok=False,
                http_status=http_status,
                error_type=request_error_type or "other",
                error_detail=error_detail,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("CISA KEV request failed", error_type=status.error_type)
            return pd.DataFrame(columns=["timestamp", "kev_count", "signal"]), status

        # Parse JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            status = SourceStatus(
                provider="CISA KEV",
                ok=False,
                http_status=http_status,
                error_type="decode_error",
                error_detail=f"JSON decode error: {str(e)[:100]}",
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.error("CISA KEV JSON decode failed", error=str(e)[:200])
            return pd.DataFrame(columns=["timestamp", "kev_count", "signal"]), status

        # CISA KEV response structure: { "vulnerabilities": [...] }
        vulnerabilities = data.get("vulnerabilities", [])
        if not vulnerabilities:
            # Empty catalog is valid (ok=true, rows=0)
            status = SourceStatus(
                provider="CISA KEV",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("CISA KEV catalog is empty")
            return pd.DataFrame(columns=["timestamp", "kev_count", "signal"]), status

        # Count KEVs added/updated in the query window
        cutoff_date = datetime.now() - timedelta(days=days_back)
        kev_counts_by_date = {}

        for vuln in vulnerabilities:
            # Use dateAdded if available, else dateUpdated
            date_str = vuln.get("dateAdded", vuln.get("dateUpdated", ""))
            if date_str:
                try:
                    # Parse date (format: YYYY-MM-DD)
                    vuln_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if vuln_date >= cutoff_date:
                        date_key = vuln_date.date()
                        kev_counts_by_date[date_key] = (
                            kev_counts_by_date.get(date_key, 0) + 1
                        )
                except (ValueError, TypeError):
                    continue

        if not kev_counts_by_date:
            # No KEVs in query window is valid (ok=true, rows=0)
            status = SourceStatus(
                provider="CISA KEV",
                ok=True,
                http_status=http_status,
                fetched_at=fetched_at,
                rows=0,
                query_window_days=days_back,
            )
            logger.info("CISA KEV catalog has no entries in query window")
            return pd.DataFrame(columns=["timestamp", "kev_count", "signal"]), status

        # Create DataFrame with date, count, and normalized signal (0-1)
        max_count = max(kev_counts_by_date.values())
        records = []
        for date, count in kev_counts_by_date.items():
            # Normalize count to [0,1] using max as denominator
            # Use a scaling factor to avoid extreme values (divide by max, cap at 1.0)
            signal = min(1.0, count / max(max_count, 1.0))
            records.append(
                {
                    "timestamp": datetime.combine(date, datetime.min.time()),
                    "kev_count": count,
                    "signal": signal,
                }
            )

        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Cache result
        self._cache[cache_key] = (df.copy(), datetime.now())

        status = SourceStatus(
            provider="CISA KEV",
            ok=True,
            http_status=http_status,
            fetched_at=fetched_at,
            rows=len(df),
            query_window_days=days_back,
        )

        logger.info(
            "Successfully fetched CISA KEV catalog",
            rows=len(df),
            days_back=days_back,
        )

        return df, status
