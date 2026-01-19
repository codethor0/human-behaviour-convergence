# SPDX-License-Identifier: PROPRIETARY
"""Early warning and advanced intelligence.

This module provides:
- Change acceleration detection (rate-of-change increases)
- Early warning indicators (pre-alert warnings)
- Cross-factor interaction effects
- Confidence-weighted foresight

All outputs are derived from existing signals only.
Zero numerical drift is a HARD invariant.
"""
import math
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger("core.early_warning")


def detect_change_acceleration(
    values: List[float],
    window_size: int = 7,
    acceleration_threshold: float = 0.1,
) -> Dict[str, Any]:
    """
    Detect acceleration in rate of change.

    Acceleration is defined as: rate_of_change(t) > rate_of_change(t-1) + threshold

    Args:
        values: Time series values (most recent last)
        window_size: Window size for rate-of-change calculation
        acceleration_threshold: Minimum acceleration to flag

    Returns:
        Dictionary with:
        - detected: bool
        - acceleration_rate: float
        - current_rate: float
        - previous_rate: float
        - confidence: float [0.0, 1.0]
    """
    if len(values) < window_size * 2:
        return {
            "detected": False,
            "acceleration_rate": 0.0,
            "current_rate": 0.0,
            "previous_rate": 0.0,
            "confidence": 0.0,
            "reason": "Insufficient data",
        }

    # Calculate rate of change for recent window
    recent_window = values[-window_size:]
    previous_window = values[-window_size * 2 : -window_size]

    if len(recent_window) < 2 or len(previous_window) < 2:
        return {
            "detected": False,
            "acceleration_rate": 0.0,
            "current_rate": 0.0,
            "previous_rate": 0.0,
            "confidence": 0.0,
            "reason": "Insufficient window data",
        }

    # Calculate average rate of change (slope)
    def calculate_slope(window: List[float]) -> float:
        if len(window) < 2:
            return 0.0
        # Simple linear regression slope
        n = len(window)
        x_mean = (n - 1) / 2.0
        y_mean = sum(window) / n

        numerator = sum((i - x_mean) * (window[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if abs(denominator) < 1e-10:
            return 0.0

        return numerator / denominator

    current_rate = calculate_slope(recent_window)
    previous_rate = calculate_slope(previous_window)

    # Acceleration is the change in rate of change
    # Positive acceleration means rate is increasing
    acceleration_rate = current_rate - previous_rate

    # Normalize by window size to get per-time-step acceleration
    acceleration_rate = acceleration_rate / window_size

    # Confidence based on data stability
    recent_std = (
        math.sqrt(
            sum(
                (x - sum(recent_window) / len(recent_window)) ** 2
                for x in recent_window
            )
            / len(recent_window)
        )
        if recent_window
        else 0.0
    )
    previous_std = (
        math.sqrt(
            sum(
                (x - sum(previous_window) / len(previous_window)) ** 2
                for x in previous_window
            )
            / len(previous_window)
        )
        if previous_window
        else 0.0
    )

    # Higher confidence if acceleration is large relative to noise
    noise_level = max(recent_std, previous_std, 0.01)
    confidence = min(abs(acceleration_rate) / max(noise_level, 0.01), 1.0)

    detected = acceleration_rate > acceleration_threshold

    return {
        "detected": detected,
        "acceleration_rate": acceleration_rate,
        "current_rate": current_rate,
        "previous_rate": previous_rate,
        "confidence": confidence,
        "reason": "Acceleration detected" if detected else "No acceleration",
    }


def compose_early_warning_indicators(
    behavior_index_history: List[float],
    temporal_attribution: Optional[Dict[str, Any]] = None,
    sensitivity_analysis: Optional[Dict[str, Any]] = None,
    alerts: Optional[Dict[str, Any]] = None,
    benchmarks: Optional[Dict[str, Any]] = None,
    factor_quality: Optional[Dict[str, Any]] = None,
    min_confidence: float = 0.6,
) -> Dict[str, Any]:
    """
    Compose early warning indicators from multiple signals.

    Early warnings are pre-alert signals that indicate potential risk
    but don't yet meet alert thresholds.

    Args:
        behavior_index_history: Historical behavior index values
        temporal_attribution: Temporal attribution analysis (from N+28)
        sensitivity_analysis: Sensitivity analysis (from N+29)
        alerts: Alert analysis (from N+30)
        benchmarks: Benchmark analysis (from N+31)
        factor_quality: Factor quality metrics (from N+26)
        min_confidence: Minimum confidence threshold for early warnings

    Returns:
        Dictionary with:
        - warnings: List of early warning objects
        - warning_count: int
        - metadata: Dict
    """
    warnings = []

    # 1. Acceleration-based warnings
    if len(behavior_index_history) >= 14:
        acceleration = detect_change_acceleration(behavior_index_history)
        if acceleration["detected"] and acceleration["confidence"] >= min_confidence:
            warnings.append(
                {
                    "type": "acceleration",
                    "severity": "medium",
                    "message": "Rate of change is accelerating",
                    "confidence": acceleration["confidence"],
                    "details": {
                        "acceleration_rate": acceleration["acceleration_rate"],
                        "current_rate": acceleration["current_rate"],
                        "previous_rate": acceleration["previous_rate"],
                    },
                }
            )

    # 2. Trend + sensitivity warnings
    if temporal_attribution and sensitivity_analysis:
        global_delta = temporal_attribution.get("global_delta", {})
        delta_value = global_delta.get("delta_value", 0.0)
        direction = global_delta.get("direction", "stable")

        # Check if trend is significant and factors are sensitive
        if direction in ["increasing", "decreasing"] and abs(delta_value) > 0.02:
            factor_elasticities = sensitivity_analysis.get("factor_elasticities", {})
            high_elasticity_factors = [
                factor
                for factor, elasticity in factor_elasticities.items()
                if abs(elasticity) > 0.5
            ]

            if high_elasticity_factors:
                warnings.append(
                    {
                        "type": "trend_sensitivity",
                        "severity": "medium",
                        "message": f"Significant trend ({direction}) with high-sensitivity factors",
                        "confidence": min(abs(delta_value) * 10, 1.0),
                        "details": {
                            "direction": direction,
                            "delta_value": delta_value,
                            "high_elasticity_factors": high_elasticity_factors,
                        },
                    }
                )

    # 3. Benchmark deviation warnings
    if benchmarks:
        baseline_deviation = benchmarks.get("baseline_deviation", {})
        deviation_classification = baseline_deviation.get("classification", "normal")

        if deviation_classification in ["elevated", "anomalous"]:
            z_score = baseline_deviation.get("z_score", 0.0)
            confidence = min(abs(z_score) / 3.0, 1.0)  # Normalize to [0, 1]

            if confidence >= min_confidence:
                warnings.append(
                    {
                        "type": "benchmark_deviation",
                        "severity": (
                            "medium"
                            if deviation_classification == "elevated"
                            else "high"
                        ),
                        "message": f"Deviation from baseline: {deviation_classification}",
                        "confidence": confidence,
                        "details": {
                            "classification": deviation_classification,
                            "z_score": z_score,
                            "baseline_value": baseline_deviation.get("baseline_value"),
                            "current_value": baseline_deviation.get("current_value"),
                        },
                    }
                )

    # 4. Factor quality warnings
    if factor_quality:
        factor_provenances = factor_quality.get("factor_provenances", {})
        for factor_id, provenance in factor_provenances.items():
            confidence = provenance.get("confidence", 1.0)
            signal_strength = provenance.get("signal_strength", 0.0)

            # Warn if low confidence but high signal strength (unreliable but important)
            if confidence < 0.5 and signal_strength > 0.7:
                warnings.append(
                    {
                        "type": "factor_quality",
                        "severity": "low",
                        "message": f"Factor {factor_id} has high signal but low confidence",
                        "confidence": confidence,
                        "details": {
                            "factor_id": factor_id,
                            "confidence": confidence,
                            "signal_strength": signal_strength,
                        },
                    }
                )

    # 5. Alert persistence warnings (pre-alert)
    if alerts:
        alert_count = alerts.get("alert_count", 0)
        # If alerts exist but are rate-limited, that's a warning
        operational = alerts.get("metadata", {}).get("operational", {})
        rate_limited_count = operational.get("rate_limited_count", 0)

        if rate_limited_count > 0:
            warnings.append(
                {
                    "type": "alert_persistence",
                    "severity": "low",
                    "message": f"{rate_limited_count} alerts rate-limited (may indicate persistent conditions)",
                    "confidence": 0.7,
                    "details": {
                        "rate_limited_count": rate_limited_count,
                        "alert_count": alert_count,
                    },
                }
            )

    # Filter warnings by confidence
    filtered_warnings = [w for w in warnings if w["confidence"] >= min_confidence]

    return {
        "warnings": filtered_warnings,
        "warning_count": len(filtered_warnings),
        "metadata": {
            "min_confidence": min_confidence,
            "total_signals_checked": 5,
        },
    }


def detect_cross_factor_interactions(
    factor_values: Dict[str, float],
    factor_contributions: Dict[str, float],
    behavior_index: float,
    interaction_threshold: float = 0.15,
) -> Dict[str, Any]:
    """
    Detect cross-factor interaction effects.

    Interaction is detected when combined factor changes produce
    disproportionate impact on behavior index.

    Args:
        factor_values: Current factor values
        factor_contributions: Factor contributions to behavior index
        behavior_index: Current behavior index
        interaction_threshold: Minimum interaction strength to flag

    Returns:
        Dictionary with:
        - detected: bool
        - interactions: List of interaction objects
        - metadata: Dict
    """
    interactions = []

    # Check pairwise interactions
    factor_names = list(factor_values.keys())

    for i, factor_a in enumerate(factor_names):
        for factor_b in factor_names[i + 1 :]:
            value_a = factor_values.get(factor_a, 0.0)
            value_b = factor_values.get(factor_b, 0.0)
            contrib_a = factor_contributions.get(factor_a, 0.0)
            contrib_b = factor_contributions.get(factor_b, 0.0)

            # Both factors elevated
            if value_a > 0.6 and value_b > 0.6:
                # Expected combined contribution (additive)
                expected_combined = contrib_a + contrib_b

                # If both are high, check if their combined effect is amplified
                # This is a heuristic - we can't measure true interaction without counterfactuals
                # So we label it as a hypothesis
                combined_strength = (value_a + value_b) / 2.0

                if (
                    combined_strength > 0.7
                    and expected_combined > interaction_threshold
                ):
                    interactions.append(
                        {
                            "factor_a": factor_a,
                            "factor_b": factor_b,
                            "value_a": value_a,
                            "value_b": value_b,
                            "contribution_a": contrib_a,
                            "contribution_b": contrib_b,
                            "combined_strength": combined_strength,
                            "interaction_type": "amplification_hypothesis",
                            "confidence": min(combined_strength, 0.8),  # Conservative
                            "note": "This is a hypothesis based on correlation, not causal proof",
                        }
                    )

    return {
        "detected": len(interactions) > 0,
        "interactions": interactions,
        "metadata": {
            "interaction_threshold": interaction_threshold,
            "total_pairs_checked": len(factor_names) * (len(factor_names) - 1) // 2,
        },
    }


def compose_confidence_weighted_foresight(
    early_warnings: Dict[str, Any],
    factor_interactions: Optional[Dict[str, Any]] = None,
    provenance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compose confidence-weighted foresight summary.

    All early warnings and interactions are weighted by confidence,
    coverage, and freshness.

    Args:
        early_warnings: Early warning indicators
        factor_interactions: Cross-factor interactions
        provenance: Provenance analysis (for coverage/freshness)

    Returns:
        Dictionary with:
        - foresight_summary: str
        - high_confidence_warnings: List
        - medium_confidence_warnings: List
        - low_confidence_warnings: List
        - interaction_hypotheses: List
        - confidence_disclaimer: str
        - metadata: Dict
    """
    warnings = early_warnings.get("warnings", [])

    # Classify by confidence
    high_confidence = [w for w in warnings if w["confidence"] >= 0.8]
    medium_confidence = [w for w in warnings if 0.6 <= w["confidence"] < 0.8]
    low_confidence = [w for w in warnings if w["confidence"] < 0.6]

    # Extract interaction hypotheses
    interaction_hypotheses = []
    if factor_interactions and factor_interactions.get("detected"):
        interaction_hypotheses = factor_interactions.get("interactions", [])

    # Compose foresight summary
    summary_parts = []

    if high_confidence:
        summary_parts.append(
            f"{len(high_confidence)} high-confidence early warning(s) detected. "
            "These warrant close monitoring."
        )

    if medium_confidence:
        summary_parts.append(
            f"{len(medium_confidence)} medium-confidence warning(s) present. "
            "Monitor trends for confirmation."
        )

    if interaction_hypotheses:
        summary_parts.append(
            f"{len(interaction_hypotheses)} potential factor interaction(s) identified. "
            "These are hypotheses based on correlation, not causal proof."
        )

    if not summary_parts:
        summary_parts.append("No early warnings detected at this time.")

    foresight_summary = " ".join(summary_parts)

    # Confidence disclaimer
    coverage_ok = True
    freshness_ok = True

    if provenance:
        aggregate = provenance.get("aggregate_provenance", {})
        coverage = aggregate.get("coverage_ratio", 1.0)
        freshness = aggregate.get("freshness_classification", "fresh")

        coverage_ok = coverage >= 0.8
        freshness_ok = freshness in ["fresh", "delayed"]

    disclaimer_parts = []
    if not coverage_ok:
        disclaimer_parts.append("Data coverage is incomplete, reducing confidence.")
    if not freshness_ok:
        disclaimer_parts.append("Data freshness is suboptimal, affecting reliability.")

    if not disclaimer_parts:
        disclaimer_parts.append(
            "Confidence is based on signal strength and data quality."
        )

    confidence_disclaimer = " ".join(disclaimer_parts)

    return {
        "foresight_summary": foresight_summary,
        "high_confidence_warnings": high_confidence,
        "medium_confidence_warnings": medium_confidence,
        "low_confidence_warnings": low_confidence,
        "interaction_hypotheses": interaction_hypotheses,
        "confidence_disclaimer": confidence_disclaimer,
        "metadata": {
            "total_warnings": len(warnings),
            "total_interactions": len(interaction_hypotheses),
            "coverage_ok": coverage_ok,
            "freshness_ok": freshness_ok,
        },
    }
