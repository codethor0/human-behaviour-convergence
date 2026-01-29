# SPDX-License-Identifier: PROPRIETARY
"""FRED API connector for consumer spending data (expanding existing economic fetcher)."""
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple

import pandas as pd
import requests
import structlog

from app.services.ingestion.ci_offline_data import (
    is_ci_offline_mode,
)
from app.services.ingestion.gdelt_events import SourceStatus

logger = structlog.get_logger("ingestion.consumer_spending")

# FRED API base URL
FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"

# FRED series IDs for consumer spending
FRED_SPENDING_SERIES = {
    "retail_sales": "RSXFS",  # Advance Retail Sales: Retail Trade
    "personal_consumption": "PCECC96",  # Real Personal Consumption Expenditures
    "consumer_credit": "TOTALSL",  # Total Consumer Credit Outstanding
}


class ConsumerSpendingFetcher:
    """
    Fetch consumer spending indicators from FRED (Federal Reserve Economic Data) API.

    Requires FRED_API_KEY environment variable.
    Free API key available at: https://fred.stlouisfed.org/docs/api/api_key.html

    Rate limits: 120 requests per 120 seconds

    Provides:
    - Retail sales stress index
    - Consumer spending trends
    - Credit utilization indicators
    """

    def __init__(self, api_key: Optional[str] = None, cache_duration_minutes: int = 60):
        """
        Initialize consumer spending fetcher.

        Args:
            api_key: FRED API key (defaults to FRED_API_KEY env var)
            cache_duration_minutes: Cache duration (default: 60 minutes)
        """
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

        if not self.api_key:
            logger.warning(
                "FRED_API_KEY not set; consumer spending indicators will return empty data"
            )

    def fetch_retail_sales_stress(
        self,
        days_back: int = 90,
        use_cache: bool = True,
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """
        Fetch retail sales data and compute spending stress index.

        Retail sales stress: Lower sales growth = higher economic stress

        Args:
            days_back: Number of days of historical data (default: 90)
            use_cache: Whether to use cached data (default: True)

        Returns:
            Tuple of (DataFrame with columns: ['timestamp', 'retail_sales_stress',
            'retail_sales_value'], SourceStatus)
        """
        # CI offline mode: return synthetic deterministic data
        if is_ci_offline_mode():
            logger.info("Using CI offline mode for retail sales")
            today = pd.Timestamp.today().normalize()
            dates = pd.date_range(end=today, periods=min(days_back, 90), freq="D")
            # Simulate retail sales with some volatility
            base_sales = 500_000_000_000  # $500B baseline
            values = (
                base_sales + (pd.Series(range(len(dates))) % 30 - 15) * 10_000_000_000
            )
            # Normalize to stress index: lower sales = higher stress
            min_sales = values.min()
            max_sales = values.max()
            stress = 1.0 - ((values - min_sales) / (max_sales - min_sales))

            df = pd.DataFrame(
                {
                    "timestamp": dates,
                    "retail_sales_stress": stress.values,
                    "retail_sales_value": values.values,
                }
            )
            status = SourceStatus(
                provider="CI_Synthetic_FRED_Retail",
                ok=True,
                http_status=200,
                fetched_at=datetime.now().isoformat(),
                rows=len(df),
            )
            return df, status

        if not self.api_key:
            logger.warning("FRED_API_KEY not set, returning empty DataFrame")
            return pd.DataFrame(
                columns=["timestamp", "retail_sales_stress", "retail_sales_value"]
            ), SourceStatus(
                provider="FRED_Retail",
                ok=False,
                http_status=None,
                error_type="missing_key",
                error_detail="FRED_API_KEY not set",
                fetched_at=datetime.now().isoformat(),
                rows=0,
            )

        cache_key = f"fred_retail_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached FRED retail sales data")
                status = SourceStatus(
                    provider="FRED_Retail_Cached",
                    ok=True,
                    http_status=200,
                    fetched_at=cache_time.isoformat(),
                    rows=len(df),
                )
                return df.copy(), status

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        try:
            params = {
                "series_id": FRED_SPENDING_SERIES["retail_sales"],
                "api_key": self.api_key,
                "file_type": "json",
                "observation_start": start_date.strftime("%Y-%m-%d"),
                "observation_end": end_date.strftime("%Y-%m-%d"),
                "sort_order": "asc",
            }

            logger.info("Fetching FRED retail sales data", days_back=days_back)
            response = requests.get(FRED_API_BASE, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if "observations" not in data or not data["observations"]:
                logger.warning("No observations in FRED retail sales response")
                return self._fallback_retail_data(days_back)

            # Parse observations
            records = []
            for obs in data["observations"]:
                date_str = obs.get("date")
                value_str = obs.get("value")

                if value_str == "." or value_str is None:
                    continue

                try:
                    value = float(value_str)
                    records.append({"timestamp": date_str, "retail_sales_value": value})
                except (ValueError, TypeError):
                    continue

            if not records:
                logger.warning("No valid observations after parsing")
                return self._fallback_retail_data(days_back)

            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)

            # Compute YoY growth rate
            df["yoy_growth"] = df["retail_sales_value"].pct_change(periods=12) * 100.0

            # Normalize to stress index: negative growth = high stress (1.0),
            # positive growth = low stress (0.0)
            # Typical range: -20% to +20%
            min_growth = max(df["yoy_growth"].min(), -20.0)
            max_growth = min(df["yoy_growth"].max(), 20.0)

            if max_growth > min_growth:
                df["retail_sales_stress"] = (max_growth - df["yoy_growth"]) / (
                    max_growth - min_growth
                )
                df["retail_sales_stress"] = df["retail_sales_stress"].clip(0.0, 1.0)
            else:
                df["retail_sales_stress"] = 0.5

            result_df = df[
                ["timestamp", "retail_sales_stress", "retail_sales_value"]
            ].copy()

            # Cache result
            self._cache[cache_key] = (result_df.copy(), datetime.now())

            status = SourceStatus(
                provider="FRED_Retail",
                ok=True,
                http_status=response.status_code,
                fetched_at=datetime.now().isoformat(),
                rows=len(result_df),
            )

            logger.info(
                "Successfully fetched FRED retail sales",
                rows=len(result_df),
                date_range=(result_df["timestamp"].min(), result_df["timestamp"].max()),
            )

            return result_df, status

        except requests.exceptions.RequestException as e:
            logger.error(
                "Error fetching FRED retail sales", error=str(e), exc_info=True
            )
            return self._fallback_retail_data(days_back)
        except Exception as e:
            logger.error(
                "Unexpected error fetching FRED retail sales",
                error=str(e),
                exc_info=True,
            )
            return self._fallback_retail_data(days_back)

    def _fallback_retail_data(
        self, days_back: int
    ) -> Tuple[pd.DataFrame, SourceStatus]:
        """Fallback to default values when API fails."""
        today = pd.Timestamp.today().normalize()
        dates = pd.date_range(end=today, periods=min(days_back, 30), freq="D")
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "retail_sales_stress": [0.5] * len(dates),
                "retail_sales_value": [500_000_000_000] * len(dates),
            }
        )

        status = SourceStatus(
            provider="FRED_Retail_Fallback",
            ok=False,
            http_status=None,
            error_type="fallback",
            error_detail="API unavailable, using default values",
            fetched_at=datetime.now().isoformat(),
            rows=len(df),
        )

        return df, status
