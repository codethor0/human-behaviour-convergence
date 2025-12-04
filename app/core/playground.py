# SPDX-License-Identifier: PROPRIETARY
"""Playground module for interactive scenario exploration.

This module provides multi-region comparison and optional scenario
adjustments for exploring "what-if" behavioral forecasts.
"""
from typing import Dict, List, Optional

import structlog

from app.core.prediction import BehavioralForecaster
from app.core.regions import get_region_by_id

logger = structlog.get_logger("core.playground")


def apply_scenario(
    sub_indices: Dict[str, float],
    scenario: Optional[Dict] = None,
) -> Dict[str, float]:
    """
    Apply optional scenario adjustments to sub-indices (post-processing).

    This is a pure what-if transformation for exploration only.
    The original sub-indices are adjusted by offsets, then clamped to [0.0, 1.0].

    Args:
        sub_indices: Dictionary mapping sub-index names to values (0.0-1.0)
        scenario: Optional scenario configuration with offsets:
            {
                "economic_stress_offset": 0.1,  # Add 0.1 to economic_stress
                "environmental_stress_offset": -0.05,
                "digital_attention_offset": 0.2,
                ...
            }

    Returns:
        Adjusted sub-indices dictionary with same keys
    """
    if scenario is None:
        return sub_indices.copy()

    adjusted = sub_indices.copy()

    # Apply offsets for each sub-index if specified
    offset_keys = [
        "economic_stress_offset",
        "environmental_stress_offset",
        "mobility_activity_offset",
        "digital_attention_offset",
        "public_health_stress_offset",
    ]

    for offset_key in offset_keys:
        if offset_key in scenario:
            offset = float(scenario[offset_key])
            # Map offset key to sub-index key
            sub_index_key = offset_key.replace("_offset", "")
            if sub_index_key in adjusted:
                # Apply offset and clamp to [0.0, 1.0]
                adjusted[sub_index_key] = max(
                    0.0, min(1.0, adjusted[sub_index_key] + offset)
                )
                logger.debug(
                    "Applied scenario offset",
                    sub_index=sub_index_key,
                    offset=offset,
                    original=sub_indices[sub_index_key],
                    adjusted=adjusted[sub_index_key],
                )

    return adjusted


def recompute_behavior_index_from_sub_indices(
    sub_indices: Dict[str, float],
    economic_weight: float = 0.25,
    environmental_weight: float = 0.25,
    mobility_weight: float = 0.20,
    digital_attention_weight: float = 0.15,
    health_weight: float = 0.15,
) -> float:
    """
    Recompute behavior index from sub-indices using fixed weights.

    This uses the same formula as BehaviorIndexComputer but allows
    recomputation with adjusted sub-indices for scenario exploration.

    Args:
        sub_indices: Dictionary with sub-index values
        economic_weight: Weight for economic stress (default: 0.25)
        environmental_weight: Weight for environmental stress (default: 0.25)
        mobility_weight: Weight for mobility activity (default: 0.20)
        digital_attention_weight: Weight for digital attention (default: 0.15)
        health_weight: Weight for public health stress (default: 0.15)

    Returns:
        Behavior index value (0.0-1.0)
    """
    economic_stress = sub_indices.get("economic_stress", 0.5)
    environmental_stress = sub_indices.get("environmental_stress", 0.5)
    mobility_activity = sub_indices.get("mobility_activity", 0.5)
    digital_attention = sub_indices.get("digital_attention", 0.5)
    public_health_stress = sub_indices.get("public_health_stress", 0.5)

    # Same formula as BehaviorIndexComputer
    behavior_index = (
        (economic_stress * economic_weight)
        + (environmental_stress * environmental_weight)
        + (
            (1.0 - mobility_activity) * mobility_weight
        )  # Inverse: lower activity = higher disruption
        + (digital_attention * digital_attention_weight)
        + (public_health_stress * health_weight)
    )

    # Clip to valid range
    return max(0.0, min(1.0, behavior_index))


