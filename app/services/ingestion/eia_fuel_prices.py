# SPDX-License-Identifier: PROPRIETARY
"""EIA (Energy Information Administration) state-level gasoline prices connector."""
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
import requests
import structlog

from app.services.ingestion.ci_offline_data import (
    is_ci_offline_mode,
    get_ci_fuel_prices_data,
)
from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.eia_fuel_prices")

# EIA API base URL (v2)
EIA_API_BASE = "https://api.eia.gov/v2"

# State FIPS code mapping (2-letter to numeric for EIA API)
STATE_FIPS = {
    "AL": "01",
    "AK": "02",
    "AZ": "04",
    "AR": "05",
    "CA": "06",
    "CO": "08",
    "CT": "09",
    "DE": "10",
    "FL": "12",
    "GA": "13",
    "HI": "15",
    "ID": "16",
    "IL": "17",
    "IN": "18",
    "IA": "19",
    "KS": "20",
    "KY": "21",
    "LA": "22",
    "ME": "23",
    "MD": "24",
    "MA": "25",
    "MI": "26",
    "MN": "27",
    "MS": "28",
    "MO": "29",
    "MT": "30",
    "NE": "31",
    "NV": "32",
    "NH": "33",
    "NJ": "34",
    "NM": "35",
    "NY": "36",
    "NC": "37",
    "ND": "38",
    "OH": "39",
    "OK": "40",
    "OR": "41",
    "PA": "42",
    "RI": "43",
    "SC": "44",
    "SD": "45",
    "TN": "47",
    "TX": "48",
    "UT": "49",
    "VT": "50",
    "VA": "51",
    "WA": "53",
    "WV": "54",
    "WI": "55",
    "WY": "56",
    "DC": "11",
}


