# SPDX-License-Identifier: PROPRIETARY
"""Temporal attribution and change explanation.

This module explains why values changed over time by attributing changes
to factor-level deltas, sub-index changes, and distinguishing signal vs noise.
"""
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger("core.temporal_attribution")


def calculate_factor_delta(
    current_value: float,
    previous_value: Optional[float],
    current_weight: float,
    previous_weight: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate factor-level delta and contribution change.

    Args:
        current_value: Current factor value
        previous_value: Previous factor value (None if not available)
        current_weight: Current factor weight
        previous_weight: Previous factor weight (None if not available)

    Returns:
        Dictionary with:
        - value_delta: Change in factor value
        - contribution_delta: Change in factor contribution
        - has_change: Whether change is meaningful
    """
    if previous_value is None:
        return {
            "value_delta": 0.0,
            "contribution_delta": 0.0,
            "has_change": False,
            "previous_value": None,
            "previous_weight": previous_weight,
        }

    if previous_weight is None:
        previous_weight = current_weight

    value_delta = current_value - previous_value
    current_contribution = current_value * current_weight
    previous_contribution = previous_value * previous_weight
    contribution_delta = current_contribution - previous_contribution

    # Change is meaningful if delta exceeds threshold
    has_change = abs(contribution_delta) >= 0.01

    return {
        "value_delta": float(value_delta),
        "contribution_delta": float(contribution_delta),
        "has_change": has_change,
        "previous_value": float(previous_value),
        "previous_weight": float(previous_weight),
    }


def calculate_sub_index_delta(
    current_value: float,
    previous_value: Optional[float],
) -> Dict[str, Any]:
    """
    Calculate sub-index level delta.

    Args:
        current_value: Current sub-index value
        previous_value: Previous sub-index value (None if not available)

    Returns:
        Dictionary with:
        - delta: Change in sub-index value
        - delta_percent: Percentage change
        - has_change: Whether change is meaningful
        - direction: "increasing", "decreasing", or "stable"
    """
    if previous_value is None:
        return {
            "delta": 0.0,
            "delta_percent": 0.0,
            "has_change": False,
            "direction": "stable",
            "previous_value": None,
        }

    delta = current_value - previous_value
    delta_percent = (
        (delta / previous_value * 100.0) if abs(previous_value) > 1e-10 else 0.0
    )

    # Change is meaningful if delta exceeds threshold
    has_change = abs(delta) >= 0.01

    if delta > 0.01:
        direction = "increasing"
    elif delta < -0.01:
        direction = "decreasing"
    else:
        direction = "stable"

    return {
        "delta": float(delta),
        "delta_percent": float(delta_percent),
        "has_change": has_change,
        "direction": direction,
        "previous_value": float(previous_value),
    }


def calculate_global_index_delta(
    current_index: float,
    previous_index: Optional[float],
) -> Dict[str, Any]:
    """
    Calculate global behavior index delta.

    Args:
        current_index: Current behavior index value
        previous_index: Previous behavior index value (None if not available)

    Returns:
        Dictionary with delta information
    """
    return calculate_sub_index_delta(current_index, previous_index)


def attribute_factor_changes(
    current_details: Dict[str, Dict[str, Any]],
    previous_details: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Attribute factor-level changes for each sub-index.

    Args:
        current_details: Current sub-index details with factors
        previous_details: Previous sub-index details (None if not available)

    Returns:
        Dictionary mapping sub-index names to lists of factor change dictionaries
    """
    factor_changes = {}

    for sub_index_name, sub_index_data in current_details.items():
        if "components" not in sub_index_data:
            continue

        changes = []
        previous_factors = {}
        if previous_details and sub_index_name in previous_details:
            previous_sub_index = previous_details[sub_index_name]
            if "components" in previous_sub_index:
                # Build lookup by factor ID
                for factor in previous_sub_index["components"]:
                    factor_id = factor.get("id")
                    if factor_id:
                        previous_factors[factor_id] = factor

        for factor in sub_index_data["components"]:
            factor_id = factor.get("id")
            if not factor_id:
                continue

            current_value = factor.get("value", 0.0)
            current_weight = factor.get("weight", 0.0)

            previous_factor = previous_factors.get(factor_id)
            previous_value = previous_factor.get("value") if previous_factor else None
            previous_weight = previous_factor.get("weight") if previous_factor else None

            delta_info = calculate_factor_delta(
                current_value, previous_value, current_weight, previous_weight
            )

            if delta_info["has_change"]:
                changes.append(
                    {
                        "factor_id": factor_id,
                        "factor_label": factor.get("label", factor_id),
                        "sub_index": sub_index_name,
                        "current_value": current_value,
                        "current_contribution": factor.get("contribution", 0.0),
                        "value_delta": delta_info["value_delta"],
                        "contribution_delta": delta_info["contribution_delta"],
                        "previous_value": delta_info["previous_value"],
                    }
                )

        # Sort by absolute contribution delta (descending)
        changes.sort(key=lambda x: abs(x["contribution_delta"]), reverse=True)
        factor_changes[sub_index_name] = changes

    return factor_changes


def attribute_sub_index_changes(
    current_details: Dict[str, Dict[str, Any]],
    previous_details: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Attribute sub-index level changes.

    Args:
        current_details: Current sub-index details
        previous_details: Previous sub-index details (None if not available)

    Returns:
        Dictionary mapping sub-index names to change dictionaries
    """
    sub_index_changes = {}

    for sub_index_name, sub_index_data in current_details.items():
        current_value = sub_index_data.get("value", 0.0)

        previous_value = None
        if previous_details and sub_index_name in previous_details:
            previous_value = previous_details[sub_index_name].get("value")

        delta_info = calculate_sub_index_delta(current_value, previous_value)

        if delta_info["has_change"]:
            sub_index_changes[sub_index_name] = {
                "sub_index": sub_index_name,
                "current_value": current_value,
                "delta": delta_info["delta"],
                "delta_percent": delta_info["delta_percent"],
                "direction": delta_info["direction"],
                "previous_value": delta_info["previous_value"],
            }

    return sub_index_changes


def classify_change_signal_vs_noise(
    factor_change: Dict[str, Any],
    factor_quality: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Classify whether a factor change is signal or noise.

    Args:
        factor_change: Factor change dictionary
        factor_quality: Factor quality metrics (optional)

    Returns:
        "signal" or "noise"
    """
    contribution_delta = abs(factor_change.get("contribution_delta", 0.0))

    # Large changes are always signal
    if contribution_delta > 0.05:
        return "signal"

    # Small changes with high volatility are noise
    if factor_quality:
        volatility_classification = factor_quality.get(
            "volatility_classification", "low"
        )
        confidence = factor_quality.get("confidence", 0.5)

        if volatility_classification == "high" and contribution_delta < 0.02:
            return "noise"
        if confidence < 0.5 and contribution_delta < 0.02:
            return "noise"

    # Default: small changes are noise, medium+ are signal
    if contribution_delta < 0.01:
        return "noise"

    return "signal"


def generate_change_narrative(
    global_delta: Dict[str, Any],
    sub_index_changes: Dict[str, Dict[str, Any]],
    factor_changes: Dict[str, List[Dict[str, Any]]],
    time_window_days: int = 7,
) -> str:
    """
    Generate narrative explanation of changes.

    Args:
        global_delta: Global behavior index delta information
        sub_index_changes: Sub-index change dictionaries
        factor_changes: Factor change dictionaries per sub-index
        time_window_days: Time window for comparison

    Returns:
        Narrative string explaining changes
    """
    if not global_delta.get("has_change"):
        return f"No significant change detected over the past {time_window_days} days."

    direction = global_delta.get("direction", "stable")
    delta = global_delta.get("delta", 0.0)

    sentences = []

    # Opening: overall change
    if direction == "increasing":
        sentences.append(
            f"Behavior index increased by {delta:.3f} over the past {time_window_days} days."
        )
    elif direction == "decreasing":
        sentences.append(
            f"Behavior index decreased by {abs(delta):.3f} over the past {time_window_days} days."
        )

    # Top contributing sub-index changes
    sorted_sub_indices = sorted(
        sub_index_changes.items(),
        key=lambda x: abs(x[1].get("delta", 0.0)),
        reverse=True,
    )

    if sorted_sub_indices:
        top_sub_index_name, top_sub_index_change = sorted_sub_indices[0]
        top_delta = top_sub_index_change.get("delta", 0.0)
        top_direction = top_sub_index_change.get("direction", "stable")

        sub_index_label = top_sub_index_name.replace("_", " ").title()
        if top_direction == "increasing":
            sentences.append(
                f"The largest contributor was {sub_index_label}, which increased by {top_delta:.3f}."
            )
        elif top_direction == "decreasing":
            sentences.append(
                f"The largest contributor was {sub_index_label}, which decreased by {abs(top_delta):.3f}."
            )

    # Top factor changes
    all_factor_changes = []
    for sub_index_name, changes in factor_changes.items():
        for change in changes:
            all_factor_changes.append(change)

    if all_factor_changes:
        top_factor = max(
            all_factor_changes, key=lambda x: abs(x.get("contribution_delta", 0.0))
        )
        factor_label = top_factor.get("factor_label", "")
        factor_delta = top_factor.get("contribution_delta", 0.0)

        if abs(factor_delta) > 0.01:
            if factor_delta > 0:
                sentences.append(
                    f"At the factor level, {factor_label} contributed an increase of {factor_delta:.3f}."
                )
            else:
                sentences.append(
                    f"At the factor level, {factor_label} contributed a decrease of {abs(factor_delta):.3f}."
                )

    return " ".join(sentences)


def compose_temporal_attribution(
    current_behavior_index: float,
    current_details: Dict[str, Dict[str, Any]],
    previous_behavior_index: Optional[float] = None,
    previous_details: Optional[Dict[str, Dict[str, Any]]] = None,
    time_window_days: int = 7,
) -> Dict[str, Any]:
    """
    Compose complete temporal attribution from current and previous states.

    Args:
        current_behavior_index: Current behavior index value
        current_details: Current sub-index details with factors
        previous_behavior_index: Previous behavior index value (None if not available)
        previous_details: Previous sub-index details (None if not available)
        time_window_days: Time window for comparison

    Returns:
        Temporal attribution dictionary with:
        - global_delta: Global index change information
        - sub_index_deltas: Sub-index change dictionaries
        - factor_deltas: Factor change dictionaries per sub-index
        - change_narrative: Narrative explanation of changes
        - signal_vs_noise: Classification per factor change
        - metadata: Attribution metadata
    """
    # Calculate global delta
    global_delta = calculate_global_index_delta(
        current_behavior_index, previous_behavior_index
    )

    # Attribute sub-index changes
    sub_index_deltas = attribute_sub_index_changes(current_details, previous_details)

    # Attribute factor changes
    factor_deltas = attribute_factor_changes(current_details, previous_details)

    # Classify signal vs noise for factor changes
    signal_vs_noise = {}
    for sub_index_name, changes in factor_deltas.items():
        signal_vs_noise[sub_index_name] = []
        for change in changes:
            # Get factor quality from current details
            factor_id = change["factor_id"]
            factor_quality = None
            if sub_index_name in current_details:
                for factor in current_details[sub_index_name].get("components", []):
                    if factor.get("id") == factor_id:
                        factor_quality = {
                            "volatility_classification": factor.get(
                                "volatility_classification"
                            ),
                            "confidence": factor.get("confidence"),
                        }
                        break

            classification = classify_change_signal_vs_noise(change, factor_quality)
            signal_vs_noise[sub_index_name].append(
                {
                    "factor_id": factor_id,
                    "classification": classification,
                }
            )

    # Generate change narrative
    change_narrative = generate_change_narrative(
        global_delta, sub_index_deltas, factor_deltas, time_window_days
    )

    return {
        "global_delta": global_delta,
        "sub_index_deltas": sub_index_deltas,
        "factor_deltas": factor_deltas,
        "signal_vs_noise": signal_vs_noise,
        "change_narrative": change_narrative,
        "metadata": {
            "time_window_days": time_window_days,
            "has_previous_data": previous_behavior_index is not None,
        },
    }
