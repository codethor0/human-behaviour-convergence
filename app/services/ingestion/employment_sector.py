# SPDX-License-Identifier: PROPRIETARY
"""Bureau of Labor Statistics (BLS) API connector for employment sector data."""
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict

import pandas as pd
import requests
import structlog

from app.services.ingestion.ci_offline_data import (
    is_ci_offline_mode,
)
from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.employment_sector")

# BLS API base URL
BLS_API_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data"

# BLS series IDs for employment by sector
BLS_SERIES = {
    "total_nonfarm": "CES0000000001",  # Total Nonfarm Employment
    "manufacturing": "CES3000000001",  # Manufacturing
    "retail_trade": "CES4244000001",  # Retail Trade
    "leisure_hospitality": "CES7000000001",  # Leisure and Hospitality
    "government": "CES9000000001",  # Government
    "healthcare": "CES6562000001",  # Health Care and Social Assistance
    "construction": "CES2000000001",  # Construction
    "financial_activities": "CES5500000001",  # Financial Activities
}


class EmploymentSectorFetcher:
    """
    Fetch employment data by sector from BLS (Bureau of Labor Statistics) API.
    
    BLS Public Data API: https://www.bls.gov/developers/api_signature_v2.htm
    No API key required for public data.
    Rate limits: 500 requests per day per IP
    
    Provides:
    - Sector-specific employment stress indices
    - Job creation/destruction trends by industry
    - Economic resilience indicators
    """

    def __init__(self, api_key: Optional[str] = None, cache_duration_minutes: int = 1440):
        """
        Initialize employment sector fetcher.
        
        Args:
            api_key: BLS API key (optional, not required for public data)
            cache_duration_minutes: Cache duration (default: 1440 = 24 hours,
                since BLS data updates monthly)
        """
        self.api_key = api_key or os.getenv("BLS_API_KEY")
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

    def fetch_sector_employment_stress(
        self,
        sector: str = "total_nonfarm",
        days_back: int = 365,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch employment data for a specific sector and compute stress index.
        
        Employment stress: Negative job growth = high stress (1.0),
        positive job growth = low stress (0.0)
        
        Args:
            sector: Sector key from BLS_SERIES (default: "total_nonfarm")
            days_back: Number of days of historical data (default: 365)
            use_cache: Whether to use cached data (default: True)
            
        Returns:
            Tuple of (DataFrame with columns: ['timestamp', 'employment_stress', 
            'employment_value', 'job_growth_rate'], SourceStatus)
        """
        # CI offline mode: return synthetic deterministic data
        if is_ci_offline_mode():
            logger.info("Using CI offline mode for BLS employment", sector=sector)
            today = pd.Timestamp.today().normalize()
            # BLS data is monthly, so generate monthly dates
            months_back = max(1, days_back // 30)
            dates = pd.date_range(end=today, periods=months_back, freq="MS")  # Month start
            
            # Simulate employment with some volatility
            base_employment = 150_000_000  # ~150M jobs baseline
            values = base_employment + (pd.Series(range(len(dates))) % 12 - 6) * 1_000_000
            
            # Compute monthly growth rate
            growth_rates = values.pct_change() * 100.0
            growth_rates = growth_rates.fillna(0.0)
            
            # Normalize to stress: negative growth = high stress
            min_growth = max(growth_rates.min(), -5.0)
            max_growth = min(growth_rates.max(), 5.0)
            if max_growth > min_growth:
                stress = (max_growth - growth_rates) / (max_growth - min_growth)
                stress = stress.clip(0.0, 1.0)
            else:
                stress = pd.Series([0.5] * len(dates))
            
            df = pd.DataFrame({
                "timestamp": dates,
                "employment_stress": stress.values,
                "employment_value": values.values,
                "job_growth_rate": growth_rates.values,
            })
            status = SourceStatus(
                provider="CI_Synthetic_BLS",
                ok=True,
                http_status=200,
                fetched_at=datetime.now().isoformat(),
                rows=len(df),
            )
            return df, status

        if sector not in BLS_SERIES:
            logger.warning("Unknown sector", sector=sector)
            return self._fallback_employment_data(sector, days_back)

        cache_key = f"bls_{sector}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached BLS employment data", sector=sector)
                status = SourceStatus(
                    provider="BLS_Cached",
                    ok=True,
                    http_status=200,
                    fetched_at=cache_time.isoformat(),
                    rows=len(df),
                )
                return df.copy(), status

        # Calculate date range (BLS data is monthly)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # BLS API expects YYYYMM format
        start_year_month = start_date.strftime("%Y%m")
        end_year_month = end_date.strftime("%Y%m")

        try:
            # BLS API v2 format
            series_id = BLS_SERIES[sector]
            
            payload = {
                "seriesid": [series_id],
                "startyear": start_date.year,
                "endyear": end_date.year,
            }
            
            if self.api_key:
                payload["registrationKey"] = self.api_key

            logger.info("Fetching BLS employment data", sector=sector, series_id=series_id)
            response = requests.post(BLS_API_BASE, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "REQUEST_SUCCEEDED":
                error_msg = data.get("message", ["Unknown error"])[0] if isinstance(data.get("message"), list) else str(data.get("message", "Unknown error"))
                logger.warning("BLS API request failed", sector=sector, error=error_msg)
                return self._fallback_employment_data(sector, days_back)

            results = data.get("Results", {})
            series_data = results.get("series", [])
            
            if not series_data:
                logger.warning("No series data in BLS response", sector=sector)
                return self._fallback_employment_data(sector, days_back)

            # Parse time series data
            records = []
            for series in series_data:
                data_points = series.get("data", [])
                for point in reversed(data_points):  # BLS returns newest first
                    year = int(point.get("year", 0))
                    period = point.get("period", "")
                    value_str = point.get("value", "")
                    
                    if not value_str or value_str == "-":
                        continue
                    
                    try:
                        # Parse period (M01-M12 for monthly)
                        if period.startswith("M"):
                            month = int(period[1:])
                            timestamp = pd.Timestamp(year=year, month=month, day=1)
                            value = float(value_str)
                            records.append({
                                "timestamp": timestamp,
                                "employment_value": value,
                            })
                    except (ValueError, TypeError):
                        continue

            if not records:
                logger.warning("No valid records after parsing", sector=sector)
                return self._fallback_employment_data(sector, days_back)

            df = pd.DataFrame(records)
            df = df.sort_values("timestamp").reset_index(drop=True)
            df = df[df["timestamp"] >= start_date].copy()

            # Compute monthly growth rate
            df["job_growth_rate"] = df["employment_value"].pct_change() * 100.0
            
            # Normalize to stress index: negative growth = high stress
            min_growth = max(df["job_growth_rate"].min(), -5.0)
            max_growth = min(df["job_growth_rate"].max(), 5.0)
            
            if max_growth > min_growth:
                df["employment_stress"] = (max_growth - df["job_growth_rate"]) / (max_growth - min_growth)
                df["employment_stress"] = df["employment_stress"].clip(0.0, 1.0)
            else:
                df["employment_stress"] = 0.5

            result_df = df[["timestamp", "employment_stress", "employment_value", "job_growth_rate"]].copy()

            # Cache result
            self._cache[cache_key] = (result_df.copy(), datetime.now())

            status = SourceStatus(
                provider="BLS_Employment",
                ok=True,
                http_status=response.status_code,
                fetched_at=datetime.now().isoformat(),
                rows=len(result_df),
            )

            logger.info(
                "Successfully fetched BLS employment data",
                sector=sector,
                rows=len(result_df),
                date_range=(result_df["timestamp"].min(), result_df["timestamp"].max()),
            )

            return result_df, status

        except requests.exceptions.RequestException as e:
            logger.error("Error fetching BLS employment data", sector=sector, error=str(e), exc_info=True)
            return self._fallback_employment_data(sector, days_back)
        except Exception as e:
            logger.error("Unexpected error fetching BLS employment data", sector=sector, error=str(e), exc_info=True)
            return self._fallback_employment_data(sector, days_back)

    def _fallback_employment_data(
        self, sector: str, days_back: int
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """Fallback to default values when API fails."""
        today = pd.Timestamp.today().normalize()
        months_back = max(1, days_back // 30)
        dates = pd.date_range(end=today, periods=months_back, freq="MS")
        df = pd.DataFrame({
            "timestamp": dates,
            "employment_stress": [0.5] * len(dates),
            "employment_value": [150_000_000] * len(dates),
            "job_growth_rate": [0.0] * len(dates),
        })

        status = SourceStatus(
            provider="BLS_Employment_Fallback",
            ok=False,
            http_status=None,
            error_type="fallback",
            error_detail="API unavailable, using default values",
            fetched_at=datetime.now().isoformat(),
            rows=len(df),
        )

        return df, status
