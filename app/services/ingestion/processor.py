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
        air_quality_data: Optional[pd.DataFrame] = None,
        political_data: Optional[pd.DataFrame] = None,
        crime_data: Optional[pd.DataFrame] = None,
        misinformation_data: Optional[pd.DataFrame] = None,
        social_cohesion_data: Optional[pd.DataFrame] = None,
        fuel_data: Optional[pd.DataFrame] = None,
        drought_data: Optional[pd.DataFrame] = None,
        storm_data: Optional[pd.DataFrame] = None,
        demographic_data: Optional[pd.DataFrame] = None,
        consumer_spending_data: Optional[pd.DataFrame] = None,
        employment_sector_data: Optional[pd.DataFrame] = None,
        energy_consumption_data: Optional[pd.DataFrame] = None,
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
        if air_quality_data is None:
            air_quality_data = pd.DataFrame()
        if political_data is None:
            political_data = pd.DataFrame()
        if crime_data is None:
            crime_data = pd.DataFrame()
        if misinformation_data is None:
            misinformation_data = pd.DataFrame()
        if social_cohesion_data is None:
            social_cohesion_data = pd.DataFrame()
        if fuel_data is None:
            fuel_data = pd.DataFrame()
        if drought_data is None:
            drought_data = pd.DataFrame()
        if storm_data is None:
            storm_data = pd.DataFrame()
        if demographic_data is None:
            demographic_data = pd.DataFrame()
        if consumer_spending_data is None:
            consumer_spending_data = pd.DataFrame()
        if employment_sector_data is None:
            employment_sector_data = pd.DataFrame()
        if energy_consumption_data is None:
            energy_consumption_data = pd.DataFrame()

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
            and air_quality_data.empty
            and political_data.empty
            and crime_data.empty
            and misinformation_data.empty
            and social_cohesion_data.empty
            and fuel_data.empty
            and drought_data.empty
            and storm_data.empty
            and demographic_data.empty
            and consumer_spending_data.empty
            and employment_sector_data.empty
            and energy_consumption_data.empty
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

        # Add air quality data if available
        if not air_quality_data.empty:
            aq_df = air_quality_data.copy()
            # Air quality data returns timestamp column
            if "timestamp" in aq_df.columns:
                aq_df["timestamp"] = pd.to_datetime(aq_df["timestamp"], utc=True)
                if aq_df["timestamp"].dt.tz is not None:
                    aq_df["timestamp"] = aq_df["timestamp"].dt.tz_localize(None)
                aq_df = aq_df.set_index("timestamp").sort_index()
                # Use air_quality_stress_index if available (from new fetcher)
                # Otherwise normalize AQI to 0-1 scale (AQI typically 0-500, we want 0-1)
                if "air_quality_stress_index" not in aq_df.columns:
                    if "aqi" in aq_df.columns:
                        # Normalize AQI to stress index (0-1)
                        # AQI > 100 is unhealthy, > 150 is unhealthy for sensitive groups
                        aq_df["air_quality_stress_index"] = aq_df["aqi"].apply(
                            lambda x: (
                                (x / 50) * 0.2
                                if x <= 50
                                else (
                                    (0.2 + ((x - 50) / 50) * 0.2)
                                    if x <= 100
                                    else (
                                        (0.4 + ((x - 100) / 50) * 0.2)
                                        if x <= 150
                                        else min(1.0, 0.6 + ((x - 150) / 350) * 0.4)
                                    )
                                )
                            )
                        )
                    else:
                        # Fallback: create empty stress index
                        aq_df["air_quality_stress_index"] = 0.0
                # Normalize PM2.5 and PM10 (typical ranges: PM2.5 0-500 µg/m³, PM10 0-600 µg/m³)
                if "pm25" in aq_df.columns:
                    aq_df["pm25_normalized"] = aq_df["pm25"] / 500.0
                if "pm10" in aq_df.columns:
                    aq_df["pm10_normalized"] = aq_df["pm10"] / 600.0
                dataframes.append(aq_df)
                names.append("air_quality")

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

        if not fuel_data.empty:
            fuel_df = fuel_data.copy()
            fuel_df["timestamp"] = pd.to_datetime(fuel_df["timestamp"], utc=True)
            if fuel_df["timestamp"].dt.tz is not None:
                fuel_df["timestamp"] = fuel_df["timestamp"].dt.tz_localize(None)
            fuel_df = fuel_df.set_index("timestamp").sort_index()
            dataframes.append(fuel_df)
            names.append("fuel")

        if not drought_data.empty:
            drought_df = drought_data.copy()
            drought_df["timestamp"] = pd.to_datetime(drought_df["timestamp"], utc=True)
            if drought_df["timestamp"].dt.tz is not None:
                drought_df["timestamp"] = drought_df["timestamp"].dt.tz_localize(None)
            drought_df = drought_df.set_index("timestamp").sort_index()
            dataframes.append(drought_df)
            names.append("drought")

        if not storm_data.empty:
            storm_df = storm_data.copy()
            storm_df["timestamp"] = pd.to_datetime(storm_df["timestamp"], utc=True)
            if storm_df["timestamp"].dt.tz is not None:
                storm_df["timestamp"] = storm_df["timestamp"].dt.tz_localize(None)
            storm_df = storm_df.set_index("timestamp").sort_index()
            dataframes.append(storm_df)
            names.append("storm")

        # Add new data sources
        if not demographic_data.empty:
            demo_df = demographic_data.copy()
            demo_df["timestamp"] = pd.to_datetime(demo_df["timestamp"], utc=True)
            if demo_df["timestamp"].dt.tz is not None:
                demo_df["timestamp"] = demo_df["timestamp"].dt.tz_localize(None)
            demo_df = demo_df.set_index("timestamp").sort_index()
            dataframes.append(demo_df)
            names.append("demographic")

        if not consumer_spending_data.empty:
            spending_df = consumer_spending_data.copy()
            spending_df["timestamp"] = pd.to_datetime(
                spending_df["timestamp"], utc=True
            )
            if spending_df["timestamp"].dt.tz is not None:
                spending_df["timestamp"] = spending_df["timestamp"].dt.tz_localize(None)
            spending_df = spending_df.set_index("timestamp").sort_index()
            dataframes.append(spending_df)
            names.append("consumer_spending")

        if not employment_sector_data.empty:
            employment_df = employment_sector_data.copy()
            employment_df["timestamp"] = pd.to_datetime(
                employment_df["timestamp"], utc=True
            )
            if employment_df["timestamp"].dt.tz is not None:
                employment_df["timestamp"] = employment_df["timestamp"].dt.tz_localize(
                    None
                )
            employment_df = employment_df.set_index("timestamp").sort_index()
            dataframes.append(employment_df)
            names.append("employment_sector")

        if not energy_consumption_data.empty:
            energy_df = energy_consumption_data.copy()
            energy_df["timestamp"] = pd.to_datetime(energy_df["timestamp"], utc=True)
            if energy_df["timestamp"].dt.tz is not None:
                energy_df["timestamp"] = energy_df["timestamp"].dt.tz_localize(None)
            energy_df = energy_df.set_index("timestamp").sort_index()
            dataframes.append(energy_df)
            names.append("energy_consumption")

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

        if "air_quality" in names:
            aq_idx = names.index("air_quality")
            aq_df = dataframes[aq_idx]
            aq_aligned = aq_df.reindex(date_range)
        else:
            aq_aligned = pd.DataFrame(index=date_range)

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

        if "fuel" in names:
            fuel_idx = names.index("fuel")
            fuel_df = dataframes[fuel_idx]
            fuel_aligned = fuel_df.reindex(date_range)
        else:
            fuel_aligned = pd.DataFrame(index=date_range)

        if "drought" in names:
            drought_idx = names.index("drought")
            drought_df = dataframes[drought_idx]
            drought_aligned = drought_df.reindex(date_range)
        else:
            drought_aligned = pd.DataFrame(index=date_range)

        if "storm" in names:
            storm_idx = names.index("storm")
            storm_df = dataframes[storm_idx]
            storm_aligned = storm_df.reindex(date_range)
        else:
            storm_aligned = pd.DataFrame(index=date_range)

        # Reindex new data sources
        if "demographic" in names:
            demo_idx = names.index("demographic")
            demo_df = dataframes[demo_idx]
            demo_aligned = demo_df.reindex(date_range)
        else:
            demo_aligned = pd.DataFrame(index=date_range)

        if "consumer_spending" in names:
            spending_idx = names.index("consumer_spending")
            spending_df = dataframes[spending_idx]
            spending_aligned = spending_df.reindex(date_range)
        else:
            spending_aligned = pd.DataFrame(index=date_range)

        if "employment_sector" in names:
            employment_idx = names.index("employment_sector")
            employment_df = dataframes[employment_idx]
            employment_aligned = employment_df.reindex(date_range)
        else:
            employment_aligned = pd.DataFrame(index=date_range)

        if "energy_consumption" in names:
            energy_idx = names.index("energy_consumption")
            energy_df = dataframes[energy_idx]
            energy_aligned = energy_df.reindex(date_range)
        else:
            energy_aligned = pd.DataFrame(index=date_range)

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
        # Extract air quality values (use air_quality_stress_index if available, else fallback to normalized AQI/PM2.5)
        air_quality_val = pd.Series(index=date_range, dtype=float)
        if not aq_aligned.empty:
            if "air_quality_stress_index" in aq_aligned.columns:
                air_quality_val = aq_aligned.get(
                    "air_quality_stress_index", pd.Series(index=date_range, dtype=float)
                )
            elif "aqi_normalized" in aq_aligned.columns:
                air_quality_val = aq_aligned.get(
                    "aqi_normalized", pd.Series(index=date_range, dtype=float)
                )
            elif "pm25_normalized" in aq_aligned.columns:
                air_quality_val = aq_aligned.get(
                    "pm25_normalized", pd.Series(index=date_range, dtype=float)
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
        # Extract fuel_stress_index and rename to fuel_stress for child index naming
        fuel_stress_val = fuel_aligned.get(
            "fuel_stress_index", pd.Series(index=date_range, dtype=float)
        )
        # Extract drought_stress_index
        drought_stress_val = drought_aligned.get(
            "drought_stress_index", pd.Series(index=date_range, dtype=float)
        )
        # Extract storm stress indices
        storm_severity_stress_val = storm_aligned.get(
            "storm_severity_stress", pd.Series(index=date_range, dtype=float)
        )
        heatwave_stress_val = storm_aligned.get(
            "heatwave_stress", pd.Series(index=date_range, dtype=float)
        )
        flood_risk_stress_val = storm_aligned.get(
            "flood_risk_stress", pd.Series(index=date_range, dtype=float)
        )
        # Extract new data source values
        demographic_stress_val = demo_aligned.get(
            "demographic_stress_index", pd.Series(index=date_range, dtype=float)
        )
        consumer_spending_stress_val = spending_aligned.get(
            "retail_sales_stress", pd.Series(index=date_range, dtype=float)
        )
        employment_stress_val = employment_aligned.get(
            "employment_stress", pd.Series(index=date_range, dtype=float)
        )
        energy_consumption_stress_val = energy_aligned.get(
            "energy_stress_index", pd.Series(index=date_range, dtype=float)
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
                "air_quality_index": air_quality_val.values,
                "political_stress": political_stress_val.values,
                "crime_stress": crime_stress_val.values,
                "misinformation_stress": misinformation_stress_val.values,
                "social_cohesion_stress": social_cohesion_stress_val.values,
                "fuel_stress": fuel_stress_val.values,  # Child index name (maps to fuel_stress_index from fetcher)
                "drought_stress": drought_stress_val.values,  # Child index name (maps to drought_stress_index from fetcher)
                "storm_severity_stress": storm_severity_stress_val.values,
                "heatwave_stress": heatwave_stress_val.values,
                "flood_risk_stress": flood_risk_stress_val.values,
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
        merged["air_quality_index"] = merged["air_quality_index"].interpolate(
            method="linear", limit_direction="both"
        )
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
        merged["fuel_stress"] = merged["fuel_stress"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["drought_stress"] = merged["drought_stress"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["storm_severity_stress"] = merged["storm_severity_stress"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["heatwave_stress"] = merged["heatwave_stress"].interpolate(
            method="linear", limit_direction="both"
        )
        merged["flood_risk_stress"] = merged["flood_risk_stress"].interpolate(
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
