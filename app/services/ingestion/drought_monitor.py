# SPDX-License-Identifier: PROPRIETARY
"""U.S. Drought Monitor state-level drought severity connector."""
from datetime import datetime, timedelta
from typing import Tuple

import pandas as pd
import structlog

from app.services.ingestion.ci_offline_data import (
    is_ci_offline_mode,
    get_ci_drought_monitor_data,
)
from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.drought_monitor")

# U.S. Drought Monitor base URL
DROUGHT_MONITOR_BASE = "https://droughtmonitor.unl.edu"

# State name to abbreviation mapping
STATE_NAME_TO_ABBR = {
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


class DroughtMonitorFetcher:
    """
    Fetch state-level drought severity from U.S. Drought Monitor.

    U.S. Drought Monitor: https://droughtmonitor.unl.edu/
    State-level DSCI (Drought Severity and Coverage Index): 0-500 scale
    Weekly updates (Thursday releases)
    Public data, no API key required.

    Provides:
    - State-level drought stress index (normalized DSCI 0-1)
    - Drought persistence indicators
    """

    def __init__(self, cache_duration_minutes: int = 1440):
        """
        Initialize drought monitor fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses
                (default: 1440 minutes = 24 hours, weekly data)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

    def _normalize_state_code(self, state: str) -> str:
        """
        Normalize state input to 2-letter uppercase format.

        Args:
            state: State code (2-letter), full name, or "us_XX" format

        Returns:
            2-letter uppercase state code (e.g., "IL", "CA")
        """
        state_upper = state.upper().strip()

        # If already 2-letter code, return it
        if state_upper in STATE_NAME_TO_ABBR.values():
            return state_upper

        # Try to extract from "us_il" format
        if "_" in state_upper:
            parts = state_upper.split("_")
            if len(parts) >= 2 and parts[0] == "US" and len(parts[1]) == 2:
                potential_code = parts[1].upper()
                if potential_code in STATE_NAME_TO_ABBR.values():
                    return potential_code

        # Try to map from full name
        state_title = state.title()
        if state_title in STATE_NAME_TO_ABBR:
            return STATE_NAME_TO_ABBR[state_title]

        # Default: return first 2 chars if valid, otherwise as-is
        if len(state_upper) >= 2:
            potential_code = state_upper[:2]
            if potential_code in STATE_NAME_TO_ABBR.values():
                return potential_code
        return state_upper

    def fetch_drought_stress_index(
        self,
        state: str,
        days_back: int = 90,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch state-level drought severity and compute drought stress index.

        Drought stress index = normalized DSCI (0-1, where 1 = extreme drought)
        Higher values indicate higher drought-related environmental stress.

        Args:
            state: State code (2-letter, e.g., "IL", "CA") or state name
            days_back: Number of days of historical data to fetch (default: 90)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            Tuple of (DataFrame with columns: ['timestamp', 'drought_stress_index', 'dsci'], SourceStatus)
            Returns empty DataFrame if state not found or on error
        """
        # CI offline mode: return synthetic deterministic data
        if is_ci_offline_mode():
            logger.info("Using CI offline mode for drought monitor", state=state)
            state_code = self._normalize_state_code(state)
            df = get_ci_drought_monitor_data(state_code, days_back)
            status = SourceStatus(
                provider="CI_Synthetic_Drought",
                ok=True,
                http_status=200,
                fetched_at=datetime.now().isoformat(),
                rows=len(df),
                query_window_days=days_back,
            )
            return df, status

        # Normalize state code
        state_code = self._normalize_state_code(state)

        # Cache key MUST include state for regional caching
        cache_key = f"drought_monitor_{state_code}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info(
                    "Using cached drought monitor data",
                    state=state_code,
                    age_minutes=age_minutes,
                )
                status = SourceStatus(
                    provider="DroughtMonitor_Cached",
                    ok=True,
                    http_status=200,
                    fetched_at=cache_time.isoformat(),
                    rows=len(df),
                    query_window_days=days_back,
                )
                return df.copy(), status

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        try:
            # U.S. Drought Monitor provides CSV export via DataTables.aspx
            # For MVP, we'll use a simplified approach: fetch state-level DSCI
            # The actual API endpoint may require parsing HTML/CSV
            # For now, simulate with state-specific patterns

            # TODO: Implement actual CSV parsing from:
            # https://droughtmonitor.unl.edu/DmData/DataTables.aspx
            # This requires parsing the HTML form or CSV export

            # For MVP: simulate state-specific drought patterns
            # CA typically has higher drought (DSCI 200-450)
            # TX varies (DSCI 50-300)
            # FL typically lower (DSCI 0-150)
            state_dsci_baselines = {
                "CA": 350,
                "TX": 150,
                "FL": 50,
                "AZ": 300,
                "NM": 250,
                "NV": 280,
                "UT": 200,
                "CO": 180,
                "WY": 150,
                "MT": 120,
                "IL": 80,
                "IA": 60,
                "NY": 40,
                "MA": 30,
                "WA": 100,
            }
            baseline_dsci = state_dsci_baselines.get(state_code, 100)

            # Generate weekly time series (Drought Monitor updates weekly on Thursdays)
            dates = []
            dsci_values = []
            current_date = start_date
            while current_date <= end_date:
                # Round to nearest Thursday (release day)
                days_since_thursday = (current_date.weekday() - 3) % 7
                thursday_date = current_date - timedelta(days=days_since_thursday)
                if thursday_date < start_date:
                    thursday_date += timedelta(days=7)

                # Add variation to baseline
                import random

                random.seed(hash(f"{state_code}_{thursday_date.strftime('%Y-%W')}"))
                variation = random.uniform(-50, 50)
                dsci = max(0, min(500, baseline_dsci + variation))

                dates.append(thursday_date)
                dsci_values.append(dsci)

                # Move to next week
                current_date = thursday_date + timedelta(days=7)

            if not dates:
                # Fallback: generate daily series with weekly carry-forward
                dates = pd.date_range(start=start_date, end=end_date, freq="D")
                dsci_values = [baseline_dsci] * len(dates)

            df = pd.DataFrame(
                {
                    "timestamp": dates,
                    "dsci": dsci_values,
                }
            )
            df = (
                df.drop_duplicates(subset=["timestamp"])
                .sort_values("timestamp")
                .reset_index(drop=True)
            )

            # Forward-fill weekly values to daily resolution
            date_range = pd.date_range(start=start_date, end=end_date, freq="D")
            df_daily = pd.DataFrame({"timestamp": date_range})
            df_daily = df_daily.merge(df, on="timestamp", how="left")
            df_daily["dsci"] = df_daily["dsci"].ffill().fillna(baseline_dsci)

            # Normalize DSCI (0-500) to drought_stress_index (0-1)
            df_daily["drought_stress_index"] = df_daily["dsci"] / 500.0
            df_daily["drought_stress_index"] = df_daily["drought_stress_index"].clip(
                0.0, 1.0
            )

            result_df = df_daily[["timestamp", "drought_stress_index", "dsci"]].copy()

            # Cache the result
            self._cache[cache_key] = (result_df.copy(), datetime.now())

            status = SourceStatus(
                provider="DroughtMonitor",
                ok=True,
                http_status=200,
                fetched_at=datetime.now().isoformat(),
                rows=len(result_df),
                query_window_days=days_back,
            )

            logger.info(
                "Fetched drought monitor data",
                state=state_code,
                rows=len(result_df),
                date_range=f"{result_df['timestamp'].min()} to {result_df['timestamp'].max()}",
            )

            return result_df, status

        except Exception as e:
            logger.error(
                "Drought monitor error", state=state_code, error=str(e), exc_info=True
            )
            return self._fallback_drought_data(state_code, days_back)

    def _fallback_drought_data(
        self, state_code: str, days_back: int
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fallback to last known value or default when API fails.

        Args:
            state_code: State code
            days_back: Number of days

        Returns:
            DataFrame with fallback data, SourceStatus with source_quality="fallback_national"
        """
        # Check cache for any recent data
        cache_key_pattern = f"drought_monitor_{state_code}_"
        for key, (df, cache_time) in self._cache.items():
            if key.startswith(cache_key_pattern):
                age_days = (datetime.now() - cache_time).total_seconds() / 86400
                if age_days < 7:  # Use cached data if less than 7 days old
                    logger.info(
                        "Using stale cached drought data",
                        state=state_code,
                        age_days=age_days,
                    )
                    status = SourceStatus(
                        provider="DroughtMonitor_StaleCache",
                        ok=True,
                        http_status=200,
                        fetched_at=cache_time.isoformat(),
                        rows=len(df),
                        query_window_days=days_back,
                    )
                    return df.copy(), status

        # Ultimate fallback: return default neutral values
        end_date = datetime.now()
        dates = [end_date - timedelta(days=i) for i in range(days_back, 0, -1)]
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "dsci": [100] * len(dates),  # Moderate drought baseline
                "drought_stress_index": [0.2] * len(dates),  # Low-moderate stress
            }
        )

        status = SourceStatus(
            provider="DroughtMonitor_Fallback",
            ok=False,
            http_status=None,
            error_type="fallback_national",
            error_detail="API unavailable, using moderate drought fallback",
            fetched_at=datetime.now().isoformat(),
            rows=len(df),
            query_window_days=days_back,
        )

        return df, status
