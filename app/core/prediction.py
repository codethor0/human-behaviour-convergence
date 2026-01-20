# SPDX-License-Identifier: PROPRIETARY
"""Behavioral forecasting engine using real-world public data."""
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pandas as pd
import structlog

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    ExponentialSmoothing = None

from app.services.ingestion import (
    CISAKEVFetcher,
    CrimeSafetyStressFetcher,
    DataHarmonizer,
    EnvironmentalImpactFetcher,
    FREDEconomicFetcher,
    GDELTEventsFetcher,
    MarketSentimentFetcher,
    MisinformationStressFetcher,
    MobilityFetcher,
    NWSAlertsFetcher,
    OpenFEMAEmergencyManagementFetcher,
    OpenStatesLegislativeFetcher,
    OWIDHealthFetcher,
    PoliticalStressFetcher,
    PublicHealthFetcher,
    SearchTrendsFetcher,
    SocialCohesionStressFetcher,
    USGSEarthquakeFetcher,
)

logger = structlog.get_logger("core.prediction")

# Minimum history window for reliable forecasting
# Forecasts require at least MIN_HISTORY_DAYS of data to produce meaningful results.
# If days_back < MIN_HISTORY_DAYS, the system will either:
# - Extend the internal window to MIN_HISTORY_DAYS (preserving forecast_horizon), OR
# - Return an explicit "insufficient_history" flag in metadata
MIN_HISTORY_DAYS = 14  # Minimum days of history required for stable forecasts


