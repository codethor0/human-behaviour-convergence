# SPDX-License-Identifier: PROPRIETARY
"""EIA (Energy Information Administration) API connector for energy prices and demand."""
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple, TYPE_CHECKING

import pandas as pd
import requests
import structlog

from app.services.ingestion.ci_offline_data import (
    is_ci_offline_mode,
    get_ci_energy_data,
)

if TYPE_CHECKING:
    from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.eia_energy")

# EIA API base URL (v2)
EIA_API_BASE = "https://api.eia.gov/v2"

# Common EIA series IDs (no API key required for public data)
EIA_SERIES = {
    "petroleum_price": "PET.EER_EPD2DXL0_PTE_R10D_MBBL.A",  # Weekly U.S. All Grades All Formulations Retail Gasoline Prices
    "natural_gas_price": "NG.N3010US3.M",  # Natural Gas Price (Henry Hub)
    "electricity_demand": "EBA.US48-ALL.D.H",  # U.S. 48 States Electricity Demand
    "crude_oil_price": "PET.RWTC.D",  # Cushing, OK WTI Spot Price
    "electricity_consumption": "ELEC.CONS_TOT.COW-US-99.M",  # Total Electricity Consumption
    "renewable_energy": "RE.TOT.COWUS-99.M",  # Total Renewable Energy Generation
    "total_energy_consumption": "TOTAL.ETCEUS.M",  # Total Energy Consumption
}


