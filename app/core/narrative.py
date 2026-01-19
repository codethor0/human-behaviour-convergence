# SPDX-License-Identifier: PROPRIETARY
"""Narrative intelligence layer.

This module generates human-readable, decision-useful narratives from
structured traces and factor quality metrics without changing numerical outputs.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger("core.narrative")


def generate_primary_drivers(
    subindex_details: Dict[str, Dict[str, Any]],
    top_n: int = 3,
) -> List[Dict[str, Any]]:
    """
    Generate primary drivers ranked by signal strength × confidence × persistence.

    Args:
        subindex_details: Dictionary mapping sub-index names to their details
        top_n: Number of top drivers to return

    Returns:
        List of driver dictionaries with:
        - sub_index: Sub-index name
        - factor_id: Factor identifier
        - factor_label: Human-readable factor label
        - contribution: Factor contribution to sub-index
        - signal_strength: Signal strength score
        - confidence: Factor confidence
        - persistence: Days factor has persisted
    """
    drivers = []

    for sub_index_name, sub_index_data in subindex_details.items():
        if "components" not in sub_index_data:
            continue

        for factor in sub_index_data["components"]:
            # Extract quality metrics (may be missing for backward compatibility)
            signal_strength = factor.get("signal_strength", 0.0)
            confidence = factor.get("confidence", 0.5)
            persistence = factor.get("persistence", 0)
            contribution = factor.get("contribution", 0.0)

            # Skip factors with no meaningful contribution
            if abs(contribution) < 0.01:
                continue

            # Calculate driver score: signal_strength × confidence × (1 + persistence/30)
            # Persistence bonus: factors persisting >30 days get up to 2x multiplier
            persistence_multiplier = 1.0 + min(persistence / 30.0, 1.0)
            driver_score = signal_strength * confidence * persistence_multiplier

            drivers.append(
                {
                    "sub_index": sub_index_name,
                    "factor_id": factor.get("id", ""),
                    "factor_label": factor.get("label", factor.get("id", "")),
                    "contribution": contribution,
                    "signal_strength": signal_strength,
                    "confidence": confidence,
                    "persistence": persistence,
                    "driver_score": driver_score,
                }
            )

    # Sort by driver score (descending)
    drivers.sort(key=lambda x: x["driver_score"], reverse=True)

    return drivers[:top_n]


def generate_stabilizing_factors(
    subindex_details: Dict[str, Dict[str, Any]],
    behavior_index: float,
) -> List[Dict[str, Any]]:
    """
    Generate stabilizing factors (factors that reduce disruption/stress).

    Stabilizing factors are:
    - Factors with negative contribution to stress indices
    - OR factors with positive contribution to activity indices (mobility)
    - OR factors with improving trend

    Args:
        subindex_details: Dictionary mapping sub-index names to their details
        behavior_index: Current behavior index value

    Returns:
        List of stabilizing factor dictionaries
    """
    stabilizers = []

    # Activity indices reduce disruption when high
    activity_indices = {"mobility_activity"}

    for sub_index_name, sub_index_data in subindex_details.items():
        if "components" not in sub_index_data:
            continue

        is_activity_index = sub_index_name in activity_indices

        for factor in sub_index_data["components"]:
            contribution = factor.get("contribution", 0.0)
            trend = factor.get("trend", "stable")
            signal_strength = factor.get("signal_strength", 0.0)
            confidence = factor.get("confidence", 0.5)

            # Stabilizing conditions:
            # 1. Activity index with positive contribution
            # 2. Stress index with negative contribution (rare but possible)
            # 3. Improving trend
            is_stabilizing = False
            if is_activity_index and contribution > 0.01:
                is_stabilizing = True
            elif not is_activity_index and contribution < -0.01:
                is_stabilizing = True
            elif trend == "improving" and abs(contribution) > 0.01:
                is_stabilizing = True

            if is_stabilizing and signal_strength > 0.01:
                stabilizers.append(
                    {
                        "sub_index": sub_index_name,
                        "factor_id": factor.get("id", ""),
                        "factor_label": factor.get("label", factor.get("id", "")),
                        "contribution": contribution,
                        "signal_strength": signal_strength,
                        "confidence": confidence,
                        "trend": trend,
                    }
                )

    # Sort by signal strength (descending)
    stabilizers.sort(key=lambda x: x["signal_strength"], reverse=True)

    return stabilizers


def generate_emerging_risks(
    subindex_details: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Generate emerging risks (high volatility, low persistence, worsening trend).

    Emerging risks are factors that:
    - Have high volatility (medium or high)
    - Have low persistence (<14 days)
    - Show worsening trend
    - Have meaningful contribution

    Args:
        subindex_details: Dictionary mapping sub-index names to their details

    Returns:
        List of emerging risk dictionaries
    """
    emerging = []

    for sub_index_name, sub_index_data in subindex_details.items():
        if "components" not in sub_index_data:
            continue

        for factor in sub_index_data["components"]:
            contribution = factor.get("contribution", 0.0)
            volatility_classification = factor.get("volatility_classification", "low")
            persistence = factor.get("persistence", 0)
            trend = factor.get("trend", "stable")
            signal_strength = factor.get("signal_strength", 0.0)

            # Emerging risk criteria:
            # - High volatility (medium or high)
            # - Low persistence (<14 days)
            # - Worsening trend OR high contribution
            is_emerging = (
                volatility_classification in ["medium", "high"]
                and persistence < 14
                and (trend == "worsening" or abs(contribution) > 0.05)
                and signal_strength > 0.01
            )

            if is_emerging:
                emerging.append(
                    {
                        "sub_index": sub_index_name,
                        "factor_id": factor.get("id", ""),
                        "factor_label": factor.get("label", factor.get("id", "")),
                        "contribution": contribution,
                        "volatility_classification": volatility_classification,
                        "persistence": persistence,
                        "trend": trend,
                        "signal_strength": signal_strength,
                    }
                )

    # Sort by signal strength (descending)
    emerging.sort(key=lambda x: x["signal_strength"], reverse=True)

    return emerging