def compare_regions(
    region_ids: List[str],
    historical_days: int = 30,
    forecast_horizon_days: int = 7,
    include_explanations: bool = True,
    scenario: Optional[Dict] = None,
) -> Dict:
    """
    Generate forecasts for multiple regions and optionally apply scenario adjustments.

    Args:
        region_ids: List of region IDs (e.g., ["us_dc", "us_mn", "city_nyc"])
        historical_days: Number of historical days to use (default: 30)
        forecast_horizon_days: Number of days to forecast ahead (default: 7)
        include_explanations: Whether to include explanation objects (default: True)
        scenario: Optional scenario configuration with sub-index offsets

    Returns:
        Dictionary with:
        - config: Configuration used
        - results: List of forecast results per region
        - errors: List of errors for regions that failed
    """
    if not region_ids:
        raise ValueError("At least one region_id must be provided")

    forecaster = BehavioralForecaster()
    results = []
    errors = []

    for region_id in region_ids:
        try:
            region = get_region_by_id(region_id)
            if region is None:
                errors.append(
                    {
                        "region_id": region_id,
                        "error": f"Region not found: {region_id}",
                    }
                )
                continue

            # Generate forecast using existing pipeline
            forecast_result = forecaster.forecast(
                latitude=region.latitude,
                longitude=region.longitude,
                region_name=region.name,
                days_back=historical_days,
                forecast_horizon=forecast_horizon_days,
            )

            # Extract latest sub-indices for scenario adjustment if needed
            # Note: forecast_result from BehavioralForecaster.forecast() returns raw dict
            # The history contains dict records with behavior_index and optionally sub_indices
            latest_sub_indices = None
            if forecast_result.get("history") and len(forecast_result["history"]) > 0:
                latest_history = forecast_result["history"][-1]
                if isinstance(latest_history, dict) and "sub_indices" in latest_history:
                    sub_indices_data = latest_history["sub_indices"]
                    if isinstance(sub_indices_data, dict):
                        latest_sub_indices = {
                            "economic_stress": sub_indices_data.get(
                                "economic_stress", 0.5
                            ),
                            "environmental_stress": sub_indices_data.get(
                                "environmental_stress", 0.5
                            ),
                            "mobility_activity": sub_indices_data.get(
                                "mobility_activity", 0.5
                            ),
                            "digital_attention": sub_indices_data.get(
                                "digital_attention", 0.5
                            ),
                            "public_health_stress": sub_indices_data.get(
                                "public_health_stress", 0.5
                            ),
                        }

            # Apply scenario adjustments if provided
            scenario_applied = False
            scenario_description = None
            if scenario and latest_sub_indices:
                adjusted_sub_indices = apply_scenario(latest_sub_indices, scenario)

                # Recompute behavior index with adjusted sub-indices
                adjusted_behavior_index = recompute_behavior_index_from_sub_indices(
                    adjusted_sub_indices
                )

                # Update the latest history entry with adjusted values
                # Note: We're modifying the dict in-place for scenario exploration
                if (
                    forecast_result.get("history")
                    and len(forecast_result["history"]) > 0
                ):
                    latest_history = forecast_result["history"][-1]
                    if isinstance(latest_history, dict):
                        latest_history["behavior_index"] = adjusted_behavior_index
                        if "sub_indices" in latest_history and isinstance(
                            latest_history["sub_indices"], dict
                        ):
                            for key, value in adjusted_sub_indices.items():
                                latest_history["sub_indices"][key] = value

                scenario_applied = True
                scenario_description = (
                    "Hypothetical what-if adjustment applied to sub-indices "
                    "for exploration purposes. This is not a forecast change "
                    "but a scenario exploration."
                )

            # Remove non-serializable DataFrames from metadata before returning
            # The _harmonized_df is used internally but should not be serialized
            if (
                "metadata" in forecast_result
                and "_harmonized_df" in forecast_result["metadata"]
            ):
                forecast_result["metadata"] = {
                    k: v
                    for k, v in forecast_result["metadata"].items()
                    if k != "_harmonized_df"
                }

            # Prepare result entry
            result_entry = {
                "region_id": region_id,
                "region_name": region.name,
                "forecast": forecast_result,
            }

            # Include explanations if requested
            if include_explanations and "explanations" in forecast_result:
                result_entry["explanations"] = forecast_result["explanations"]

            # Add scenario metadata if applied
            if scenario_applied:
                result_entry["scenario_applied"] = True
                result_entry["scenario_description"] = scenario_description

            results.append(result_entry)

        except Exception as e:
            logger.error(
                "Failed to generate forecast for region",
                region_id=region_id,
                error=str(e),
                exc_info=True,
            )
            errors.append(
                {
                    "region_id": region_id,
                    "error": str(e),
                }
            )

    return {
        "config": {
            "historical_days": historical_days,
            "forecast_horizon_days": forecast_horizon_days,
            "include_explanations": include_explanations,
            "scenario_applied": scenario is not None,
        },
        "results": results,
        "errors": errors,
    }