class EIAEnergyFetcher:
    """
    Fetch energy prices and demand data from EIA (Energy Information Administration) API.

    EIA Open Data API v2: https://www.eia.gov/opendata/
    No API key required for public data series.
    Rate limits: Reasonable (no strict documented limits for public data)

    Provides:
    - Energy price signals (gasoline, natural gas, crude oil)
    - Electricity demand/grid stress indicators
    - Energy-related economic stress proxies
    """

    def __init__(self, api_key: Optional[str] = None, cache_duration_minutes: int = 60):
        """
        Initialize EIA energy fetcher.

        Args:
            api_key: EIA API key (optional, not required for public series)
            cache_duration_minutes: Cache duration for API responses
                (default: 60 minutes)
        """
        self.api_key = api_key or os.getenv("EIA_API_KEY")
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

    def fetch_series(
        self,
        series_id: str,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, "SourceStatus"]:  # noqa: F821
        """
        Fetch an EIA time series.

        Args:
            series_id: EIA series ID (e.g., "PET.RWTC.D" for crude oil price)
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            Tuple of (DataFrame with columns: ['timestamp', 'value'], SourceStatus)
            Returns empty DataFrame if series not found or on error
        """
        from app.services.ingestion.gdelt_events import SourceStatus

        # CI offline mode: return synthetic deterministic data
        if is_ci_offline_mode():
            logger.info("Using CI offline mode for EIA energy data")
            df = get_ci_energy_data(series_id)
            status = SourceStatus(
                provider="CI_Synthetic_EIA",
                ok=True,
                http_status=200,
                fetched_at=datetime.now().isoformat(),
                rows=len(df),
                query_window_days=days_back,
            )
            return df, status

        # Check cache
        cache_key = f"{series_id}_{days_back}"
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached EIA data", series_id=series_id)
                status = SourceStatus(
                    provider="EIA",
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
            # EIA API v2 endpoint structure
            # Example: /data/?api_key={key}&data[0]=series_id&data[1]=start_date&data[2]=end_date
            url = f"{EIA_API_BASE}/data"
            params = {
                "data[0]": series_id,
                "data[1]": start_date.strftime("%Y-%m-%d"),
                "data[2]": end_date.strftime("%Y-%m-%d"),
                "sort[0][column]": "period",
                "sort[0][direction]": "asc",
                "length": 5000,  # Max records per request
            }

            # Add API key if available (optional for public data)
            if self.api_key:
                params["api_key"] = self.api_key

            logger.info("Fetching EIA data", series_id=series_id, url=url)

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Parse EIA response structure
            if "response" not in data or "data" not in data["response"]:
                logger.warning("Unexpected EIA response structure", series_id=series_id)
                status = SourceStatus(
                    provider="EIA",
                    ok=False,
                    http_status=response.status_code,
                    error_type="non_json",
                    error_detail="Unexpected response structure",
                    fetched_at=datetime.now().isoformat(),
                    rows=0,
                    query_window_days=days_back,
                )
                return pd.DataFrame(columns=["timestamp", "value"]), status

            records = data["response"]["data"]

            if not records:
                logger.warning("EIA returned empty data", series_id=series_id)
                status = SourceStatus(
                    provider="EIA",
                    ok=True,
                    http_status=response.status_code,
                    fetched_at=datetime.now().isoformat(),
                    rows=0,
                    query_window_days=days_back,
                )
                return pd.DataFrame(columns=["timestamp", "value"]), status

            # Convert to DataFrame
            df = pd.DataFrame(records)
            df = df.rename(columns={"period": "timestamp", "value": "value"})

            # Ensure timestamp is datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Sort by timestamp
            df = df.sort_values("timestamp").reset_index(drop=True)

            # Filter to requested date range
            df = df[df["timestamp"] >= start_date].copy()

            # Cache the result
            self._cache[cache_key] = (df.copy(), datetime.now())

            status = SourceStatus(
                provider="EIA",
                ok=True,
                http_status=response.status_code,
                fetched_at=datetime.now().isoformat(),
                rows=len(df),
                query_window_days=days_back,
            )

            logger.info(
                "Fetched EIA data",
                series_id=series_id,
                rows=len(df),
                date_range=f"{df['timestamp'].min()} to {df['timestamp'].max()}",
            )

            return df[["timestamp", "value"]], status

        except requests.exceptions.Timeout:
            logger.error("EIA API timeout", series_id=series_id)
            status = SourceStatus(
                provider="EIA",
                ok=False,
                http_status=None,
                error_type="timeout",
                error_detail="Request timeout",
                fetched_at=datetime.now().isoformat(),
                rows=0,
                query_window_days=days_back,
            )
            return pd.DataFrame(columns=["timestamp", "value"]), status

        except requests.exceptions.HTTPError as e:
            logger.error(
                "EIA API HTTP error",
                series_id=series_id,
                status_code=e.response.status_code,
            )
            status = SourceStatus(
                provider="EIA",
                ok=False,
                http_status=e.response.status_code,
                error_type="http_error",
                error_detail=str(e),
                fetched_at=datetime.now().isoformat(),
                rows=0,
                query_window_days=days_back,
            )
            return pd.DataFrame(columns=["timestamp", "value"]), status

        except Exception as e:
            logger.error(
                "EIA API error", series_id=series_id, error=str(e), exc_info=True
            )
            status = SourceStatus(
                provider="EIA",
                ok=False,
                http_status=None,
                error_type="other",
                error_detail=str(e),
                fetched_at=datetime.now().isoformat(),
                rows=0,
                query_window_days=days_back,
            )
            return pd.DataFrame(columns=["timestamp", "value"]), status

    def fetch_energy_stress_index(
        self, days_back: int = 30
    ) -> Tuple[pd.DataFrame, "SourceStatus"]:  # noqa: F821
        """
        Compute a composite energy stress index from multiple EIA series.

        Combines:
        - Gasoline price (normalized)
        - Natural gas price (normalized)
        - Electricity demand (normalized)

        Returns:
            DataFrame with columns: ['timestamp', 'energy_stress_index']
            Higher values indicate higher energy-related stress
        """
        from app.services.ingestion.gdelt_events import SourceStatus

        try:
            # Fetch multiple series
            gasoline_df, gasoline_status = self.fetch_series(
                EIA_SERIES["petroleum_price"], days_back=days_back
            )
            natural_gas_df, natural_gas_status = self.fetch_series(
                EIA_SERIES["natural_gas_price"], days_back=days_back
            )
            electricity_df, electricity_status = self.fetch_series(
                EIA_SERIES["electricity_demand"], days_back=days_back
            )

            # Check if we have sufficient data
            if (
                len(gasoline_df) == 0
                and len(natural_gas_df) == 0
                and len(electricity_df) == 0
            ):
                status = SourceStatus(
                    provider="EIA",
                    ok=False,
                    http_status=None,
                    error_type="empty",
                    error_detail="All EIA series returned empty",
                    fetched_at=datetime.now().isoformat(),
                    rows=0,
                    query_window_days=days_back,
                )
                return (
                    pd.DataFrame(columns=["timestamp", "energy_stress_index"]),
                    status,
                )

            # Merge series on timestamp
            merged = pd.DataFrame()
            if len(gasoline_df) > 0:
                merged = gasoline_df.rename(columns={"value": "gasoline_price"})
            if len(natural_gas_df) > 0:
                if len(merged) > 0:
                    merged = merged.merge(
                        natural_gas_df.rename(columns={"value": "natural_gas_price"}),
                        on="timestamp",
                        how="outer",
                    )
                else:
                    merged = natural_gas_df.rename(
                        columns={"value": "natural_gas_price"}
                    )
            if len(electricity_df) > 0:
                if len(merged) > 0:
                    merged = merged.merge(
                        electricity_df.rename(columns={"value": "electricity_demand"}),
                        on="timestamp",
                        how="outer",
                    )
                else:
                    merged = electricity_df.rename(
                        columns={"value": "electricity_demand"}
                    )

            # Normalize each series (0-1 scale) and compute composite
            for col in ["gasoline_price", "natural_gas_price", "electricity_demand"]:
                if col in merged.columns:
                    col_min = merged[col].min()
                    col_max = merged[col].max()
                    if col_max > col_min:
                        merged[f"{col}_normalized"] = (merged[col] - col_min) / (
                            col_max - col_min
                        )
                    else:
                        merged[f"{col}_normalized"] = 0.5

            # Compute composite stress index (average of normalized values)
            normalized_cols = [
                col for col in merged.columns if col.endswith("_normalized")
            ]
            if normalized_cols:
                merged["energy_stress_index"] = merged[normalized_cols].mean(axis=1)
            else:
                merged["energy_stress_index"] = 0.5  # Default neutral

            result_df = merged[["timestamp", "energy_stress_index"]].copy()
            result_df = result_df.sort_values("timestamp").reset_index(drop=True)

            # Determine overall status (ok if at least one series succeeded)
            overall_ok = (
                gasoline_status.ok or natural_gas_status.ok or electricity_status.ok
            )

            status = SourceStatus(
                provider="EIA",
                ok=overall_ok,
                http_status=200 if overall_ok else None,
                fetched_at=datetime.now().isoformat(),
                rows=len(result_df),
                query_window_days=days_back,
            )

            return result_df, status

        except Exception as e:
            logger.error(
                "Error computing energy stress index", error=str(e), exc_info=True
            )
            from app.services.ingestion.gdelt_events import SourceStatus

            status = SourceStatus(
                provider="EIA",
                ok=False,
                http_status=None,
                error_type="other",
                error_detail=str(e),
                fetched_at=datetime.now().isoformat(),
                rows=0,
                query_window_days=days_back,
            )
            return pd.DataFrame(columns=["timestamp", "energy_stress_index"]), status
