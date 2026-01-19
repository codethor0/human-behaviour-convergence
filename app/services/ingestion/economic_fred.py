# SPDX-License-Identifier: PROPRIETARY
"""FRED API connector for economic indicators."""
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests
import structlog

logger = structlog.get_logger("ingestion.economic_fred")

# FRED API base URL
FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Common FRED series IDs
FRED_SERIES = {
    "consumer_sentiment": "UMCSENT",  # University of Michigan Consumer Sentiment Index
    "unemployment_rate": "UNRATE",  # Unemployment Rate
    "jobless_claims": "ICSA",  # Initial Jobless Claims
    "gdp_growth": "A191RL1Q225SBEA",  # Real Gross Domestic Product (quarterly, annualized %)
    "cpi_all_items": "CPIAUCSL",  # Consumer Price Index for All Urban Consumers: All Items
    "cpi_inflation": "CPIAUCSL",  # Same as CPI, but we'll compute YoY % change
}


class FREDEconomicFetcher:
    """
    Fetch economic indicators from FRED (Federal Reserve Economic Data) API.

    Requires FRED_API_KEY environment variable.
    Free API key available at: https://fred.stlouisfed.org/docs/api/api_key.html

    Rate limits: 120 requests per 120 seconds
    """

    def __init__(self, api_key: Optional[str] = None, cache_duration_minutes: int = 60):
        """
        Initialize FRED economic fetcher.

        Args:
            api_key: FRED API key (defaults to FRED_API_KEY env var)
            cache_duration_minutes: Cache duration for API responses
                (default: 60 minutes)
        """
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

        if not self.api_key:
            logger.warning(
                "FRED_API_KEY not set; FRED economic indicators will return empty data"
            )

    def fetch_series(
        self,
        series_id: str,
        days_back: int = 30,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch a FRED time series.

        Args:
            series_id: FRED series ID (e.g., "UMCSENT", "UNRATE", "ICSA")
            days_back: Number of days of historical data to fetch (default: 30)
            use_cache: Whether to use cached data if available (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'value']
            Returns empty DataFrame if API key not set or on error
        """
        if not self.api_key:
            logger.warning("FRED_API_KEY not set, returning empty DataFrame")
            return pd.DataFrame(columns=["timestamp", "value"])

        # Check cache
        cache_key = f"{series_id}_{days_back}"
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached FRED data", series_id=series_id)
                return df.copy()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        try:
            # FRED API request
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "observation_start": start_date.strftime("%Y-%m-%d"),
                "observation_end": end_date.strftime("%Y-%m-%d"),
                "sort_order": "asc",
            }

            logger.info("Fetching FRED data", series_id=series_id, days_back=days_back)
            response = requests.get(FRED_API_BASE, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Parse observations
            if "observations" not in data:
                logger.warning("No observations in FRED response", series_id=series_id)
                return pd.DataFrame(columns=["timestamp", "value"])

            observations = data["observations"]
            if not observations:
                logger.warning(
                    "Empty observations in FRED response", series_id=series_id
                )
                return pd.DataFrame(columns=["timestamp", "value"])

            # Convert to DataFrame
            records = []
            for obs in observations:
                date_str = obs.get("date")
                value_str = obs.get("value")

                # Skip missing values (FRED uses "." for missing)
                if value_str == "." or value_str is None:
                    continue

                try:
                    value = float(value_str)
                    records.append({"timestamp": date_str, "value": value})
                except (ValueError, TypeError):
                    logger.debug(
                        "Skipping invalid value",
                        series_id=series_id,
                        date=date_str,
                        value=value_str,
                    )
                    continue

            if not records:
                logger.warning(
                    "No valid observations after parsing", series_id=series_id
                )
                return pd.DataFrame(columns=["timestamp", "value"])

            df = pd.DataFrame(records)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Sort by timestamp
            df = df.sort_values("timestamp").reset_index(drop=True)

            # Cache result
            self._cache[cache_key] = (df.copy(), datetime.now())

            logger.info(
                "Successfully fetched FRED data",
                series_id=series_id,
                rows=len(df),
                date_range=(df["timestamp"].min(), df["timestamp"].max()),
            )

            return df

        except requests.exceptions.RequestException as e:
            logger.error(
                "Error fetching FRED data",
                series_id=series_id,
                error=str(e),
                exc_info=True,
            )
            return pd.DataFrame(columns=["timestamp", "value"])

        except Exception as e:
            logger.error(
                "Unexpected error fetching FRED data",
                series_id=series_id,
                error=str(e),
                exc_info=True,
            )
            return pd.DataFrame(columns=["timestamp", "value"])

    def fetch_consumer_sentiment(
        self, days_back: int = 30, use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch University of Michigan Consumer Sentiment Index.

        Args:
            days_back: Number of days of historical data (default: 30)
            use_cache: Whether to use cached data (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'consumer_sentiment']
            Values normalized to [0.0, 1.0] where 1.0 = maximum sentiment (low stress)
        """
        df = self.fetch_series(FRED_SERIES["consumer_sentiment"], days_back, use_cache)

        if df.empty:
            return pd.DataFrame(columns=["timestamp", "consumer_sentiment"])

        # Normalize to [0.0, 1.0]
        # Consumer sentiment typically ranges from ~50-120
        # Higher sentiment = lower economic stress
        min_val = df["value"].min()
        max_val = df["value"].max()
        if max_val > min_val:
            df["consumer_sentiment"] = (df["value"] - min_val) / (max_val - min_val)
        else:
            df["consumer_sentiment"] = 0.5  # Default neutral

        # Invert: high sentiment = low stress, so invert for stress index
        df["consumer_sentiment"] = 1.0 - df["consumer_sentiment"]

        return df[["timestamp", "consumer_sentiment"]]

    def fetch_unemployment_rate(
        self, days_back: int = 30, use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch U.S. Unemployment Rate.

        Args:
            days_back: Number of days of historical data (default: 30)
            use_cache: Whether to use cached data (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'unemployment_rate']
            Values normalized to [0.0, 1.0] where 1.0 = maximum unemployment
                (high stress)
        """
        df = self.fetch_series(FRED_SERIES["unemployment_rate"], days_back, use_cache)

        if df.empty:
            return pd.DataFrame(columns=["timestamp", "unemployment_rate"])

        # Normalize to [0.0, 1.0]
        # Unemployment rate typically ranges from ~3-15%
        min_val = df["value"].min()
        max_val = df["value"].max()
        if max_val > min_val:
            df["unemployment_rate"] = (df["value"] - min_val) / (max_val - min_val)
        else:
            df["unemployment_rate"] = 0.5  # Default neutral

        return df[["timestamp", "unemployment_rate"]]

    def fetch_jobless_claims(
        self, days_back: int = 30, use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch Initial Jobless Claims (weekly).

        Args:
            days_back: Number of days of historical data (default: 30)
            use_cache: Whether to use cached data (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'jobless_claims']
            Values normalized to [0.0, 1.0] where 1.0 = maximum claims (high stress)
        """
        df = self.fetch_series(FRED_SERIES["jobless_claims"], days_back, use_cache)

        if df.empty:
            return pd.DataFrame(columns=["timestamp", "jobless_claims"])

        # Normalize to [0.0, 1.0]
        # Jobless claims typically range from ~200k-6M
        min_val = df["value"].min()
        max_val = df["value"].max()
        if max_val > min_val:
            df["jobless_claims"] = (df["value"] - min_val) / (max_val - min_val)
        else:
            df["jobless_claims"] = 0.5  # Default neutral

            return df[["timestamp", "jobless_claims"]]

    def fetch_gdp_growth(
        self, days_back: int = 365, use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch Real GDP Growth Rate (quarterly, annualized %).

        Args:
            days_back: Number of days of historical data (default: 365 to get quarterly data)
            use_cache: Whether to use cached data (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'gdp_growth']
            Values are percentage points (e.g., 2.5 = 2.5% annualized growth)
            Returns empty DataFrame if API key not set or on error
        """
        df = self.fetch_series(FRED_SERIES["gdp_growth"], days_back, use_cache)

        if df.empty:
            return pd.DataFrame(columns=["timestamp", "gdp_growth"])

        # GDP growth is already in percentage points, normalize to [0.0, 1.0] stress index
        # Negative growth = high stress, positive growth = low stress
        # Typical range: -10% to +10% annualized
        df = df.copy()
        df["gdp_growth"] = df["value"]

        # Normalize: negative growth = high stress (1.0), positive growth = low stress (0.0)
        # Use historical min/max or fixed bounds for normalization
        min_val = max(df["gdp_growth"].min(), -10.0)  # Cap at -10%
        max_val = min(df["gdp_growth"].max(), 10.0)  # Cap at +10%

        if max_val > min_val:
            # Normalize: growth of -10% = 1.0 stress, growth of +10% = 0.0 stress
            df["gdp_growth_stress"] = (max_val - df["gdp_growth"]) / (max_val - min_val)
            df["gdp_growth_stress"] = df["gdp_growth_stress"].clip(0.0, 1.0)
        else:
            df["gdp_growth_stress"] = 0.5  # Default neutral

        return df[["timestamp", "gdp_growth", "gdp_growth_stress"]]

    def fetch_cpi_inflation(
        self, days_back: int = 365, use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch Consumer Price Index and compute YoY inflation rate.

        Args:
            days_back: Number of days of historical data (default: 365 for YoY calculation)
            use_cache: Whether to use cached data (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'cpi_value', 'cpi_inflation']
            cpi_inflation is YoY % change, normalized to [0.0, 1.0] stress index
            Returns empty DataFrame if API key not set or on error
        """
        df = self.fetch_series(FRED_SERIES["cpi_all_items"], days_back, use_cache)

        if df.empty:
            return pd.DataFrame(columns=["timestamp", "cpi_value", "cpi_inflation"])

        # Calculate YoY inflation rate
        df = df.copy()
        df["cpi_value"] = df["value"]
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Calculate YoY % change (12 months back)
        df["cpi_inflation"] = df["cpi_value"].pct_change(periods=12) * 100.0

        # Normalize inflation to [0.0, 1.0] stress index
        # High inflation = high stress (typically 0-15% range for normalization)
        df["cpi_inflation_stress"] = df["cpi_inflation"].fillna(0.0)

        # Normalize: 0% inflation = 0.0 stress, 15%+ inflation = 1.0 stress
        min_inflation = 0.0
        max_inflation = 15.0

        df["cpi_inflation_stress"] = (
            (df["cpi_inflation_stress"] - min_inflation)
            / (max_inflation - min_inflation)
        ).clip(0.0, 1.0)

        return df[["timestamp", "cpi_value", "cpi_inflation", "cpi_inflation_stress"]]
