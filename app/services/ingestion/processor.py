# SPDX-License-Identifier: MIT-0
"""Data harmonization and merging for multi-vector behavioral forecasting."""
from typing import Optional

import pandas as pd
import structlog

logger = structlog.get_logger("ingestion.processor")


class DataHarmonizer:
    """
    Merge and harmonize multi-vector time series data for behavioral forecasting.

    Handles date alignment, forward-filling for weekend market closures,
    and creates a unified dataset from economic, environmental, search trends,
    public health, and mobility data sources.
    """

    def __init__(self):
        """Initialize the data harmonizer."""
        pass

    def harmonize(
        self,
        market_data: pd.DataFrame,
        weather_data: pd.DataFrame,
        search_data: Optional[pd.DataFrame] = None,
        health_data: Optional[pd.DataFrame] = None,
        mobility_data: Optional[pd.DataFrame] = None,
        forward_fill_days: int = 2,
    ) -> pd.DataFrame:
        """
        Merge multi-vector time series data on a shared datetime index.

        Args:
            market_data: DataFrame with columns ['timestamp', 'stress_index', ...]
                Must have 'timestamp' column as datetime
            weather_data: DataFrame with columns ['timestamp', 'discomfort_score', ...]
                Must have 'timestamp' column as datetime
            search_data: Optional DataFrame with columns ['timestamp', 'search_interest_score', ...]
            health_data: Optional DataFrame with columns ['timestamp', 'health_risk_index', ...]
            mobility_data: Optional DataFrame with columns ['timestamp', 'mobility_index', ...]
            forward_fill_days: Number of days to forward-fill market data for weekends (default: 2)

        Returns:
            Merged DataFrame with columns:
            ['timestamp', 'stress_index', 'discomfort_score', 'search_interest_score',
             'health_risk_index', 'mobility_index', 'behavior_index']
            
            behavior_index formula (weights sum to 1.0):
            (inverse_stress * 0.25) + (comfort * 0.25) + (attention_score * 0.15) +
            (inverse_health_burden * 0.15) + (mobility_activity * 0.10) + (seasonality * 0.10)
            
            Where:
            - inverse_stress = 1 - stress_index
            - comfort = 1 - discomfort_score
            - attention_score = search_interest_score (if available, else 0.5)
            - inverse_health_burden = 1 - health_risk_index (if available, else 0.5)
            - mobility_activity = mobility_index (if available, else 0.5)
            - seasonality = day_of_year / 365.0
        """
        # Handle empty DataFrames
        if search_data is None:
            search_data = pd.DataFrame()
        if health_data is None:
            health_data = pd.DataFrame()
        if mobility_data is None:
            mobility_data = pd.DataFrame()

        if (
            market_data.empty
            and weather_data.empty
            and search_data.empty
            and health_data.empty
            and mobility_data.empty
        ):
            logger.warning("All data sources are empty")
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "stress_index",
                    "discomfort_score",
                    "search_interest_score",
                    "health_risk_index",
                    "mobility_index",
                    "behavior_index",
                ],
                dtype=float,
            )

        # Ensure timestamp columns are datetime and set as index
        dataframes = []
        names = []
        
        if not market_data.empty:
            market_data = market_data.copy()
            market_data["timestamp"] = pd.to_datetime(market_data["timestamp"])
            market_data = market_data.set_index("timestamp").sort_index()
            dataframes.append(market_data)
            names.append("market")
        
        if not weather_data.empty:
            weather_data = weather_data.copy()
            weather_data["timestamp"] = pd.to_datetime(weather_data["timestamp"])
            weather_data = weather_data.set_index("timestamp").sort_index()
            dataframes.append(weather_data)
            names.append("weather")
        
        if not search_data.empty:
            search_data = search_data.copy()
            search_data["timestamp"] = pd.to_datetime(search_data["timestamp"])
            search_data = search_data.set_index("timestamp").sort_index()
            dataframes.append(search_data)
            names.append("search")
        
        if not health_data.empty:
            health_data = health_data.copy()
            health_data["timestamp"] = pd.to_datetime(health_data["timestamp"])
            health_data = health_data.set_index("timestamp").sort_index()
            dataframes.append(health_data)
            names.append("health")
        
        if not mobility_data.empty:
            mobility_data = mobility_data.copy()
            mobility_data["timestamp"] = pd.to_datetime(mobility_data["timestamp"])
            mobility_data = mobility_data.set_index("timestamp").sort_index()
            dataframes.append(mobility_data)
            names.append("mobility")

        # Forward-fill market data for weekends (market is closed Sat/Sun)
        if not market_data.empty and forward_fill_days > 0:
            market_daily = market_data.resample("D").last()
            market_daily = market_daily.ffill(limit=forward_fill_days)
            market_data = market_daily
            # Update market_data in dataframes list if it was added
            if "market" in names and len(dataframes) > 0:
                market_idx = names.index("market")
                if market_idx < len(dataframes):
                    dataframes[market_idx] = market_data

        # Determine common date range from all available data
        start_date = None
        end_date = None

        # Collect all date ranges from modified dataframes and original variables
        all_date_sources = []
        if not market_data.empty:
            all_date_sources.append((market_data.index.min(), market_data.index.max()))
        if not weather_data.empty:
            all_date_sources.append((weather_data.index.min(), weather_data.index.max()))
        if not search_data.empty:
            all_date_sources.append((search_data.index.min(), search_data.index.max()))
        if not health_data.empty:
            all_date_sources.append((health_data.index.min(), health_data.index.max()))
        if not mobility_data.empty:
            all_date_sources.append((mobility_data.index.min(), mobility_data.index.max()))

        if all_date_sources:
            start_date = min(ds[0] for ds in all_date_sources)
            end_date = max(ds[1] for ds in all_date_sources)

        if start_date is None or end_date is None:
            logger.warning("Cannot determine date range from empty data")
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "stress_index",
                    "discomfort_score",
                    "search_interest_score",
                    "health_risk_index",
                    "mobility_index",
                    "behavior_index",
                ],
                dtype=float,
            )

        # Create daily index
        date_range = pd.date_range(
            start=start_date, end=end_date, freq="D", normalize=True
        )

        # Reindex all DataFrames to common date range
        if not market_data.empty:
            market_aligned = market_data.reindex(date_range)
        else:
            market_aligned = pd.DataFrame(index=date_range)

        if not weather_data.empty:
            weather_aligned = weather_data.reindex(date_range)
        else:
            weather_aligned = pd.DataFrame(index=date_range)

        if not search_data.empty:
            search_aligned = search_data.reindex(date_range)
        else:
            search_aligned = pd.DataFrame(index=date_range)

        if not health_data.empty:
            health_aligned = health_data.reindex(date_range)
        else:
            health_aligned = pd.DataFrame(index=date_range)

        if not mobility_data.empty:
            mobility_aligned = mobility_data.reindex(date_range)
        else:
            mobility_aligned = pd.DataFrame(index=date_range)

        # Extract key columns
        market_stress = market_aligned.get(
            "stress_index", pd.Series(index=date_range, dtype=float)
        )
        weather_discomfort = weather_aligned.get(
            "discomfort_score", pd.Series(index=date_range, dtype=float)
        )
        search_interest = search_aligned.get(
            "search_interest_score", pd.Series(index=date_range, dtype=float)
        )
        health_risk = health_aligned.get(
            "health_risk_index", pd.Series(index=date_range, dtype=float)
        )
        mobility_activity = mobility_aligned.get(
            "mobility_index", pd.Series(index=date_range, dtype=float)
        )

        # Create merged DataFrame
        merged = pd.DataFrame(
            {
                "timestamp": date_range,
                "stress_index": market_stress.values,
                "discomfort_score": weather_discomfort.values,
                "search_interest_score": search_interest.values,
                "health_risk_index": health_risk.values,
                "mobility_index": mobility_activity.values,
            }
        )

        # Forward-fill missing values (for weekends in market data)
        merged["stress_index"] = merged["stress_index"].ffill(limit=forward_fill_days)
        
        # Interpolate other continuous signals
        merged["discomfort_score"] = merged["discomfort_score"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["search_interest_score"] = merged["search_interest_score"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["health_risk_index"] = merged["health_risk_index"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["mobility_index"] = merged["mobility_index"].interpolate(
            method="linear", limit_direction="both"
        )

        # Calculate derived features for behavior_index
        # Inverse of stress (low stress = high activity)
        stress_inv = 1.0 - merged["stress_index"].fillna(0.5)
        
        # Comfort = 1 - discomfort (low discomfort = high comfort)
        comfort = 1.0 - merged["discomfort_score"].fillna(0.5)
        
        # Attention score from search trends (already normalized)
        attention_score = merged["search_interest_score"].fillna(0.5)
        
        # Inverse health burden (low risk = high activity)
        inverse_health_burden = 1.0 - merged["health_risk_index"].fillna(0.5)
        
        # Mobility activity (already normalized)
        mobility_activity = merged["mobility_index"].fillna(0.5)
        
        # Seasonality component (day of year normalized to 0-1)
        merged["day_of_year"] = pd.to_datetime(merged["timestamp"]).dt.dayofyear
        seasonality = (merged["day_of_year"] / 365.0).values

        # Calculate behavior_index with updated formula
        # Weights: stress_inv=0.25, comfort=0.25, attention=0.15, health=0.15, mobility=0.10, seasonality=0.10
        behavior_index = (
            (stress_inv * 0.25)
            + (comfort * 0.25)
            + (attention_score * 0.15)
            + (inverse_health_burden * 0.15)
            + (mobility_activity * 0.10)
            + (seasonality * 0.10)
        )

        # Clip to valid range [0.0, 1.0]
        merged["behavior_index"] = behavior_index.clip(0.0, 1.0)

        # Drop intermediate columns
        merged = merged.drop(columns=["day_of_year"])

        # Reset index
        merged = merged.reset_index(drop=True)

        # Drop rows where all input signals are NaN
        signal_cols = [
            "stress_index",
            "discomfort_score",
            "search_interest_score",
            "health_risk_index",
            "mobility_index",
        ]
        merged = merged.dropna(subset=signal_cols, how="all")

        logger.info(
            "Data harmonized successfully",
            rows=len(merged),
            date_range=(merged["timestamp"].min(), merged["timestamp"].max()),
            behavior_index_range=(
                merged["behavior_index"].min(),
                merged["behavior_index"].max(),
            ),
            available_signals=[
                col
                for col in signal_cols
                if merged[col].notna().any()
            ],
        )

        return merged
