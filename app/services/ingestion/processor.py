# SPDX-License-Identifier: MIT-0
"""Data harmonization and merging for multi-vector behavioral forecasting."""
from typing import Optional

import pandas as pd
import structlog

logger = structlog.get_logger("ingestion.processor")


class DataHarmonizer:
    """
    Merge and harmonize economic and environmental time series data.

    Handles date alignment, forward-filling for weekend market closures,
    and creates a unified dataset for behavioral forecasting.
    """

    def __init__(self):
        """Initialize the data harmonizer."""
        pass

    def harmonize(
        self,
        market_data: pd.DataFrame,
        weather_data: pd.DataFrame,
        forward_fill_days: int = 2,
    ) -> pd.DataFrame:
        """
        Merge economic and environmental data on a shared datetime index.

        Args:
            market_data: DataFrame with columns ['timestamp', 'stress_index', ...]
                Must have 'timestamp' column as datetime
            weather_data: DataFrame with columns ['timestamp', 'discomfort_score', ...]
                Must have 'timestamp' column as datetime
            forward_fill_days: Number of days to forward-fill market data for weekends (default: 2)

        Returns:
            Merged DataFrame with columns:
            ['timestamp', 'stress_index', 'discomfort_score', 'behavior_index']
            behavior_index = (Inverse(stress_index) * 0.4) + (Comfort(discomfort) * 0.4) + (Seasonality * 0.2)
        """
        if market_data.empty and weather_data.empty:
            logger.warning("Both market and weather data are empty")
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "stress_index",
                    "discomfort_score",
                    "behavior_index",
                ],
                dtype=float,
            )

        # Ensure timestamp columns are datetime
        if not market_data.empty:
            market_data = market_data.copy()
            market_data["timestamp"] = pd.to_datetime(market_data["timestamp"])
            market_data = market_data.set_index("timestamp").sort_index()

        if not weather_data.empty:
            weather_data = weather_data.copy()
            weather_data["timestamp"] = pd.to_datetime(weather_data["timestamp"])
            weather_data = weather_data.set_index("timestamp").sort_index()

        # Forward-fill market data for weekends (market is closed Sat/Sun)
        if not market_data.empty and forward_fill_days > 0:
            # Resample to daily frequency and forward-fill
            market_daily = market_data.resample("D").last()
            market_daily = market_daily.ffill(limit=forward_fill_days)
            market_data = market_daily

        # Create a common date range
        start_date = None
        end_date = None

        if not market_data.empty:
            start_date = market_data.index.min()
            end_date = (
                max(end_date, market_data.index.max())
                if end_date
                else market_data.index.max()
            )

        if not weather_data.empty:
            weather_start = weather_data.index.min()
            weather_end = weather_data.index.max()
            if start_date is None:
                start_date = weather_start
            else:
                start_date = min(start_date, weather_start)
            if end_date is None:
                end_date = weather_end
            else:
                end_date = max(end_date, weather_end)

        if start_date is None or end_date is None:
            logger.warning("Cannot determine date range from empty data")
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "stress_index",
                    "discomfort_score",
                    "behavior_index",
                ],
                dtype=float,
            )

        # Create daily index
        date_range = pd.date_range(
            start=start_date, end=end_date, freq="D", normalize=True
        )

        # Reindex both DataFrames to common date range
        if not market_data.empty:
            market_aligned = market_data.reindex(date_range)
        else:
            market_aligned = pd.DataFrame(index=date_range)

        if not weather_data.empty:
            weather_aligned = weather_data.reindex(date_range)
        else:
            weather_aligned = pd.DataFrame(index=date_range)

        # Extract key columns
        market_stress = market_aligned.get(
            "stress_index", pd.Series(index=date_range, dtype=float)
        )
        weather_discomfort = weather_aligned.get(
            "discomfort_score", pd.Series(index=date_range, dtype=float)
        )

        # Create merged DataFrame
        merged = pd.DataFrame(
            {
                "timestamp": date_range,
                "stress_index": market_stress.values,
                "discomfort_score": weather_discomfort.values,
            }
        )

        # Forward-fill missing values (for weekends in market data)
        merged["stress_index"] = merged["stress_index"].ffill(limit=forward_fill_days)
        merged["discomfort_score"] = merged["discomfort_score"].interpolate(
            method="linear", limit_direction="both"
        )

        # Calculate behavior index
        # Inverse of stress (low stress = high activity)
        # Comfort = 1 - discomfort (low discomfort = high comfort)
        # Seasonality component (day of year normalized to 0-1)
        merged["day_of_year"] = pd.to_datetime(merged["timestamp"]).dt.dayofyear
        seasonality = (merged["day_of_year"] / 365.0).values

        # Calculate behavior index
        # Handle NaN values
        stress_inv = 1.0 - merged["stress_index"].fillna(0.5)
        comfort = 1.0 - merged["discomfort_score"].fillna(0.5)

        behavior_index = (stress_inv * 0.4) + (comfort * 0.4) + (seasonality * 0.2)

        # Clip to valid range [0.0, 1.0]
        merged["behavior_index"] = behavior_index.clip(0.0, 1.0)

        # Drop intermediate columns
        merged = merged.drop(columns=["day_of_year"])

        # Reset index
        merged = merged.reset_index(drop=True)

        # Drop rows where both stress_index and discomfort_score are NaN
        merged = merged.dropna(subset=["stress_index", "discomfort_score"], how="all")

        logger.info(
            "Data harmonized successfully",
            rows=len(merged),
            date_range=(merged["timestamp"].min(), merged["timestamp"].max()),
            behavior_index_range=(
                merged["behavior_index"].min(),
                merged["behavior_index"].max(),
            ),
        )

        return merged
