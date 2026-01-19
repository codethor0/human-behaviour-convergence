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

    def __init__(
        self,
        behavior_index_computer: Optional[BehaviorIndexComputer] = None,
        include_political: bool = False,
    ):
        """
        Initialize the data harmonizer.

        Args:
            behavior_index_computer: Optional BehaviorIndexComputer instance.
                If None, creates a new one with default weights.
            include_political: Whether to include political stress in index calculation.
                If True, adjusts weights to include political_weight=0.15.
        """
        if behavior_index_computer is None:
            if include_political:
                # Adjust weights to include political stress
                # (reduce others proportionally)
                # Original: 0.25, 0.25, 0.20, 0.15, 0.15 = 1.0
                # With political (0.15): need to reduce others to sum to 0.85
                # Scale factor: 0.85/1.0 = 0.85
                self.behavior_index_computer = BehaviorIndexComputer(
                    economic_weight=0.25 * 0.85,
                    environmental_weight=0.25 * 0.85,
                    mobility_weight=0.20 * 0.85,
                    digital_attention_weight=0.15 * 0.85,
                    health_weight=0.15 * 0.85,
                    political_weight=0.15,
                )
            else:
                self.behavior_index_computer = BehaviorIndexComputer()
        else:
            self.behavior_index_computer = behavior_index_computer

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
        fred_gdp_growth: Optional[pd.DataFrame] = None,
        fred_cpi_inflation: Optional[pd.DataFrame] = None,
        gdelt_tone: Optional[pd.DataFrame] = None,
        owid_health: Optional[pd.DataFrame] = None,
        usgs_earthquakes: Optional[pd.DataFrame] = None,
        political_data: Optional[pd.DataFrame] = None,
        crime_data: Optional[pd.DataFrame] = None,
        misinformation_data: Optional[pd.DataFrame] = None,
        social_cohesion_data: Optional[pd.DataFrame] = None,
        forward_fill_days: int = 2,
    ) -> pd.DataFrame:
        """
        Merge multi-vector time series data on a shared datetime index.

        Args:
            market_data: DataFrame with columns ['timestamp', 'stress_index', ...]
                Must have 'timestamp' column as datetime
            weather_data: DataFrame with columns ['timestamp', 'discomfort_score', ...]
                Must have 'timestamp' column as datetime
            search_data: Optional DataFrame with columns
                ['timestamp', 'search_interest_score', ...]
            health_data: Optional DataFrame with columns
                ['timestamp', 'health_risk_index', ...]
            mobility_data: Optional DataFrame with columns
                ['timestamp', 'mobility_index', ...]
            forward_fill_days: Number of days to forward-fill market data
                for weekends (default: 2)

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
        if fred_gdp_growth is None:
            fred_gdp_growth = pd.DataFrame()
        if fred_cpi_inflation is None:
            fred_cpi_inflation = pd.DataFrame()
        if gdelt_tone is None:
            gdelt_tone = pd.DataFrame()
        if owid_health is None:
            owid_health = pd.DataFrame()
        if usgs_earthquakes is None:
            usgs_earthquakes = pd.DataFrame()
        if political_data is None:
            political_data = pd.DataFrame()
        if crime_data is None:
            crime_data = pd.DataFrame()
        if misinformation_data is None:
            misinformation_data = pd.DataFrame()
        if social_cohesion_data is None:
            social_cohesion_data = pd.DataFrame()

        if (
            market_data.empty
            and weather_data.empty
            and search_data.empty
            and health_data.empty
            and mobility_data.empty
            and fred_consumer_sentiment.empty
            and fred_unemployment.empty
            and fred_jobless_claims.empty
            and fred_gdp_growth.empty
            and fred_cpi_inflation.empty
            and gdelt_tone.empty
            and owid_health.empty
            and usgs_earthquakes.empty
            and political_data.empty
            and crime_data.empty
            and misinformation_data.empty
            and social_cohesion_data.empty
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

        if not fred_gdp_growth.empty:
            fred_gdp = fred_gdp_growth.copy()
            fred_gdp["timestamp"] = pd.to_datetime(fred_gdp["timestamp"], utc=True)
            if fred_gdp["timestamp"].dt.tz is not None:
                fred_gdp["timestamp"] = fred_gdp["timestamp"].dt.tz_localize(None)
            fred_gdp = fred_gdp.set_index("timestamp").sort_index()
            dataframes.append(fred_gdp)
            names.append("fred_gdp_growth")

        if not fred_cpi_inflation.empty:
            fred_cpi = fred_cpi_inflation.copy()
            fred_cpi["timestamp"] = pd.to_datetime(fred_cpi["timestamp"], utc=True)
            if fred_cpi["timestamp"].dt.tz is not None:
                fred_cpi["timestamp"] = fred_cpi["timestamp"].dt.tz_localize(None)
            fred_cpi = fred_cpi.set_index("timestamp").sort_index()
            dataframes.append(fred_cpi)
            names.append("fred_cpi_inflation")

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

        if not political_data.empty:
            political_df = political_data.copy()
            political_df["timestamp"] = pd.to_datetime(
                political_df["timestamp"], utc=True
            )
            if political_df["timestamp"].dt.tz is not None:
                political_df["timestamp"] = political_df["timestamp"].dt.tz_localize(
                    None
                )
            political_df = political_df.set_index("timestamp").sort_index()
            dataframes.append(political_df)
            names.append("political")

        if not crime_data.empty:
            crime_df = crime_data.copy()
            crime_df["timestamp"] = pd.to_datetime(crime_df["timestamp"], utc=True)
            if crime_df["timestamp"].dt.tz is not None:
                crime_df["timestamp"] = crime_df["timestamp"].dt.tz_localize(None)
            crime_df = crime_df.set_index("timestamp").sort_index()
            dataframes.append(crime_df)
            names.append("crime")

        if not misinformation_data.empty:
            misinformation_df = misinformation_data.copy()
            misinformation_df["timestamp"] = pd.to_datetime(
                misinformation_df["timestamp"], utc=True
            )
            if misinformation_df["timestamp"].dt.tz is not None:
                misinformation_df["timestamp"] = misinformation_df[
                    "timestamp"
                ].dt.tz_localize(None)
            misinformation_df = misinformation_df.set_index("timestamp").sort_index()
            dataframes.append(misinformation_df)
            names.append("misinformation")

        if not social_cohesion_data.empty:
            social_cohesion_df = social_cohesion_data.copy()
            social_cohesion_df["timestamp"] = pd.to_datetime(
                social_cohesion_df["timestamp"], utc=True
            )
            if social_cohesion_df["timestamp"].dt.tz is not None:
                social_cohesion_df["timestamp"] = social_cohesion_df[
                    "timestamp"
                ].dt.tz_localize(None)
            social_cohesion_df = social_cohesion_df.set_index("timestamp").sort_index()
            dataframes.append(social_cohesion_df)
            names.append("social_cohesion")

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

        # Collect all date ranges from indexed dataframes
        # (all are already properly indexed)
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
        if "fred_gdp_growth" in names:
            fred_gdp_idx = names.index("fred_gdp_growth")
            fred_gdp_df = dataframes[fred_gdp_idx]
            fred_gdp_aligned = fred_gdp_df.reindex(date_range)
        else:
            fred_gdp_aligned = pd.DataFrame(index=date_range)

        if "fred_cpi_inflation" in names:
            fred_cpi_idx = names.index("fred_cpi_inflation")
            fred_cpi_df = dataframes[fred_cpi_idx]
            fred_cpi_aligned = fred_cpi_df.reindex(date_range)
        else:
            fred_cpi_aligned = pd.DataFrame(index=date_range)
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

        if "political" in names:
            political_idx = names.index("political")
            political_df = dataframes[political_idx]
            political_aligned = political_df.reindex(date_range)
        else:
            political_aligned = pd.DataFrame(index=date_range)

        if "crime" in names:
            crime_idx = names.index("crime")
            crime_df = dataframes[crime_idx]
            crime_aligned = crime_df.reindex(date_range)
        else:
            crime_aligned = pd.DataFrame(index=date_range)

        if "misinformation" in names:
            misinformation_idx = names.index("misinformation")
            misinformation_df = dataframes[misinformation_idx]
            misinformation_aligned = misinformation_df.reindex(date_range)
        else:
            misinformation_aligned = pd.DataFrame(index=date_range)

        if "social_cohesion" in names:
            social_cohesion_idx = names.index("social_cohesion")
            social_cohesion_df = dataframes[social_cohesion_idx]
            social_cohesion_aligned = social_cohesion_df.reindex(date_range)
        else:
            social_cohesion_aligned = pd.DataFrame(index=date_range)

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
        fred_gdp_growth_stress_val = fred_gdp_aligned.get(
            "gdp_growth_stress", pd.Series(index=date_range, dtype=float)
        )
        fred_cpi_inflation_stress_val = fred_cpi_aligned.get(
            "cpi_inflation_stress", pd.Series(index=date_range, dtype=float)
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
        political_stress_val = political_aligned.get(
            "political_stress", pd.Series(index=date_range, dtype=float)
        )
        crime_stress_val = crime_aligned.get(
            "crime_stress", pd.Series(index=date_range, dtype=float)
        )
        misinformation_stress_val = misinformation_aligned.get(
            "misinformation_stress", pd.Series(index=date_range, dtype=float)
        )
        social_cohesion_stress_val = social_cohesion_aligned.get(
            "social_cohesion_stress", pd.Series(index=date_range, dtype=float)
        )

        # Check if new data is present to adjust BehaviorIndexComputer weights
        has_political_data = (
            not political_aligned.empty and political_stress_val.notna().any()
        )
        has_crime_data = not crime_aligned.empty and crime_stress_val.notna().any()
        has_misinformation_data = (
            not misinformation_aligned.empty and misinformation_stress_val.notna().any()
        )
        has_social_cohesion_data = (
            not social_cohesion_aligned.empty
            and social_cohesion_stress_val.notna().any()
        )

        # Calculate total weight of new indices
        new_weight_total = 0.0
        if has_political_data and self.behavior_index_computer.political_weight == 0:
            new_weight_total += 0.15
        if has_crime_data and self.behavior_index_computer.crime_weight == 0:
            new_weight_total += 0.15
        if (
            has_misinformation_data
            and self.behavior_index_computer.misinformation_weight == 0
        ):
            new_weight_total += 0.10
        if (
            has_social_cohesion_data
            and self.behavior_index_computer.social_cohesion_weight == 0
        ):
            new_weight_total += 0.15

        if new_weight_total > 0:
            # Scale existing weights to make room for new indices
            scale = 1.0 - new_weight_total
            self.behavior_index_computer.economic_weight *= scale
            self.behavior_index_computer.environmental_weight *= scale
            self.behavior_index_computer.mobility_weight *= scale
            self.behavior_index_computer.digital_attention_weight *= scale
            self.behavior_index_computer.health_weight *= scale

            if has_political_data:
                self.behavior_index_computer.political_weight = 0.15
            if has_crime_data:
                self.behavior_index_computer.crime_weight = 0.15
            if has_misinformation_data:
                self.behavior_index_computer.misinformation_weight = 0.10
            if has_social_cohesion_data:
                self.behavior_index_computer.social_cohesion_weight = 0.15

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
                "fred_gdp_growth_stress": fred_gdp_growth_stress_val.values,
                "fred_cpi_inflation_stress": fred_cpi_inflation_stress_val.values,
                "gdelt_tone_score": gdelt_tone_val.values,
                "owid_health_stress": owid_health_val.values,
                "usgs_earthquake_intensity": usgs_earthquake_val.values,
                "political_stress": political_stress_val.values,
                "crime_stress": crime_stress_val.values,
                "misinformation_stress": misinformation_stress_val.values,
                "social_cohesion_stress": social_cohesion_stress_val.values,
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
        # GDP growth: quarterly data, forward-fill up to 90 days
        merged["fred_gdp_growth_stress"] = merged["fred_gdp_growth_stress"].ffill(
            limit=90
        )
        # CPI inflation: monthly data, forward-fill up to 90 days
        merged["fred_cpi_inflation_stress"] = merged["fred_cpi_inflation_stress"].ffill(
            limit=90
        )
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
        merged["political_stress"] = merged["political_stress"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["crime_stress"] = merged["crime_stress"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["misinformation_stress"] = merged["misinformation_stress"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["social_cohesion_stress"] = merged["social_cohesion_stress"].interpolate(
            method="linear", limit_direction="both"
        )

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
