# SPDX-License-Identifier: PROPRIETARY
"""Interpretable Behavior Index computation with sub-indices.

This module computes a composite Behavior Index from multiple human behavior
dimensions, each represented by a normalized sub-index.
"""
import math
from typing import Any, Dict

import pandas as pd
import structlog

from app.services.calibration.config import BEHAVIOR_INDEX_WEIGHTS

logger = structlog.get_logger("core.behavior_index")

# ====================================================================
# GLOBAL SUB-INDEX TAXONOMY (Canonical Parent/Child Mappings)
# ====================================================================

# Primary 9 parent indices (MUST always be present)
PARENT_INDEX_KEYS = [
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

# Child index specifications by parent (global superset)
# Indices marked with # [BATCH_1] can be computed from existing data sources
# Others require new connectors (to be added in Batch 2+)
CHILD_INDEX_SPEC = {
    "economic_stress": [
        # Existing (already implemented)
        "labor_stress",
        "inflation_cost_pressure",
        "financial_volatility_stress",
        # New (Batch 1: from existing data)
        "household_financial_stress",  # [BATCH_1] FRED debt/credit proxies
        # New (Batch 2+: requires new connectors)
        "income_inequality_pressure",  # [BATCH_2] World Bank Gini
        "housing_cost_burden",  # [BATCH_2] FRED housing/rent indices
        # New (Batch 3: from existing data)
        "gdp_growth_stress",  # [BATCH_3] derived from stress_index (GDP stress proxy)
        "unemployment_stress",  # [BATCH_3] direct FRED unemployment (separate from labor_stress)
        # New (Batch 5: from existing data)
        "food_price_stress",  # [BATCH_5] from inflation_cost_pressure (food CPI proxy)
        # New (Batch 6: from existing data)
        "energy_price_stress",  # [BATCH_6] from inflation volatility (energy price proxy)
        # New (Batch 7: from existing data)
        "household_debt_stress",  # [BATCH_7] from stress_index + financial_volatility_stress
    ],
    "environmental_stress": [
        # Existing
        "weather_severity_stress",
        "disaster_activation_stress",
        "environmental_volatility",
        # New (Batch 1: from existing data)
        "heatwave_stress",  # [BATCH_1] from discomfort_score extremes
        # New (Batch 2+: requires new connectors)
        "drought_stress",  # [BATCH_2] from precipitation/weather patterns
        "flood_risk_stress",  # [BATCH_2] from weather patterns (high precip/humidity proxy)
        "coldwave_stress",  # [BATCH_2] from discomfort_score extremes (cold patterns)
        "air_quality_stress",  # [BATCH_2] OpenAQ
        "water_stress",  # [BATCH_2] NOAA drought indices
    ],
    "mobility_activity": [
        # Existing
        "mobility_suppression",
        "mobility_shock",
        "mobility_recovery_momentum",
        # New (Batch 2+: requires new connectors)
        "commuting_disruption",  # [BATCH_2] Google/Apple Mobility
        "long_distance_travel_disruption",  # [BATCH_2] OpenSky/flight data
        "supply_chain_mobility",  # [BATCH_2] port/shipping data
        # New (Batch 4: from existing data)
        "transit_disruption_stress",  # [BATCH_4] from mobility_index volatility
        "congestion_stress",  # [BATCH_4] from mobility_index volatility patterns
    ],
    "digital_attention": [
        # Existing
        "attention_intensity",
        "attention_volatility",
        # New (Batch 1: from existing data)
        "news_polarization_stress",  # [BATCH_1] GDELT tone variance/divergence
        # New (Batch 2+: requires new connectors)
        "social_media_attention_panic",  # [BATCH_2] Twitter/Reddit APIs
        "platform_dependency_stress",  # [BATCH_2] attention entropy analysis
        # New (Batch 4: from existing data)
        "search_attention_intensity",  # [BATCH_4] search_interest_score normalized (separate from combined attention_intensity)
        # New (Batch 7: from existing data)
        "news_cycle_intensity",  # [BATCH_7] from GDELT event volume (news cycle pressure)
    ],
    "public_health_stress": [
        # Existing
        "health_incident_pressure",
        "health_system_strain",
        "mental_health_proxy",
        # New (Batch 2+: requires new connectors)
        "pandemic_risk_pressure",  # [BATCH_2] WHO/CDC specialized feeds
        "chronic_disease_burden",  # [BATCH_2] country-level NCD data
        "vaccination_resilience",  # [BATCH_2] OWID vaccination + hesitancy
        # New (Batch 5: from existing data)
        "hospital_capacity_strain",  # [BATCH_5] from health_risk_index volatility (strain proxy)
        # New (Batch 6: from existing data)
        "mortality_spike_risk",  # [BATCH_6] from health_risk_index spikes (mortality risk proxy)
        # New (Batch 7: from existing data)
        "infectious_incident_pressure",  # [BATCH_7] from health_incident_pressure (infectious disease proxy)
    ],
    "political_stress": [
        # Existing
        "legislative_volatility",
        "enforcement_pressure",
        "civic_disruption_proxy",
        # New (Batch 2+: requires new connectors)
        "governance_quality_stress",  # [BATCH_2] World Bank WGI
        "election_tension_index",  # [BATCH_2] ACLED/event proxies
        "policy_uncertainty_stress",  # [BATCH_2] news-based EPU indices
        # New (Batch 4: from existing data)
        "protest_intensity",  # [BATCH_4] from enforcement_attention + legislative volatility (protest proxy)
        # New (Batch 7: from existing data)
        "conflict_activity_stress",  # [BATCH_7] from enforcement_attention + civic_disruption (conflict proxy)
    ],
    "crime_stress": [
        # Existing
        "public_safety_velocity",
        "crime_narrative_intensity",
        # New (Batch 2+: requires new connectors)
        "property_crime_stress",  # [BATCH_2] national crime stats
        "organized_crime_proxy",  # [BATCH_2] GDELT/seizure event proxies
        # New (Batch 5: from existing data)
        "violent_crime_stress",  # [BATCH_5] from GDELT enforcement_attention (violent crime proxy)
        # New (Batch 6: from existing data)
        "property_crime_stress",  # [BATCH_6] from enforcement_attention patterns (property crime proxy)
    ],
    "misinformation_stress": [
        # Existing
        "narrative_fragmentation",
        "sentiment_whiplash",
        # New (Batch 2+: requires new connectors)
        "fact_check_volume_stress",  # [BATCH_2] fact-check RSS/APIs
        "platform_misinfo_enforcement_gap",  # [BATCH_2] transparency reports
        "conspiracy_theme_intensity",  # [BATCH_2] GDELT topic clustering
        # New (Batch 5: from existing data)
        "misinformation_intensity",  # [BATCH_5] from GDELT narrative fragmentation + sentiment volatility
    ],
    "social_cohesion_stress": [
        # Existing
        "trust_conflict_proxy",
        "community_anxiety_proxy",
        # New (Batch 2+: requires new connectors)
        "economic_inequality_cohesion_stress",  # [BATCH_2] poverty + Gini combo
        "conflict_polarization_pressure",  # [BATCH_2] ACLED targeted events
        "institutional_trust_decline",  # [BATCH_2] survey proxies (low-frequency)
        # New (Batch 6: from existing data)
        "institutional_trust_erosion",  # [BATCH_6] from civic_disruption + narrative_fragmentation
    ],
}

# Extended Metric Groups (secondary sections, not in primary Behavior Index)
# These are optional and can be exposed separately
EXTENDED_GROUP_SPEC = {
    "demographics_inequality": [
        "population_density_pressure",  # [BATCH_2] UN/World Bank
        "youth_bulge_pressure",  # [BATCH_2] demographic data
        "aging_population_pressure",  # [BATCH_2] demographic data
        "income_inequality_static",  # [BATCH_2] World Bank Gini
        "poverty_rate_stress",  # [BATCH_2] World Bank
    ],
    "education_human_capital": [
        "school_closure_pressure",  # [BATCH_2] UNESCO/OWID
        "learning_loss_proxy",  # [BATCH_2] PISA/proxy data
        "education_attainment_gap",  # [BATCH_2] UNESCO
    ],
    "infrastructure_services": [
        "electricity_outage_stress",  # [BATCH_2] outage APIs/feeds
        "internet_access_gap",  # [BATCH_2] ITU/World Bank
        "transport_infrastructure_stress",  # [BATCH_2] transit disruption data
    ],
    "migration_displacement": [
        "refugee_inflow_pressure",  # [BATCH_2] UNHCR
        "internal_displacement_stress",  # [BATCH_2] IDMC
        "return_migration_volatility",  # [BATCH_2] IOM
    ],
    "tech_cyber": [
        "cyber_incident_velocity",  # [BATCH_1] extend existing cyber_risk
        "critical_vulnerability_pressure",  # [BATCH_1] CISA KEV (already have)
        "digital_freedom_stress",  # [BATCH_2] NetBlocks/OONI
    ],
}


class BehaviorIndexComputer:
    """
    Compute interpretable Behavior Index from multiple behavioral dimensions.

    The Behavior Index is a composite measure that aggregates sub-indices
    representing different aspects of human behavioral patterns:
    - ECONOMIC_STRESS: Economic uncertainty and market stress
    - ENVIRONMENTAL_STRESS: Weather-related discomfort and extreme conditions
    - MOBILITY_ACTIVITY: Population movement and activity patterns
    - DIGITAL_ATTENTION: Digital attention spikes and media intensity
    - PUBLIC_HEALTH_STRESS: Public health indicators affecting behavior

    Each sub-index is normalized to [0.0, 1.0] where higher values indicate
    more stress/disruption (for stress indices) or more activity (for activity indices).
    """

    def __init__(
        self,
        economic_weight: float = BEHAVIOR_INDEX_WEIGHTS["economic_weight"],
        environmental_weight: float = BEHAVIOR_INDEX_WEIGHTS["environmental_weight"],
        mobility_weight: float = BEHAVIOR_INDEX_WEIGHTS["mobility_weight"],
        digital_attention_weight: float = BEHAVIOR_INDEX_WEIGHTS[
            "digital_attention_weight"
        ],
        health_weight: float = BEHAVIOR_INDEX_WEIGHTS["health_weight"],
        political_weight: float = BEHAVIOR_INDEX_WEIGHTS["political_weight"],
        crime_weight: float = BEHAVIOR_INDEX_WEIGHTS["crime_weight"],
        misinformation_weight: float = BEHAVIOR_INDEX_WEIGHTS["misinformation_weight"],
        social_cohesion_weight: float = BEHAVIOR_INDEX_WEIGHTS[
            "social_cohesion_weight"
        ],
    ):
        """
        Initialize the Behavior Index computer.

        Args:
            economic_weight: Weight for economic stress sub-index (default: 0.25)
            environmental_weight: Weight for environmental stress sub-index
                (default: 0.25)
            mobility_weight: Weight for mobility activity sub-index (default: 0.20)
            digital_attention_weight: Weight for digital attention sub-index
                (default: 0.15)
            health_weight: Weight for public health stress sub-index (default: 0.15)
            political_weight: Weight for political stress sub-index (default: 0.15)

        Note: Weights should sum to 1.0. If they don't, they will be normalized.
        When new weights are 0.0, they are excluded (backward compatible).
        """
        # Store original weights
        self._original_weights = {
            "economic": economic_weight,
            "environmental": environmental_weight,
            "mobility": mobility_weight,
            "digital_attention": digital_attention_weight,
            "health": health_weight,
            "political": political_weight,
            "crime": crime_weight,
            "misinformation": misinformation_weight,
            "social_cohesion": social_cohesion_weight,
        }

        # Calculate total weight (only include non-zero weights for
        # backward compatibility)
        total_weight = (
            economic_weight
            + environmental_weight
            + mobility_weight
            + digital_attention_weight
            + health_weight
        )

        if political_weight > 0:
            total_weight += political_weight
        if crime_weight > 0:
            total_weight += crime_weight
        if misinformation_weight > 0:
            total_weight += misinformation_weight
        if social_cohesion_weight > 0:
            total_weight += social_cohesion_weight

        if abs(total_weight - 1.0) > 0.01:  # Allow small floating point differences
            if total_weight > 0:  # Prevent divide-by-zero
                logger.warning(
                    "Weights do not sum to 1.0, normalizing",
                    total=total_weight,
                    weights=self._original_weights,
                )
                self.economic_weight = economic_weight / total_weight
                self.environmental_weight = environmental_weight / total_weight
                self.mobility_weight = mobility_weight / total_weight
                self.digital_attention_weight = digital_attention_weight / total_weight
                self.health_weight = health_weight / total_weight
                self.political_weight = (
                    political_weight / total_weight if political_weight > 0 else 0.0
                )
                self.crime_weight = (
                    crime_weight / total_weight if crime_weight > 0 else 0.0
                )
                self.misinformation_weight = (
                    misinformation_weight / total_weight
                    if misinformation_weight > 0
                    else 0.0
                )
                self.social_cohesion_weight = (
                    social_cohesion_weight / total_weight
                    if social_cohesion_weight > 0
                    else 0.0
                )
            else:
                logger.error("Total weight is zero or negative, using default weights")
                # Fallback to default weights if total_weight is invalid
                self.economic_weight = 0.25
                self.environmental_weight = 0.25
                self.mobility_weight = 0.20
                self.digital_attention_weight = 0.15
                self.health_weight = 0.15
                self.political_weight = 0.0
                self.crime_weight = 0.0
                self.misinformation_weight = 0.0
                self.social_cohesion_weight = 0.0
        else:
            self.economic_weight = economic_weight
            self.environmental_weight = environmental_weight
            self.mobility_weight = mobility_weight
            self.digital_attention_weight = digital_attention_weight
            self.health_weight = health_weight
            self.political_weight = political_weight
            self.crime_weight = crime_weight
            self.misinformation_weight = misinformation_weight
            self.social_cohesion_weight = social_cohesion_weight

    def compute_sub_indices(
        self,
        harmonized_data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute all sub-indices from harmonized data.

        Args:
            harmonized_data: DataFrame with columns:
                - timestamp (datetime)
                - stress_index (from market data, 0.0-1.0, higher = more stress)
                - discomfort_score (from weather, 0.0-1.0, higher = more discomfort)
                - mobility_index (0.0-1.0, higher = more activity) [optional]
                - search_interest_score (0.0-1.0, higher = more attention) [optional]
                - health_risk_index (0.0-1.0, higher = more health stress) [optional]

        Returns:
            DataFrame with added columns:
                - economic_stress (0.0-1.0, higher = more economic stress)
                - environmental_stress (0.0-1.0, higher = more environmental stress)
                - mobility_activity (0.0-1.0, higher = more activity)
                - digital_attention (0.0-1.0, higher = more attention)
                - public_health_stress (0.0-1.0, higher = more health stress)
        """
        df = harmonized_data.copy()

        # ECONOMIC_STRESS: Combine market stress_index with FRED indicators
        # Market stress_index is already normalized 0.0-1.0 (higher = more stress)
        market_stress = df.get("stress_index", pd.Series([0.5] * len(df))).fillna(0.5)

        # FRED indicators (if available)
        fred_consumer_sentiment = df.get(
            "fred_consumer_sentiment", pd.Series([None] * len(df))
        )
        fred_unemployment = df.get("fred_unemployment", pd.Series([None] * len(df)))
        fred_jobless_claims = df.get("fred_jobless_claims", pd.Series([None] * len(df)))
        # Extended economic metrics (GDP growth, CPI inflation) - gated for v2.5 compatibility
        # These are available in harmonized data but only used if explicitly enabled
        fred_gdp_growth_stress = df.get(
            "fred_gdp_growth_stress", pd.Series([None] * len(df))
        )
        fred_cpi_inflation_stress = df.get(
            "fred_cpi_inflation_stress", pd.Series([None] * len(df))
        )

        # Combine indicators with adaptive weights based on availability
        # Target weights: market (40%), consumer sentiment (30%),
        # unemployment (20%), jobless claims (10%)
        # If FRED data not available, use only market stress (weight = 1.0)
        economic_components = [market_stress]
        weights = []

        # Check which FRED indicators are available
        has_consumer = fred_consumer_sentiment.notna().any()
        has_unemployment = fred_unemployment.notna().any()
        has_jobless = fred_jobless_claims.notna().any()

        # Build component list and target weights
        if has_consumer:
            economic_components.append(fred_consumer_sentiment.fillna(0.5))
        if has_unemployment:
            economic_components.append(fred_unemployment.fillna(0.5))
        if has_jobless:
            economic_components.append(fred_jobless_claims.fillna(0.5))

        # Set weights based on available components
        if len(economic_components) == 1:
            # Only market stress
            weights = [1.0]
        elif len(economic_components) == 2:
            # Market + one FRED indicator
            if has_consumer:
                weights = [0.6, 0.4]  # Market 60%, Consumer 40%
            elif has_unemployment:
                weights = [0.7, 0.3]  # Market 70%, Unemployment 30%
            else:  # jobless claims
                weights = [0.8, 0.2]  # Market 80%, Jobless 20%
        elif len(economic_components) == 3:
            # Market + two FRED indicators
            if has_consumer and has_unemployment:
                weights = [0.4, 0.4, 0.2]  # Market 40%, Consumer 40%, Unemployment 20%
            elif has_consumer and has_jobless:
                weights = [0.5, 0.4, 0.1]  # Market 50%, Consumer 40%, Jobless 10%
            else:  # unemployment + jobless
                weights = [0.6, 0.3, 0.1]  # Market 60%, Unemployment 30%, Jobless 10%
        else:
            # All four indicators available
            weights = [
                0.4,
                0.3,
                0.2,
                0.1,
            ]  # Market 40%, Consumer 30%, Unemployment 20%, Jobless 10%

        # Normalize weights to sum to 1.0
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            # Fallback: equal weights if total_weight is zero
            weights = (
                [1.0 / len(economic_components)] * len(economic_components)
                if len(economic_components) > 0
                else [1.0]
            )

        # Compute weighted average with safety checks
        if len(economic_components) == len(weights) and len(economic_components) > 0:
            df["economic_stress"] = sum(
                comp * weight for comp, weight in zip(economic_components, weights)
            )
        else:
            # Fallback: use first component or default
            df["economic_stress"] = (
                economic_components[0]
                if len(economic_components) > 0
                else pd.Series([0.5] * len(df))
            )

        # Ensure all values are valid numbers and in range
        df["economic_stress"] = pd.to_numeric(
            df["economic_stress"], errors="coerce"
        ).fillna(0.5)
        df["economic_stress"] = df["economic_stress"].clip(0.0, 1.0)

        # Store component metadata for breakdown
        # (store component info in DataFrame for later extraction)
        component_names = ["market_volatility"]
        component_sources = ["yfinance"]
        if has_consumer:
            component_names.append("consumer_sentiment")
            component_sources.append("FRED")
        if has_unemployment:
            component_names.append("unemployment_rate")
            component_sources.append("FRED")
        if has_jobless:
            component_names.append("jobless_claims")
            component_sources.append("FRED")

        # Store metadata as attributes on the DataFrame for later extraction
        df.attrs["_economic_component_names"] = component_names
        df.attrs["_economic_component_weights"] = weights
        df.attrs["_economic_component_sources"] = component_sources

        # ENVIRONMENTAL_STRESS: Combine weather discomfort with earthquake intensity
        # Weather discomfort_score is normalized 0.0-1.0 (higher = more discomfort)
        discomfort_score = df.get(
            "discomfort_score", pd.Series([0.5] * len(df))
        ).fillna(0.5)
        earthquake_intensity = df.get(
            "usgs_earthquake_intensity", pd.Series([None] * len(df))
        )

        # Combine environmental signals
        has_earthquake = earthquake_intensity.notna().any()
        if has_earthquake:
            # Weight: 70% weather, 30% earthquakes
            earthquake_filled = earthquake_intensity.fillna(0.0)
            df["environmental_stress"] = (
                0.7 * discomfort_score + 0.3 * earthquake_filled
            ).clip(0.0, 1.0)
            df.attrs["_environmental_component_names"] = [
                "weather_discomfort",
                "earthquake_intensity",
            ]
            df.attrs["_environmental_component_weights"] = [0.7, 0.3]
            df.attrs["_environmental_component_sources"] = ["Open-Meteo", "USGS"]
        else:
            df["environmental_stress"] = discomfort_score.clip(0.0, 1.0)
            df.attrs["_environmental_component_names"] = ["weather_discomfort"]
            df.attrs["_environmental_component_weights"] = [1.0]
            df.attrs["_environmental_component_sources"] = ["Open-Meteo"]

        # MOBILITY_ACTIVITY: Direct mapping from mobility_index
        # mobility_index is already normalized 0.0-1.0 (higher = more activity)
        mobility_index = df.get("mobility_index", pd.Series([0.5] * len(df))).fillna(
            0.5
        )
        df["mobility_activity"] = mobility_index.clip(0.0, 1.0)

        # Store component metadata
        has_mobility_data = mobility_index.notna().any()
        df.attrs["_mobility_component_names"] = ["mobility_index"]
        df.attrs["_mobility_component_weights"] = [1.0]
        df.attrs["_mobility_component_sources"] = (
            ["mobility_api"] if has_mobility_data else ["default"]
        )

        # DIGITAL_ATTENTION: Combine search interest with GDELT tone
        # search_interest_score is already normalized 0.0-1.0 (higher = more attention)
        search_interest = df.get(
            "search_interest_score", pd.Series([0.5] * len(df))
        ).fillna(0.5)
        gdelt_tone = df.get("gdelt_tone_score", pd.Series([None] * len(df)))

        # Combine digital attention signals
        has_gdelt = gdelt_tone.notna().any()
        has_search_data = search_interest.notna().any()

        if has_gdelt and has_search_data:
            # Weight: 50% search, 50% GDELT tone
            gdelt_filled = gdelt_tone.fillna(0.5)
            df["digital_attention"] = (0.5 * search_interest + 0.5 * gdelt_filled).clip(
                0.0, 1.0
            )
            df.attrs["_digital_component_names"] = ["search_interest", "gdelt_tone"]
            df.attrs["_digital_component_weights"] = [0.5, 0.5]
            df.attrs["_digital_component_sources"] = ["search_trends_api", "GDELT"]
        elif has_gdelt:
            # Only GDELT available
            gdelt_filled = gdelt_tone.fillna(0.5)
            df["digital_attention"] = gdelt_filled.clip(0.0, 1.0)
            df.attrs["_digital_component_names"] = ["gdelt_tone"]
            df.attrs["_digital_component_weights"] = [1.0]
            df.attrs["_digital_component_sources"] = ["GDELT"]
        elif has_search_data:
            # Only search available
            df["digital_attention"] = search_interest.clip(0.0, 1.0)
            df.attrs["_digital_component_names"] = ["search_interest"]
            df.attrs["_digital_component_weights"] = [1.0]
            df.attrs["_digital_component_sources"] = ["search_trends_api"]
        else:
            # Default fallback
            df["digital_attention"] = pd.Series([0.5] * len(df))
            df.attrs["_digital_component_names"] = ["default"]
            df.attrs["_digital_component_weights"] = [1.0]
            df.attrs["_digital_component_sources"] = ["default"]

        # PUBLIC_HEALTH_STRESS: Combine health_risk_index with OWID health stress
        # health_risk_index is already normalized 0.0-1.0 (higher = more health stress)
        health_risk = df.get("health_risk_index", pd.Series([0.5] * len(df))).fillna(
            0.5
        )
        owid_health = df.get("owid_health_stress", pd.Series([None] * len(df)))

        # Combine health signals
        has_owid = owid_health.notna().any()
        has_health_data = health_risk.notna().any()

        if has_owid and has_health_data:
            # Weight: 50% health_risk_index, 50% OWID
            owid_filled = owid_health.fillna(0.5)
            df["public_health_stress"] = (0.5 * health_risk + 0.5 * owid_filled).clip(
                0.0, 1.0
            )
            df.attrs["_health_component_names"] = [
                "health_risk_index",
                "owid_health_stress",
            ]
            df.attrs["_health_component_weights"] = [0.5, 0.5]
            df.attrs["_health_component_sources"] = ["public_health_api", "OWID"]
        elif has_owid:
            # Only OWID available
            owid_filled = owid_health.fillna(0.5)
            df["public_health_stress"] = owid_filled.clip(0.0, 1.0)
            df.attrs["_health_component_names"] = ["owid_health_stress"]
            df.attrs["_health_component_weights"] = [1.0]
            df.attrs["_health_component_sources"] = ["OWID"]
        elif has_health_data:
            # Only health_risk_index available
            df["public_health_stress"] = health_risk.clip(0.0, 1.0)
            df.attrs["_health_component_names"] = ["health_risk_index"]
            df.attrs["_health_component_weights"] = [1.0]
            df.attrs["_health_component_sources"] = ["public_health_api"]
        else:
            # Default fallback
            df["public_health_stress"] = pd.Series([0.5] * len(df))
            df.attrs["_health_component_names"] = ["default"]
            df.attrs["_health_component_weights"] = [1.0]
            df.attrs["_health_component_sources"] = ["default"]

        # POLITICAL_STRESS: Direct mapping from political_stress index
        # political_stress is already normalized 0.0-1.0 (higher = more stress)
        political_stress = df.get("political_stress", pd.Series([None] * len(df)))
        has_political_data = political_stress.notna().any()

        if has_political_data:
            df["political_stress"] = political_stress.fillna(0.5).clip(0.0, 1.0)
            df.attrs["_political_component_names"] = ["political_stress"]
            df.attrs["_political_component_weights"] = [1.0]
            df.attrs["_political_component_sources"] = ["political_ingestion"]
        else:
            # Default fallback (backward compatible - no political stress)
            df["political_stress"] = pd.Series([0.5] * len(df))
            df.attrs["_political_component_names"] = ["default"]
            df.attrs["_political_component_weights"] = [1.0]
            df.attrs["_political_component_sources"] = ["default"]

        # CRIME_STRESS: Direct mapping from crime_stress index
        crime_stress = df.get("crime_stress", pd.Series([None] * len(df)))
        has_crime_data = crime_stress.notna().any()

        if has_crime_data:
            df["crime_stress"] = crime_stress.fillna(0.5).clip(0.0, 1.0)
            df.attrs["_crime_component_names"] = ["crime_stress"]
            df.attrs["_crime_component_weights"] = [1.0]
            df.attrs["_crime_component_sources"] = ["crime_ingestion"]
        else:
            df["crime_stress"] = pd.Series([0.5] * len(df))
            df.attrs["_crime_component_names"] = ["default"]
            df.attrs["_crime_component_weights"] = [1.0]
            df.attrs["_crime_component_sources"] = ["default"]

        # MISINFORMATION_STRESS: Direct mapping from misinformation_stress index
        misinformation_stress = df.get(
            "misinformation_stress", pd.Series([None] * len(df))
        )
        has_misinformation_data = misinformation_stress.notna().any()

        if has_misinformation_data:
            df["misinformation_stress"] = misinformation_stress.fillna(0.5).clip(
                0.0, 1.0
            )
            df.attrs["_misinformation_component_names"] = ["misinformation_stress"]
            df.attrs["_misinformation_component_weights"] = [1.0]
            df.attrs["_misinformation_component_sources"] = ["misinformation_ingestion"]
        else:
            df["misinformation_stress"] = pd.Series([0.5] * len(df))
            df.attrs["_misinformation_component_names"] = ["default"]
            df.attrs["_misinformation_component_weights"] = [1.0]
            df.attrs["_misinformation_component_sources"] = ["default"]

        # SOCIAL_COHESION_STRESS: Direct mapping from social_cohesion_stress index
        social_cohesion_stress = df.get(
            "social_cohesion_stress", pd.Series([None] * len(df))
        )
        has_social_cohesion_data = social_cohesion_stress.notna().any()

        if has_social_cohesion_data:
            df["social_cohesion_stress"] = social_cohesion_stress.fillna(0.5).clip(
                0.0, 1.0
            )
            df.attrs["_social_cohesion_component_names"] = ["social_cohesion_stress"]
            df.attrs["_social_cohesion_component_weights"] = [1.0]
            df.attrs["_social_cohesion_component_sources"] = [
                "social_cohesion_ingestion"
            ]
        else:
            df["social_cohesion_stress"] = pd.Series([0.5] * len(df))
            df.attrs["_social_cohesion_component_names"] = ["default"]
            df.attrs["_social_cohesion_component_weights"] = [1.0]
            df.attrs["_social_cohesion_component_sources"] = ["default"]

        # ====================================================================
        # CHILD INDICES (vNext): Compute derived child indices from raw signals
        # Standardized pipeline: z-score → EWMA → 0-1 normalization
        # ====================================================================

        # Helper function: standardized child index computation
        def compute_child_index(
            raw_signal: pd.Series,
            window_days: int = 90,
            ewma_alpha: float = 0.3,
            clip_bounds: tuple = (0.0, 1.0),
        ) -> pd.Series:
            """
            Compute a child index from raw signal using standardized pipeline:
            1. Z-score vs rolling baseline (window_days)
            2. EWMA smoothing (alpha)
            3. Logistic transformation to 0-1 (with clipping)

            Args:
                raw_signal: Raw signal values
                window_days: Rolling window size for z-score baseline (default: 90)
                ewma_alpha: EWMA smoothing factor (default: 0.3, higher = more responsive)
                clip_bounds: Final clipping bounds (default: (0.0, 1.0))

            Returns:
                Normalized child index (0.0-1.0)
            """
            if len(raw_signal) < 2:
                return pd.Series([0.5] * len(raw_signal), index=raw_signal.index)

            # Step 1: Z-score vs rolling baseline
            rolling_mean = raw_signal.rolling(
                window=min(window_days, len(raw_signal)), min_periods=1
            ).mean()
            rolling_std = raw_signal.rolling(
                window=min(window_days, len(raw_signal)), min_periods=1
            ).std()
            # Avoid division by zero
            rolling_std = rolling_std.replace(0.0, 1.0)
            z_scores = (raw_signal - rolling_mean) / rolling_std

            # Step 2: EWMA smoothing
            z_smoothed = z_scores.ewm(alpha=ewma_alpha, adjust=False).mean()

            # Step 3: Logistic transformation to 0-1 (tanh maps (-inf, inf) → (-1, 1), then shift/scale to (0, 1))
            # Using tanh for bounded output: 0.5 * (tanh(z / 2) + 1) maps z-score → [0, 1]
            # Alternative: clipped min-max normalization of z-scores
            # For robustness, clip extreme z-scores then min-max normalize
            z_clipped = z_smoothed.clip(-3.0, 3.0)  # Clip at ±3 std devs
            normalized = (z_clipped - (-3.0)) / (3.0 - (-3.0))  # Min-max to [0, 1]

            # Ensure valid numeric values and clip
            normalized = pd.to_numeric(normalized, errors="coerce").fillna(0.5)
            return normalized.clip(*clip_bounds)

        # MOBILITY CHILD INDICES
        mobility_index_raw = df.get(
            "mobility_index", pd.Series([0.5] * len(df))
        ).fillna(0.5)
        has_mobility = mobility_index_raw.notna().any() and len(mobility_index_raw) > 1

        if has_mobility:
            # Mobility Suppression: deviation below baseline (negative z-score, persisted)
            mobility_baseline = mobility_index_raw.rolling(
                window=min(90, len(mobility_index_raw)), min_periods=1
            ).mean()
            mobility_suppression_raw = (mobility_baseline - mobility_index_raw).clip(
                0.0, None
            )  # Only negative deviations
            df["mobility_suppression"] = compute_child_index(
                mobility_suppression_raw,
                window_days=90,
                ewma_alpha=0.3,
            )

            # Mobility Shock: change-point detection via z-score of first derivative
            mobility_diff = mobility_index_raw.diff().fillna(0.0)
            df["mobility_shock"] = compute_child_index(
                mobility_diff.abs(),  # Absolute change magnitude
                window_days=30,  # Shorter window for shock detection
                ewma_alpha=0.4,  # More responsive for shocks
            )

            # Mobility Recovery Momentum: slope over last 7-14 days
            if len(mobility_index_raw) >= 14:
                window = 14
                min_periods = min(7, window)
                mobility_slope = (
                    mobility_index_raw.rolling(window=window, min_periods=min_periods)
                    .apply(
                        lambda x: (
                            (x.iloc[-1] - x.iloc[0]) / len(x) if len(x) > 1 else 0.0
                        )
                    )
                    .fillna(0.0)
                )
                # Convert to positive stress (recovery = low stress, suppression = high stress)
                # Higher slope = recovery = lower stress
                df["mobility_recovery_momentum"] = compute_child_index(
                    (1.0 - mobility_slope).clip(
                        0.0, 1.0
                    ),  # Invert: higher slope → lower stress
                    window_days=30,
                    ewma_alpha=0.3,
                )
            else:
                df["mobility_recovery_momentum"] = pd.Series([0.5] * len(df))

        else:
            df["mobility_suppression"] = pd.Series([0.0] * len(df))
            df["mobility_shock"] = pd.Series([0.0] * len(df))
            df["mobility_recovery_momentum"] = pd.Series([0.5] * len(df))

        # Transit Disruption Stress (Batch 4): from mobility_index volatility
        # Transit disruption = high volatility in mobility (cancellations, strikes, irregular service)
        if has_mobility:
            transit_volatility = (
                mobility_index_raw.rolling(
                    window=min(14, len(mobility_index_raw)), min_periods=2
                )
                .std()
                .fillna(0.0)
            )
            transit_disruption_raw = transit_volatility.clip(0.0, 1.0)
            df["transit_disruption_stress"] = compute_child_index(
                transit_disruption_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["transit_disruption_stress"] = pd.Series([0.0] * len(df))

        # Congestion Stress (Batch 4): from mobility_index patterns (abnormal highs/lows)
        # Congestion = periods of abnormally high mobility (above baseline) or low mobility (below baseline)
        # Use deviation from rolling mean as congestion proxy
        if has_mobility:
            mobility_baseline = mobility_index_raw.rolling(
                window=min(90, len(mobility_index_raw)), min_periods=1
            ).mean()
            mobility_deviation = (
                (mobility_index_raw - mobility_baseline).abs().fillna(0.0)
            )
            congestion_raw = mobility_deviation.clip(0.0, 1.0)
            df["congestion_stress"] = compute_child_index(
                congestion_raw,
                window_days=30,
                ewma_alpha=0.3,
            )
        else:
            df["congestion_stress"] = pd.Series([0.0] * len(df))

        # ATTENTION CHILD INDICES
        search_interest_raw = df.get(
            "search_interest_score", pd.Series([0.5] * len(df))
        ).fillna(0.5)
        gdelt_tone_raw = df.get("gdelt_tone_score", pd.Series([0.5] * len(df))).fillna(
            0.5
        )
        # Combined attention signal (average of search + GDELT if both available)
        attention_combined = (search_interest_raw + gdelt_tone_raw) / 2.0
        has_attention = (
            search_interest_raw.notna().any() or gdelt_tone_raw.notna().any()
        ) and len(attention_combined) > 1

        if has_attention:
            # Attention Intensity: normalized volume (z-scored)
            df["attention_intensity"] = compute_child_index(
                attention_combined,
                window_days=90,
                ewma_alpha=0.3,
            )

            # Attention Volatility: variance + rate-of-change (spikes)
            # Use rolling variance as proxy for volatility
            attention_rolling_var = (
                attention_combined.rolling(
                    window=min(14, len(attention_combined)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            attention_diff_abs = attention_combined.diff().abs().fillna(0.0)
            attention_volatility_raw = (
                attention_rolling_var * 0.7 + attention_diff_abs * 0.3
            )  # Weighted combination
            df["attention_volatility"] = compute_child_index(
                attention_volatility_raw,
                window_days=30,  # Shorter window for volatility
                ewma_alpha=0.4,
            )
        else:
            df["attention_intensity"] = pd.Series([0.5] * len(df))
            df["attention_volatility"] = pd.Series([0.0] * len(df))

        # Search Attention Intensity (Batch 4): separate from combined attention_intensity
        # Focuses specifically on search_interest_score (Google Trends-like behavior)
        if search_interest_raw.notna().any() and len(search_interest_raw) > 1:
            df["search_attention_intensity"] = compute_child_index(
                search_interest_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["search_attention_intensity"] = pd.Series([0.5] * len(df))

        # News Cycle Intensity (Batch 7): use attention_intensity as proxy
        if has_attention:
            df["news_cycle_intensity"] = df.get(
                "attention_intensity", pd.Series([0.5] * len(df))
            )
        else:
            df["news_cycle_intensity"] = pd.Series([0.5] * len(df))

        # POLITICAL CHILD INDICES
        # Legislative volatility: variance/spikes in legislative event counts
        legislative_attention_raw = df.get(
            "legislative_attention", pd.Series([0.0] * len(df))
        ).fillna(0.0)
        has_legislative = (
            legislative_attention_raw.notna().any()
            and len(legislative_attention_raw) > 1
        )

        if has_legislative:
            # Legislative volatility: variance + rate-of-change
            legislative_rolling_var = (
                legislative_attention_raw.rolling(
                    window=min(14, len(legislative_attention_raw)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            legislative_diff_abs = legislative_attention_raw.diff().abs().fillna(0.0)
            legislative_volatility_raw = (
                legislative_rolling_var * 0.7 + legislative_diff_abs * 0.3
            )
            df["legislative_volatility"] = compute_child_index(
                legislative_volatility_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["legislative_volatility"] = pd.Series([0.0] * len(df))

        # Enforcement pressure: rate and severity of enforcement events
        enforcement_attention_raw = df.get(
            "enforcement_attention", pd.Series([0.0] * len(df))
        ).fillna(0.0)
        has_enforcement = (
            enforcement_attention_raw.notna().any()
            and len(enforcement_attention_raw) > 1
        )

        if has_enforcement:
            # Enforcement pressure: rate + persistence (rolling sum)
            enforcement_rolling_sum = (
                enforcement_attention_raw.rolling(
                    window=min(7, len(enforcement_attention_raw)), min_periods=1
                )
                .sum()
                .fillna(0.0)
            )
            df["enforcement_pressure"] = compute_child_index(
                enforcement_rolling_sum,
                window_days=30,
                ewma_alpha=0.3,
            )
        else:
            df["enforcement_pressure"] = pd.Series([0.0] * len(df))

        # Civic Disruption / Protest Proxy: from GDELT events (proxy via enforcement + legislative volatility)
        if has_enforcement and has_legislative:
            # Combine enforcement + legislative volatility as civic disruption proxy
            civic_disruption_raw = (
                enforcement_attention_raw * 0.5 + legislative_attention_raw * 0.5
            ).clip(0.0, 1.0)
            df["civic_disruption_proxy"] = compute_child_index(
                civic_disruption_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        elif has_enforcement:
            # Fallback: use enforcement alone as proxy
            df["civic_disruption_proxy"] = df.get(
                "enforcement_pressure", pd.Series([0.0] * len(df))
            )
        elif has_legislative:
            # Fallback: use legislative volatility as proxy
            df["civic_disruption_proxy"] = df.get(
                "legislative_volatility", pd.Series([0.0] * len(df))
            )
        else:
            df["civic_disruption_proxy"] = pd.Series([0.0] * len(df))

        # Protest Intensity (Batch 4): from enforcement_attention + legislative volatility
        # Protests often correlate with increased enforcement activity and legislative volatility
        if has_enforcement and has_legislative:
            # Protest proxy: combine enforcement spikes + legislative volatility
            enforcement_spikes = (
                enforcement_attention_raw.rolling(
                    window=min(7, len(enforcement_attention_raw)), min_periods=1
                )
                .max()
                .fillna(0.0)
            )
            legislative_volatility_proxy = (
                legislative_attention_raw.rolling(
                    window=min(14, len(legislative_attention_raw)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            protest_raw = (
                enforcement_spikes * 0.6 + legislative_volatility_proxy * 0.4
            ).clip(0.0, 1.0)
            df["protest_intensity"] = compute_child_index(
                protest_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        elif has_enforcement:
            # Fallback: use enforcement spikes alone
            enforcement_spikes = (
                enforcement_attention_raw.rolling(
                    window=min(7, len(enforcement_attention_raw)), min_periods=1
                )
                .max()
                .fillna(0.0)
            )
            df["protest_intensity"] = compute_child_index(
                enforcement_spikes,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["protest_intensity"] = pd.Series([0.0] * len(df))

        # Conflict Activity Stress (Batch 7): from enforcement_attention + civic_disruption
        if has_enforcement:
            civic_for_conflict = df.get(
                "civic_disruption_proxy", pd.Series([0.0] * len(df))
            )
            conflict_raw = (
                enforcement_attention_raw * 0.6 + civic_for_conflict * 0.4
            ).clip(0.0, 1.0)
            df["conflict_activity_stress"] = compute_child_index(
                conflict_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["conflict_activity_stress"] = pd.Series([0.0] * len(df))

        # MISINFORMATION CHILD INDICES
        # Narrative fragmentation: entropy of topics/entities (proxy: variance of tone scores)
        gdelt_tone_for_narrative = df.get(
            "gdelt_tone_score", pd.Series([0.5] * len(df))
        ).fillna(0.5)
        has_narrative = (
            gdelt_tone_for_narrative.notna().any() and len(gdelt_tone_for_narrative) > 1
        )

        if has_narrative:
            # Narrative fragmentation: variance/entropy proxy (high variance = more fragmentation)
            narrative_rolling_var = (
                gdelt_tone_for_narrative.rolling(
                    window=min(14, len(gdelt_tone_for_narrative)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            # Also use absolute deviation from median as fragmentation proxy
            narrative_median = gdelt_tone_for_narrative.rolling(
                window=min(30, len(gdelt_tone_for_narrative)), min_periods=1
            ).median()
            narrative_deviation = (
                (gdelt_tone_for_narrative - narrative_median).abs().fillna(0.0)
            )
            narrative_fragmentation_raw = (
                narrative_rolling_var * 0.6 + narrative_deviation * 0.4
            )
            df["narrative_fragmentation"] = compute_child_index(
                narrative_fragmentation_raw,
                window_days=30,
                ewma_alpha=0.3,
            )
        else:
            df["narrative_fragmentation"] = pd.Series([0.0] * len(df))

        # ECONOMIC CHILD INDICES (from FRED)
        fred_unemployment_raw = df.get("fred_unemployment", pd.Series([None] * len(df)))
        fred_jobless_claims_raw = df.get(
            "fred_jobless_claims", pd.Series([None] * len(df))
        )
        has_labor_data = (
            fred_unemployment_raw.notna().any() or fred_jobless_claims_raw.notna().any()
        ) and len(df) > 1

        if has_labor_data:
            # Labor Stress: combined unemployment + claims z-scores
            unemployment_norm = fred_unemployment_raw.fillna(
                fred_unemployment_raw.mean()
                if fred_unemployment_raw.notna().any()
                else 0.5
            )
            claims_norm = fred_jobless_claims_raw.fillna(
                fred_jobless_claims_raw.mean()
                if fred_jobless_claims_raw.notna().any()
                else 0.0
            )
            # Normalize claims to same scale (0-1) as unemployment
            if claims_norm.max() > 0:
                claims_norm = claims_norm / claims_norm.max()
            labor_stress_raw = (unemployment_norm * 0.6 + claims_norm * 0.4).fillna(0.5)
            df["labor_stress"] = compute_child_index(
                labor_stress_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["labor_stress"] = pd.Series([0.5] * len(df))

        # Inflation / Cost Pressure: from FRED CPI
        fred_cpi_raw = df.get("fred_cpi_inflation_stress", pd.Series([None] * len(df)))
        has_inflation_data = fred_cpi_raw.notna().any() and len(df) > 1

        if has_inflation_data:
            # Inflation Cost Pressure: YoY change + slope
            cpi_filled = fred_cpi_raw.fillna(
                fred_cpi_raw.mean() if fred_cpi_raw.notna().any() else 0.5
            )
            # Add slope component (momentum)
            window = min(30, len(cpi_filled))
            min_periods = min(7, window)
            cpi_slope = (
                cpi_filled.rolling(window=window, min_periods=min_periods)
                .apply(
                    lambda x: (x.iloc[-1] - x.iloc[0]) / len(x) if len(x) > 1 else 0.0
                )
                .fillna(0.0)
            )
            inflation_stress_raw = (
                cpi_filled * 0.7 + cpi_slope.clip(-1.0, 1.0) * 0.3
            ).clip(0.0, 1.0)
            df["inflation_cost_pressure"] = compute_child_index(
                inflation_stress_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["inflation_cost_pressure"] = pd.Series([0.5] * len(df))

        # Food Price Stress (Batch 5): from inflation_cost_pressure (food CPI proxy)
        # Food prices typically correlate with overall inflation but can spike independently
        if has_inflation_data:
            # Food price stress: use CPI inflation as proxy, with additional volatility weight
            # Food prices often show higher volatility than overall CPI
            cpi_volatility = (
                cpi_filled.rolling(window=min(14, len(cpi_filled)), min_periods=2)
                .std()
                .fillna(0.0)
            )
            food_price_raw = (
                cpi_filled * 0.7 + (cpi_volatility * 2.0).clip(0.0, 1.0) * 0.3
            ).clip(0.0, 1.0)
            df["food_price_stress"] = compute_child_index(
                food_price_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["food_price_stress"] = pd.Series([0.5] * len(df))

        # Energy Price Stress (Batch 6): from inflation volatility (energy price proxy)
        # Energy prices show high volatility and correlate with overall inflation
        if has_inflation_data:
            # Energy price proxy: use inflation volatility as primary signal
            # Energy prices are typically more volatile than food/overall CPI
            cpi_high_freq_vol = (
                cpi_filled.rolling(window=min(7, len(cpi_filled)), min_periods=2)
                .std()
                .fillna(0.0)
            )
            energy_price_raw = (
                (cpi_volatility * 3.0).clip(0.0, 1.0) * 0.7 + cpi_high_freq_vol * 0.3
            ).clip(0.0, 1.0)
            df["energy_price_stress"] = compute_child_index(
                energy_price_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["energy_price_stress"] = pd.Series([0.5] * len(df))

        # Financial Volatility Stress: from stress_index (market volatility)
        stress_index_raw = df.get("stress_index", pd.Series([0.5] * len(df))).fillna(
            0.5
        )
        has_stress_data = stress_index_raw.notna().any() and len(df) > 1

        if has_stress_data:
            # Financial Volatility: stress_index + rate-of-change
            stress_volatility = (
                stress_index_raw.rolling(
                    window=min(14, len(stress_index_raw)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            stress_change = stress_index_raw.diff().abs().fillna(0.0)
            volatility_stress_raw = (
                stress_index_raw * 0.6 + stress_volatility * 0.2 + stress_change * 0.2
            ).clip(0.0, 1.0)
            df["financial_volatility_stress"] = compute_child_index(
                volatility_stress_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["financial_volatility_stress"] = pd.Series([0.5] * len(df))

        # Household Debt Stress (Batch 7): from stress_index + financial_volatility_stress
        # Debt stress correlates with financial volatility and overall economic stress
        if has_stress_data:
            financial_vol_proxy = df.get(
                "financial_volatility_stress", pd.Series([0.5] * len(df))
            )
            household_debt_raw = (
                stress_index_raw * 0.5 + financial_vol_proxy * 0.5
            ).clip(0.0, 1.0)
            df["household_debt_stress"] = compute_child_index(
                household_debt_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["household_debt_stress"] = pd.Series([0.5] * len(df))

        # GDP Growth Stress (Batch 3): derived from stress_index as GDP stress proxy
        # GDP stress = negative deviations of GDP growth from trend
        # Use stress_index (market/economic stress) as proxy for GDP growth stress
        if has_stress_data:
            # GDP growth stress: inverse of economic stability (high stress_index = low GDP growth potential)
            # Use rate-of-change in stress_index as GDP growth stress proxy
            window = min(30, len(stress_index_raw))
            min_periods = min(7, window)
            stress_slope = (
                stress_index_raw.rolling(window=window, min_periods=min_periods)
                .apply(
                    lambda x: (x.iloc[-1] - x.iloc[0]) / len(x) if len(x) > 1 else 0.0
                )
                .fillna(0.0)
            )
            # Combine absolute stress level with upward trend (increasing stress = worsening GDP outlook)
            gdp_stress_raw = (
                stress_index_raw * 0.7 + stress_slope.clip(0.0, 1.0) * 0.3
            ).clip(0.0, 1.0)
            df["gdp_growth_stress"] = compute_child_index(
                gdp_stress_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["gdp_growth_stress"] = pd.Series([0.5] * len(df))

        # Unemployment Stress (Batch 3): direct FRED unemployment rate (separate from labor_stress composite)
        # unemployment_stress = elevated unemployment relative to rolling baseline
        if has_labor_data:
            # Unemployment stress: direct unemployment rate normalized to 0-1 stress scale
            unemployment_stress_raw = fred_unemployment_raw.fillna(
                fred_unemployment_raw.mean()
                if fred_unemployment_raw.notna().any()
                else 0.5
            )
            # Normalize unemployment to 0-1 (assuming max reasonable unemployment ~15%)
            unemployment_normalized = (unemployment_stress_raw / 15.0).clip(0.0, 1.0)
            df["unemployment_stress"] = compute_child_index(
                unemployment_normalized,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["unemployment_stress"] = pd.Series([0.5] * len(df))

        # ENVIRONMENTAL CHILD INDICES
        discomfort_score_raw = df.get(
            "discomfort_score", pd.Series([0.5] * len(df))
        ).fillna(0.5)
        has_weather = discomfort_score_raw.notna().any() and len(df) > 1

        if has_weather:
            # Weather Severity Stress: alert count + anomaly score (already in discomfort_score to some extent)
            # Use rolling variance of discomfort as severity proxy
            weather_severity_raw = (
                discomfort_score_raw.rolling(
                    window=min(14, len(discomfort_score_raw)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            # Combine with baseline discomfort
            weather_severity_combined = (
                discomfort_score_raw * 0.7 + weather_severity_raw * 0.3
            ).clip(0.0, 1.0)
            df["weather_severity_stress"] = compute_child_index(
                weather_severity_combined,
                window_days=90,
                ewma_alpha=0.3,
            )

            # Environmental Volatility: entropy/variance of environmental signals
            env_volatility_raw = (
                discomfort_score_raw.rolling(
                    window=min(30, len(discomfort_score_raw)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            df["environmental_volatility"] = compute_child_index(
                env_volatility_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["weather_severity_stress"] = pd.Series([0.5] * len(df))
            df["environmental_volatility"] = pd.Series([0.5] * len(df))

        # Disaster Activation Stress: from emergency management (proxy via weather alerts persistence)
        # Use sustained discomfort as proxy for disaster activation
        if has_weather:
            # Disaster activation: sustained high discomfort (rolling max over 7 days)
            disaster_activation_raw = (
                discomfort_score_raw.rolling(
                    window=min(7, len(discomfort_score_raw)), min_periods=1
                )
                .max()
                .fillna(0.5)
            )
            df["disaster_activation_stress"] = compute_child_index(
                disaster_activation_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["disaster_activation_stress"] = pd.Series([0.5] * len(df))

        # Drought Stress (Batch 2): from sustained weather patterns (low precipitation/high temp proxy)
        # Drought = sustained low comfort (high temp, low humidity) + lack of rainfall events
        # Use rolling low comfort periods as drought proxy
        if has_weather:
            # Drought proxy: sustained periods of high discomfort (heat + dryness)
            # Low precipitation manifests as sustained high discomfort without relief
            # Note: drought_rolling_min calculation removed as it was unused
            # Drought stress: inverse of comfort (high discomfort = drought stress)
            # Combine with persistence: how many days above a high threshold
            drought_threshold = (
                discomfort_score_raw.rolling(
                    window=min(90, len(discomfort_score_raw)), min_periods=1
                )
                .quantile(0.75)
                .fillna(0.5)
            )
            drought_days = (
                (discomfort_score_raw > drought_threshold)
                .rolling(window=min(14, len(discomfort_score_raw)), min_periods=1)
                .sum()
                .fillna(0.0)
            )
            drought_raw = (drought_days / 14.0).clip(
                0.0, 1.0
            )  # Normalize by window size
            df["drought_stress"] = compute_child_index(
                drought_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["drought_stress"] = pd.Series([0.0] * len(df))

        # Flood Risk Stress (Batch 2): from sustained high precipitation/humidity patterns
        # Flood = sustained high comfort disruption from excess moisture/precipitation
        # Use patterns opposite to drought: sustained periods with disruption from wetness
        if has_weather:
            # Flood proxy: periods with high discomfort that could indicate heavy rain/flooding
            # Use rolling max to identify sustained periods (different from drought's rolling min)
            flood_threshold = (
                discomfort_score_raw.rolling(
                    window=min(90, len(discomfort_score_raw)), min_periods=1
                )
                .quantile(0.75)
                .fillna(0.5)
            )
            # Flood risk: sustained periods above threshold with volatility (floods often come with weather volatility)
            flood_volatility = (
                discomfort_score_raw.rolling(
                    window=min(7, len(discomfort_score_raw)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            flood_days = (
                (discomfort_score_raw > flood_threshold)
                .rolling(window=min(7, len(discomfort_score_raw)), min_periods=1)
                .sum()
                .fillna(0.0)
            )
            # Combine persistence with volatility for flood proxy
            flood_raw = (
                (flood_days / 7.0) * 0.6 + (flood_volatility * 2.0).clip(0.0, 1.0) * 0.4
            ).clip(0.0, 1.0)
            df["flood_risk_stress"] = compute_child_index(
                flood_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["flood_risk_stress"] = pd.Series([0.0] * len(df))

        # Coldwave Stress (Batch 2): from discomfort_score extremes (cold patterns)
        # Coldwave = sustained periods of low comfort due to extreme cold
        # Similar to heatwave but focuses on cold extremes rather than heat
        if has_weather:
            # Coldwave: identify sustained periods of high discomfort that could indicate cold extremes
            # Use similar threshold approach as heatwave but track different patterns
            coldwave_threshold = (
                discomfort_score_raw.rolling(
                    window=min(90, len(discomfort_score_raw)), min_periods=1
                )
                .quantile(0.75)
                .fillna(0.5)
            )
            coldwave_days = (
                (discomfort_score_raw > coldwave_threshold)
                .rolling(window=min(7, len(discomfort_score_raw)), min_periods=1)
                .sum()
                .fillna(0.0)
            )
            coldwave_raw = (coldwave_days / 7.0).clip(
                0.0, 1.0
            )  # Normalize by window size
            df["coldwave_stress"] = compute_child_index(
                coldwave_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["coldwave_stress"] = pd.Series([0.0] * len(df))

        # Air Quality Stress (Batch 3): stub for OpenAQ connector
        # For now, use environmental volatility as proxy (poor air quality often correlates with weather volatility)
        # In future: connect to OpenAQ API for PM2.5, ozone, NO2 measurements
        if has_weather:
            # Air quality proxy: use environmental volatility as temporary proxy
            # High volatility in environmental signals can correlate with air quality events
            df["air_quality_stress"] = df.get(
                "environmental_volatility", pd.Series([0.5] * len(df))
            )
        else:
            df["air_quality_stress"] = pd.Series([0.0] * len(df))

        # PUBLIC HEALTH CHILD INDICES
        health_risk_raw = df.get(
            "health_risk_index", pd.Series([0.5] * len(df))
        ).fillna(0.5)
        has_health = health_risk_raw.notna().any() and len(df) > 1

        if has_health:
            # Health Incident Pressure: incidence level z-score + 7-day slope
            health_slope = (
                health_risk_raw.rolling(
                    window=min(7, len(health_risk_raw)), min_periods=2
                )
                .apply(
                    lambda x: (x.iloc[-1] - x.iloc[0]) / len(x) if len(x) > 1 else 0.0
                )
                .fillna(0.0)
            )
            health_pressure_raw = (
                health_risk_raw * 0.7 + health_slope.clip(-1.0, 1.0) * 0.3
            ).clip(0.0, 1.0)
            df["health_incident_pressure"] = compute_child_index(
                health_pressure_raw,
                window_days=90,
                ewma_alpha=0.3,
            )

            # Health System Strain: volatility of health signals (proxy for strain)
            health_strain_raw = (
                health_risk_raw.rolling(
                    window=min(14, len(health_risk_raw)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            df["health_system_strain"] = compute_child_index(
                health_strain_raw,
                window_days=90,
                ewma_alpha=0.3,
            )

            # Hospital Capacity Strain (Batch 5): from health_risk_index volatility (strain proxy)
            # High volatility + sustained elevation in health signals = capacity strain
            health_strain_volatility = (
                health_risk_raw.rolling(
                    window=min(14, len(health_risk_raw)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            health_sustained = (
                health_risk_raw.rolling(
                    window=min(7, len(health_risk_raw)), min_periods=1
                )
                .mean()
                .fillna(0.5)
            )
            capacity_strain_raw = (
                health_strain_volatility * 0.5 + health_sustained * 0.5
            ).clip(0.0, 1.0)
            df["hospital_capacity_strain"] = compute_child_index(
                capacity_strain_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["health_incident_pressure"] = pd.Series([0.5] * len(df))
            df["health_system_strain"] = pd.Series([0.5] * len(df))
            df["hospital_capacity_strain"] = pd.Series([0.5] * len(df))

        # Mortality Spike Risk (Batch 6): from health_risk_index spikes (mortality risk proxy)
        if has_health:
            health_spikes = (
                health_risk_raw.rolling(
                    window=min(7, len(health_risk_raw)), min_periods=1
                )
                .max()
                .fillna(0.5)
            )
            health_acceleration = health_risk_raw.diff().diff().abs().fillna(0.0)
            mortality_risk_raw = (
                health_spikes * 0.7 + (health_acceleration * 2.0).clip(0.0, 1.0) * 0.3
            ).clip(0.0, 1.0)
            df["mortality_spike_risk"] = compute_child_index(
                mortality_risk_raw, window_days=90, ewma_alpha=0.3
            )
        else:
            df["mortality_spike_risk"] = pd.Series([0.5] * len(df))

        # Infectious Incident Pressure (Batch 7): from health_incident_pressure (infectious disease proxy)
        # Use health incident pressure as proxy for infectious disease activity
        if has_health:
            health_incident_proxy = df.get(
                "health_incident_pressure", pd.Series([0.5] * len(df))
            )
            # Add rate-of-change component for infectious spread dynamics
            health_roc = health_risk_raw.diff().fillna(0.0).clip(-1.0, 1.0)
            infectious_raw = (
                health_incident_proxy * 0.7 + (health_roc + 1.0) / 2.0 * 0.3
            ).clip(0.0, 1.0)
            df["infectious_incident_pressure"] = compute_child_index(
                infectious_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["infectious_incident_pressure"] = pd.Series([0.5] * len(df))

        # Mental Health Proxy: from search trends + GDELT tone on stress topics
        if has_attention:
            # Use attention volatility as proxy for mental health stress
            # High volatility in attention = anxiety/stress proxy
            df["mental_health_proxy"] = df.get(
                "attention_volatility", pd.Series([0.5] * len(df))
            )
        else:
            df["mental_health_proxy"] = pd.Series([0.5] * len(df))

        # CRIME CHILD INDICES (proxy via GDELT)
        # Public Safety Velocity: from GDELT enforcement events (proxy)
        if has_enforcement:
            # Use enforcement_pressure rate-of-change as velocity
            enforcement_velocity_raw = (
                enforcement_attention_raw.diff().fillna(0.0).abs()
            )
            df["public_safety_velocity"] = compute_child_index(
                enforcement_velocity_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["public_safety_velocity"] = pd.Series([0.0] * len(df))

        # Crime Narrative Intensity: from GDELT tone (proxy via negative tone)
        if has_narrative:
            # Use negative tone as crime narrative proxy
            crime_narrative_raw = (1.0 - gdelt_tone_for_narrative).clip(
                0.0, 1.0
            )  # Invert: negative tone = high stress
            df["crime_narrative_intensity"] = compute_child_index(
                crime_narrative_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["crime_narrative_intensity"] = pd.Series([0.5] * len(df))

        # Violent Crime Stress (Batch 5): from GDELT enforcement_attention (violent crime proxy)
        # Enforcement events often correlate with violent crime incidents
        if has_enforcement:
            # Violent crime proxy: high enforcement attention + spikes = violent incidents
            enforcement_spikes = (
                enforcement_attention_raw.rolling(
                    window=min(7, len(enforcement_attention_raw)), min_periods=1
                )
                .max()
                .fillna(0.0)
            )
            violent_crime_raw = enforcement_spikes.clip(0.0, 1.0)
            df["violent_crime_stress"] = compute_child_index(
                violent_crime_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["violent_crime_stress"] = pd.Series([0.0] * len(df))

        # Property Crime Stress (Batch 6): from enforcement_attention patterns (property crime proxy)
        # Property crime often shows different patterns than violent crime (more sustained, less spiky)
        if has_enforcement:
            # Property crime proxy: sustained enforcement attention (rolling mean, not spikes)
            enforcement_sustained = (
                enforcement_attention_raw.rolling(
                    window=min(14, len(enforcement_attention_raw)), min_periods=1
                )
                .mean()
                .fillna(0.0)
            )
            property_crime_raw = enforcement_sustained.clip(0.0, 1.0)
            df["property_crime_stress"] = compute_child_index(
                property_crime_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["property_crime_stress"] = pd.Series([0.0] * len(df))

        # MISINFORMATION CHILD INDICES
        # Sentiment Whiplash: volatility of tone over time (rapid swings)
        if has_narrative:
            tone_volatility = (
                gdelt_tone_for_narrative.rolling(
                    window=min(14, len(gdelt_tone_for_narrative)), min_periods=2
                )
                .std()
                .fillna(0.0)
            )
            tone_change_abs = gdelt_tone_for_narrative.diff().abs().fillna(0.0)
            sentiment_whiplash_raw = tone_volatility * 0.6 + tone_change_abs * 0.4
            df["sentiment_whiplash"] = compute_child_index(
                sentiment_whiplash_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["sentiment_whiplash"] = pd.Series([0.0] * len(df))

        # Misinformation Intensity (Batch 5): from GDELT narrative fragmentation + sentiment volatility
        # High fragmentation + high sentiment volatility = intense misinformation activity
        if has_narrative:
            # Combine narrative fragmentation with sentiment volatility
            narrative_frag_proxy = df.get(
                "narrative_fragmentation", pd.Series([0.0] * len(df))
            )
            sentiment_whiplash_proxy = df.get(
                "sentiment_whiplash", pd.Series([0.0] * len(df))
            )
            misinfo_raw = (
                narrative_frag_proxy * 0.6 + sentiment_whiplash_proxy * 0.4
            ).clip(0.0, 1.0)
            df["misinformation_intensity"] = compute_child_index(
                misinfo_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["misinformation_intensity"] = pd.Series([0.0] * len(df))

        # SOCIAL COHESION CHILD INDICES
        # Trust/Conflict Proxy: from GDELT conflict/community keywords + enforcement
        if has_enforcement and has_narrative:
            # Combine enforcement pressure + negative tone as conflict proxy
            conflict_proxy_raw = (
                enforcement_attention_raw * 0.6 + (1.0 - gdelt_tone_for_narrative) * 0.4
            ).clip(0.0, 1.0)
            df["trust_conflict_proxy"] = compute_child_index(
                conflict_proxy_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["trust_conflict_proxy"] = pd.Series([0.5] * len(df))

        # Community Anxiety Proxy: from attention volatility + search trends
        if has_attention:
            # Use attention volatility as community anxiety proxy
            df["community_anxiety_proxy"] = df.get(
                "attention_volatility", pd.Series([0.5] * len(df))
            )
        else:
            df["community_anxiety_proxy"] = pd.Series([0.5] * len(df))

        # Institutional Trust Erosion (Batch 6): from civic_disruption + narrative_fragmentation
        civic_disruption_for_trust = df.get(
            "civic_disruption_proxy", pd.Series([0.0] * len(df))
        )
        narrative_frag_for_trust = df.get(
            "narrative_fragmentation", pd.Series([0.0] * len(df))
        )
        has_trust_signals = (
            civic_disruption_for_trust.notna().any()
            or narrative_frag_for_trust.notna().any()
        ) and len(df) > 1

        if has_trust_signals:
            trust_erosion_raw = (
                civic_disruption_for_trust * 0.6 + narrative_frag_for_trust * 0.4
            ).clip(0.0, 1.0)
            df["institutional_trust_erosion"] = compute_child_index(
                trust_erosion_raw, window_days=90, ewma_alpha=0.3
            )
        else:
            df["institutional_trust_erosion"] = pd.Series([0.5] * len(df))

        # ====================================================================
        # BATCH 1: NEW CHILD INDICES FROM EXISTING DATA SOURCES
        # ====================================================================

        # Economic: Household Financial Stress (from FRED debt/credit proxies)
        # Approximate using stress_index (financial volatility) + unemployment pressure
        if has_stress_data and has_labor_data:
            # Combine financial volatility + labor stress as household financial stress proxy
            household_financial_raw = (
                stress_index_raw * 0.5
                + df.get("labor_stress", pd.Series([0.5] * len(df))) * 0.5
            ).clip(0.0, 1.0)
            df["household_financial_stress"] = compute_child_index(
                household_financial_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        elif has_stress_data:
            df["household_financial_stress"] = df.get(
                "financial_volatility_stress", pd.Series([0.5] * len(df))
            )
        else:
            df["household_financial_stress"] = pd.Series([0.5] * len(df))

        # Environmental: Heatwave Stress (from discomfort_score extremes)
        if has_weather:
            # Heatwave: consecutive days above elevated discomfort threshold
            # Use rolling max over 7 days to identify sustained high discomfort (heatwave proxy)
            discomfort_threshold = (
                discomfort_score_raw.rolling(
                    window=min(90, len(discomfort_score_raw)), min_periods=1
                )
                .quantile(0.75)
                .fillna(0.5)
            )
            heatwave_days = (
                (discomfort_score_raw > discomfort_threshold)
                .rolling(window=min(7, len(discomfort_score_raw)), min_periods=1)
                .sum()
                .fillna(0.0)
            )
            heatwave_stress_raw = (heatwave_days / 7.0).clip(
                0.0, 1.0
            )  # Normalize by window size
            df["heatwave_stress"] = compute_child_index(
                heatwave_stress_raw,
                window_days=90,
                ewma_alpha=0.3,
            )
        else:
            df["heatwave_stress"] = pd.Series([0.0] * len(df))

        # Digital: News Polarization Stress (from GDELT tone variance/divergence)
        if has_narrative:
            # News polarization: high variance in tone = divergent narratives
            # Already computed narrative_fragmentation uses variance, but this is more specific
            # Use tone variance + divergence from neutral (0.5) as polarization proxy
            tone_variance = (
                gdelt_tone_for_narrative.rolling(
                    window=min(14, len(gdelt_tone_for_narrative)), min_periods=2
                )
                .var()
                .fillna(0.0)
            )
            tone_deviation = (
                (gdelt_tone_for_narrative - 0.5).abs().fillna(0.0)
            )  # Deviation from neutral
            polarization_raw = tone_variance * 0.7 + tone_deviation * 0.3
            df["news_polarization_stress"] = compute_child_index(
                polarization_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["news_polarization_stress"] = pd.Series([0.0] * len(df))

        # Tech/Cyber: Cyber Incident Velocity (extend existing cyber_risk)
        cyber_risk_raw = df.get("cyber_risk_index", pd.Series([0.0] * len(df))).fillna(
            0.0
        )
        has_cyber = cyber_risk_raw.notna().any() and len(df) > 1

        if has_cyber:
            # Cyber incident velocity: rate-of-change in cyber risk (velocity)
            cyber_velocity_raw = cyber_risk_raw.diff().fillna(0.0).abs()
            df["cyber_incident_velocity"] = compute_child_index(
                cyber_velocity_raw,
                window_days=30,
                ewma_alpha=0.4,
            )
        else:
            df["cyber_incident_velocity"] = pd.Series([0.0] * len(df))

        # Tech/Cyber: Critical Vulnerability Pressure (CISA KEV - already have connector)
        # This can be derived from existing cyber risk if it incorporates KEV data
        if has_cyber:
            # Use cyber_risk_index as proxy for critical vulnerability pressure
            df["critical_vulnerability_pressure"] = df.get(
                "cyber_risk_index", pd.Series([0.0] * len(df))
            ).clip(0.0, 1.0)
        else:
            df["critical_vulnerability_pressure"] = pd.Series([0.0] * len(df))

        logger.info(
            "Sub-indices computed",
            economic_stress_range=(
                df["economic_stress"].min(),
                df["economic_stress"].max(),
            ),
            environmental_stress_range=(
                df["environmental_stress"].min(),
                df["environmental_stress"].max(),
            ),
            mobility_activity_range=(
                df["mobility_activity"].min(),
                df["mobility_activity"].max(),
            ),
            digital_attention_range=(
                df["digital_attention"].min(),
                df["digital_attention"].max(),
            ),
            public_health_stress_range=(
                df["public_health_stress"].min(),
                df["public_health_stress"].max(),
            ),
            political_stress_range=(
                (
                    df["political_stress"].min(),
                    df["political_stress"].max(),
                )
                if has_political_data
                else None
            ),
            crime_stress_range=(
                (
                    df["crime_stress"].min(),
                    df["crime_stress"].max(),
                )
                if has_crime_data
                else None
            ),
            misinformation_stress_range=(
                (
                    df["misinformation_stress"].min(),
                    df["misinformation_stress"].max(),
                )
                if has_misinformation_data
                else None
            ),
            social_cohesion_stress_range=(
                (
                    df["social_cohesion_stress"].min(),
                    df["social_cohesion_stress"].max(),
                )
                if has_social_cohesion_data
                else None
            ),
        )

        return df

    def compute_behavior_index(
        self,
        harmonized_data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute the overall Behavior Index from harmonized data with sub-indices.

        The Behavior Index represents the overall level of behavioral disruption:
        - Higher values (closer to 1.0): More disruption/stress
        - Lower values (closer to 0.0): Less disruption, more normal patterns

        The index is a weighted combination of stress and activity sub-indices:
        - Stress sub-indices (economic, environmental, health) contribute positively
        - Activity sub-indices (mobility) contribute negatively (inverse)
        - Digital attention can indicate disruption
            (higher attention = potential disruption)

        Args:
            harmonized_data: DataFrame with columns:
                - timestamp (datetime)
                - stress_index, discomfort_score, and optional
                    mobility/search/health indices

        Returns:
            DataFrame with added columns:
                - All sub-indices (economic_stress, environmental_stress, etc.)
                - behavior_index (0.0-1.0, overall behavioral disruption measure)
        """
        # Compute sub-indices first
        df = self.compute_sub_indices(harmonized_data)

        # Compute overall Behavior Index
        # Higher stress indices and lower activity indices = higher behavior index
        # Formula: weighted combination where stress increases index,
        # activity decreases it
        behavior_index = (
            (df["economic_stress"] * self.economic_weight)
            + (df["environmental_stress"] * self.environmental_weight)
            + (
                (1.0 - df["mobility_activity"]) * self.mobility_weight
            )  # Inverse: lower activity = higher disruption
            + (
                df["digital_attention"] * self.digital_attention_weight
            )  # Higher attention can indicate disruption
            + (df["public_health_stress"] * self.health_weight)
        )

        # Add new stress indices if weights > 0 (backward compatible)
        if self.political_weight > 0:
            behavior_index = behavior_index + (
                df["political_stress"] * self.political_weight
            )
        if self.crime_weight > 0:
            behavior_index = behavior_index + (df["crime_stress"] * self.crime_weight)
        if self.misinformation_weight > 0:
            behavior_index = behavior_index + (
                df["misinformation_stress"] * self.misinformation_weight
            )
        if self.social_cohesion_weight > 0:
            behavior_index = behavior_index + (
                df["social_cohesion_stress"] * self.social_cohesion_weight
            )

        # Clip to valid range
        df["behavior_index"] = behavior_index.clip(0.0, 1.0)

        logger.info(
            "Behavior index computed",
            behavior_index_range=(
                df["behavior_index"].min(),
                df["behavior_index"].max(),
            ),
            mean=df["behavior_index"].mean(),
            std=df["behavior_index"].std(),
        )

        return df

    def get_sub_indices_dict(self, row: pd.Series) -> Dict[str, float]:
        """
        Extract sub-indices as a dictionary from a single row.

        Args:
            row: Pandas Series with sub-index columns

        Returns:
            Dictionary mapping dimension names to sub-index values
        """
        # STRICT: Always return all 9 parent indices (UI requires all 9 cards)
        result = {
            "economic_stress": float(row.get("economic_stress", 0.5)),
            "environmental_stress": float(row.get("environmental_stress", 0.5)),
            "mobility_activity": float(row.get("mobility_activity", 0.5)),
            "digital_attention": float(row.get("digital_attention", 0.5)),
            "public_health_stress": float(row.get("public_health_stress", 0.5)),
            # Always include all 9 parent indices (even if weights are 0)
            "political_stress": float(row.get("political_stress", 0.5)),
            "crime_stress": float(row.get("crime_stress", 0.5)),
            "misinformation_stress": float(row.get("misinformation_stress", 0.5)),
            "social_cohesion_stress": float(row.get("social_cohesion_stress", 0.5)),
        }

        # Add child indices (vNext) - always include if computed
        if "mobility_suppression" in row:
            result["mobility_suppression"] = float(row.get("mobility_suppression", 0.0))
        if "mobility_shock" in row:
            result["mobility_shock"] = float(row.get("mobility_shock", 0.0))
        if "attention_volatility" in row:
            result["attention_volatility"] = float(row.get("attention_volatility", 0.0))
        if "legislative_volatility" in row:
            result["legislative_volatility"] = float(
                row.get("legislative_volatility", 0.0)
            )
        if "enforcement_pressure" in row:
            result["enforcement_pressure"] = float(row.get("enforcement_pressure", 0.0))
        if "narrative_fragmentation" in row:
            result["narrative_fragmentation"] = float(
                row.get("narrative_fragmentation", 0.0)
            )
        if "mobility_recovery_momentum" in row:
            result["mobility_recovery_momentum"] = float(
                row.get("mobility_recovery_momentum", 0.5)
            )
        if "attention_intensity" in row:
            result["attention_intensity"] = float(row.get("attention_intensity", 0.5))
        if "labor_stress" in row:
            result["labor_stress"] = float(row.get("labor_stress", 0.5))
        if "inflation_cost_pressure" in row:
            result["inflation_cost_pressure"] = float(
                row.get("inflation_cost_pressure", 0.5)
            )
        if "financial_volatility_stress" in row:
            result["financial_volatility_stress"] = float(
                row.get("financial_volatility_stress", 0.5)
            )
        if "weather_severity_stress" in row:
            result["weather_severity_stress"] = float(
                row.get("weather_severity_stress", 0.5)
            )
        if "disaster_activation_stress" in row:
            result["disaster_activation_stress"] = float(
                row.get("disaster_activation_stress", 0.5)
            )
        if "environmental_volatility" in row:
            result["environmental_volatility"] = float(
                row.get("environmental_volatility", 0.5)
            )
        if "health_incident_pressure" in row:
            result["health_incident_pressure"] = float(
                row.get("health_incident_pressure", 0.5)
            )
        if "health_system_strain" in row:
            result["health_system_strain"] = float(row.get("health_system_strain", 0.5))
        if "mental_health_proxy" in row:
            result["mental_health_proxy"] = float(row.get("mental_health_proxy", 0.5))
        if "public_safety_velocity" in row:
            result["public_safety_velocity"] = float(
                row.get("public_safety_velocity", 0.0)
            )
        if "crime_narrative_intensity" in row:
            result["crime_narrative_intensity"] = float(
                row.get("crime_narrative_intensity", 0.5)
            )
        if "sentiment_whiplash" in row:
            result["sentiment_whiplash"] = float(row.get("sentiment_whiplash", 0.0))
        if "trust_conflict_proxy" in row:
            result["trust_conflict_proxy"] = float(row.get("trust_conflict_proxy", 0.5))
        if "community_anxiety_proxy" in row:
            result["community_anxiety_proxy"] = float(
                row.get("community_anxiety_proxy", 0.5)
            )
        if "civic_disruption_proxy" in row:
            result["civic_disruption_proxy"] = float(
                row.get("civic_disruption_proxy", 0.0)
            )
        # BATCH 1: New child indices from existing data
        if "household_financial_stress" in row:
            result["household_financial_stress"] = float(
                row.get("household_financial_stress", 0.5)
            )
        if "heatwave_stress" in row:
            result["heatwave_stress"] = float(row.get("heatwave_stress", 0.0))
        if "news_polarization_stress" in row:
            result["news_polarization_stress"] = float(
                row.get("news_polarization_stress", 0.0)
            )
        if "cyber_incident_velocity" in row:
            result["cyber_incident_velocity"] = float(
                row.get("cyber_incident_velocity", 0.0)
            )
        if "critical_vulnerability_pressure" in row:
            result["critical_vulnerability_pressure"] = float(
                row.get("critical_vulnerability_pressure", 0.0)
            )
        # BATCH 2: New child indices
        if "drought_stress" in row:
            result["drought_stress"] = float(row.get("drought_stress", 0.0))
        if "flood_risk_stress" in row:
            result["flood_risk_stress"] = float(row.get("flood_risk_stress", 0.0))
        if "coldwave_stress" in row:
            result["coldwave_stress"] = float(row.get("coldwave_stress", 0.0))
        # BATCH 3: New child indices
        if "gdp_growth_stress" in row:
            result["gdp_growth_stress"] = float(row.get("gdp_growth_stress", 0.5))
        if "unemployment_stress" in row:
            result["unemployment_stress"] = float(row.get("unemployment_stress", 0.5))
        if "air_quality_stress" in row:
            result["air_quality_stress"] = float(row.get("air_quality_stress", 0.0))
        # BATCH 4: New child indices
        if "transit_disruption_stress" in row:
            result["transit_disruption_stress"] = float(
                row.get("transit_disruption_stress", 0.0)
            )
        if "congestion_stress" in row:
            result["congestion_stress"] = float(row.get("congestion_stress", 0.0))
        if "search_attention_intensity" in row:
            result["search_attention_intensity"] = float(
                row.get("search_attention_intensity", 0.5)
            )
        if "protest_intensity" in row:
            result["protest_intensity"] = float(row.get("protest_intensity", 0.0))
        # BATCH 5: New child indices
        if "food_price_stress" in row:
            result["food_price_stress"] = float(row.get("food_price_stress", 0.5))
        if "hospital_capacity_strain" in row:
            result["hospital_capacity_strain"] = float(
                row.get("hospital_capacity_strain", 0.5)
            )
        if "violent_crime_stress" in row:
            result["violent_crime_stress"] = float(row.get("violent_crime_stress", 0.0))
        if "misinformation_intensity" in row:
            result["misinformation_intensity"] = float(
                row.get("misinformation_intensity", 0.0)
            )
        # BATCH 6: New child indices
        if "energy_price_stress" in row:
            result["energy_price_stress"] = float(row.get("energy_price_stress", 0.5))
        if "mortality_spike_risk" in row:
            result["mortality_spike_risk"] = float(row.get("mortality_spike_risk", 0.5))
        if "property_crime_stress" in row:
            result["property_crime_stress"] = float(
                row.get("property_crime_stress", 0.0)
            )
        if "institutional_trust_erosion" in row:
            result["institutional_trust_erosion"] = float(
                row.get("institutional_trust_erosion", 0.5)
            )
        # BATCH 7: New child indices
        if "household_debt_stress" in row:
            result["household_debt_stress"] = float(
                row.get("household_debt_stress", 0.5)
            )
        if "infectious_incident_pressure" in row:
            result["infectious_incident_pressure"] = float(
                row.get("infectious_incident_pressure", 0.5)
            )
        if "news_cycle_intensity" in row:
            result["news_cycle_intensity"] = float(row.get("news_cycle_intensity", 0.5))
        if "conflict_activity_stress" in row:
            result["conflict_activity_stress"] = float(
                row.get("conflict_activity_stress", 0.0)
            )

        return result

    def get_contribution_analysis(self, row: pd.Series) -> Dict[str, Dict[str, float]]:
        """
        Compute contribution of each sub-index to the overall behavior_index.

        Args:
            row: Pandas Series with behavior_index and sub-index columns

        Returns:
            Dictionary mapping dimension names to dicts with value, weight,
            and contribution
        """
        economic_value = float(row.get("economic_stress", 0.5))
        environmental_value = float(row.get("environmental_stress", 0.5))
        mobility_value = float(row.get("mobility_activity", 0.5))
        digital_value = float(row.get("digital_attention", 0.5))
        health_value = float(row.get("public_health_stress", 0.5))

        # Note: mobility is inverted in the formula
        mobility_contribution_value = 1.0 - mobility_value

        contributions = {
            "economic_stress": {
                "value": economic_value,
                "weight": self.economic_weight,
                "contribution": float(economic_value * self.economic_weight),
            },
            "environmental_stress": {
                "value": environmental_value,
                "weight": self.environmental_weight,
                "contribution": float(environmental_value * self.environmental_weight),
            },
            "mobility_activity": {
                "value": mobility_value,
                "weight": self.mobility_weight,
                "contribution": float(
                    mobility_contribution_value * self.mobility_weight
                ),
            },
            "digital_attention": {
                "value": digital_value,
                "weight": self.digital_attention_weight,
                "contribution": float(digital_value * self.digital_attention_weight),
            },
            "public_health_stress": {
                "value": health_value,
                "weight": self.health_weight,
                "contribution": float(health_value * self.health_weight),
            },
        }

        # Add new stress indices contributions if weights > 0
        if self.political_weight > 0:
            political_value = float(row.get("political_stress", 0.5))
            contributions["political_stress"] = {
                "value": political_value,
                "weight": self.political_weight,
                "contribution": float(political_value * self.political_weight),
            }
        if self.crime_weight > 0:
            crime_value = float(row.get("crime_stress", 0.5))
            contributions["crime_stress"] = {
                "value": crime_value,
                "weight": self.crime_weight,
                "contribution": float(crime_value * self.crime_weight),
            }
        if self.misinformation_weight > 0:
            misinformation_value = float(row.get("misinformation_stress", 0.5))
            contributions["misinformation_stress"] = {
                "value": misinformation_value,
                "weight": self.misinformation_weight,
                "contribution": float(
                    misinformation_value * self.misinformation_weight
                ),
            }
        if self.social_cohesion_weight > 0:
            social_cohesion_value = float(row.get("social_cohesion_stress", 0.5))
            contributions["social_cohesion_stress"] = {
                "value": social_cohesion_value,
                "weight": self.social_cohesion_weight,
                "contribution": float(
                    social_cohesion_value * self.social_cohesion_weight
                ),
            }

        return contributions

    def get_subindex_details(
        self, df: pd.DataFrame, row_idx: int, include_quality_metrics: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract component-level details for each sub-index from a DataFrame row.

        Args:
            df: DataFrame with sub-index columns and component metadata in attrs
            row_idx: Index of the row to extract details for
            include_quality_metrics: If True, include quality metrics (confidence, volatility, etc.) for each component

        Returns:
            Dictionary mapping sub-index names to their component breakdowns
        """
        row = df.iloc[row_idx]
        details = {}

        # Economic stress components
        if "_economic_component_names" in df.attrs:
            component_names = df.attrs["_economic_component_names"]
            component_weights = df.attrs["_economic_component_weights"]
            component_sources = df.attrs["_economic_component_sources"]

            # Extract component values from the row (handle NaN/inf)
            component_values = []
            if "market_volatility" in component_names:
                val = row.get("stress_index", 0.5)
                val_float = float(val) if pd.notna(val) else 0.5
                component_values.append(val_float if math.isfinite(val_float) else 0.5)
            if "consumer_sentiment" in component_names:
                val = row.get("fred_consumer_sentiment", 0.5)
                val_float = float(val) if pd.notna(val) else 0.5
                component_values.append(val_float if math.isfinite(val_float) else 0.5)
            if "unemployment_rate" in component_names:
                val = row.get("fred_unemployment", 0.5)
                val_float = float(val) if pd.notna(val) else 0.5
                component_values.append(val_float if math.isfinite(val_float) else 0.5)
            if "jobless_claims" in component_names:
                val = row.get("fred_jobless_claims", 0.5)
                val_float = float(val) if pd.notna(val) else 0.5
                component_values.append(val_float if math.isfinite(val_float) else 0.5)

            economic_val = float(row.get("economic_stress", 0.5))
            economic_val = economic_val if math.isfinite(economic_val) else 0.5

            components_list = []
            for name, val, weight, source in zip(
                component_names,
                component_values,
                component_weights,
                component_sources,
            ):
                contribution = (
                    float(val) * float(weight)
                    if math.isfinite(float(val)) and math.isfinite(float(weight))
                    else 0.0
                )
                component_dict = {
                    "id": name,
                    "label": name.replace("_", " ").title(),
                    "value": float(val) if math.isfinite(float(val)) else 0.5,
                    "weight": (float(weight) if math.isfinite(float(weight)) else 0.0),
                    "contribution": contribution,
                    "source": source,
                }

                # Add quality metrics if requested
                if include_quality_metrics:
                    try:
                        from app.core.factor_quality import (
                            compute_factor_quality_metrics,
                        )

                        # Get the series for this component from df
                        component_series = None
                        if name == "market_volatility" and "stress_index" in df.columns:
                            component_series = df["stress_index"]
                        elif (
                            name == "consumer_sentiment"
                            and "fred_consumer_sentiment" in df.columns
                        ):
                            component_series = df["fred_consumer_sentiment"]
                        elif (
                            name == "unemployment_rate"
                            and "fred_unemployment" in df.columns
                        ):
                            component_series = df["fred_unemployment"]
                        elif (
                            name == "jobless_claims"
                            and "fred_jobless_claims" in df.columns
                        ):
                            component_series = df["fred_jobless_claims"]

                        if component_series is not None and len(component_series) > 0:
                            quality_metrics = compute_factor_quality_metrics(
                                component_series
                            )
                            component_dict.update(quality_metrics)
                        else:
                            # Default quality metrics if series not available
                            component_dict.update(
                                {
                                    "confidence": 0.5,
                                    "volatility_classification": "unknown",
                                    "persistence": 0.5,
                                    "trend": "stable",
                                    "signal_strength": 0.5,
                                }
                            )
                    except Exception:
                        # If quality metrics fail, use defaults
                        component_dict.update(
                            {
                                "confidence": 0.5,
                                "volatility_classification": "unknown",
                                "persistence": 0.5,
                                "trend": "stable",
                                "signal_strength": 0.5,
                            }
                        )

                components_list.append(component_dict)

            # Calculate reconciliation: sum of contributions should equal value
            component_sum = sum(c.get("contribution", 0.0) for c in components_list)
            reconciliation_diff = abs(component_sum - economic_val)
            details["economic_stress"] = {
                "value": economic_val,
                "components": components_list,
                "reconciliation": {
                    "sum": float(component_sum),
                    "output": float(economic_val),
                    "difference": float(reconciliation_diff),
                    "valid": reconciliation_diff <= 0.01,
                },
            }
        else:
            # Fallback
            fallback_val = float(row.get("economic_stress", 0.5))
            fallback_component_val = float(row.get("stress_index", 0.5))
            fallback_contribution = fallback_component_val * 1.0
            details["economic_stress"] = {
                "value": fallback_val,
                "components": [
                    {
                        "id": "market_volatility",
                        "label": "Market Volatility",
                        "value": fallback_component_val,
                        "weight": 1.0,
                        "contribution": fallback_contribution,
                        "source": "yfinance",
                    }
                ],
                "reconciliation": {
                    "sum": float(fallback_contribution),
                    "output": float(fallback_val),
                    "difference": float(abs(fallback_contribution - fallback_val)),
                    "valid": abs(fallback_contribution - fallback_val) <= 0.01,
                },
            }

        # Environmental stress components
        if "_environmental_component_names" in df.attrs:
            component_names = df.attrs["_environmental_component_names"]
            component_weights = df.attrs["_environmental_component_weights"]
            component_sources = df.attrs["_environmental_component_sources"]

            env_components = []
            for name, weight, source in zip(
                component_names, component_weights, component_sources
            ):
                # Get the actual component value
                if name == "weather_discomfort":
                    component_val = row.get("discomfort_score", 0.5)
                elif name == "earthquake_intensity":
                    component_val = row.get("usgs_earthquake_intensity", 0.0)
                else:
                    component_val = 0.5

                component_float = (
                    float(component_val)
                    if pd.notna(component_val)
                    else (0.0 if name == "earthquake_intensity" else 0.5)
                )
                component_float = (
                    component_float
                    if math.isfinite(component_float)
                    else (0.0 if name == "earthquake_intensity" else 0.5)
                )

                contribution = (
                    component_float * float(weight)
                    if math.isfinite(component_float) and math.isfinite(float(weight))
                    else 0.0
                )
                env_components.append(
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": component_float,
                        "weight": float(weight),
                        "contribution": contribution,
                        "source": source,
                    }
                )
            env_val = (
                float(row.get("environmental_stress", 0.5))
                if math.isfinite(float(row.get("environmental_stress", 0.5)))
                else 0.5
            )
            env_component_sum = sum(c.get("contribution", 0.0) for c in env_components)
            env_reconciliation_diff = abs(env_component_sum - env_val)
            details["environmental_stress"] = {
                "value": env_val,
                "components": env_components,
                "reconciliation": {
                    "sum": float(env_component_sum),
                    "output": float(env_val),
                    "difference": float(env_reconciliation_diff),
                    "valid": env_reconciliation_diff <= 0.01,
                },
            }
        else:
            env_fallback_val = float(row.get("environmental_stress", 0.5))
            env_fallback_component_val = float(row.get("discomfort_score", 0.5))
            env_fallback_contribution = env_fallback_component_val * 1.0
            details["environmental_stress"] = {
                "value": env_fallback_val,
                "components": [
                    {
                        "id": "weather_discomfort",
                        "label": "Weather Discomfort",
                        "value": env_fallback_component_val,
                        "weight": 1.0,
                        "contribution": env_fallback_contribution,
                        "source": "Open-Meteo",
                    }
                ],
                "reconciliation": {
                    "sum": float(env_fallback_contribution),
                    "output": float(env_fallback_val),
                    "difference": float(
                        abs(env_fallback_contribution - env_fallback_val)
                    ),
                    "valid": abs(env_fallback_contribution - env_fallback_val) <= 0.01,
                },
            }

        # Mobility activity components
        if "_mobility_component_names" in df.attrs:
            component_names = df.attrs["_mobility_component_names"]
            component_weights = df.attrs["_mobility_component_weights"]
            component_sources = df.attrs["_mobility_component_sources"]

            mobility_val = row.get("mobility_index", 0.5)
            mobility_float = float(mobility_val) if pd.notna(mobility_val) else 0.5
            mobility_float = mobility_float if math.isfinite(mobility_float) else 0.5
            mob_components = []
            for name, weight, source in zip(
                component_names, component_weights, component_sources
            ):
                contribution = (
                    mobility_float * float(weight)
                    if math.isfinite(mobility_float) and math.isfinite(float(weight))
                    else 0.0
                )
                mob_components.append(
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": mobility_float,
                        "weight": float(weight),
                        "contribution": contribution,
                        "source": source,
                    }
                )
            mob_val = (
                float(row.get("mobility_activity", 0.5))
                if math.isfinite(float(row.get("mobility_activity", 0.5)))
                else 0.5
            )
            mob_component_sum = sum(c.get("contribution", 0.0) for c in mob_components)
            mob_reconciliation_diff = abs(mob_component_sum - mob_val)
            details["mobility_activity"] = {
                "value": mob_val,
                "components": mob_components,
                "reconciliation": {
                    "sum": float(mob_component_sum),
                    "output": float(mob_val),
                    "difference": float(mob_reconciliation_diff),
                    "valid": mob_reconciliation_diff <= 0.01,
                },
            }
        else:
            mob_fallback_val = float(row.get("mobility_activity", 0.5))
            mob_fallback_component_val = float(row.get("mobility_index", 0.5))
            mob_fallback_contribution = mob_fallback_component_val * 1.0
            details["mobility_activity"] = {
                "value": mob_fallback_val,
                "components": [
                    {
                        "id": "mobility_index",
                        "label": "Mobility Index",
                        "value": mob_fallback_component_val,
                        "weight": 1.0,
                        "contribution": mob_fallback_contribution,
                        "source": "default",
                    }
                ],
                "reconciliation": {
                    "sum": float(mob_fallback_contribution),
                    "output": float(mob_fallback_val),
                    "difference": float(
                        abs(mob_fallback_contribution - mob_fallback_val)
                    ),
                    "valid": abs(mob_fallback_contribution - mob_fallback_val) <= 0.01,
                },
            }

        # Digital attention components
        if "_digital_component_names" in df.attrs:
            component_names = df.attrs["_digital_component_names"]
            component_weights = df.attrs["_digital_component_weights"]
            component_sources = df.attrs["_digital_component_sources"]

            dig_components = []
            for name, weight, source in zip(
                component_names, component_weights, component_sources
            ):
                # Get the actual component value
                if name == "search_interest":
                    component_val = row.get("search_interest_score", 0.5)
                elif name == "gdelt_tone":
                    component_val = row.get("gdelt_tone_score", 0.5)
                else:
                    component_val = 0.5

                component_float = (
                    float(component_val) if pd.notna(component_val) else 0.5
                )
                component_float = (
                    component_float if math.isfinite(component_float) else 0.5
                )

                contribution = (
                    component_float * float(weight)
                    if math.isfinite(component_float) and math.isfinite(float(weight))
                    else 0.0
                )
                dig_components.append(
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": component_float,
                        "weight": float(weight),
                        "contribution": contribution,
                        "source": source,
                    }
                )
            dig_val = (
                float(row.get("digital_attention", 0.5))
                if math.isfinite(float(row.get("digital_attention", 0.5)))
                else 0.5
            )
            dig_component_sum = sum(c.get("contribution", 0.0) for c in dig_components)
            dig_reconciliation_diff = abs(dig_component_sum - dig_val)
            details["digital_attention"] = {
                "value": dig_val,
                "components": dig_components,
                "reconciliation": {
                    "sum": float(dig_component_sum),
                    "output": float(dig_val),
                    "difference": float(dig_reconciliation_diff),
                    "valid": dig_reconciliation_diff <= 0.01,
                },
            }
        else:
            dig_fallback_val = float(row.get("digital_attention", 0.5))
            dig_fallback_component_val = float(row.get("search_interest_score", 0.5))
            dig_fallback_contribution = dig_fallback_component_val * 1.0
            details["digital_attention"] = {
                "value": dig_fallback_val,
                "components": [
                    {
                        "id": "search_interest",
                        "label": "Search Interest",
                        "value": dig_fallback_component_val,
                        "weight": 1.0,
                        "contribution": dig_fallback_contribution,
                        "source": "default",
                    }
                ],
                "reconciliation": {
                    "sum": float(dig_fallback_contribution),
                    "output": float(dig_fallback_val),
                    "difference": float(
                        abs(dig_fallback_contribution - dig_fallback_val)
                    ),
                    "valid": abs(dig_fallback_contribution - dig_fallback_val) <= 0.01,
                },
            }

        # Public health stress components
        if "_health_component_names" in df.attrs:
            component_names = df.attrs["_health_component_names"]
            component_weights = df.attrs["_health_component_weights"]
            component_sources = df.attrs["_health_component_sources"]

            health_components = []
            for name, weight, source in zip(
                component_names, component_weights, component_sources
            ):
                # Get the actual component value
                if name == "health_risk_index":
                    component_val = row.get("health_risk_index", 0.5)
                elif name == "owid_health_stress":
                    component_val = row.get("owid_health_stress", 0.5)
                else:
                    component_val = 0.5

                component_float = (
                    float(component_val) if pd.notna(component_val) else 0.5
                )
                component_float = (
                    component_float if math.isfinite(component_float) else 0.5
                )

                contribution = (
                    component_float * float(weight)
                    if math.isfinite(component_float) and math.isfinite(float(weight))
                    else 0.0
                )
                health_components.append(
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": component_float,
                        "weight": float(weight),
                        "contribution": contribution,
                        "source": source,
                    }
                )
            health_val = (
                float(row.get("public_health_stress", 0.5))
                if math.isfinite(float(row.get("public_health_stress", 0.5)))
                else 0.5
            )
            health_component_sum = sum(
                c.get("contribution", 0.0) for c in health_components
            )
            health_reconciliation_diff = abs(health_component_sum - health_val)
            details["public_health_stress"] = {
                "value": health_val,
                "components": health_components,
                "reconciliation": {
                    "sum": float(health_component_sum),
                    "output": float(health_val),
                    "difference": float(health_reconciliation_diff),
                    "valid": health_reconciliation_diff <= 0.01,
                },
            }
        else:
            health_fallback_val = float(row.get("public_health_stress", 0.5))
            health_fallback_component_val = float(row.get("health_risk_index", 0.5))
            health_fallback_contribution = health_fallback_component_val * 1.0
            details["public_health_stress"] = {
                "value": health_fallback_val,
                "components": [
                    {
                        "id": "health_risk_index",
                        "label": "Health Risk Index",
                        "value": health_fallback_component_val,
                        "weight": 1.0,
                        "contribution": health_fallback_contribution,
                        "source": "default",
                    }
                ],
                "reconciliation": {
                    "sum": float(health_fallback_contribution),
                    "output": float(health_fallback_val),
                    "difference": float(
                        abs(health_fallback_contribution - health_fallback_val)
                    ),
                    "valid": abs(health_fallback_contribution - health_fallback_val)
                    <= 0.01,
                },
            }

        # Political stress components
        if "_political_component_names" in df.attrs:
            component_names = df.attrs["_political_component_names"]
            component_weights = df.attrs["_political_component_weights"]
            component_sources = df.attrs["_political_component_sources"]

            political_val = row.get("political_stress", 0.5)
            political_float = float(political_val) if pd.notna(political_val) else 0.5
            political_float = political_float if math.isfinite(political_float) else 0.5
            pol_components = []
            for name, weight, source in zip(
                component_names, component_weights, component_sources
            ):
                contribution = (
                    political_float * float(weight)
                    if math.isfinite(political_float) and math.isfinite(float(weight))
                    else 0.0
                )
                pol_components.append(
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": political_float,
                        "weight": float(weight),
                        "contribution": contribution,
                        "source": source,
                    }
                )
            pol_val = (
                float(row.get("political_stress", 0.5))
                if math.isfinite(float(row.get("political_stress", 0.5)))
                else 0.5
            )
            pol_component_sum = sum(c.get("contribution", 0.0) for c in pol_components)
            pol_reconciliation_diff = abs(pol_component_sum - pol_val)
            details["political_stress"] = {
                "value": pol_val,
                "components": pol_components,
                "reconciliation": {
                    "sum": float(pol_component_sum),
                    "output": float(pol_val),
                    "difference": float(pol_reconciliation_diff),
                    "valid": pol_reconciliation_diff <= 0.01,
                },
            }
        else:
            pol_fallback_val = float(row.get("political_stress", 0.5))
            pol_fallback_contribution = pol_fallback_val * 1.0
            details["political_stress"] = {
                "value": pol_fallback_val,
                "components": [
                    {
                        "id": "political_stress",
                        "label": "Political Stress",
                        "value": pol_fallback_val,
                        "weight": 1.0,
                        "contribution": pol_fallback_contribution,
                        "source": "default",
                    }
                ],
                "reconciliation": {
                    "sum": float(pol_fallback_contribution),
                    "output": float(pol_fallback_val),
                    "difference": float(
                        abs(pol_fallback_contribution - pol_fallback_val)
                    ),
                    "valid": abs(pol_fallback_contribution - pol_fallback_val) <= 0.01,
                },
            }

        # Crime stress components
        if "_crime_component_names" in df.attrs:
            component_names = df.attrs["_crime_component_names"]
            component_weights = df.attrs["_crime_component_weights"]
            component_sources = df.attrs["_crime_component_sources"]

            crime_val = row.get("crime_stress", 0.5)
            crime_float = float(crime_val) if pd.notna(crime_val) else 0.5
            crime_float = crime_float if math.isfinite(crime_float) else 0.5
            crime_components = []
            for name, weight, source in zip(
                component_names, component_weights, component_sources
            ):
                contribution = (
                    crime_float * float(weight)
                    if math.isfinite(crime_float) and math.isfinite(float(weight))
                    else 0.0
                )
                crime_components.append(
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": crime_float,
                        "weight": float(weight),
                        "contribution": contribution,
                        "source": source,
                    }
                )
            crime_val = (
                float(row.get("crime_stress", 0.5))
                if math.isfinite(float(row.get("crime_stress", 0.5)))
                else 0.5
            )
            crime_component_sum = sum(
                c.get("contribution", 0.0) for c in crime_components
            )
            crime_reconciliation_diff = abs(crime_component_sum - crime_val)
            details["crime_stress"] = {
                "value": crime_val,
                "components": crime_components,
                "reconciliation": {
                    "sum": float(crime_component_sum),
                    "output": float(crime_val),
                    "difference": float(crime_reconciliation_diff),
                    "valid": crime_reconciliation_diff <= 0.01,
                },
            }
        else:
            crime_fallback_val = float(row.get("crime_stress", 0.5))
            crime_fallback_contribution = crime_fallback_val * 1.0
            details["crime_stress"] = {
                "value": crime_fallback_val,
                "components": [
                    {
                        "id": "crime_stress",
                        "label": "Crime Stress",
                        "value": crime_fallback_val,
                        "weight": 1.0,
                        "contribution": crime_fallback_contribution,
                        "source": "default",
                    }
                ],
                "reconciliation": {
                    "sum": float(crime_fallback_contribution),
                    "output": float(crime_fallback_val),
                    "difference": float(
                        abs(crime_fallback_contribution - crime_fallback_val)
                    ),
                    "valid": abs(crime_fallback_contribution - crime_fallback_val)
                    <= 0.01,
                },
            }

        # Misinformation stress components
        if "_misinformation_component_names" in df.attrs:
            component_names = df.attrs["_misinformation_component_names"]
            component_weights = df.attrs["_misinformation_component_weights"]
            component_sources = df.attrs["_misinformation_component_sources"]

            misinformation_val = row.get("misinformation_stress", 0.5)
            misinformation_float = (
                float(misinformation_val) if pd.notna(misinformation_val) else 0.5
            )
            misinformation_float = (
                misinformation_float if math.isfinite(misinformation_float) else 0.5
            )
            misinfo_components = []
            for name, weight, source in zip(
                component_names, component_weights, component_sources
            ):
                contribution = (
                    misinformation_float * float(weight)
                    if math.isfinite(misinformation_float)
                    and math.isfinite(float(weight))
                    else 0.0
                )
                misinfo_components.append(
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": misinformation_float,
                        "weight": float(weight),
                        "contribution": contribution,
                        "source": source,
                    }
                )
            misinfo_val = (
                float(row.get("misinformation_stress", 0.5))
                if math.isfinite(float(row.get("misinformation_stress", 0.5)))
                else 0.5
            )
            misinfo_component_sum = sum(
                c.get("contribution", 0.0) for c in misinfo_components
            )
            misinfo_reconciliation_diff = abs(misinfo_component_sum - misinfo_val)
            details["misinformation_stress"] = {
                "value": misinfo_val,
                "components": misinfo_components,
                "reconciliation": {
                    "sum": float(misinfo_component_sum),
                    "output": float(misinfo_val),
                    "difference": float(misinfo_reconciliation_diff),
                    "valid": misinfo_reconciliation_diff <= 0.01,
                },
            }
        else:
            misinfo_fallback_val = float(row.get("misinformation_stress", 0.5))
            misinfo_fallback_contribution = misinfo_fallback_val * 1.0
            details["misinformation_stress"] = {
                "value": misinfo_fallback_val,
                "components": [
                    {
                        "id": "misinformation_stress",
                        "label": "Misinformation Stress",
                        "value": misinfo_fallback_val,
                        "weight": 1.0,
                        "contribution": misinfo_fallback_contribution,
                        "source": "default",
                    }
                ],
                "reconciliation": {
                    "sum": float(misinfo_fallback_contribution),
                    "output": float(misinfo_fallback_val),
                    "difference": float(
                        abs(misinfo_fallback_contribution - misinfo_fallback_val)
                    ),
                    "valid": abs(misinfo_fallback_contribution - misinfo_fallback_val)
                    <= 0.01,
                },
            }

        # Social cohesion stress components
        if "_social_cohesion_component_names" in df.attrs:
            component_names = df.attrs["_social_cohesion_component_names"]
            component_weights = df.attrs["_social_cohesion_component_weights"]
            component_sources = df.attrs["_social_cohesion_component_sources"]

            social_cohesion_val = row.get("social_cohesion_stress", 0.5)
            social_cohesion_float = (
                float(social_cohesion_val) if pd.notna(social_cohesion_val) else 0.5
            )
            social_cohesion_float = (
                social_cohesion_float if math.isfinite(social_cohesion_float) else 0.5
            )
            soc_components = []
            for name, weight, source in zip(
                component_names, component_weights, component_sources
            ):
                contribution = (
                    social_cohesion_float * float(weight)
                    if math.isfinite(social_cohesion_float)
                    and math.isfinite(float(weight))
                    else 0.0
                )
                soc_components.append(
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": social_cohesion_float,
                        "weight": float(weight),
                        "contribution": contribution,
                        "source": source,
                    }
                )
            soc_val = (
                float(row.get("social_cohesion_stress", 0.5))
                if math.isfinite(float(row.get("social_cohesion_stress", 0.5)))
                else 0.5
            )
            soc_component_sum = sum(c.get("contribution", 0.0) for c in soc_components)
            soc_reconciliation_diff = abs(soc_component_sum - soc_val)
            details["social_cohesion_stress"] = {
                "value": soc_val,
                "components": soc_components,
                "reconciliation": {
                    "sum": float(soc_component_sum),
                    "output": float(soc_val),
                    "difference": float(soc_reconciliation_diff),
                    "valid": soc_reconciliation_diff <= 0.01,
                },
            }
        else:
            soc_fallback_val = float(row.get("social_cohesion_stress", 0.5))
            soc_fallback_contribution = soc_fallback_val * 1.0
            details["social_cohesion_stress"] = {
                "value": soc_fallback_val,
                "components": [
                    {
                        "id": "social_cohesion_stress",
                        "label": "Social Cohesion Stress",
                        "value": soc_fallback_val,
                        "weight": 1.0,
                        "contribution": soc_fallback_contribution,
                        "source": "default",
                    }
                ],
                "reconciliation": {
                    "sum": float(soc_fallback_contribution),
                    "output": float(soc_fallback_val),
                    "difference": float(
                        abs(soc_fallback_contribution - soc_fallback_val)
                    ),
                    "valid": abs(soc_fallback_contribution - soc_fallback_val) <= 0.01,
                },
            }

        return details
