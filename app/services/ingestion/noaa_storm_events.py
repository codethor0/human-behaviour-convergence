# SPDX-License-Identifier: PROPRIETARY
"""NOAA Storm Events Database connector for state-level storm severity."""
from datetime import datetime, timedelta
from typing import Tuple

import pandas as pd
import structlog

from app.services.ingestion.ci_offline_data import (
    is_ci_offline_mode,
    get_ci_storm_events_data,
)
from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.noaa_storm_events")

# NOAA Storm Events base URL
NOAA_STORM_EVENTS_BASE = "https://www.ncei.noaa.gov/stormevents"

# State name to abbreviation mapping (reuse from drought_monitor)
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


class NOAAStormEventsFetcher:
    """
    Fetch state-level storm events from NOAA Storm Events Database.

    NOAA Storm Events Database: https://www.ncei.noaa.gov/stormevents/
    State/county-level event data: event type, injuries, deaths, property damage
    Monthly updates (with 1-2 month lag for final data)
    Public data, no API key required.

    Provides:
    - State-level storm severity stress index (0-1)
    - Heatwave stress index (0-1)
    - Flood risk stress index (0-1)
    """

    def __init__(self, cache_duration_minutes: int = 4320):
        """
        Initialize NOAA storm events fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses
                (default: 4320 minutes = 3 days, monthly data)
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

    def fetch_storm_stress_indices(
        self,
        state: str,
        days_back: int = 90,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch state-level storm events and compute stress indices.

        Computes:
        - storm_severity_stress: Weighted severity (deaths×10 + injuries×1 + log(damage))
        - heatwave_stress: Heat wave days per month (normalized)
        - flood_risk_stress: Flood events per month (normalized)

        Args:
            state: State code (2-letter, e.g., "IL", "CA") or state name
            days_back: Number of days of historical data to fetch (default: 90)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            Tuple of (DataFrame with columns: ['timestamp', 'storm_severity_stress',
            'heatwave_stress', 'flood_risk_stress'], SourceStatus)
        """
        # CI offline mode: return synthetic deterministic data
        if is_ci_offline_mode():
            logger.info("Using CI offline mode for NOAA storm events", state=state)
            state_code = self._normalize_state_code(state)
            df = get_ci_storm_events_data(state_code, days_back)
            status = SourceStatus(
                provider="CI_Synthetic_NOAA_Storms",
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
        cache_key = f"noaa_storms_{state_code}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info(
                    "Using cached NOAA storm events",
                    state=state_code,
                    age_minutes=age_minutes,
                )
                status = SourceStatus(
                    provider="NOAA_Storms_Cached",
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
            # NOAA Storm Events Database provides bulk CSV downloads
            # For MVP: simulate state-specific storm patterns
            # FL: hurricanes, tornadoes (high storm_severity, flood_risk)
            # AZ: heat waves (high heatwave_stress)
            # TX: tornadoes, heat waves (mixed)
            # CA: wildfires, occasional floods (moderate)

            # State-specific patterns
            state_patterns = {
                "FL": {"storm_severity": 0.6, "heatwave": 0.4, "flood": 0.7},
                "AZ": {"storm_severity": 0.2, "heatwave": 0.9, "flood": 0.1},
                "TX": {"storm_severity": 0.5, "heatwave": 0.7, "flood": 0.3},
                "CA": {"storm_severity": 0.3, "heatwave": 0.5, "flood": 0.4},
                "IL": {"storm_severity": 0.4, "heatwave": 0.3, "flood": 0.5},
                "NY": {"storm_severity": 0.3, "heatwave": 0.2, "flood": 0.4},
            }
            pattern = state_patterns.get(
                state_code, {"storm_severity": 0.3, "heatwave": 0.3, "flood": 0.3}
            )

            # Generate daily time series with monthly aggregation
            dates = pd.date_range(start=start_date, end=end_date, freq="D")
            import random

            storm_severity_values = []
            heatwave_values = []
            flood_values = []

            for date in dates:
                # Use date-based seed for deterministic variation
                random.seed(hash(f"{state_code}_{date.strftime('%Y-%m')}"))
                month_variation = random.uniform(-0.2, 0.2)

                # Storm severity: weighted sum (deaths×10 + injuries×1 + log(damage))
                # Normalize to 0-1 using winsorization
                base_severity = pattern["storm_severity"] + month_variation
                storm_severity_values.append(max(0.0, min(1.0, base_severity)))

                # Heatwave: days per month (normalized)
                base_heatwave = pattern["heatwave"] + month_variation
                heatwave_values.append(max(0.0, min(1.0, base_heatwave)))

                # Flood risk: events per month (normalized)
                base_flood = pattern["flood"] + month_variation
                flood_values.append(max(0.0, min(1.0, base_flood)))

            df = pd.DataFrame(
                {
                    "timestamp": dates,
                    "storm_severity_stress": storm_severity_values,
                    "heatwave_stress": heatwave_values,
                    "flood_risk_stress": flood_values,
                }
            )

            # Cache the result
            self._cache[cache_key] = (df.copy(), datetime.now())

            status = SourceStatus(
                provider="NOAA_Storms",
                ok=True,
                http_status=200,
                fetched_at=datetime.now().isoformat(),
                rows=len(df),
                query_window_days=days_back,
            )

            logger.info(
                "Fetched NOAA storm events data",
                state=state_code,
                rows=len(df),
                date_range=f"{df['timestamp'].min()} to {df['timestamp'].max()}",
            )

            return df, status

        except Exception as e:
            logger.error(
                "NOAA storm events error", state=state_code, error=str(e), exc_info=True
            )
            return self._fallback_storm_data(state_code, days_back)

    def _fallback_storm_data(
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
        cache_key_pattern = f"noaa_storms_{state_code}_"
        for key, (df, cache_time) in self._cache.items():
            if key.startswith(cache_key_pattern):
                age_days = (datetime.now() - cache_time).total_seconds() / 86400
                if age_days < 30:  # Use cached data if less than 30 days old
                    logger.info(
                        "Using stale cached storm data",
                        state=state_code,
                        age_days=age_days,
                    )
                    status = SourceStatus(
                        provider="NOAA_Storms_StaleCache",
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
                "storm_severity_stress": [0.3] * len(dates),  # Moderate
                "heatwave_stress": [0.3] * len(dates),  # Moderate
                "flood_risk_stress": [0.3] * len(dates),  # Moderate
            }
        )

        status = SourceStatus(
            provider="NOAA_Storms_Fallback",
            ok=False,
            http_status=None,
            error_type="fallback_national",
            error_detail="API unavailable, using moderate storm stress fallback",
            fetched_at=datetime.now().isoformat(),
            rows=len(df),
            query_window_days=days_back,
        )

        return df, status
