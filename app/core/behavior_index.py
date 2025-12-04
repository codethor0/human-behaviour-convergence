# SPDX-License-Identifier: PROPRIETARY
"""Interpretable Behavior Index computation with sub-indices.

This module computes a composite Behavior Index from multiple human behavior
dimensions, each represented by a normalized sub-index.
"""
import math
from typing import Any, Dict

import pandas as pd
import structlog

logger = structlog.get_logger("core.behavior_index")


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
        economic_weight: float = 0.25,
        environmental_weight: float = 0.25,
        mobility_weight: float = 0.20,
        digital_attention_weight: float = 0.15,
        health_weight: float = 0.15,
        political_weight: float = 0.15,
        crime_weight: float = 0.15,
        misinformation_weight: float = 0.10,
        social_cohesion_weight: float = 0.15,
    ):
        """
        Initialize the Behavior Index computer.

        Args:
            economic_weight: Weight for economic stress sub-index (default: 0.25)
            environmental_weight: Weight for environmental stress sub-index (default: 0.25)
            mobility_weight: Weight for mobility activity sub-index (default: 0.20)
            digital_attention_weight: Weight for digital attention sub-index (default: 0.15)
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

        # Calculate total weight (only include non-zero weights for backward compatibility)
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

        # Combine indicators with adaptive weights based on availability
        # Target weights: market (40%), consumer sentiment (30%), unemployment (20%), jobless claims (10%)
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

        # Store component metadata for breakdown (store component info in DataFrame for later extraction)
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
        # Weather discomfort_score is already normalized 0.0-1.0 (higher = more discomfort)
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
        - Digital attention can indicate disruption (higher attention = potential disruption)

        Args:
            harmonized_data: DataFrame with columns:
                - timestamp (datetime)
                - stress_index, discomfort_score, and optional mobility/search/health indices

        Returns:
            DataFrame with added columns:
                - All sub-indices (economic_stress, environmental_stress, etc.)
                - behavior_index (0.0-1.0, overall behavioral disruption measure)
        """
        # Compute sub-indices first
        df = self.compute_sub_indices(harmonized_data)

        # Compute overall Behavior Index
        # Higher stress indices and lower activity indices = higher behavior index
        # Formula: weighted combination where stress increases index, activity decreases it
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
        result = {
            "economic_stress": float(row.get("economic_stress", 0.5)),
            "environmental_stress": float(row.get("environmental_stress", 0.5)),
            "mobility_activity": float(row.get("mobility_activity", 0.5)),
            "digital_attention": float(row.get("digital_attention", 0.5)),
            "public_health_stress": float(row.get("public_health_stress", 0.5)),
        }
        # Add new stress indices if weights > 0
        if self.political_weight > 0:
            result["political_stress"] = float(row.get("political_stress", 0.5))
        if self.crime_weight > 0:
            result["crime_stress"] = float(row.get("crime_stress", 0.5))
        if self.misinformation_weight > 0:
            result["misinformation_stress"] = float(
                row.get("misinformation_stress", 0.5)
            )
        if self.social_cohesion_weight > 0:
            result["social_cohesion_stress"] = float(
                row.get("social_cohesion_stress", 0.5)
            )
        return result

    def get_contribution_analysis(self, row: pd.Series) -> Dict[str, Dict[str, float]]:
        """
        Compute contribution of each sub-index to the overall behavior_index.

        Args:
            row: Pandas Series with behavior_index and sub-index columns

        Returns:
            Dictionary mapping dimension names to dicts with value, weight, and contribution
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
        self, df: pd.DataFrame, row_idx: int
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract component-level details for each sub-index from a DataFrame row.

        Args:
            df: DataFrame with sub-index columns and component metadata in attrs
            row_idx: Index of the row to extract details for

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
            details["economic_stress"] = {
                "value": economic_val,
                "components": [
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": float(val) if math.isfinite(float(val)) else 0.5,
                        "weight": (
                            float(weight) if math.isfinite(float(weight)) else 0.0
                        ),
                        "source": source,
                    }
                    for name, val, weight, source in zip(
                        component_names,
                        component_values,
                        component_weights,
                        component_sources,
                    )
                ],
            }
        else:
            # Fallback
            details["economic_stress"] = {
                "value": float(row.get("economic_stress", 0.5)),
                "components": [
                    {
                        "id": "market_volatility",
                        "label": "Market Volatility",
                        "value": float(row.get("stress_index", 0.5)),
                        "weight": 1.0,
                        "source": "yfinance",
                    }
                ],
            }

        # Environmental stress components
        if "_environmental_component_names" in df.attrs:
            component_names = df.attrs["_environmental_component_names"]
            component_weights = df.attrs["_environmental_component_weights"]
            component_sources = df.attrs["_environmental_component_sources"]

            discomfort_val = row.get("discomfort_score", 0.5)
            discomfort_float = (
                float(discomfort_val) if pd.notna(discomfort_val) else 0.5
            )
            discomfort_float = (
                discomfort_float if math.isfinite(discomfort_float) else 0.5
            )
            details["environmental_stress"] = {
                "value": (
                    float(row.get("environmental_stress", 0.5))
                    if math.isfinite(float(row.get("environmental_stress", 0.5)))
                    else 0.5
                ),
                "components": [
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": discomfort_float,
                        "weight": float(weight),
                        "source": source,
                    }
                    for name, weight, source in zip(
                        component_names, component_weights, component_sources
                    )
                ],
            }
        else:
            details["environmental_stress"] = {
                "value": float(row.get("environmental_stress", 0.5)),
                "components": [
                    {
                        "id": "weather_discomfort",
                        "label": "Weather Discomfort",
                        "value": float(row.get("discomfort_score", 0.5)),
                        "weight": 1.0,
                        "source": "Open-Meteo",
                    }
                ],
            }

        # Mobility activity components
        if "_mobility_component_names" in df.attrs:
            component_names = df.attrs["_mobility_component_names"]
            component_weights = df.attrs["_mobility_component_weights"]
            component_sources = df.attrs["_mobility_component_sources"]

            mobility_val = row.get("mobility_index", 0.5)
            mobility_float = float(mobility_val) if pd.notna(mobility_val) else 0.5
            mobility_float = mobility_float if math.isfinite(mobility_float) else 0.5
            details["mobility_activity"] = {
                "value": (
                    float(row.get("mobility_activity", 0.5))
                    if math.isfinite(float(row.get("mobility_activity", 0.5)))
                    else 0.5
                ),
                "components": [
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": mobility_float,
                        "weight": float(weight),
                        "source": source,
                    }
                    for name, weight, source in zip(
                        component_names, component_weights, component_sources
                    )
                ],
            }
        else:
            details["mobility_activity"] = {
                "value": float(row.get("mobility_activity", 0.5)),
                "components": [
                    {
                        "id": "mobility_index",
                        "label": "Mobility Index",
                        "value": float(row.get("mobility_index", 0.5)),
                        "weight": 1.0,
                        "source": "default",
                    }
                ],
            }

        # Digital attention components
        if "_digital_component_names" in df.attrs:
            component_names = df.attrs["_digital_component_names"]
            component_weights = df.attrs["_digital_component_weights"]
            component_sources = df.attrs["_digital_component_sources"]

            search_val = row.get("search_interest_score", 0.5)
            search_float = float(search_val) if pd.notna(search_val) else 0.5
            search_float = search_float if math.isfinite(search_float) else 0.5
            details["digital_attention"] = {
                "value": (
                    float(row.get("digital_attention", 0.5))
                    if math.isfinite(float(row.get("digital_attention", 0.5)))
                    else 0.5
                ),
                "components": [
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": search_float,
                        "weight": float(weight),
                        "source": source,
                    }
                    for name, weight, source in zip(
                        component_names, component_weights, component_sources
                    )
                ],
            }
        else:
            details["digital_attention"] = {
                "value": float(row.get("digital_attention", 0.5)),
                "components": [
                    {
                        "id": "search_interest",
                        "label": "Search Interest",
                        "value": float(row.get("search_interest_score", 0.5)),
                        "weight": 1.0,
                        "source": "default",
                    }
                ],
            }

        # Public health stress components
        if "_health_component_names" in df.attrs:
            component_names = df.attrs["_health_component_names"]
            component_weights = df.attrs["_health_component_weights"]
            component_sources = df.attrs["_health_component_sources"]

            health_val = row.get("health_risk_index", 0.5)
            health_float = float(health_val) if pd.notna(health_val) else 0.5
            health_float = health_float if math.isfinite(health_float) else 0.5
            details["public_health_stress"] = {
                "value": (
                    float(row.get("public_health_stress", 0.5))
                    if math.isfinite(float(row.get("public_health_stress", 0.5)))
                    else 0.5
                ),
                "components": [
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": health_float,
                        "weight": float(weight),
                        "source": source,
                    }
                    for name, weight, source in zip(
                        component_names, component_weights, component_sources
                    )
                ],
            }
        else:
            details["public_health_stress"] = {
                "value": float(row.get("public_health_stress", 0.5)),
                "components": [
                    {
                        "id": "health_risk_index",
                        "label": "Health Risk Index",
                        "value": float(row.get("health_risk_index", 0.5)),
                        "weight": 1.0,
                        "source": "default",
                    }
                ],
            }

        # Political stress components
        if "_political_component_names" in df.attrs:
            component_names = df.attrs["_political_component_names"]
            component_weights = df.attrs["_political_component_weights"]
            component_sources = df.attrs["_political_component_sources"]

            political_val = row.get("political_stress", 0.5)
            political_float = float(political_val) if pd.notna(political_val) else 0.5
            political_float = political_float if math.isfinite(political_float) else 0.5
            details["political_stress"] = {
                "value": (
                    float(row.get("political_stress", 0.5))
                    if math.isfinite(float(row.get("political_stress", 0.5)))
                    else 0.5
                ),
                "components": [
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": political_float,
                        "weight": float(weight),
                        "source": source,
                    }
                    for name, weight, source in zip(
                        component_names, component_weights, component_sources
                    )
                ],
            }
        else:
            details["political_stress"] = {
                "value": float(row.get("political_stress", 0.5)),
                "components": [
                    {
                        "id": "political_stress",
                        "label": "Political Stress",
                        "value": float(row.get("political_stress", 0.5)),
                        "weight": 1.0,
                        "source": "default",
                    }
                ],
            }

        # Crime stress components
        if "_crime_component_names" in df.attrs:
            component_names = df.attrs["_crime_component_names"]
            component_weights = df.attrs["_crime_component_weights"]
            component_sources = df.attrs["_crime_component_sources"]

            crime_val = row.get("crime_stress", 0.5)
            crime_float = float(crime_val) if pd.notna(crime_val) else 0.5
            crime_float = crime_float if math.isfinite(crime_float) else 0.5
            details["crime_stress"] = {
                "value": (
                    float(row.get("crime_stress", 0.5))
                    if math.isfinite(float(row.get("crime_stress", 0.5)))
                    else 0.5
                ),
                "components": [
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": crime_float,
                        "weight": float(weight),
                        "source": source,
                    }
                    for name, weight, source in zip(
                        component_names, component_weights, component_sources
                    )
                ],
            }
        else:
            details["crime_stress"] = {
                "value": float(row.get("crime_stress", 0.5)),
                "components": [
                    {
                        "id": "crime_stress",
                        "label": "Crime Stress",
                        "value": float(row.get("crime_stress", 0.5)),
                        "weight": 1.0,
                        "source": "default",
                    }
                ],
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
            details["misinformation_stress"] = {
                "value": (
                    float(row.get("misinformation_stress", 0.5))
                    if math.isfinite(float(row.get("misinformation_stress", 0.5)))
                    else 0.5
                ),
                "components": [
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": misinformation_float,
                        "weight": float(weight),
                        "source": source,
                    }
                    for name, weight, source in zip(
                        component_names, component_weights, component_sources
                    )
                ],
            }
        else:
            details["misinformation_stress"] = {
                "value": float(row.get("misinformation_stress", 0.5)),
                "components": [
                    {
                        "id": "misinformation_stress",
                        "label": "Misinformation Stress",
                        "value": float(row.get("misinformation_stress", 0.5)),
                        "weight": 1.0,
                        "source": "default",
                    }
                ],
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
            details["social_cohesion_stress"] = {
                "value": (
                    float(row.get("social_cohesion_stress", 0.5))
                    if math.isfinite(float(row.get("social_cohesion_stress", 0.5)))
                    else 0.5
                ),
                "components": [
                    {
                        "id": name,
                        "label": name.replace("_", " ").title(),
                        "value": social_cohesion_float,
                        "weight": float(weight),
                        "source": source,
                    }
                    for name, weight, source in zip(
                        component_names, component_weights, component_sources
                    )
                ],
            }
        else:
            details["social_cohesion_stress"] = {
                "value": float(row.get("social_cohesion_stress", 0.5)),
                "components": [
                    {
                        "id": "social_cohesion_stress",
                        "label": "Social Cohesion Stress",
                        "value": float(row.get("social_cohesion_stress", 0.5)),
                        "weight": 1.0,
                        "source": "default",
                    }
                ],
            }

        return details
