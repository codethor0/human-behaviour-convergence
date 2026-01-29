# SPDX-License-Identifier: PROPRIETARY
"""Scenario sensitivity and counterfactual analysis.

This module computes factor elasticity (Δoutput / Δinput) and enables safe
what-if scenario analysis without changing numerical outputs.
"""
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger("core.scenario_sensitivity")


def calculate_factor_elasticity(
    base_behavior_index: float,
    perturbed_behavior_index: float,
    base_factor_value: float,
    perturbed_factor_value: float,
    factor_weight: float,
    tolerance: float = 1e-10,
) -> Dict[str, Any]:
    """
    Calculate factor elasticity (Δoutput / Δinput).

    Elasticity measures how sensitive the behavior index is to changes in a factor.

    Args:
        base_behavior_index: Base behavior index value
        perturbed_behavior_index: Behavior index after factor perturbation
        base_factor_value: Base factor value
        perturbed_factor_value: Perturbed factor value
        factor_weight: Weight of the factor in the aggregation
        tolerance: Numerical tolerance for zero detection

    Returns:
        Dictionary with:
        - elasticity: Elasticity value (Δoutput / Δinput)
        - output_delta: Change in behavior index
        - input_delta: Change in factor value
        - sensitivity_classification: "high", "medium", or "low"
        - is_non_linear: Whether response shows non-linearity
    """
    input_delta = perturbed_factor_value - base_factor_value
    output_delta = perturbed_behavior_index - base_behavior_index

    # Handle zero input delta
    if abs(input_delta) < tolerance:
        return {
            "elasticity": 0.0,
            "output_delta": float(output_delta),
            "input_delta": float(input_delta),
            "sensitivity_classification": "none",
            "is_non_linear": False,
        }

    # Calculate elasticity: Δoutput / Δinput
    # Normalize by factor weight to get true sensitivity
    if input_delta == 0:
        raise ValueError("input_delta cannot be zero for elasticity calculation")
    elasticity = (output_delta / input_delta) * factor_weight

    # Classify sensitivity
    abs_elasticity = abs(elasticity)
    if abs_elasticity > 0.5:
        sensitivity_classification = "high"
    elif abs_elasticity > 0.2:
        sensitivity_classification = "medium"
    else:
        sensitivity_classification = "low"

    # Detect non-linearity (simplified: large elasticity suggests non-linear response)
    # More sophisticated detection would require multiple perturbation points
    is_non_linear = abs_elasticity > 0.7

    return {
        "elasticity": float(elasticity),
        "output_delta": float(output_delta),
        "input_delta": float(input_delta),
        "sensitivity_classification": sensitivity_classification,
        "is_non_linear": is_non_linear,
    }


