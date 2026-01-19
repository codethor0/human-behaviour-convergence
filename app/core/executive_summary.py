# SPDX-License-Identifier: PROPRIETARY
"""Executive summary and decision consumption layer.

This module generates executive-grade summaries from existing analytics outputs
without changing any numerical computations. All summaries are deterministic,
fully derivable, and traceable to underlying data.

Zero numerical drift is a HARD invariant.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger("core.executive_summary")


def compose_current_status(
    behavior_index: float,
    risk_tier: str,
    region_name: str,
) -> str:
    """
    Compose current status sentence.

    Args:
        behavior_index: Current behavior index value
        risk_tier: Risk tier classification
        region_name: Region name

    Returns:
        One-sentence status summary
    """
    # Classify behavior index level
    if behavior_index < 0.3:
        level = "low"
    elif behavior_index < 0.5:
        level = "moderate"
    elif behavior_index < 0.7:
        level = "elevated"
    else:
        level = "high"

    tier_label = risk_tier.replace("_", " ").title()

    return f"{region_name} shows {level} behavioral disruption ({behavior_index:.2f}) with {tier_label} risk classification."


def compose_primary_drivers_summary(
    primary_drivers: List[Dict[str, Any]],
    max_drivers: int = 3,
) -> List[Dict[str, Any]]:
    """
    Compose primary drivers summary from narrative drivers.

    Args:
        primary_drivers: List of driver dictionaries from narrative module
        max_drivers: Maximum number of drivers to include

    Returns:
        List of driver summaries with:
        - factor_label: Human-readable factor name
        - sub_index: Sub-index name
        - contribution: Contribution value
        - signal_strength: Signal strength classification
    """
    drivers = []
    for driver in primary_drivers[:max_drivers]:
        signal_strength = driver.get("signal_strength", 0.0)
        if signal_strength > 0.7:
            strength_label = "strong"
        elif signal_strength > 0.4:
            strength_label = "moderate"
        else:
            strength_label = "weak"

        drivers.append(
            {
                "factor_label": driver.get(
                    "factor_label", driver.get("factor_id", "Unknown")
                ),
                "sub_index": driver.get("sub_index", "unknown"),
                "contribution": driver.get("contribution", 0.0),
                "signal_strength": strength_label,
                "confidence": driver.get("confidence", 0.5),
            }
        )

    return drivers


def compose_change_summary(
    temporal_attribution: Optional[Dict[str, Any]],
    behavior_index: float,
    previous_behavior_index: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compose change summary since last period.

    Args:
        temporal_attribution: Temporal attribution dictionary
        behavior_index: Current behavior index
        previous_behavior_index: Previous behavior index (if available)

    Returns:
        Dictionary with:
        - direction: "increasing", "decreasing", or "stable"
        - magnitude: Change magnitude
        - magnitude_label: "significant", "moderate", or "minor"
        - primary_driver: Primary driver of change (if available)
    """
    if temporal_attribution:
        global_delta = temporal_attribution.get("global_delta", {})
        delta_value = global_delta.get("delta_value", 0.0)
        direction = global_delta.get("direction", "stable")

        # Get primary change driver
        primary_drivers = temporal_attribution.get("primary_drivers", [])
        primary_driver = None
        if primary_drivers:
            primary_driver = primary_drivers[0].get("factor_id", None)

    elif previous_behavior_index is not None:
        delta_value = behavior_index - previous_behavior_index
        if abs(delta_value) < 0.01:
            direction = "stable"
        elif delta_value > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        primary_driver = None
    else:
        delta_value = 0.0
        direction = "stable"
        primary_driver = None

    # Classify magnitude
    abs_delta = abs(delta_value)
    if abs_delta > 0.1:
        magnitude_label = "significant"
    elif abs_delta > 0.05:
        magnitude_label = "moderate"
    else:
        magnitude_label = "minor"

    return {
        "direction": direction,
        "magnitude": float(delta_value),
        "magnitude_label": magnitude_label,
        "primary_driver": primary_driver,
    }


