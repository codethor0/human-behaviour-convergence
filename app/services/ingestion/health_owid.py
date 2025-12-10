# SPDX-License-Identifier: PROPRIETARY
"""Our World in Data (OWID) connector for public health indicators."""
from datetime import datetime, timedelta

import pandas as pd
import requests
import structlog

logger = structlog.get_logger("ingestion.health_owid")

# OWID data repository base URL
OWID_CSV_BASE = "https://raw.githubusercontent.com/owid/owid-datasets/master/datasets"


class OWIDHealthFetcher:
    """
    Fetch public health indicators from Our World in Data (OWID).

    OWID provides aggregated, country-level health data including:
    - COVID-19 metrics
    - Excess mortality
    - Vaccination rates
    - Hospitalization rates

    No authentication required.
    Data is updated daily via GitHub repository.

    Source: https://github.com/owid/owid-datasets
    """

    def __init__(self, cache_duration_minutes: int = 1440):
        """
        Initialize OWID health fetcher.

        Args:
            cache_duration_minutes: Cache duration for API responses
                (default: 1440 = 24 hours)
        """
        self.cache_duration_minutes = cache_duration_minutes
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}

    def fetch_excess_mortality(
        self,
        country: str = "United States",
        days_back: int = 90,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch excess mortality data from OWID.

        Excess mortality is the percentage above baseline mortality,
        indicating health burden beyond normal patterns.

        Args:
            country: Country name (default: "United States")
            days_back: Number of days of historical data (default: 90)
            use_cache: Whether to use cached data (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'excess_mortality']
            Values normalized to [0.0, 1.0] where 1.0 = maximum excess mortality
        """
        cache_key = f"owid_excess_{country}_{days_back}"

        # Check cache
        if use_cache and cache_key in self._cache:
            df, cache_time = self._cache[cache_key]
            age_minutes = (datetime.now() - cache_time).total_seconds() / 60
            if age_minutes < self.cache_duration_minutes:
                logger.info("Using cached OWID excess mortality data")
                return df.copy()

        try:
            # OWID excess mortality dataset
            # Using a simplified approach: fetch from CSV URL
            # Note: OWID structure may vary, this is a simplified implementation
            url = (
                f"{OWID_CSV_BASE}/Excess mortality - P-scores - All ages - P-scores.csv"
            )

            logger.info(
                "Fetching OWID excess mortality data",
                country=country,
                days_back=days_back,
            )

            response = requests.get(url, timeout=60)
            response.raise_for_status()

            # Read CSV
            from io import StringIO

            df = pd.read_csv(StringIO(response.text))

            # Filter by country and date range
            if "Entity" in df.columns:
                df = df[df["Entity"] == country]
            elif "Country" in df.columns:
                df = df[df["Country"] == country]

            if df.empty:
                logger.warning(
                    "No data found for country",
                    country=country,
                )
                return pd.DataFrame(columns=["timestamp", "excess_mortality"])

            # Find date column (could be "Date", "Day", "Year", etc.)
            date_col = None
            for col in ["Date", "Day", "date", "day"]:
                if col in df.columns:
                    date_col = col
                    break

            if date_col is None:
                logger.warning("No date column found in OWID data")
                return pd.DataFrame(columns=["timestamp", "excess_mortality"])

            # Find excess mortality column
            excess_col = None
            for col in df.columns:
                if "excess" in col.lower() or "p-score" in col.lower():
                    excess_col = col
                    break

            if excess_col is None:
                logger.warning("No excess mortality column found")
                return pd.DataFrame(columns=["timestamp", "excess_mortality"])

            # Convert date and filter by date range
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=[date_col, excess_col])

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            df = df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]

            if df.empty:
                logger.warning("No data in date range")
                return pd.DataFrame(columns=["timestamp", "excess_mortality"])

            # Extract and normalize
            result_df = pd.DataFrame(
                {
                    "timestamp": df[date_col],
                    "excess_mortality": df[excess_col],
                }
            )

            # Normalize to [0.0, 1.0]
            min_val = result_df["excess_mortality"].min()
            max_val = result_df["excess_mortality"].max()

            if max_val > min_val:
                result_df["excess_mortality"] = (
                    result_df["excess_mortality"] - min_val
                ) / (max_val - min_val)
            else:
                result_df["excess_mortality"] = 0.5

            result_df = result_df.sort_values("timestamp").reset_index(drop=True)

            # Cache result
            self._cache[cache_key] = (result_df.copy(), datetime.now())

            logger.info(
                "Successfully fetched OWID excess mortality data",
                rows=len(result_df),
                date_range=(
                    result_df["timestamp"].min(),
                    result_df["timestamp"].max(),
                ),
            )

            return result_df

        except requests.exceptions.RequestException as e:
            logger.error(
                "Error fetching OWID excess mortality data",
                error=str(e),
                exc_info=True,
            )
            return pd.DataFrame(columns=["timestamp", "excess_mortality"])

        except Exception as e:
            logger.error(
                "Unexpected error fetching OWID excess mortality data",
                error=str(e),
                exc_info=True,
            )
            return pd.DataFrame(columns=["timestamp", "excess_mortality"])

    def fetch_health_stress_index(
        self,
        country: str = "United States",
        days_back: int = 90,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch composite health stress index from OWID.

        Combines multiple health indicators into a single normalized index.

        Args:
            country: Country name (default: "United States")
            days_back: Number of days of historical data (default: 90)
            use_cache: Whether to use cached data (default: True)

        Returns:
            DataFrame with columns: ['timestamp', 'health_stress_index']
            Values normalized to [0.0, 1.0] where 1.0 = maximum health stress
        """
        # For now, use excess mortality as proxy
        # In future, could combine multiple indicators
        excess_df = self.fetch_excess_mortality(country, days_back, use_cache)

        if excess_df.empty:
            return pd.DataFrame(columns=["timestamp", "health_stress_index"])

        result_df = excess_df.rename(
            columns={"excess_mortality": "health_stress_index"}
        )
        return result_df