def compute_sensitivity_ranking(
    factor_elasticities: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Rank factors by sensitivity (elasticity magnitude).

    Args:
        factor_elasticities: Dictionary mapping factor IDs to elasticity dictionaries

    Returns:
        List of factor dictionaries sorted by absolute elasticity (descending)
    """
    rankings = []
    for factor_id, elasticity_data in factor_elasticities.items():
        rankings.append(
            {
                "factor_id": factor_id,
                "elasticity": elasticity_data.get("elasticity", 0.0),
                "sensitivity_classification": elasticity_data.get(
                    "sensitivity_classification", "low"
                ),
                "is_non_linear": elasticity_data.get("is_non_linear", False),
            }
        )

    # Sort by absolute elasticity (descending)
    rankings.sort(key=lambda x: abs(x["elasticity"]), reverse=True)
    return rankings


def detect_non_linear_threshold(
    factor_id: str,
    base_value: float,
    base_index: float,
    factor_weight: float,
    test_values: List[float],
    compute_behavior_index_fn: callable,
) -> Optional[Dict[str, Any]]:
    """
    Detect non-linear response threshold for a factor.

    Tests multiple perturbation values to identify where response becomes non-linear.

    Args:
        factor_id: Factor identifier
        base_value: Base factor value
        base_index: Base behavior index
        factor_weight: Factor weight
        test_values: List of test perturbation values
        compute_behavior_index_fn: Function to compute behavior index given factor values

    Returns:
        Dictionary with threshold information, or None if no threshold detected
    """
    elasticities = []
    for test_value in test_values:
        # Compute behavior index with perturbed factor
        perturbed_index = compute_behavior_index_fn({factor_id: test_value})
        elasticity_data = calculate_factor_elasticity(
            base_index,
            perturbed_index,
            base_value,
            test_value,
            factor_weight,
        )
        elasticities.append(
            {
                "value": test_value,
                "elasticity": elasticity_data["elasticity"],
            }
        )

    # Detect threshold: where elasticity changes significantly
    if len(elasticities) < 2:
        return None

    # Find point where elasticity changes by >50%
    for i in range(1, len(elasticities)):
        prev_elasticity = abs(elasticities[i - 1]["elasticity"])
        curr_elasticity = abs(elasticities[i]["elasticity"])

        if prev_elasticity > 0:
            change_ratio = abs(curr_elasticity - prev_elasticity) / prev_elasticity
            if change_ratio > 0.5:
                return {
                    "factor_id": factor_id,
                    "threshold_value": elasticities[i]["value"],
                    "threshold_elasticity": elasticities[i]["elasticity"],
                    "pre_threshold_elasticity": elasticities[i - 1]["elasticity"],
                }

    return None


def validate_scenario_bounds(
    factor_id: str,
    base_value: float,
    perturbation: float,
    min_value: float = 0.0,
    max_value: float = 1.0,
) -> Tuple[bool, Optional[str]]:
    """
    Validate that scenario perturbation is within safe bounds.

    Args:
        factor_id: Factor identifier
        base_value: Base factor value
        perturbation: Perturbation amount
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        Tuple of (is_valid, warning_message)
    """
    perturbed_value = base_value + perturbation

    if perturbed_value < min_value:
        return (
            False,
            f"Perturbation would result in {factor_id} < {min_value} (out of bounds)",
        )
    if perturbed_value > max_value:
        return (
            False,
            f"Perturbation would result in {factor_id} > {max_value} (out of bounds)",
        )

    # Warn on large perturbations (>50% absolute change or >50% relative change)
    if abs(perturbation) > 0.5:
        return (
            True,
            f"Large perturbation ({perturbation:.2f}) may produce unrealistic results",
        )
    elif base_value > 0:
        relative_change = abs(perturbation / base_value)
        if relative_change > 0.5:
            return (
                True,
                f"Large relative perturbation ({relative_change:.1%}) may produce unrealistic results",
            )

    return True, None


def generate_sensitivity_narrative(
    sensitivity_rankings: List[Dict[str, Any]],
    top_n: int = 3,
) -> str:
    """
    Generate narrative explanation of factor sensitivities.

    Args:
        sensitivity_rankings: Ranked list of factor sensitivities
        top_n: Number of top factors to highlight

    Returns:
        Narrative string explaining sensitivities
    """
    if not sensitivity_rankings:
        return "Sensitivity analysis unavailable."

    top_factors = sensitivity_rankings[:top_n]
    sentences = []

    if top_factors:
        factor_labels = [
            f.get("factor_id", "unknown").replace("_", " ").title() for f in top_factors
        ]
        sentences.append(f"The most sensitive factors are {', '.join(factor_labels)}.")

    # Highlight non-linear responses
    non_linear_factors = [f for f in top_factors if f.get("is_non_linear", False)]
    if non_linear_factors:
        sentences.append(
            f"{len(non_linear_factors)} factor(s) show non-linear responses, "
            "indicating that large changes may have disproportionate effects."
        )

    return " ".join(sentences) if sentences else "Sensitivity analysis complete."


def compose_sensitivity_analysis(
    base_behavior_index: float,
    factor_elasticities: Dict[str, Dict[str, Any]],
    sensitivity_rankings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Compose complete sensitivity analysis.

    Args:
        base_behavior_index: Base behavior index value
        factor_elasticities: Dictionary mapping factor IDs to elasticity data
        sensitivity_rankings: Pre-computed rankings (optional, will compute if None)

    Returns:
        Sensitivity analysis dictionary with:
        - base_behavior_index: Base behavior index
        - factor_elasticities: Factor elasticity data
        - sensitivity_rankings: Ranked factors by sensitivity
        - sensitivity_narrative: Narrative explanation
        - metadata: Analysis metadata
    """
    if sensitivity_rankings is None:
        sensitivity_rankings = compute_sensitivity_ranking(factor_elasticities)

    sensitivity_narrative = generate_sensitivity_narrative(sensitivity_rankings)

    return {
        "base_behavior_index": float(base_behavior_index),
        "factor_elasticities": factor_elasticities,
        "sensitivity_rankings": sensitivity_rankings,
        "sensitivity_narrative": sensitivity_narrative,
        "metadata": {
            "factors_analyzed": len(factor_elasticities),
            "high_sensitivity_count": sum(
                1
                for r in sensitivity_rankings
                if r.get("sensitivity_classification") == "high"
            ),
            "non_linear_count": sum(
                1 for r in sensitivity_rankings if r.get("is_non_linear", False)
            ),
        },
    }