def generate_persistent_risks(
    subindex_details: Dict[str, Dict[str, Any]],
    min_persistence_days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Generate persistent risks (high persistence, stable or worsening).

    Persistent risks are factors that:
    - Have persisted for >= min_persistence_days
    - Show stable or worsening trend
    - Have meaningful contribution

    Args:
        subindex_details: Dictionary mapping sub-index names to their details
        min_persistence_days: Minimum days to be considered persistent

    Returns:
        List of persistent risk dictionaries
    """
    persistent = []

    for sub_index_name, sub_index_data in subindex_details.items():
        if "components" not in sub_index_data:
            continue

        for factor in sub_index_data["components"]:
            contribution = factor.get("contribution", 0.0)
            persistence = factor.get("persistence", 0)
            trend = factor.get("trend", "stable")
            signal_strength = factor.get("signal_strength", 0.0)

            # Persistent risk criteria:
            # - High persistence (>= min_persistence_days)
            # - Stable or worsening trend
            # - Meaningful contribution
            is_persistent = (
                persistence >= min_persistence_days
                and trend in ["stable", "worsening"]
                and abs(contribution) > 0.01
                and signal_strength > 0.01
            )

            if is_persistent:
                persistent.append(
                    {
                        "sub_index": sub_index_name,
                        "factor_id": factor.get("id", ""),
                        "factor_label": factor.get("label", factor.get("id", "")),
                        "contribution": contribution,
                        "persistence": persistence,
                        "trend": trend,
                        "signal_strength": signal_strength,
                    }
                )

    # Sort by persistence (descending), then signal strength
    persistent.sort(
        key=lambda x: (x["persistence"], x["signal_strength"]), reverse=True
    )

    return persistent


def generate_confidence_disclaimer(
    subindex_details: Dict[str, Dict[str, Any]],
    behavior_index: float,
) -> str:
    """
    Generate confidence disclaimer based on aggregate factor confidence and volatility.

    Args:
        subindex_details: Dictionary mapping sub-index names to their details
        behavior_index: Current behavior index value

    Returns:
        Confidence disclaimer string
    """
    all_confidences = []
    all_volatilities = []
    missing_data_count = 0
    total_factors = 0

    for sub_index_name, sub_index_data in subindex_details.items():
        if "components" not in sub_index_data:
            continue

        for factor in sub_index_data["components"]:
            total_factors += 1
            confidence = factor.get("confidence")
            volatility_classification = factor.get("volatility_classification", "low")

            if confidence is not None:
                all_confidences.append(confidence)
            else:
                missing_data_count += 1

            if volatility_classification == "high":
                all_volatilities.append(1.0)
            elif volatility_classification == "medium":
                all_volatilities.append(0.5)
            else:
                all_volatilities.append(0.0)

    if not all_confidences:
        return "Confidence assessment unavailable due to insufficient data quality metrics."

    avg_confidence = sum(all_confidences) / len(all_confidences)
    high_volatility_ratio = sum(1 for v in all_volatilities if v >= 0.5) / max(
        len(all_volatilities), 1
    )
    missing_data_ratio = missing_data_count / max(total_factors, 1)

    # Generate disclaimer based on aggregate metrics
    parts = []

    if avg_confidence >= 0.75:
        parts.append("Overall confidence in this assessment is high")
    elif avg_confidence >= 0.6:
        parts.append("Overall confidence in this assessment is moderate")
    else:
        parts.append("Overall confidence in this assessment is limited")

    if high_volatility_ratio > 0.3:
        parts.append(
            f"due to high variability in {int(high_volatility_ratio * 100)}% of factors"
        )

    if missing_data_ratio > 0.2:
        parts.append(
            f"and missing data quality metrics for {int(missing_data_ratio * 100)}% of factors"
        )

    if not parts:
        return "Confidence assessment is moderate."

    disclaimer = ", ".join(parts) + "."
    return disclaimer


def generate_assessment_summary(
    behavior_index: float,
    primary_drivers: List[Dict[str, Any]],
    stabilizing_factors: List[Dict[str, Any]],
    emerging_risks: List[Dict[str, Any]],
    persistent_risks: List[Dict[str, Any]],
    confidence_disclaimer: str,
) -> str:
    """
    Generate executive assessment summary synthesizing all narrative components.

    Args:
        behavior_index: Current behavior index value
        primary_drivers: List of primary driver dictionaries
        stabilizing_factors: List of stabilizing factor dictionaries
        emerging_risks: List of emerging risk dictionaries
        persistent_risks: List of persistent risk dictionaries
        confidence_disclaimer: Confidence disclaimer string

    Returns:
        Assessment summary string (3-5 sentences)
    """
    # Classify behavior index level
    if behavior_index < 0.3:
        level = "low disruption"
    elif behavior_index < 0.5:
        level = "moderate disruption"
    elif behavior_index < 0.7:
        level = "elevated disruption"
    else:
        level = "high disruption"

    sentences = []

    # Opening sentence: overall assessment
    sentences.append(
        f"The region shows {level} driven primarily by "
        + (
            ", ".join([d["factor_label"] for d in primary_drivers[:2]])
            if primary_drivers
            else "multiple contributing factors"
        )
        + "."
    )

    # Stabilizing factors
    if stabilizing_factors:
        stabilizer_labels = [s["factor_label"] for s in stabilizing_factors[:2]]
        sentences.append(
            f"{stabilizer_labels[0] if len(stabilizer_labels) == 1 else ' and '.join(stabilizer_labels)} "
            + ("remain" if len(stabilizer_labels) == 1 else "remain")
            + " stable and are acting as a dampening force."
        )

    # Emerging vs persistent risks
    if emerging_risks and persistent_risks:
        sentences.append(
            f"While {emerging_risks[0]['factor_label']} shows emerging volatility, "
            f"several risk factors have persisted for over {persistent_risks[0]['persistence']} days, "
            "indicating structural rather than transient pressure."
        )
    elif persistent_risks:
        sentences.append(
            f"Several risk factors have persisted for over {persistent_risks[0]['persistence']} days, "
            "indicating structural rather than transient pressure."
        )
    elif emerging_risks:
        sentences.append(
            f"{emerging_risks[0]['factor_label']} shows emerging volatility, "
            "suggesting recent changes rather than established patterns."
        )

    # Confidence disclaimer (condensed)
    if "high" in confidence_disclaimer.lower():
        sentences.append("Overall confidence in this assessment is high.")
    elif "limited" in confidence_disclaimer.lower():
        sentences.append("Confidence is limited due to data quality considerations.")

    # Join sentences
    summary = " ".join(sentences)
    return summary


def compose_narrative(
    behavior_index: float,
    subindex_details: Dict[str, Dict[str, Any]],
    top_drivers: int = 3,
    min_persistence_days: int = 30,
) -> Dict[str, Any]:
    """
    Compose complete narrative from behavior index and sub-index details.

    Args:
        behavior_index: Current behavior index value
        subindex_details: Dictionary mapping sub-index names to their details
        top_drivers: Number of top drivers to include
        min_persistence_days: Minimum days for persistent risks

    Returns:
        Narrative dictionary with:
        - assessment_summary: Executive summary (string)
        - primary_drivers: List of primary driver dictionaries
        - stabilizing_factors: List of stabilizing factor dictionaries
        - emerging_risks: List of emerging risk dictionaries
        - persistent_risks: List of persistent risk dictionaries
        - confidence_disclaimer: Confidence disclaimer (string)
        - metadata: Generation metadata
    """
    # Generate all narrative components
    primary_drivers = generate_primary_drivers(subindex_details, top_n=top_drivers)
    stabilizing_factors = generate_stabilizing_factors(subindex_details, behavior_index)
    emerging_risks = generate_emerging_risks(subindex_details)
    persistent_risks = generate_persistent_risks(subindex_details, min_persistence_days)
    confidence_disclaimer = generate_confidence_disclaimer(
        subindex_details, behavior_index
    )
    assessment_summary = generate_assessment_summary(
        behavior_index,
        primary_drivers,
        stabilizing_factors,
        emerging_risks,
        persistent_risks,
        confidence_disclaimer,
    )

    return {
        "assessment_summary": assessment_summary,
        "primary_drivers": primary_drivers,
        "stabilizing_factors": stabilizing_factors,
        "emerging_risks": emerging_risks,
        "persistent_risks": persistent_risks,
        "confidence_disclaimer": confidence_disclaimer,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "top_drivers_count": top_drivers,
            "min_persistence_days": min_persistence_days,
        },
    }