class BehavioralForecaster:
    """
    Multi-vector behavioral forecasting engine.

    Uses economic (VIX/SPY), environmental (weather), search trends,
    public health, and mobility data to forecast human behavioral
    convergence using exponential smoothing (Holt-Winters) model.
    """

    def __init__(
        self,
        market_fetcher: Optional[MarketSentimentFetcher] = None,
        fred_fetcher: Optional[FREDEconomicFetcher] = None,
        weather_fetcher: Optional[EnvironmentalImpactFetcher] = None,
        search_fetcher: Optional[SearchTrendsFetcher] = None,
        health_fetcher: Optional[PublicHealthFetcher] = None,
        mobility_fetcher: Optional[MobilityFetcher] = None,
        gdelt_fetcher: Optional[GDELTEventsFetcher] = None,
        owid_fetcher: Optional[OWIDHealthFetcher] = None,
        usgs_fetcher: Optional[USGSEarthquakeFetcher] = None,
        political_fetcher: Optional[PoliticalStressFetcher] = None,
        crime_fetcher: Optional[CrimeSafetyStressFetcher] = None,
        misinformation_fetcher: Optional[MisinformationStressFetcher] = None,
        social_cohesion_fetcher: Optional[SocialCohesionStressFetcher] = None,
        harmonizer: Optional[DataHarmonizer] = None,
    ):
        """
        Initialize the behavioral forecaster.

        Args:
            market_fetcher: Market sentiment fetcher instance (creates new if None)
            fred_fetcher: FRED economic indicators fetcher instance
                (creates new if None)
            weather_fetcher: Environmental impact fetcher instance (creates new if None)
            search_fetcher: Search trends fetcher instance (creates new if None)
            health_fetcher: Public health fetcher instance (creates new if None)
            mobility_fetcher: Mobility fetcher instance (creates new if None)
            gdelt_fetcher: GDELT events fetcher instance (creates new if None)
            owid_fetcher: OWID health fetcher instance (creates new if None)
            usgs_fetcher: USGS earthquake fetcher instance (creates new if None)
            political_fetcher: Political stress fetcher instance (creates new if None)
            crime_fetcher: Crime & public safety stress fetcher instance
                (creates new if None)
            misinformation_fetcher: Misinformation stress fetcher instance
                (creates new if None)
            social_cohesion_fetcher: Social cohesion stress fetcher instance
                (creates new if None)
            harmonizer: Data harmonizer instance (creates new if None)
        """
        self.market_fetcher = market_fetcher or MarketSentimentFetcher()
        self.fred_fetcher = fred_fetcher or FREDEconomicFetcher()
        self.weather_fetcher = weather_fetcher or EnvironmentalImpactFetcher()
        self.search_fetcher = search_fetcher or SearchTrendsFetcher()
        self.health_fetcher = health_fetcher or PublicHealthFetcher()
        self.mobility_fetcher = mobility_fetcher or MobilityFetcher()
        self.gdelt_fetcher = gdelt_fetcher or GDELTEventsFetcher()
        self.openfema_fetcher = OpenFEMAEmergencyManagementFetcher()
        self.openstates_fetcher = OpenStatesLegislativeFetcher()
        self.nws_alerts_fetcher = NWSAlertsFetcher()
        self.cisa_kev_fetcher = CISAKEVFetcher()
        self.owid_fetcher = owid_fetcher or OWIDHealthFetcher()
        self.usgs_fetcher = usgs_fetcher or USGSEarthquakeFetcher()
        self.political_fetcher = political_fetcher or PoliticalStressFetcher()
        self.crime_fetcher = crime_fetcher or CrimeSafetyStressFetcher()
        self.misinformation_fetcher = (
            misinformation_fetcher or MisinformationStressFetcher()
        )
        self.social_cohesion_fetcher = (
            social_cohesion_fetcher or SocialCohesionStressFetcher()
        )
        self.harmonizer = harmonizer or DataHarmonizer()
        # Intelligence Layer components
        from app.services.analytics.correlation import CorrelationEngine
        from app.services.convergence.engine import ConvergenceEngine
        from app.services.forecast.monitor import ForecastMonitor
        from app.services.risk.classifier import RiskClassifier
        from app.services.shocks.detector import ShockDetector

        self.shock_detector = ShockDetector()
        self.convergence_engine = ConvergenceEngine()
        self.risk_classifier = RiskClassifier()
        self.forecast_monitor = ForecastMonitor()
        self.correlation_engine = CorrelationEngine()
        # Use dict for LRU cache (Python 3.7+ dicts maintain insertion order)
        self._cache: Dict[str, Tuple[pd.DataFrame, pd.DataFrame, Dict]] = {}
        self._max_cache_size: Optional[int] = None
        self._cache_lock = __import__('threading').Lock()

    def reset_cache(self) -> None:
        """
        Reset all in-memory forecast caches used by this BehavioralForecaster.

        Intended for tests and process-lifetime reset paths.
        """
        with self._cache_lock:
            self._cache.clear()

    def _is_us_state(self, region_name: str) -> bool:
        """Check if region_name is a US state."""
        us_states = {
            "Alabama",
            "Alaska",
            "Arizona",
            "Arkansas",
            "California",
            "Colorado",
            "Connecticut",
            "Delaware",
            "Florida",
            "Georgia",
            "Hawaii",
            "Idaho",
            "Illinois",
            "Indiana",
            "Iowa",
            "Kansas",
            "Kentucky",
            "Louisiana",
            "Maine",
            "Maryland",
            "Massachusetts",
            "Michigan",
            "Minnesota",
            "Mississippi",
            "Missouri",
            "Montana",
            "Nebraska",
            "Nevada",
            "New Hampshire",
            "New Jersey",
            "New Mexico",
            "New York",
            "North Carolina",
            "North Dakota",
            "Ohio",
            "Oklahoma",
            "Oregon",
            "Pennsylvania",
            "Rhode Island",
            "South Carolina",
            "South Dakota",
            "Tennessee",
            "Texas",
            "Utah",
            "Vermont",
            "Virginia",
            "Washington",
            "West Virginia",
            "Wisconsin",
            "Wyoming",
            "District of Columbia",
        }
        # Also check for state abbreviations or common variations
        return region_name in us_states or any(
            region_name.startswith(state) for state in us_states
        )

    def forecast(
        self,
        latitude: float,
        longitude: float,
        region_name: str,
        days_back: int = 30,
        forecast_horizon: int = 7,
    ) -> Dict:
        """
        Generate behavioral forecast for a given region.

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
            region_name: Human-readable region name
            days_back: Number of historical days to use (default: 30)
            forecast_horizon: Number of days to forecast ahead (default: 7)

        Returns:
            Dictionary containing:
            - history: DataFrame with past behavior_index data
            - forecast: DataFrame with future predictions and confidence intervals
            - sources: List of public APIs used
            - metadata: Additional information about the forecast
        """
        cache_key = (
            f"{latitude:.4f},{longitude:.4f},{region_name},"
            f"{days_back},{forecast_horizon}"
        )

        # Check cache with LRU access pattern
        with self._cache_lock:
            if cache_key in self._cache:
                logger.info("Using cached forecast", cache_key=cache_key)
                # LRU: move accessed item to end (most recent)
                history, forecast, metadata = self._cache.pop(cache_key)
                self._cache[cache_key] = (history, forecast, metadata)
                # Convert timestamps to ISO strings for API response
                history_dict = history.copy()
                if not history.empty and "timestamp" in history_dict.columns:
                    history_dict["timestamp"] = history_dict["timestamp"].dt.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                forecast_dict = forecast.copy()
                if not forecast.empty and "timestamp" in forecast_dict.columns:
                    forecast_dict["timestamp"] = forecast_dict["timestamp"].dt.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                # Preserve harmonized_df in metadata for component extraction
                # (will be removed in API layer)
                return {
                    "history": history_dict.to_dict("records") if not history.empty else [],
                    "forecast": (
                        forecast_dict.to_dict("records") if not forecast.empty else []
                    ),
                    "sources": metadata.get("sources", []),
                    "metadata": metadata,
                }

        sources = []

        try:
            logger.info(
                "Generating behavioral forecast",
                latitude=latitude,
                longitude=longitude,
                region_name=region_name,
                days_back=days_back,
                forecast_horizon=forecast_horizon,
            )

            # Fetch market sentiment data
            market_data = self.market_fetcher.fetch_stress_index(days_back=days_back)
            if not market_data.empty:
                sources.append("yfinance (VIX/SPY)")

            # Fetch FRED economic indicators (if API key available)
            fred_consumer_sentiment = self.fred_fetcher.fetch_consumer_sentiment(
                days_back=days_back
            )
            fred_unemployment = self.fred_fetcher.fetch_unemployment_rate(
                days_back=days_back
            )
            fred_jobless_claims = self.fred_fetcher.fetch_jobless_claims(
                days_back=days_back
            )
            # Extended economic metrics (GDP growth, CPI inflation)
            # Note: These use longer lookback (365 days) for YoY calculations
            fred_gdp_growth = pd.DataFrame()
            fred_cpi_inflation = pd.DataFrame()
            try:
                fred_gdp_growth = self.fred_fetcher.fetch_gdp_growth(
                    days_back=365  # Quarterly data, need longer window
                )
                if not fred_gdp_growth.empty:
                    sources.append("FRED (GDP Growth)")
            except Exception as e:
                logger.debug("Failed to fetch GDP growth", error=str(e))

            try:
                fred_cpi_inflation = self.fred_fetcher.fetch_cpi_inflation(
                    days_back=365  # Need 12 months for YoY calculation
                )
                if not fred_cpi_inflation.empty:
                    sources.append("FRED (CPI Inflation)")
            except Exception as e:
                logger.debug("Failed to fetch CPI inflation", error=str(e))

            if (
                not fred_consumer_sentiment.empty
                or not fred_unemployment.empty
                or not fred_jobless_claims.empty
                or not fred_gdp_growth.empty
                or not fred_cpi_inflation.empty
            ):
                sources.append("FRED (Economic Indicators)")

            # Fetch weather data
            weather_data = self.weather_fetcher.fetch_regional_comfort(
                latitude=latitude, longitude=longitude, days_back=days_back
            )
            if not weather_data.empty:
                sources.append("openmeteo.com (Weather)")

            # Fetch search trends data (Wikipedia Pageviews - no key required)
            search_data, search_status = self.search_fetcher.fetch_search_interest(
                query="behavioral patterns",
                days_back=days_back,
                region_name=region_name,
            )
            if search_status.ok and not search_data.empty:
                sources.append("Wikimedia Pageviews (Search Trends)")
            # Always store search trends status in metadata (even if failed)

            # Fetch public health data
            # Derive region code from coordinates if possible (placeholder)
            health_data = self.health_fetcher.fetch_health_risk_index(
                region_code=None, days_back=days_back
            )
            if not health_data.empty:
                sources.append("public health API")

            # Fetch mobility data (TSA passenger throughput - no key required)
            mobility_data = self.mobility_fetcher.fetch_mobility_index(
                latitude=latitude, longitude=longitude, days_back=days_back
            )
            if not mobility_data.empty:
                sources.append("TSA Passenger Throughput (Mobility)")
            # Get status from last_status attribute if needed
            mobility_status = getattr(self.mobility_fetcher, "last_status", None)

            # Fetch GDELT events data (digital attention)
            gdelt_tone, gdelt_status = self.gdelt_fetcher.fetch_event_tone(
                days_back=days_back
            )
            if gdelt_status.ok and not gdelt_tone.empty:
                sources.append("GDELT (Global Events)")
            # Always store GDELT status in metadata (even if failed)

            # Fetch OpenFEMA emergency management data
            openfema_declarations, openfema_status = (
                self.openfema_fetcher.fetch_disaster_declarations(
                    region_name=region_name, days_back=days_back
                )
            )
            if openfema_status.ok and not openfema_declarations.empty:
                sources.append("OpenFEMA (Emergency Management)")
            # Always store OpenFEMA status in metadata (even if failed)

            # Fetch OpenStates legislative activity data
            openstates_activity, openstates_status = (
                self.openstates_fetcher.fetch_legislative_activity(
                    region_name=region_name, days_back=days_back
                )
            )
            if openstates_status.ok and not openstates_activity.empty:
                sources.append("OpenStates (Legislative Activity)")
            # Always store OpenStates status in metadata (even if failed)

            # Fetch NWS weather alerts data
            nws_alerts, nws_alerts_status = (
                self.nws_alerts_fetcher.fetch_weather_alerts(
                    latitude=latitude, longitude=longitude, days_back=days_back
                )
            )
            if nws_alerts_status.ok and not nws_alerts.empty:
                sources.append("NWS (Weather Alerts)")
            # Always store NWS alerts status in metadata (even if failed)

            # Fetch CISA KEV cyber risk data
            cisa_kev_data, cisa_kev_status = self.cisa_kev_fetcher.fetch_kev_catalog(
                days_back=days_back
            )
            if cisa_kev_status.ok and not cisa_kev_data.empty:
                sources.append("CISA KEV (Cyber Risk)")
            # Always store CISA KEV status in metadata (even if failed)

            # Fetch OWID health data
            # Try to map region to country (simplified: use region_name
            # if it's a country)
            country_name = (
                region_name
                if region_name in ["United States", "USA"]
                else "United States"
            )
            owid_health = self.owid_fetcher.fetch_health_stress_index(
                country=country_name, days_back=days_back
            )
            if not owid_health.empty:
                sources.append("OWID (Public Health)")

            # Fetch USGS earthquake data (environmental hazard)
            usgs_earthquakes = self.usgs_fetcher.fetch_earthquake_intensity(
                days_back=days_back
            )
            if not usgs_earthquakes.empty:
                sources.append("USGS (Earthquakes)")

            # Fetch legislative activity signal from GDELT (no-key fallback)
            legislative_data = pd.DataFrame()
            legislative_status = None
            try:
                legislative_data, legislative_status = (
                    self.gdelt_fetcher.fetch_legislative_attention(
                        region_name=region_name, days_back=days_back
                    )
                )
                if legislative_status.ok and not legislative_data.empty:
                    sources.append("GDELT Legislative Events")
            except Exception as e:
                logger.warning("Failed to fetch legislative data", error=str(e))
                # Create empty status for metadata
                from app.services.ingestion.gdelt_events import SourceStatus

                legislative_status = SourceStatus(
                    provider="GDELT Legislative Events",
                    ok=False,
                    error_type="exception",
                    error_detail=str(e)[:100],
                    fetched_at=datetime.now().isoformat(),
                    rows=0,
                    query_window_days=days_back,
                )

            # Fetch enforcement/ICE event signal from GDELT (for adjustment of political/social stress)
            enforcement_data = pd.DataFrame()
            enforcement_status = None
            try:
                enforcement_data, enforcement_status = (
                    self.gdelt_fetcher.fetch_enforcement_attention(
                        region_name=region_name, days_back=days_back
                    )
                )
                if enforcement_status.ok and not enforcement_data.empty:
                    sources.append("GDELT Enforcement Events")
            except Exception as e:
                logger.warning("Failed to fetch enforcement data", error=str(e))
                # Create empty status for metadata
                from app.services.ingestion.gdelt_events import SourceStatus

                enforcement_status = SourceStatus(
                    provider="GDELT Enforcement Events",
                    ok=False,
                    error_type="exception",
                    error_detail=str(e)[:100],
                    fetched_at=datetime.now().isoformat(),
                    rows=0,
                    query_window_days=days_back,
                )

            # Fetch political stress data (for US states only)
            political_data = pd.DataFrame()
            crime_data = pd.DataFrame()
            misinformation_data = pd.DataFrame()
            social_cohesion_data = pd.DataFrame()

            is_us_state = self._is_us_state(region_name)
            if is_us_state:
                try:
                    political_data = self.political_fetcher.calculate_political_stress(
                        state_name=region_name, days_back=days_back
                    )
                    if (
                        not political_data.empty
                        and "political_stress" in political_data.columns
                    ):
                        political_data = political_data[
                            ["timestamp", "political_stress"]
                        ]
                        sources.append("political_ingestion")
                except Exception as e:
                    logger.warning("Failed to fetch political data", error=str(e))

                try:
                    crime_data = self.crime_fetcher.calculate_crime_stress(
                        region_name=region_name, days_back=days_back
                    )
                    if not crime_data.empty and "crime_stress" in crime_data.columns:
                        crime_data = crime_data[["timestamp", "crime_stress"]]
                        sources.append("crime_ingestion")
                except Exception as e:
                    logger.warning("Failed to fetch crime data", error=str(e))

                try:
                    misinformation_data = (
                        self.misinformation_fetcher.calculate_misinformation_stress(
                            region_name=region_name, days_back=days_back
                        )
                    )
                    if (
                        not misinformation_data.empty
                        and "misinformation_stress" in misinformation_data.columns
                    ):
                        misinformation_data = misinformation_data[
                            ["timestamp", "misinformation_stress"]
                        ]
                        sources.append("misinformation_ingestion")
                except Exception as e:
                    logger.warning("Failed to fetch misinformation data", error=str(e))

                try:
                    social_cohesion_data = (
                        self.social_cohesion_fetcher.calculate_social_cohesion_stress(
                            region_name=region_name, days_back=days_back
                        )
                    )
                    if (
                        not social_cohesion_data.empty
                        and "social_cohesion_stress" in social_cohesion_data.columns
                    ):
                        social_cohesion_data = social_cohesion_data[
                            ["timestamp", "social_cohesion_stress"]
                        ]
                        sources.append("social_cohesion_ingestion")
                except Exception as e:
                    logger.warning("Failed to fetch social cohesion data", error=str(e))

            # Harmonize data
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
                and political_data.empty
                and crime_data.empty
                and misinformation_data.empty
                and social_cohesion_data.empty
            ):
                logger.warning("No data available for forecast")
                return {
                    "history": [],
                    "forecast": [],
                    "sources": [],
                    "metadata": {
                        "region_name": region_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "error": "No data available",
                        "sources_status": {
                            "gdelt": gdelt_status.to_dict(),
                            "openfema_emergency_management": openfema_status.to_dict(),
                        },
                    },
                }

            harmonized = self.harmonizer.harmonize(
                market_data=market_data,
                fred_consumer_sentiment=fred_consumer_sentiment,
                fred_unemployment=fred_unemployment,
                fred_jobless_claims=fred_jobless_claims,
                fred_gdp_growth=fred_gdp_growth if not fred_gdp_growth.empty else None,
                fred_cpi_inflation=(
                    fred_cpi_inflation if not fred_cpi_inflation.empty else None
                ),
                weather_data=weather_data,
                search_data=search_data,
                health_data=health_data,
                mobility_data=mobility_data,
                gdelt_tone=gdelt_tone,
                owid_health=owid_health,
                usgs_earthquakes=usgs_earthquakes,
                political_data=political_data,
                crime_data=crime_data,
                misinformation_data=misinformation_data,
                social_cohesion_data=social_cohesion_data,
            )

            if harmonized.empty or "behavior_index" not in harmonized.columns:
                logger.warning("Harmonized data is empty or missing behavior_index")
                return {
                    "history": [],
                    "forecast": [],
                    "sources": sources,
                    "metadata": {
                        "region_name": region_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "error": "Harmonized data is empty",
                        "sources_status": {
                            "gdelt": gdelt_status.to_dict(),
                            "openfema_emergency_management": openfema_status.to_dict(),
                        },
                    },
                }

            # Compute legislative_stress from GDELT legislative_attention (and optionally OpenStates)
            legislative_stress = 0.0
            max_legislative_attention = 0.0
            openstates_signal = 0.0

            if (
                not legislative_data.empty
                and "legislative_attention" in legislative_data.columns
            ):
                # Use GDELT legislative_attention as base signal
                max_legislative_attention = float(
                    legislative_data["legislative_attention"].max()
                )
                legislative_stress = max_legislative_attention

                # Optionally blend with OpenStates if available
                if openstates_status.ok and not openstates_activity.empty:
                    # Normalize OpenStates signal to [0,1] if it has a legislative_stress column
                    if "legislative_stress" in openstates_activity.columns:
                        openstates_signal = float(
                            openstates_activity["legislative_stress"].max()
                        )
                        # Blend: 70% GDELT, 30% OpenStates
                        legislative_stress = min(
                            1.0, 0.7 * legislative_stress + 0.3 * openstates_signal
                        )
                        logger.info(
                            "Blended legislative stress",
                            gdelt_attention=max_legislative_attention,
                            openstates_signal=openstates_signal,
                            blended_stress=legislative_stress,
                        )

            # Apply enforcement signal adjustment to political_stress and social_cohesion_stress
            # Bounded adjustment: enforcement_attention contributes up to +0.25 to political_stress, +0.20 to social_cohesion_stress
            enforcement_summary = f"No enforcement events in last {days_back}d (enforcement_attention=0.0)"
            max_enforcement_attention = 0.0
            enforcement_attention_applied = False
            if (
                not enforcement_data.empty
                and "enforcement_attention" in enforcement_data.columns
            ):
                # Merge enforcement_attention into harmonized data
                enforcement_df = enforcement_data[
                    ["timestamp", "enforcement_attention"]
                ].copy()
                enforcement_df["timestamp"] = pd.to_datetime(
                    enforcement_df["timestamp"], utc=True
                )
                if enforcement_df["timestamp"].dt.tz is not None:
                    enforcement_df["timestamp"] = enforcement_df[
                        "timestamp"
                    ].dt.tz_localize(None)
                    enforcement_df = enforcement_df.set_index("timestamp").sort_index()

                    # Align enforcement_attention with harmonized timestamps
                    harmonized["timestamp"] = pd.to_datetime(
                        harmonized["timestamp"], utc=True
                    )
                if harmonized["timestamp"].dt.tz is not None:
                    harmonized["timestamp"] = harmonized["timestamp"].dt.tz_localize(
                        None
                    )
                    harmonized_indexed = harmonized.set_index("timestamp").sort_index()

                    # Reindex enforcement to match harmonized timestamps (forward-fill for alignment)
                    enforcement_aligned = (
                        enforcement_df.reindex(harmonized_indexed.index)[
                            "enforcement_attention"
                        ]
                        .ffill()
                        .fillna(0.0)
                    )

                # Apply bounded adjustments: alpha=0.15 for political, beta=0.10 for social_cohesion
                # Cap total adjustment at +0.25 for political_stress, +0.20 for social_cohesion_stress
                alpha = 0.15  # Adjustment coefficient for political_stress
                beta = 0.10  # Adjustment coefficient for social_cohesion_stress

                if "political_stress" in harmonized_indexed.columns:
                    adjustment_political = (enforcement_aligned * alpha).clip(0.0, 0.25)
                    harmonized_indexed["political_stress"] = (
                        harmonized_indexed["political_stress"].fillna(0.0)
                        + adjustment_political
                    ).clip(0.0, 1.0)

                if "social_cohesion_stress" in harmonized_indexed.columns:
                    adjustment_social = (enforcement_aligned * beta).clip(0.0, 0.20)
                    harmonized_indexed["social_cohesion_stress"] = (
                        harmonized_indexed["social_cohesion_stress"].fillna(0.0)
                        + adjustment_social
                    ).clip(0.0, 1.0)

                    # Reset index back
                    harmonized = harmonized_indexed.reset_index()

                # Recompute behavior_index to reflect adjusted stress values
                harmonized = (
                    self.harmonizer.behavior_index_computer.compute_behavior_index(
                        harmonized
                    )
                )

                max_enforcement_attention = float(enforcement_aligned.max())
                event_count = len(enforcement_data)
                enforcement_summary = (
                    f"{event_count} enforcement-related events in last {days_back}d "
                    f"(max enforcement_attention={max_enforcement_attention:.2f}, "
                    f"adjustments: political_stress +{alpha*max_enforcement_attention:.2f} max, "
                    f"social_cohesion_stress +{beta*max_enforcement_attention:.2f} max)"
                )
                enforcement_attention_applied = True

                logger.info(
                    "Applied enforcement signal adjustment",
                    enforcement_events=event_count,
                    max_enforcement_attention=max_enforcement_attention,
                    enforcement_summary=enforcement_summary,
                )

            # PHASE 3.1: Apply shock multiplier to political_stress and social_cohesion_stress
            # When shock_events > 15, multiply these sub-indices to reflect crisis reality
            # Compute shock count from behavior_index in harmonized DataFrame (before history extraction)
            from app.services.calibration.config import SHOCK_MULTIPLIER

            if (
                "timestamp" in harmonized.columns
                and "behavior_index" in harmonized.columns
            ):
                harmonized_temp_indexed = harmonized.set_index("timestamp")
                try:
                    shock_events_prelim_sub = self.shock_detector.detect_shocks(
                        harmonized_temp_indexed
                    )
                    shock_count_sub = (
                        len(shock_events_prelim_sub)
                        if isinstance(shock_events_prelim_sub, list)
                        else 0
                    )

                    if shock_count_sub >= SHOCK_MULTIPLIER["threshold"]:
                        # Calculate multiplier for sub-indices (1.25x to 1.5x range)
                        sub_multiplier = min(
                            1.0
                            + (shock_count_sub / 100.0)
                            * SHOCK_MULTIPLIER["multiplier_per_shock"]
                            * 100,
                            1.5,  # Cap at 1.5x for sub-indices
                        )

                        # Apply multiplier to political_stress and social_cohesion_stress
                        if "political_stress" in harmonized.columns:
                            harmonized["political_stress"] = (
                                harmonized["political_stress"] * sub_multiplier
                            ).clip(0.0, 0.99)
                        if "social_cohesion_stress" in harmonized.columns:
                            harmonized["social_cohesion_stress"] = (
                                harmonized["social_cohesion_stress"] * sub_multiplier
                            ).clip(0.0, 0.99)

                        logger.info(
                            "Applied shock multiplier to political/social_cohesion stress",
                            shock_count=shock_count_sub,
                            multiplier=sub_multiplier,
                            political_stress_max=(
                                float(harmonized["political_stress"].max())
                                if "political_stress" in harmonized.columns
                                else 0.0
                            ),
                            social_cohesion_stress_max=(
                                float(harmonized["social_cohesion_stress"].max())
                                if "social_cohesion_stress" in harmonized.columns
                                else 0.0
                            ),
                        )

                        # Recompute behavior_index to reflect adjusted stress values
                        harmonized = self.harmonizer.behavior_index_computer.compute_behavior_index(
                            harmonized
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to apply shock multiplier to sub-indices", error=str(e)
                    )

            # Prepare history data with sub-indices
            # Keep full harmonized DataFrame for component extraction
            # (store in metadata)
            # But extract only needed columns for history
            sub_index_cols = [
                "economic_stress",
                "environmental_stress",
                "mobility_activity",
                "digital_attention",
                "public_health_stress",
                "political_stress",
                "crime_stress",
                "misinformation_stress",
                "social_cohesion_stress",
            ]
            history_cols = ["timestamp", "behavior_index"] + [
                col for col in sub_index_cols if col in harmonized.columns
            ]
            history = harmonized[history_cols].copy()

            # Preserve the full harmonized DataFrame
            # (with component metadata in attrs) for API extraction
            # We'll attach it to metadata temporarily
            harmonized_for_details = harmonized.copy()
            # Normalize timestamps to timezone-naive UTC
            history["timestamp"] = pd.to_datetime(history["timestamp"], utc=True)
            if history["timestamp"].dt.tz is not None:
                history["timestamp"] = history["timestamp"].dt.tz_localize(None)
            history = history.sort_values("timestamp").reset_index(drop=True)

            # Window integrity: Ensure we have enough data points for forecasting
            # MIN_HISTORY_DAYS defines the minimum viable history window for stable forecasts.
            # If days_back < MIN_HISTORY_DAYS, we return an explicit "insufficient_history" flag.
            if len(history) < MIN_HISTORY_DAYS:
                logger.warning(
                    "Insufficient historical data for forecasting",
                    data_points=len(history),
                )
                # Convert timestamps to ISO strings for API response
                history_dict = history.copy()
                if "timestamp" in history_dict.columns:
                    history_dict["timestamp"] = history_dict["timestamp"].dt.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                    # Explicit "insufficient history" response with clear flag
                    return {
                        "history": history_dict.to_dict("records"),
                        "forecast": [],
                        "sources": sources,
                        "metadata": {
                            "region_name": region_name,
                            "latitude": latitude,
                            "longitude": longitude,
                            "warning": "Insufficient data for forecasting",
                            "data_points": len(history),
                            "flags": {
                                "insufficient_history": True,
                                "min_history_days_required": MIN_HISTORY_DAYS,
                                "actual_data_points": len(history),
                            },
                            "sources_status": {
                                "gdelt": gdelt_status.to_dict(),
                                "openfema_emergency_management": openfema_status.to_dict(),
                            },
                        },
                    }

            # Extract behavior_index time series
            if "behavior_index" not in history.columns:
                logger.warning(
                    "behavior_index column missing from history, using default 0.5"
                )
                history["behavior_index"] = 0.5

            # Ensure behavior_index values are valid
            history["behavior_index"] = pd.to_numeric(
                history["behavior_index"], errors="coerce"
            ).fillna(0.5)
            history["behavior_index"] = history["behavior_index"].clip(0.0, 1.0)

            # CRITICAL: Apply Shock Multiplier to align with reality
            # High shock events (e.g., 55 in MN) must produce high risk scores
            # Compute shock count early for multiplier application
            history_indexed = history.set_index("timestamp")
            shock_events_prelim = self.shock_detector.detect_shocks(history_indexed)
            shock_count = (
                len(shock_events_prelim) if isinstance(shock_events_prelim, list) else 0
            )

            shock_multiplier_applied = False
            if shock_count >= SHOCK_MULTIPLIER["threshold"]:
                # Calculate multiplier: base + (shock_count / 100) * multiplier_per_shock * 100
                # Example: 55 shocks = 1.0 + (55/100) * 0.01 * 100 = 1.55x
                multiplier = (
                    SHOCK_MULTIPLIER["base_multiplier"]
                    + (shock_count / 100.0)
                    * SHOCK_MULTIPLIER["multiplier_per_shock"]
                    * 100
                )
                # Apply multiplier: behavior_index = min(base_index * multiplier, max_behavior_index)
                history["behavior_index"] = (
                    history["behavior_index"] * multiplier
                ).clip(0.0, SHOCK_MULTIPLIER["max_behavior_index"])
                shock_multiplier_applied = True

                logger.info(
                    "Shock multiplier applied",
                    shock_count=shock_count,
                    multiplier=multiplier,
                    behavior_index_before_multiplier=(
                        history["behavior_index"].iloc[-1] / multiplier
                        if multiplier > 0
                        else 0.0
                    ),
                    behavior_index_after_multiplier=history["behavior_index"].iloc[-1],
                )

            behavior_ts = history.set_index("timestamp")["behavior_index"]

            # Validate time series
            if behavior_ts.empty:
                logger.warning(
                    "Empty behavior_index time series, returning empty forecast"
                )
                return {
                    "history": (
                        history_dict.to_dict("records") if not history.empty else []
                    ),
                    "forecast": [],
                    "sources": sources,
                    "metadata": {
                        "region_name": region_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "warning": "Empty time series",
                        "data_points": len(history),
                        "sources_status": {
                            "gdelt": gdelt_status.to_dict(),
                            "openfema_emergency_management": openfema_status.to_dict(),
                        },
                    },
                }

            # Fit Exponential Smoothing (Holt-Winters) model
            try:
                if not HAS_STATSMODELS:
                    logger.warning(
                        "statsmodels not available, using simple moving average"
                    )
                    # Fallback to simple moving average if statsmodels not available
                    window_size = min(7, len(behavior_ts) // 2)
                    if window_size < 2:
                        window_size = 2
                    ma = behavior_ts.rolling(window=window_size, center=False).mean()
                    if ma.empty or len(ma) == 0:
                        last_value = (
                            behavior_ts.iloc[-1] if len(behavior_ts) > 0 else 0.5
                        )
                    else:
                        last_value = (
                            float(ma.iloc[-1])
                            if pd.notna(ma.iloc[-1])
                            else (
                                float(behavior_ts.iloc[-1])
                                if len(behavior_ts) > 0
                                and pd.notna(behavior_ts.iloc[-1])
                                else 0.5
                            )
                        )

                    # Ensure last_value is valid
                    if pd.isna(last_value) or not isinstance(last_value, (int, float)):
                        last_value = 0.5
                    last_value = max(0.0, min(1.0, float(last_value)))

                    trend = (
                        (float(behavior_ts.iloc[-1]) - float(behavior_ts.iloc[0]))
                        / len(behavior_ts)
                        if len(behavior_ts) > 1
                        and pd.notna(behavior_ts.iloc[-1])
                        and pd.notna(behavior_ts.iloc[0])
                        else 0.0
                    )
                    # Clamp trend to reasonable bounds
                    trend = max(-0.1, min(0.1, float(trend)))
                    # Generate forecast dates safely
                    try:
                        last_date = behavior_ts.index[-1]
                        if not isinstance(last_date, pd.Timestamp):
                            last_date = pd.Timestamp(last_date)
                        forecast_dates = pd.date_range(
                            start=last_date + pd.Timedelta(days=1),
                            periods=forecast_horizon,
                            freq="D",
                            tz=None,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to generate forecast dates", error=str(e)
                        )
                        forecast_dates = pd.date_range(
                            start=pd.Timestamp.now(),
                            periods=forecast_horizon,
                            freq="D",
                            tz=None,
                        )

                    forecast_values = []
                    for i in range(1, forecast_horizon + 1):
                        value = last_value + trend * i
                        # Clamp to valid range
                        value = max(0.0, min(1.0, float(value)))
                        forecast_values.append(value)

                    forecast_result = pd.Series(forecast_values, index=forecast_dates)

                    # Calculate std_error safely
                    if len(behavior_ts) > 1:
                        std_error = float(behavior_ts.std())
                        if pd.isna(std_error):
                            std_error = 0.1
                        std_error = max(0.01, min(0.5, std_error))
                    else:
                        std_error = 0.1
                else:
                    # Use additive seasonality with yearly period (365 days)
                    # For shorter series, use trend-only model
                    if len(behavior_ts) >= 30:
                        model = ExponentialSmoothing(
                            behavior_ts,
                            trend="add",
                            seasonal="add",
                            seasonal_periods=min(
                                7, len(behavior_ts) // 4
                            ),  # Weekly seasonality
                        ).fit(optimized=True)
                    else:
                        # Trend-only for shorter series
                        model = ExponentialSmoothing(behavior_ts, trend="add").fit(
                            optimized=True
                        )

                    # Generate forecast with error handling
                    try:
                        forecast_result = model.forecast(steps=forecast_horizon)
                    except Exception as e:
                        logger.warning(
                            "Model forecast failed, using fallback", error=str(e)
                        )
                        # Fallback: use last value with small trend
                        last_val = (
                            float(behavior_ts.iloc[-1])
                            if len(behavior_ts) > 0 and pd.notna(behavior_ts.iloc[-1])
                            else 0.5
                        )
                        forecast_result = pd.Series([last_val] * forecast_horizon)

                    # Validate forecast_result
                    if (
                        not isinstance(forecast_result, pd.Series)
                        or len(forecast_result) == 0
                    ):
                        logger.warning("Invalid forecast result, using fallback")
                        last_val = (
                            float(behavior_ts.iloc[-1])
                            if len(behavior_ts) > 0 and pd.notna(behavior_ts.iloc[-1])
                            else 0.5
                        )
                        forecast_result = pd.Series([last_val] * forecast_horizon)

                    # Ensure forecast values are valid
                    forecast_result = pd.to_numeric(
                        forecast_result, errors="coerce"
                    ).fillna(0.5)
                    forecast_result = forecast_result.clip(0.0, 1.0)

                    # Calculate confidence intervals
                    # (approximate using model's fitted values variance)
                    try:
                        fitted_values = model.fittedvalues
                        residuals = behavior_ts - fitted_values
                        std_error = float(residuals.std())
                        if pd.isna(std_error) or std_error <= 0:
                            std_error = 0.1
                        std_error = max(0.01, min(0.5, std_error))
                    except Exception as e:
                        logger.warning("Failed to calculate std_error", error=str(e))
                        std_error = 0.1

                # Generate forecast dates with error handling
                try:
                    if (
                        isinstance(forecast_result, pd.Series)
                        and not forecast_result.index.empty
                        and len(forecast_result) > 0
                    ):
                        forecast_dates = forecast_result.index
                    else:
                        last_date = behavior_ts.index.max()
                        if not isinstance(last_date, pd.Timestamp):
                            last_date = pd.Timestamp(last_date)
                        forecast_dates = pd.date_range(
                            start=last_date + timedelta(days=1),
                            periods=forecast_horizon,
                            freq="D",
                            tz=None,
                        )
                except Exception as e:
                    logger.warning("Failed to generate forecast dates", error=str(e))
                    forecast_dates = pd.date_range(
                        start=pd.Timestamp.now(),
                        periods=forecast_horizon,
                        freq="D",
                        tz=None,
                    )

                # Ensure forecast_result has correct length
                if len(forecast_result) != forecast_horizon:
                    logger.warning(
                        f"Forecast length mismatch: expected {forecast_horizon}, "
                        f"got {len(forecast_result)}"
                    )
                    if len(forecast_result) > forecast_horizon:
                        forecast_result = forecast_result[:forecast_horizon]
                    else:
                        last_val = (
                            float(forecast_result.iloc[-1])
                            if len(forecast_result) > 0
                            else 0.5
                        )
                        forecast_result = pd.concat(
                            [
                                forecast_result,
                                pd.Series(
                                    [last_val]
                                    * (forecast_horizon - len(forecast_result))
                                ),
                            ]
                        )

                # Create forecast DataFrame with confidence intervals
                try:
                    forecast_df = pd.DataFrame(
                        {
                            "timestamp": forecast_dates[: len(forecast_result)],
                            "prediction": forecast_result.values,
                            "lower_bound": (forecast_result - 1.96 * std_error).values,
                            "upper_bound": (forecast_result + 1.96 * std_error).values,
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to create forecast DataFrame", error=str(e))
                    # Fallback: create minimal forecast
                    forecast_df = pd.DataFrame(
                        {
                            "timestamp": forecast_dates[:forecast_horizon],
                            "prediction": [0.5] * forecast_horizon,
                            "lower_bound": [0.4] * forecast_horizon,
                            "upper_bound": [0.6] * forecast_horizon,
                        }
                    )

                # Clip values to valid range [0.0, 1.0] and ensure numeric
                forecast_df["prediction"] = (
                    pd.to_numeric(forecast_df["prediction"], errors="coerce")
                    .fillna(0.5)
                    .clip(0.0, 1.0)
                )
                forecast_df["lower_bound"] = (
                    pd.to_numeric(forecast_df["lower_bound"], errors="coerce")
                    .fillna(0.4)
                    .clip(0.0, 1.0)
                )
                forecast_df["upper_bound"] = (
                    pd.to_numeric(forecast_df["upper_bound"], errors="coerce")
                    .fillna(0.6)
                    .clip(0.0, 1.0)
                )

                # Ensure forecast is sorted by timestamp
                # (invariant: forecast arrays always sorted)
                forecast_df = forecast_df.sort_values("timestamp").reset_index(
                    drop=True
                )

                # Prepare metadata
                model_type = (
                    "Moving Average + Trend"
                    if not HAS_STATSMODELS
                    else "ExponentialSmoothing (Holt-Winters)"
                )
                metadata = {
                    "region_name": region_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "forecast_date": datetime.now().isoformat(),
                    "forecast_horizon": forecast_horizon,
                    "historical_data_points": len(history),
                    "model_type": model_type,
                    "confidence_level": 0.95,
                    "sources": sources,
                    "_harmonized_df": harmonized_for_details,  # Store for extraction
                }
                # Add source status metadata
                sources_status_dict = {
                    "gdelt": gdelt_status.to_dict(),
                    "openfema_emergency_management": openfema_status.to_dict(),
                    "openstates_legislative": openstates_status.to_dict(),
                    "nws_alerts": nws_alerts_status.to_dict(),
                    "cisa_kev": cisa_kev_status.to_dict(),
                    "search_trends": search_status.to_dict(),
                    "mobility_patterns": mobility_status.to_dict(),
                }
                # Always include legislative_status and enforcement_status in sources_status (even if None/empty)
                if legislative_status is not None:
                    sources_status_dict["gdelt_legislative"] = (
                        legislative_status.to_dict()
                    )
                    # Always include openstates_status for legislative_activity (even if missing key)
                    sources_status_dict["openstates_legislative"] = (
                        openstates_status.to_dict()
                    )
                if enforcement_status is not None:
                    sources_status_dict["gdelt_enforcement"] = (
                        enforcement_status.to_dict()
                    )
                    metadata["sources_status"] = sources_status_dict

                    # Guardrail: Detect if behavior_index is suspiciously all zeros when sources have data
                    # This indicates a pipeline bug, not real-world conditions
                    max_bi = (
                        float(history["behavior_index"].max())
                        if not history.empty and "behavior_index" in history.columns
                        else 0.0
                    )
                    has_source_data = any(
                        status.get("ok", False) and status.get("rows", 0) > 0
                        for status in sources_status_dict.values()
                        if isinstance(status, dict)
                    )

                if (
                    max_bi == 0.0
                    and has_source_data
                    and len(history) >= MIN_HISTORY_DAYS
                ):
                    logger.error(
                        "Pipeline integrity failure: behavior_index is all zeros despite source data",
                        data_points=len(history),
                        sources_with_data=sum(
                            1
                            for status in sources_status_dict.values()
                            if isinstance(status, dict)
                            and status.get("ok", False)
                            and status.get("rows", 0) > 0
                        ),
                    )
                    # Fallback: use a safe default (0.4 = moderate baseline) rather than 0.0
                    # This prevents misleading "zero stress" when data exists but aggregation failed
                    history["behavior_index"] = 0.4
                    behavior_ts = history.set_index("timestamp")["behavior_index"]
                    # Flag this in metadata for transparency
                    metadata.setdefault("flags", {})["behavior_index_fallback"] = True
                    metadata.setdefault("flags", {})[
                        "fallback_reason"
                    ] = "behavior_index was all zeros despite source data"

                # Add shock multiplier metadata to integrity section
                if "integrity" not in metadata:
                    metadata["integrity"] = {}
                if shock_multiplier_applied:
                    metadata["integrity"]["shock_multiplier_applied"] = True
                    metadata["integrity"]["shock_count"] = shock_count
                    metadata["integrity"]["shock_multiplier_value"] = multiplier
                else:
                    metadata["integrity"]["shock_multiplier_applied"] = False
                    metadata["integrity"]["shock_count"] = shock_count

                # Add legislative and enforcement metadata
                # Note: metadata["sources"] is a list of source names, not a dict
                # Use metadata["source_signals"] or similar for signal-level metadata
                if "source_signals" not in metadata:
                    metadata["source_signals"] = {}
                if "gdelt" not in metadata["source_signals"]:
                    metadata["source_signals"]["gdelt"] = {}
                    metadata["source_signals"]["gdelt"]["legislative_attention"] = {
                        "value": max_legislative_attention,
                        "normalized": True,
                        "window_days": days_back,
                        "region_filter": region_name or "global",
                        "applied": True,
                    }
                    metadata["source_signals"]["gdelt"]["enforcement_attention"] = {
                        "value": max_enforcement_attention,
                        "normalized": True,
                        "window_days": days_back,
                        "region_filter": region_name or "global",
                        "applied": enforcement_attention_applied,
                    }

                # Add to dimensions drivers (if dimensions exist in harmonized data)
                if "dimensions" not in metadata:
                    metadata["dimensions"] = {}

                    # Add legislative_activity dimension
                    metadata["dimensions"]["legislative_activity"] = {
                        "value": legislative_stress,
                        "label": "legislative activity",
                        "drivers": {
                            "gdelt_legislative_attention": max_legislative_attention,
                        },
                    }
                if openstates_status.ok and openstates_signal > 0:
                    metadata["dimensions"]["legislative_activity"]["drivers"][
                        "openstates_events"
                    ] = openstates_signal

                if "political_stress" not in metadata["dimensions"]:
                    metadata["dimensions"]["political_stress"] = {"drivers": {}}
                elif "drivers" not in metadata["dimensions"]["political_stress"]:
                    metadata["dimensions"]["political_stress"]["drivers"] = {}
                    # Add legislative_stress as a driver of political_stress
                    metadata["dimensions"]["political_stress"]["drivers"][
                        "legislative_activity"
                    ] = legislative_stress
                    metadata["dimensions"]["political_stress"]["drivers"][
                        "enforcement_attention"
                    ] = max_enforcement_attention

                if "social_cohesion_stress" not in metadata["dimensions"]:
                    metadata["dimensions"]["social_cohesion_stress"] = {"drivers": {}}
                elif "drivers" not in metadata["dimensions"]["social_cohesion_stress"]:
                    metadata["dimensions"]["social_cohesion_stress"]["drivers"] = {}
                    metadata["dimensions"]["social_cohesion_stress"]["drivers"][
                        "enforcement_attention"
                    ] = max_enforcement_attention

                # Add enforcement summary to intelligence layer
                if enforcement_summary:
                    if "intelligence" not in metadata:
                        metadata["intelligence"] = {}
                    metadata["intelligence"][
                        "enforcement_summary"
                    ] = enforcement_summary
                    metadata["intelligence"][
                        "enforcement_attention"
                    ] = max_enforcement_attention

                # Cache result with LRU eviction
                with self._cache_lock:
                    self._cache[cache_key] = (history, forecast_df, metadata)

                    # Enforce cache size limit (LRU eviction)
                    if (
                        self._max_cache_size is not None
                        and len(self._cache) > self._max_cache_size
                    ):
                        # Remove oldest entry (first key in dict)
                        oldest_key = next(iter(self._cache))
                        del self._cache[oldest_key]

                logger.info(
                        "Forecast generated successfully",
                        region_name=region_name,
                        forecast_points=len(forecast_df),
                        prediction_range=(
                            forecast_df["prediction"].min(),
                            forecast_df["prediction"].max(),
                        ),
                    )

                # Convert timestamps to ISO strings for API response
                history_dict = history.copy()
                history_dict["timestamp"] = history_dict["timestamp"].dt.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
                forecast_dict = forecast_df.copy()
                forecast_dict["timestamp"] = forecast_dict["timestamp"].dt.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )

                # Store harmonized DataFrame (with component metadata) for extraction
                # Attach to metadata so API can extract component details
                # Note: This will be removed in the API layer before JSON serialization
                metadata["_harmonized_df"] = harmonized_for_details

                # Intelligence Layer Analysis
                intelligence_data = self._analyze_intelligence(
                    history, harmonized_for_details
                )

                return {
                    "history": history_dict.to_dict("records"),
                    "forecast": forecast_dict.to_dict("records"),
                    "sources": sources,
                    "metadata": metadata,
                    **intelligence_data,  # Add intelligence layer data
                }

            except Exception as e:
                logger.error(
                    "Error fitting forecasting model", error=str(e), exc_info=True
                )
                # Convert timestamps to ISO strings for API response
                history_dict = history.copy()
                if "timestamp" in history_dict.columns:
                    history_dict["timestamp"] = history_dict["timestamp"].dt.strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                    return {
                        "history": history_dict.to_dict("records"),
                        "forecast": [],
                        "sources": sources,
                        "metadata": {
                            "region_name": region_name,
                            "latitude": latitude,
                            "longitude": longitude,
                            "error": f"Model fitting failed: {str(e)}",
                        },
                        **self._empty_intelligence_data(),  # Add empty intelligence data
                    }

        except Exception as e:
            logger.error("Error generating forecast", error=str(e), exc_info=True)
            return {
                "history": [],
                "forecast": [],
                "sources": sources,
                "metadata": {
                    "region_name": region_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "error": str(e),
                },
                **self._empty_intelligence_data(),  # Add empty intelligence data
            }

    def _analyze_intelligence(
        self, history_df: pd.DataFrame, harmonized_df: pd.DataFrame
    ) -> Dict:
        """Run intelligence layer analysis on historical data."""
        try:
            # Convert history DataFrame if needed
            if (
                "timestamp" not in history_df.columns
                and history_df.index.name == "timestamp"
            ):
                history_df = history_df.reset_index()

            # Ensure timestamp is datetime
            history_df_work = history_df.copy()
            if "timestamp" in history_df_work.columns:
                history_df_work["timestamp"] = pd.to_datetime(
                    history_df_work["timestamp"]
                )
                # Set timestamp as index for shock detection
                history_df_indexed = history_df_work.set_index("timestamp")
            else:
                history_df_indexed = history_df_work

            # 1. Shock Detection (use indexed version)
            shock_events = self.shock_detector.detect_shocks(history_df_indexed)

            # 2. Convergence Analysis (use original with timestamp column)
            convergence_result = self.convergence_engine.analyze_convergence(history_df)

            # 3. Risk Classification
            if len(history_df) > 0 and "behavior_index" in history_df.columns:
                latest_bi = history_df["behavior_index"].iloc[-1]
                # Calculate trend direction
                if len(history_df) >= 7:
                    recent_trend = (
                        history_df["behavior_index"].tail(7).iloc[-1]
                        - history_df["behavior_index"].tail(7).iloc[0]
                    )
                    trend_direction = (
                        "increasing"
                        if recent_trend > 0.05
                        else "decreasing" if recent_trend < -0.05 else "stable"
                    )
                else:
                    trend_direction = "stable"

                risk_classification = self.risk_classifier.classify_risk(
                    behavior_index=float(latest_bi),
                    shock_events=shock_events,
                    convergence_score=convergence_result.get("score", 0.0),
                    trend_direction=trend_direction,
                )
            else:
                risk_classification = {
                    "tier": "stable",
                    "risk_score": 0.5,
                    "base_risk": 0.5,
                    "shock_adjustment": 0.0,
                    "convergence_adjustment": 0.0,
                    "trend_adjustment": 0.0,
                    "contributing_factors": [],
                }

            # 4. Forecast Confidence (use original with timestamp column)
            confidence_scores = self.forecast_monitor.calculate_confidence(history_df)

            # 5. Model Drift (use original with timestamp column)
            drift_scores = self.forecast_monitor.detect_drift(history_df)

            # 6. Correlation Analysis (use original with timestamp column)
            correlation_result = self.correlation_engine.calculate_correlations(
                history_df
            )

            return {
                "shock_events": shock_events,
                "convergence": {
                    "score": convergence_result.get("score", 0.0),
                    "reinforcing_signals": [
                        [sig[0], sig[1], sig[2]]
                        for sig in convergence_result.get("reinforcing_signals", [])
                    ],
                    "conflicting_signals": [
                        [sig[0], sig[1], sig[2]]
                        for sig in convergence_result.get("conflicting_signals", [])
                    ],
                    "patterns": convergence_result.get("patterns", []),
                },
                "risk_tier": risk_classification,
                "forecast_confidence": confidence_scores,
                "model_drift": drift_scores,
                "correlations": {
                    "correlations": correlation_result.get("correlations", {}),
                    "relationships": correlation_result.get("relationships", []),
                    "indices_analyzed": correlation_result.get("indices_analyzed", []),
                },
            }
        except Exception as e:
            logger.warning(
                "Intelligence layer analysis failed", error=str(e), exc_info=True
            )
            return self._empty_intelligence_data()

    def _empty_intelligence_data(self) -> Dict:
        """Return empty intelligence data structure."""
        return {
            "shock_events": [],
            "convergence": {
                "score": 0.0,
                "reinforcing_signals": [],
                "conflicting_signals": [],
                "patterns": [],
            },
            "risk_tier": {
                "tier": "stable",
                "risk_score": 0.5,
                "base_risk": 0.5,
                "shock_adjustment": 0.0,
                "convergence_adjustment": 0.0,
                "trend_adjustment": 0.0,
                "contributing_factors": [],
            },
            "forecast_confidence": {},
            "model_drift": {},
            "correlations": {
                "correlations": {},
                "relationships": [],
                "indices_analyzed": [],
            },
        }