def compose_risk_confidence_posture(
    risk_tier: str,
    forecast_confidence: Optional[float],
    provenance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compose risk and confidence posture.

    Args:
        risk_tier: Risk tier classification
        forecast_confidence: Forecast confidence score (0.0-1.0)
        provenance: Provenance dictionary (optional)

    Returns:
        Dictionary with:
        - risk_tier: Risk tier
        - confidence_level: "high", "medium", or "low"
        - confidence_score: Confidence score
        - data_quality: "high", "moderate", or "low" (from provenance)
    """
    # Classify confidence
    if forecast_confidence is None:
        confidence_level = "unknown"
        confidence_score = None
    elif forecast_confidence >= 0.7:
        confidence_level = "high"
        confidence_score = forecast_confidence
    elif forecast_confidence >= 0.5:
        confidence_level = "medium"
        confidence_score = forecast_confidence
    else:
        confidence_level = "low"
        confidence_score = forecast_confidence

    # Get data quality from provenance
    data_quality = "unknown"
    if provenance:
        aggregate_prov = provenance.get("aggregate_provenance", {})
        coverage_classification = aggregate_prov.get(
            "aggregate_coverage_classification", "unknown"
        )
        data_quality = coverage_classification

    return {
        "risk_tier": risk_tier,
        "confidence_level": confidence_level,
        "confidence_score": confidence_score,
        "data_quality": data_quality,
    }


def compose_action_recommendation(
    alerts: Optional[Dict[str, Any]],
    risk_tier: str,
    behavior_index: float,
) -> Dict[str, Any]:
    """
    Compose action recommendation derived from alerts and risk.

    Args:
        alerts: Alert analysis dictionary
        risk_tier: Risk tier classification
        behavior_index: Current behavior index

    Returns:
        Dictionary with:
        - recommendation: "immediate_action", "watch", or "monitor"
        - urgency: "high", "medium", or "low"
        - rationale: Brief explanation
        - alert_count: Number of active alerts
    """
    alert_count = 0
    high_severity_alerts = 0

    if alerts:
        alert_count = alerts.get("alert_count", 0)
        alert_list = alerts.get("alerts", [])
        high_severity_alerts = sum(1 for a in alert_list if a.get("severity") == "high")

    # Determine recommendation
    if high_severity_alerts > 0 or risk_tier in ["high", "critical"]:
        recommendation = "immediate_action"
        urgency = "high"
        rationale = f"{high_severity_alerts} high-severity alert(s) and {risk_tier} risk tier indicate immediate attention required."
    elif alert_count > 0 or risk_tier == "elevated":
        recommendation = "watch"
        urgency = "medium"
        rationale = f"{alert_count} alert(s) and {risk_tier} risk tier suggest close monitoring."
    else:
        recommendation = "monitor"
        urgency = "low"
        rationale = "Current indicators suggest routine monitoring is sufficient."

    return {
        "recommendation": recommendation,
        "urgency": urgency,
        "rationale": rationale,
        "alert_count": alert_count,
        "high_severity_alerts": high_severity_alerts,
    }


def compose_why_should_i_care(
    behavior_index: float,
    benchmarks: Optional[Dict[str, Any]],
    temporal_attribution: Optional[Dict[str, Any]],
    alerts: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compose "Why Should I Care?" panel.

    Args:
        behavior_index: Current behavior index
        benchmarks: Benchmark analysis dictionary
        temporal_attribution: Temporal attribution dictionary
        alerts: Alert analysis dictionary

    Returns:
        Dictionary with:
        - why_matters: Why this matters now
        - unusual_vs_baseline: What is unusual vs baseline
        - persistent_vs_noise: What is persistent vs noise
        - urgency_assessment: Urgency assessment
    """
    # Why matters now
    why_matters_parts = []
    if alerts and alerts.get("alert_count", 0) > 0:
        why_matters_parts.append(
            f"{alerts['alert_count']} active alert(s) require attention"
        )
    if behavior_index > 0.7:
        why_matters_parts.append("behavioral disruption is elevated")
    elif behavior_index < 0.3:
        why_matters_parts.append("behavioral patterns are stable")

    why_matters = (
        " ".join(why_matters_parts)
        if why_matters_parts
        else "Current indicators suggest routine monitoring"
    )

    # Unusual vs baseline
    unusual_vs_baseline = "No baseline comparison available"
    if benchmarks:
        deviation = benchmarks.get("baseline_deviation", {})
        deviation_classification = deviation.get("classification", "unknown")
        if deviation_classification == "anomalous":
            unusual_vs_baseline = (
                "Current values are anomalous compared to historical baseline"
            )
        elif deviation_classification == "elevated":
            unusual_vs_baseline = (
                "Current values are elevated compared to historical baseline"
            )
        else:
            unusual_vs_baseline = (
                "Current values are within normal range compared to baseline"
            )

    # Persistent vs noise
    persistent_vs_noise = "Change classification unavailable"
    if temporal_attribution:
        signal_vs_noise = temporal_attribution.get("signal_vs_noise", {})
        global_classification = signal_vs_noise.get("global_classification", "unknown")
        if global_classification == "signal":
            persistent_vs_noise = (
                "Recent changes appear to be persistent signal, not noise"
            )
        elif global_classification == "noise":
            persistent_vs_noise = "Recent changes appear to be transient noise"
        else:
            persistent_vs_noise = "Change classification is mixed or uncertain"

    # Urgency assessment
    urgency_assessment = "monitor"
    if alerts and alerts.get("alert_count", 0) > 0:
        high_severity = sum(
            1 for a in alerts.get("alerts", []) if a.get("severity") == "high"
        )
        if high_severity > 0:
            urgency_assessment = "urgent"
        else:
            urgency_assessment = "watch"
    elif behavior_index > 0.7:
        urgency_assessment = "watch"

    return {
        "why_matters": why_matters,
        "unusual_vs_baseline": unusual_vs_baseline,
        "persistent_vs_noise": persistent_vs_noise,
        "urgency_assessment": urgency_assessment,
    }


def compose_executive_summary(
    behavior_index: float,
    risk_tier: str,
    region_name: str,
    forecast_confidence: Optional[float] = None,
    narrative: Optional[Dict[str, Any]] = None,
    temporal_attribution: Optional[Dict[str, Any]] = None,
    alerts: Optional[Dict[str, Any]] = None,
    benchmarks: Optional[Dict[str, Any]] = None,
    provenance: Optional[Dict[str, Any]] = None,
    previous_behavior_index: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compose complete executive summary from existing analytics outputs.

    This function is purely derived - it does not change any numerical outputs.

    Args:
        behavior_index: Current behavior index value
        risk_tier: Risk tier classification
        region_name: Region name
        forecast_confidence: Forecast confidence score (optional)
        narrative: Narrative dictionary (optional)
        temporal_attribution: Temporal attribution dictionary (optional)
        alerts: Alert analysis dictionary (optional)
        benchmarks: Benchmark analysis dictionary (optional)
        provenance: Provenance dictionary (optional)
        previous_behavior_index: Previous behavior index (optional)

    Returns:
        Dictionary with:
        - current_status: One-sentence status summary
        - primary_drivers: Top 3 primary drivers
        - change_summary: Change since last period
        - risk_confidence_posture: Risk and confidence posture
        - action_recommendation: Action recommendation
        - why_should_i_care: "Why Should I Care?" panel
        - metadata: Generation metadata
    """
    # Compose current status
    current_status = compose_current_status(behavior_index, risk_tier, region_name)

    # Compose primary drivers
    primary_drivers = []
    if narrative:
        narrative_drivers = narrative.get("primary_drivers", [])
        primary_drivers = compose_primary_drivers_summary(
            narrative_drivers, max_drivers=3
        )

    # Compose change summary
    change_summary = compose_change_summary(
        temporal_attribution,
        behavior_index,
        previous_behavior_index,
    )

    # Compose risk/confidence posture
    risk_confidence_posture = compose_risk_confidence_posture(
        risk_tier,
        forecast_confidence,
        provenance,
    )

    # Compose action recommendation
    action_recommendation = compose_action_recommendation(
        alerts, risk_tier, behavior_index
    )

    # Compose "Why Should I Care?"
    why_should_i_care = compose_why_should_i_care(
        behavior_index,
        benchmarks,
        temporal_attribution,
        alerts,
    )

    return {
        "current_status": current_status,
        "primary_drivers": primary_drivers,
        "change_summary": change_summary,
        "risk_confidence_posture": risk_confidence_posture,
        "action_recommendation": action_recommendation,
        "why_should_i_care": why_should_i_care,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "behavior_index": float(behavior_index),
            "risk_tier": risk_tier,
            "region_name": region_name,
        },
    }


def compose_brief_export(
    executive_summary: Dict[str, Any],
    region_name: str,
    data_timestamp: Optional[str] = None,
    data_window_days: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compose board/brief export snapshot.

    This is a read-only snapshot suitable for PDF export, email brief, or offline review.

    Args:
        executive_summary: Executive summary dictionary
        region_name: Region name
        data_timestamp: Data timestamp (optional)
        data_window_days: Data window in days (optional)

    Returns:
        Dictionary with:
        - timestamp: Export timestamp
        - region_name: Region name
        - data_timestamp: Data timestamp
        - data_window_days: Data window
        - executive_summary: Executive summary
        - export_format: "brief"
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "region_name": region_name,
        "data_timestamp": data_timestamp,
        "data_window_days": data_window_days,
        "executive_summary": executive_summary,
        "export_format": "brief",
    }