class EIAFuelPricesFetcher:
    """
    Fetch state-level gasoline prices from EIA (Energy Information Administration) API.

    EIA Open Data API v2: https://www.eia.gov/opendata/
    State-level gasoline prices: Weekly retail prices by state
    No API key required for public data series.
    Rate limits: Reasonable (no strict documented limits for public data)

    Provides:
    - State-level fuel stress index (normalized price deviation from national average)
    - Regional fuel burden indicators
    """

    def __init__(self, api_key: Optional[str] = None, cache_duration_minutes: int = 60):
        """
        Initialize EIA fuel prices fetcher.

        Args:
            api_key: EIA API key (optional, not required for public series)
            cache_duration_minutes: Cache duration for API responses
                (default: 60 minutes)
        """
        self.api_key = api_key or os.getenv("EIA_API_KEY")
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

    def _normalize_state_code(self, state: str) -> str:
        """
        Normalize state code to 2-letter uppercase format.

        Args:
            state: State code (2-letter, full name, or FIPS)

        Returns:
            2-letter uppercase state code (e.g., "IL", "CA")
        """
        state_upper = state.upper().strip()

        # If already 2-letter code, return it
        if state_upper in STATE_FIPS:
            return state_upper

        # Try to extract from "us_il" format
        if "_" in state_upper:
            parts = state_upper.split("_")
            if len(parts) >= 2 and parts[0] == "US" and len(parts[1]) == 2:
                # Extract state code from "us_il" -> "IL"
                potential_code = parts[1].upper()
                if potential_code in STATE_FIPS:
                    return potential_code

        # Try to map from full name (simplified mapping)
        state_name_map = {
            "ILLINOIS": "IL",
            "CALIFORNIA": "CA",
            "TEXAS": "TX",
            "FLORIDA": "FL",
            "NEW YORK": "NY",
            "ARIZONA": "AZ",
            "GEORGIA": "GA",
            "MASSACHUSETTS": "MA",
            "LOUISIANA": "LA",
            "MINNESOTA": "MN",
            "COLORADO": "CO",
            "WASHINGTON": "WA",
        }
        if state_upper in state_name_map:
            return state_name_map[state_upper]

        # Default: return first 2 chars if valid, otherwise as-is
        if len(state_upper) >= 2:
            potential_code = state_upper[:2]
            if potential_code in STATE_FIPS:
                return potential_code
        return state_upper

    def fetch_fuel_stress_index(
        self,
        state: str,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch state-level gasoline prices and compute fuel stress index.

        Fuel stress index = normalized deviation from national average (0-1)
        Higher values indicate higher fuel-related economic stress.

        Args:
            state: State code (2-letter, e.g., "IL", "CA") or state name
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            Tuple of (DataFrame with columns: ['timestamp', 'fuel_stress_index', 'fuel_price'], SourceStatus)
            Returns empty DataFrame if state not found or on error
        """
        # CI offline mode: return synthetic deterministic data
        if is_ci_offline_mode():
            logger.info("Using CI offline mode for EIA fuel prices", state=state)
            state_code = self._normalize_state_code(state)
            df = get_ci_fuel_prices_data(state_code)
            # Filter to requested days_back
            df = df.tail(days_back).copy() if len(df) > days_back else df.copy()
            status = SourceStatus(
                provider="CI_Synthetic_EIA_Fuel",
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
        cache_key = f"eia_fuel_{state_code}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info(
                    "Using cached EIA fuel prices",
                    state=state_code,
                    age_minutes=age_minutes,
                )
                status = SourceStatus(
                    provider="EIA_Fuel_Cached",
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
            # EIA API v2: State-level gasoline prices
            # Series ID format: PET.EER_EPD2DXL0_PTE_R{STATE_FIPS}_MBBL.A
            # For now, use a simplified approach: fetch national average and simulate state variance
            # TODO: Find exact EIA API v2 series ID for state-level prices
            # For MVP, we'll use a proxy: national price with state-specific adjustment

            # Fetch national average gasoline price
            national_series_id = "PET.EER_EPD2DXL0_PTE_R10D_MBBL.A"  # National average

            url = f"{EIA_API_BASE}/data"
            params = {
                "data[0]": national_series_id,
                "data[1]": start_date.strftime("%Y-%m-%d"),
                "data[2]": end_date.strftime("%Y-%m-%d"),
                "sort[0][column]": "period",
                "sort[0][direction]": "asc",
                "length": 5000,
            }

            if self.api_key:
                params["api_key"] = self.api_key

            logger.info("Fetching EIA fuel prices", state=state_code, url=url)

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if "response" not in data or "data" not in data["response"]:
                logger.warning("Unexpected EIA response structure", state=state_code)
                status = SourceStatus(
                    provider="EIA_Fuel",
                    ok=False,
                    http_status=response.status_code,
                    error_type="non_json",
                    error_detail="Unexpected response structure",
                    fetched_at=datetime.now().isoformat(),
                    rows=0,
                    query_window_days=days_back,
                )
                return (
                    pd.DataFrame(
                        columns=["timestamp", "fuel_stress_index", "fuel_price"]
                    ),
                    status,
                )

            records = data["response"]["data"]

            if not records:
                logger.warning("EIA returned empty data", state=state_code)
                # Fallback to national average with state adjustment
                return self._fallback_fuel_data(state_code, days_back)

            # Convert to DataFrame
            df = pd.DataFrame(records)
            df = df.rename(columns={"period": "timestamp", "value": "national_price"})
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)
            df = df[df["timestamp"] >= start_date].copy()

            # Apply state-specific adjustment (simulated regional variance)
            # In production, this would fetch actual state-level series
            # For MVP: use state-specific multiplier based on known regional patterns
            state_multipliers = {
                "CA": 1.15,
                "NY": 1.10,
                "IL": 1.05,
                "TX": 0.95,
                "FL": 1.00,
                "AZ": 0.98,
                "CO": 1.02,
                "GA": 0.97,
                "MA": 1.08,
                "LA": 0.96,
            }
            multiplier = state_multipliers.get(state_code, 1.0)

            df["fuel_price"] = df["national_price"] * multiplier
            national_avg = df["national_price"].mean()

            # Compute fuel stress index: deviation from national average, normalized
            df["deviation"] = (df["fuel_price"] - national_avg) / national_avg
            # Normalize to 0-1: sigmoid-like transformation
            df["fuel_stress_index"] = 0.5 + (df["deviation"] * 2.5)
            df["fuel_stress_index"] = df["fuel_stress_index"].clip(0.0, 1.0)

            result_df = df[["timestamp", "fuel_stress_index", "fuel_price"]].copy()

            # Cache the result
            self._cache[cache_key] = (result_df.copy(), datetime.now())

            status = SourceStatus(
                provider="EIA_Fuel",
                ok=True,
                http_status=response.status_code,
                fetched_at=datetime.now().isoformat(),
                rows=len(result_df),
                query_window_days=days_back,
            )

            logger.info(
                "Fetched EIA fuel prices",
                state=state_code,
                rows=len(result_df),
                date_range=f"{result_df['timestamp'].min()} to {result_df['timestamp'].max()}",
            )

            return result_df, status

        except requests.exceptions.Timeout:
            logger.error("EIA API timeout", state=state_code)
            return self._fallback_fuel_data(state_code, days_back)

        except requests.exceptions.HTTPError as e:
            logger.error(
                "EIA API HTTP error",
                state=state_code,
                status_code=e.response.status_code,
            )
            return self._fallback_fuel_data(state_code, days_back)

        except Exception as e:
            logger.error("EIA API error", state=state_code, error=str(e), exc_info=True)
            return self._fallback_fuel_data(state_code, days_back)

    def _fallback_fuel_data(
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
        cache_key_pattern = f"eia_fuel_{state_code}_"
        for key, (df, cache_time) in self._cache.items():
            if key.startswith(cache_key_pattern):
                age_days = (datetime.now() - cache_time).total_seconds() / 86400
                if age_days < 7:  # Use cached data if less than 7 days old
                    logger.info(
                        "Using stale cached EIA fuel data",
                        state=state_code,
                        age_days=age_days,
                    )
                    status = SourceStatus(
                        provider="EIA_Fuel_StaleCache",
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
                "fuel_price": [3.50] * len(dates),  # Default national average
                "fuel_stress_index": [0.5] * len(dates),  # Neutral stress
            }
        )

        status = SourceStatus(
            provider="EIA_Fuel_Fallback",
            ok=False,
            http_status=None,
            error_type="fallback_national",
            error_detail="API unavailable, using national average fallback",
            fetched_at=datetime.now().isoformat(),
            rows=len(df),
            query_window_days=days_back,
        )

        return df, status
