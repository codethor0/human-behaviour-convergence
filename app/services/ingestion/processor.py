# SPDX-License-Identifier: PROPRIETARY
"""Data harmonization and merging for multi-vector behavioral forecasting."""
from typing import Optional

import pandas as pd
import structlog

from app.core.behavior_index import BehaviorIndexComputer

logger = structlog.get_logger("ingestion.processor")


class DataHarmonizer:
    """
    Merge and harmonize multi-vector time series data for behavioral forecasting.

    Handles date alignment, forward-filling for weekend market closures,
    and creates a unified dataset from economic, environmental, search trends,
    public health, and mobility data sources.
    """

    def __init__(self, behavior_index_computer: Optional[BehaviorIndexComputer] = None):
        """
        Initialize the data harmonizer.

        Args:
            behavior_index_computer: Optional BehaviorIndexComputer instance.
                If None, creates a new one with default weights.
        """
        self.behavior_index_computer = (
            behavior_index_computer or BehaviorIndexComputer()
        )

    def harmonize(
        self,
        market_data: pd.DataFrame,
        weather_data: pd.DataFrame,
        search_data: Optional[pd.DataFrame] = None,
        health_data: Optional[pd.DataFrame] = None,
        mobility_data: Optional[pd.DataFrame] = None,
        fred_consumer_sentiment: Optional[pd.DataFrame] = None,
        fred_unemployment: Optional[pd.DataFrame] = None,
        fred_jobless_claims: Optional[pd.DataFrame] = None,
        gdelt_tone: Optional[pd.DataFrame] = None,
        owid_health: Optional[pd.DataFrame] = None,
        usgs_earthquakes: Optional[pd.DataFrame] = None,
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
             'health_risk_index', 'mobility_index',
             'economic_stress', 'environmental_stress', 'mobility_activity',
             'digital_attention', 'public_health_stress', 'behavior_index']

            Behavior Index is computed using BehaviorIndexComputer which produces:
            - Sub-indices: economic_stress, environmental_stress, mobility_activity,
              digital_attention, public_health_stress
            - Overall behavior_index: weighted combination of sub-indices

            See docs/BEHAVIOR_INDEX.md for detailed formula and interpretation.
        """
        # Handle empty DataFrames
        if search_data is None:
            search_data = pd.DataFrame()
        if health_data is None:
            health_data = pd.DataFrame()
        if mobility_data is None:
            mobility_data = pd.DataFrame()
        if fred_consumer_sentiment is None:
            fred_consumer_sentiment = pd.DataFrame()
        if fred_unemployment is None:
            fred_unemployment = pd.DataFrame()
        if fred_jobless_claims is None:
            fred_jobless_claims = pd.DataFrame()
        if gdelt_tone is None:
            gdelt_tone = pd.DataFrame()
        if owid_health is None:
            owid_health = pd.DataFrame()
        if usgs_earthquakes is None:
            usgs_earthquakes = pd.DataFrame()

        if (
            market_data.empty
            and weather_data.empty
            and search_data.empty
            and health_data.empty
            and mobility_data.empty
            and fred_consumer_sentiment.empty
            and fred_unemployment.empty
            and fred_jobless_claims.empty
            and gdelt_tone.empty
            and owid_health.empty
            and usgs_earthquakes.empty
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
                    "economic_stress",
                    "environmental_stress",
                    "mobility_activity",
                    "digital_attention",
                    "public_health_stress",
                    "behavior_index",
                ],
                dtype=float,
            )

        # Ensure timestamp columns are datetime and set as index
        dataframes = []
        names = []

        if not market_data.empty:
            market_data = market_data.copy()
            # Normalize timestamps to timezone-naive UTC
            market_data["timestamp"] = pd.to_datetime(
                market_data["timestamp"], utc=True
            )
            if market_data["timestamp"].dt.tz is not None:
                market_data["timestamp"] = market_data["timestamp"].dt.tz_localize(None)
            market_data = market_data.set_index("timestamp").sort_index()
            dataframes.append(market_data)
            names.append("market")

        if not weather_data.empty:
            weather_data = weather_data.copy()
            # Normalize timestamps to timezone-naive UTC
            weather_data["timestamp"] = pd.to_datetime(
                weather_data["timestamp"], utc=True
            )
            if weather_data["timestamp"].dt.tz is not None:
                weather_data["timestamp"] = weather_data["timestamp"].dt.tz_localize(
                    None
                )
            weather_data = weather_data.set_index("timestamp").sort_index()
            dataframes.append(weather_data)
            names.append("weather")

        if not search_data.empty:
            search_data = search_data.copy()
            # Normalize timestamps to timezone-naive UTC
            search_data["timestamp"] = pd.to_datetime(
                search_data["timestamp"], utc=True
            )
            if search_data["timestamp"].dt.tz is not None:
                search_data["timestamp"] = search_data["timestamp"].dt.tz_localize(None)
            search_data = search_data.set_index("timestamp").sort_index()
            dataframes.append(search_data)
            names.append("search")

        if not health_data.empty:
            health_data = health_data.copy()
            # Normalize timestamps to timezone-naive UTC
            health_data["timestamp"] = pd.to_datetime(
                health_data["timestamp"], utc=True
            )
            if health_data["timestamp"].dt.tz is not None:
                health_data["timestamp"] = health_data["timestamp"].dt.tz_localize(None)
            health_data = health_data.set_index("timestamp").sort_index()
            dataframes.append(health_data)
            names.append("health")

        if not mobility_data.empty:
            mobility_data = mobility_data.copy()
            # Normalize timestamps to timezone-naive UTC
            mobility_data["timestamp"] = pd.to_datetime(
                mobility_data["timestamp"], utc=True
            )
            if mobility_data["timestamp"].dt.tz is not None:
                mobility_data["timestamp"] = mobility_data["timestamp"].dt.tz_localize(
                    None
                )
            mobility_data = mobility_data.set_index("timestamp").sort_index()
            dataframes.append(mobility_data)
            names.append("mobility")

        # Add FRED data sources
        if not fred_consumer_sentiment.empty:
            fred_cs = fred_consumer_sentiment.copy()
            fred_cs["timestamp"] = pd.to_datetime(fred_cs["timestamp"], utc=True)
            if fred_cs["timestamp"].dt.tz is not None:
                fred_cs["timestamp"] = fred_cs["timestamp"].dt.tz_localize(None)
            fred_cs = fred_cs.set_index("timestamp").sort_index()
            dataframes.append(fred_cs)
            names.append("fred_consumer_sentiment")

        if not fred_unemployment.empty:
            fred_unemp = fred_unemployment.copy()
            fred_unemp["timestamp"] = pd.to_datetime(fred_unemp["timestamp"], utc=True)
            if fred_unemp["timestamp"].dt.tz is not None:
                fred_unemp["timestamp"] = fred_unemp["timestamp"].dt.tz_localize(None)
            fred_unemp = fred_unemp.set_index("timestamp").sort_index()
            dataframes.append(fred_unemp)
            names.append("fred_unemployment")

        if not fred_jobless_claims.empty:
            fred_jc = fred_jobless_claims.copy()
            fred_jc["timestamp"] = pd.to_datetime(fred_jc["timestamp"], utc=True)
            if fred_jc["timestamp"].dt.tz is not None:
                fred_jc["timestamp"] = fred_jc["timestamp"].dt.tz_localize(None)
            fred_jc = fred_jc.set_index("timestamp").sort_index()
            dataframes.append(fred_jc)
            names.append("fred_jobless_claims")

        if not gdelt_tone.empty:
            gdelt_df = gdelt_tone.copy()
            gdelt_df["timestamp"] = pd.to_datetime(gdelt_df["timestamp"], utc=True)
            if gdelt_df["timestamp"].dt.tz is not None:
                gdelt_df["timestamp"] = gdelt_df["timestamp"].dt.tz_localize(None)
            gdelt_df = gdelt_df.set_index("timestamp").sort_index()
            dataframes.append(gdelt_df)
            names.append("gdelt_tone")

        if not owid_health.empty:
            owid_df = owid_health.copy()
            owid_df["timestamp"] = pd.to_datetime(owid_df["timestamp"], utc=True)
            if owid_df["timestamp"].dt.tz is not None:
                owid_df["timestamp"] = owid_df["timestamp"].dt.tz_localize(None)
            owid_df = owid_df.set_index("timestamp").sort_index()
            dataframes.append(owid_df)
            names.append("owid_health")

        if not usgs_earthquakes.empty:
            usgs_df = usgs_earthquakes.copy()
            usgs_df["timestamp"] = pd.to_datetime(usgs_df["timestamp"], utc=True)
            if usgs_df["timestamp"].dt.tz is not None:
                usgs_df["timestamp"] = usgs_df["timestamp"].dt.tz_localize(None)
            usgs_df = usgs_df.set_index("timestamp").sort_index()
            dataframes.append(usgs_df)
            names.append("usgs_earthquakes")

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

        # Collect all date ranges from indexed dataframes (all are already properly indexed)
        all_date_sources = []
        for df in dataframes:
            if not df.empty and isinstance(df.index, pd.DatetimeIndex):
                all_date_sources.append((df.index.min(), df.index.max()))

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
                    "economic_stress",
                    "environmental_stress",
                    "mobility_activity",
                    "digital_attention",
                    "public_health_stress",
                    "behavior_index",
                ],
                dtype=float,
            )

        # Create daily index (timezone-naive for consistency)
        date_range = pd.date_range(
            start=start_date, end=end_date, freq="D", normalize=True, tz=None
        )
        # Ensure all dates are timezone-naive
        if date_range.tz is not None:
            date_range = date_range.tz_localize(None)

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

        if not fred_consumer_sentiment.empty:
            fred_cs_aligned = fred_consumer_sentiment.reindex(date_range)
        else:
            fred_cs_aligned = pd.DataFrame(index=date_range)

        if not fred_unemployment.empty:
            fred_unemp_aligned = fred_unemployment.reindex(date_range)
        else:
            fred_unemp_aligned = pd.DataFrame(index=date_range)

        if not fred_jobless_claims.empty:
            fred_jc_aligned = fred_jobless_claims.reindex(date_range)
        else:
            fred_jc_aligned = pd.DataFrame(index=date_range)

        # Reindex new data sources (use indexed versions from dataframes list)
        if "gdelt_tone" in names:
            gdelt_idx = names.index("gdelt_tone")
            gdelt_df = dataframes[gdelt_idx]
            gdelt_aligned = gdelt_df.reindex(date_range)
        else:
            gdelt_aligned = pd.DataFrame(index=date_range)

        if "owid_health" in names:
            owid_idx = names.index("owid_health")
            owid_df = dataframes[owid_idx]
            owid_aligned = owid_df.reindex(date_range)
        else:
            owid_aligned = pd.DataFrame(index=date_range)

        if "usgs_earthquakes" in names:
            usgs_idx = names.index("usgs_earthquakes")
            usgs_df = dataframes[usgs_idx]
            usgs_aligned = usgs_df.reindex(date_range)
        else:
            usgs_aligned = pd.DataFrame(index=date_range)

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
        fred_consumer_sentiment_val = fred_cs_aligned.get(
            "consumer_sentiment", pd.Series(index=date_range, dtype=float)
        )
        fred_unemployment_val = fred_unemp_aligned.get(
            "unemployment_rate", pd.Series(index=date_range, dtype=float)
        )
        fred_jobless_claims_val = fred_jc_aligned.get(
            "jobless_claims", pd.Series(index=date_range, dtype=float)
        )
        gdelt_tone_val = gdelt_aligned.get(
            "tone_score", pd.Series(index=date_range, dtype=float)
        )
        owid_health_val = owid_aligned.get(
            "health_stress_index", pd.Series(index=date_range, dtype=float)
        )
        usgs_earthquake_val = usgs_aligned.get(
            "earthquake_intensity", pd.Series(index=date_range, dtype=float)
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
                "fred_consumer_sentiment": fred_consumer_sentiment_val.values,
                "fred_unemployment": fred_unemployment_val.values,
                "fred_jobless_claims": fred_jobless_claims_val.values,
                "gdelt_tone_score": gdelt_tone_val.values,
                "owid_health_stress": owid_health_val.values,
                "usgs_earthquake_intensity": usgs_earthquake_val.values,
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
        # FRED indicators are monthly/weekly, so forward-fill is more appropriate
        merged["fred_consumer_sentiment"] = merged["fred_consumer_sentiment"].ffill(
            limit=90
        )  # Forward-fill up to 90 days
        merged["fred_unemployment"] = merged["fred_unemployment"].ffill(limit=90)
        merged["fred_jobless_claims"] = merged["fred_jobless_claims"].ffill(
            limit=30
        )  # Weekly data
        # New data sources: interpolate continuous signals
        merged["gdelt_tone_score"] = merged["gdelt_tone_score"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["owid_health_stress"] = merged["owid_health_stress"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["usgs_earthquake_intensity"] = merged[
            "usgs_earthquake_intensity"
        ].interpolate(method="linear", limit_direction="both")

        # Compute behavior index and sub-indices using BehaviorIndexComputer
        merged = self.behavior_index_computer.compute_behavior_index(merged)

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
            available_signals=[col for col in signal_cols if merged[col].notna().any()],
        )

        return merged
