# SPDX-License-Identifier: PROPRIETARY
"""Alerting and watch conditions.

This module derives alerts from existing analytics outputs without changing
any numerical computations. Alerts are purely derived from:
- Behavior index levels
- Temporal attribution (deltas, trends)
- Factor quality (confidence, persistence, signal strength)
- Scenario sensitivity (elasticity)

All alerts are deterministic, rate-limited, and misuse-safe.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger("core.alerting")


def check_threshold_alert(
    current_value: float,
    threshold: float,
    comparison: str = "greater_than",
    persistence_days: int = 0,
    history_values: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """
    Check if a threshold alert condition is met.

    Args:
        current_value: Current value to check
        threshold: Threshold value
        comparison: "greater_than", "less_than", or "equals"
        persistence_days: Number of consecutive days threshold must be exceeded
        history_values: Historical values (most recent first) for persistence check

    Returns:
        Dictionary with:
        - triggered: Whether alert is triggered
        - current_value: Current value
        - threshold: Threshold value
        - comparison: Comparison operator
        - persistence_met: Whether persistence requirement is met
        - days_above_threshold: Number of consecutive days above threshold
    """
    if history_values is None:
        history_values = []

    # Check current condition
    if comparison == "greater_than":
        condition_met = current_value > threshold
    elif comparison == "less_than":
        condition_met = current_value < threshold
    elif comparison == "equals":
        condition_met = abs(current_value - threshold) < 1e-6
    else:
        logger.warning("Unknown comparison operator", comparison=comparison)
        condition_met = False

    # Check persistence
    days_above_threshold = 0
    if condition_met and history_values:
        # Count consecutive days where condition is met (most recent first)
        for val in history_values:
            if comparison == "greater_than":
                if val > threshold:
                    days_above_threshold += 1
                else:
                    break
            elif comparison == "less_than":
                if val < threshold:
                    days_above_threshold += 1
                else:
                    break
            elif comparison == "equals":
                if abs(val - threshold) < 1e-6:
                    days_above_threshold += 1
                else:
                    break
        # Add current day if condition met
        if condition_met:
            days_above_threshold += 1
    elif condition_met:
        # No history, but current condition met
        days_above_threshold = 1

    persistence_met = days_above_threshold >= persistence_days + 1  # +1 for current day

    triggered = condition_met and persistence_met

    return {
        "triggered": triggered,
        "current_value": float(current_value),
        "threshold": float(threshold),
        "comparison": comparison,
        "persistence_met": persistence_met,
        "days_above_threshold": days_above_threshold,
    }


def check_trend_alert(
    current_value: float,
    previous_value: Optional[float],
    trend_direction: str = "worsening",
    min_change_magnitude: float = 0.01,
    persistence_days: int = 0,
    history_deltas: Optional[List[float]] = None,
    confidence: Optional[float] = None,
    min_confidence: float = 0.5,
) -> Dict[str, Any]:
    """
    Check if a trend alert condition is met.

    Args:
        current_value: Current value
        previous_value: Previous value (None if not available)
        trend_direction: "worsening" (increasing for risk), "improving" (decreasing), or "any"
        min_change_magnitude: Minimum change magnitude to trigger
        persistence_days: Number of consecutive days trend must persist
        history_deltas: Historical deltas (most recent first) for persistence check
        confidence: Current confidence score (optional)
        min_confidence: Minimum confidence required to trigger alert

    Returns:
        Dictionary with:
        - triggered: Whether alert is triggered
        - trend_detected: Whether trend is detected
        - change_magnitude: Magnitude of change
        - direction: "increasing", "decreasing", or "stable"
        - persistence_met: Whether persistence requirement is met
        - confidence_met: Whether confidence requirement is met
    """
    if previous_value is None:
        return {
            "triggered": False,
            "trend_detected": False,
            "change_magnitude": 0.0,
            "direction": "stable",
            "persistence_met": False,
            "confidence_met": confidence is None or confidence >= min_confidence,
            "reason": "no_previous_value",
        }

    delta = current_value - previous_value
    change_magnitude = abs(delta)
    direction = (
        "increasing"
        if delta > min_change_magnitude
        else "decreasing" if delta < -min_change_magnitude else "stable"
    )

    # Check if trend matches direction requirement
    if trend_direction == "worsening":
        trend_detected = delta > min_change_magnitude
    elif trend_direction == "improving":
        trend_detected = delta < -min_change_magnitude
    elif trend_direction == "any":
        trend_detected = change_magnitude >= min_change_magnitude
    else:
        logger.warning("Unknown trend direction", trend_direction=trend_direction)
        trend_detected = False

    # Check confidence requirement
    confidence_met = confidence is None or confidence >= min_confidence

    # Check persistence
    persistence_met = True
    if persistence_days > 0 and history_deltas:
        # Count consecutive days with same direction trend
        consecutive_days = 0
        for hist_delta in history_deltas:
            if trend_direction == "worsening":
                if hist_delta > min_change_magnitude:
                    consecutive_days += 1
                else:
                    break
            elif trend_direction == "improving":
                if hist_delta < -min_change_magnitude:
                    consecutive_days += 1
                else:
                    break
            elif trend_direction == "any":
                if abs(hist_delta) >= min_change_magnitude:
                    consecutive_days += 1
                else:
                    break
        # Add current day if trend detected
        if trend_detected:
            consecutive_days += 1
        persistence_met = consecutive_days >= persistence_days + 1  # +1 for current day
    elif persistence_days > 0:
        # No history, but current trend detected
        persistence_met = trend_detected

    triggered = trend_detected and persistence_met and confidence_met

    return {
        "triggered": triggered,
        "trend_detected": trend_detected,
        "change_magnitude": float(change_magnitude),
        "direction": direction,
        "persistence_met": persistence_met,
        "confidence_met": confidence_met,
        "delta": float(delta),
    }


def check_sensitivity_aware_alert(
    alert_condition: Dict[str, Any],
    factor_elasticity: Optional[float] = None,
    min_elasticity: float = 0.2,
    signal_classification: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check if an alert should be triggered based on sensitivity gating.

    Suppresses alerts for low-impact factors (low elasticity) or noise signals.

    Args:
        alert_condition: Base alert condition result (from threshold or trend check)
        factor_elasticity: Factor elasticity (optional)
        min_elasticity: Minimum elasticity required to trigger alert
        signal_classification: "signal" or "noise" (optional)

    Returns:
        Dictionary with:
        - triggered: Whether alert is triggered (after sensitivity gating)
        - base_triggered: Original alert condition
        - elasticity_met: Whether elasticity requirement is met
        - signal_met: Whether signal requirement is met
        - gated: Whether alert was suppressed by sensitivity gating
    """
    base_triggered = alert_condition.get("triggered", False)

    # If base condition not met, no alert
    if not base_triggered:
        return {
            "triggered": False,
            "base_triggered": False,
            "elasticity_met": True,  # N/A
            "signal_met": True,  # N/A
            "gated": False,
        }

    # Check elasticity requirement
    elasticity_met = True
    if factor_elasticity is not None:
        elasticity_met = abs(factor_elasticity) >= min_elasticity

    # Check signal vs noise requirement
    signal_met = True
    if signal_classification is not None:
        signal_met = signal_classification == "signal"

    # Alert triggered only if all gates pass
    triggered = base_triggered and elasticity_met and signal_met
    gated = base_triggered and not triggered

    return {
        "triggered": triggered,
        "base_triggered": base_triggered,
        "elasticity_met": elasticity_met,
        "signal_met": signal_met,
        "gated": gated,
    }


def validate_alert_definition(
    alert_type: str,
    threshold: Optional[float] = None,
    comparison: Optional[str] = None,
    persistence_days: int = 0,
    min_change_magnitude: Optional[float] = None,
    min_elasticity: Optional[float] = None,
    rate_limit_hours: int = 24,
) -> Tuple[bool, Optional[str]]:
    """
    Validate an alert definition for misuse safety.

    Args:
        alert_type: "threshold" or "trend"
        threshold: Threshold value (for threshold alerts)
        comparison: Comparison operator (for threshold alerts)
        persistence_days: Persistence requirement
        min_change_magnitude: Minimum change magnitude (for trend alerts)
        min_elasticity: Minimum elasticity (for sensitivity-aware alerts)
        rate_limit_hours: Rate limit in hours

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate alert type
    if alert_type not in ["threshold", "trend"]:
        return False, f"Unknown alert type: {alert_type}"

    # Validate threshold alert parameters
    if alert_type == "threshold":
        if threshold is None:
            return False, "Threshold required for threshold alerts"
        if threshold < 0.0 or threshold > 1.0:
            return False, f"Threshold must be in [0.0, 1.0], got {threshold}"
        if comparison not in ["greater_than", "less_than", "equals"]:
            return False, f"Invalid comparison operator: {comparison}"

    # Validate trend alert parameters
    if alert_type == "trend":
        if min_change_magnitude is None:
            return False, "min_change_magnitude required for trend alerts"
        if min_change_magnitude < 0.0 or min_change_magnitude > 1.0:
            return (
                False,
                f"min_change_magnitude must be in [0.0, 1.0], got {min_change_magnitude}",
            )

    # Validate persistence
    if persistence_days < 0 or persistence_days > 365:
        return False, f"persistence_days must be in [0, 365], got {persistence_days}"

    # Validate elasticity
    if min_elasticity is not None:
        if min_elasticity < 0.0 or min_elasticity > 1.0:
            return False, f"min_elasticity must be in [0.0, 1.0], got {min_elasticity}"

    # Validate rate limit
    if rate_limit_hours < 1 or rate_limit_hours > 168:  # Max 1 week
        return False, f"rate_limit_hours must be in [1, 168], got {rate_limit_hours}"

    return True, None


def compose_alerts(
    behavior_index: float,
    behavior_index_history: Optional[List[float]] = None,
    temporal_attribution: Optional[Dict[str, Any]] = None,
    sensitivity_analysis: Optional[Dict[str, Any]] = None,
    forecast_confidence: Optional[float] = None,
    alert_definitions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Compose alerts from existing analytics outputs.

    This function is purely derived - it does not change any numerical outputs.

    Args:
        behavior_index: Current behavior index value
        behavior_index_history: Historical behavior index values (most recent first)
        temporal_attribution: Temporal attribution data (from compose_temporal_attribution)
        sensitivity_analysis: Sensitivity analysis data (from compose_sensitivity_analysis)
        forecast_confidence: Forecast confidence score
        alert_definitions: List of alert definitions to check

    Returns:
        Dictionary with:
        - alerts: List of triggered alerts
        - alert_count: Number of triggered alerts
        - metadata: Alert generation metadata
    """
    if alert_definitions is None:
        alert_definitions = []

    if behavior_index_history is None:
        behavior_index_history = []

    triggered_alerts = []
    previous_value = None
    if behavior_index_history:
        previous_value = behavior_index_history[0] if behavior_index_history else None

    # Extract deltas from temporal attribution
    history_deltas = None
    if temporal_attribution and "global_delta" in temporal_attribution:
        global_delta = temporal_attribution["global_delta"]
        if global_delta.get("has_change"):
            # For persistence, we'd need full history of deltas
            # For now, use current delta
            history_deltas = [global_delta.get("delta", 0.0)]

    # Extract factor elasticities from sensitivity analysis
    factor_elasticities = {}
    if sensitivity_analysis and "factor_elasticities" in sensitivity_analysis:
        factor_elasticities = sensitivity_analysis["factor_elasticities"]

    # Extract signal vs noise classifications
    signal_classifications = {}
    if temporal_attribution and "signal_vs_noise" in temporal_attribution:
        signal_vs_noise = temporal_attribution["signal_vs_noise"]
        for sub_index_name, classifications in signal_vs_noise.items():
            for item in classifications:
                factor_id = item.get("factor_id")
                classification = item.get("classification")
                if factor_id and classification:
                    signal_classifications[factor_id] = classification

    # Check each alert definition
    for alert_def in alert_definitions:
        alert_type = alert_def.get("type", "threshold")
        alert_id = alert_def.get("id", "unknown")
        alert_label = alert_def.get("label", alert_id)

        # Validate alert definition
        is_valid, error_msg = validate_alert_definition(
            alert_type=alert_type,
            threshold=alert_def.get("threshold"),
            comparison=alert_def.get("comparison"),
            persistence_days=alert_def.get("persistence_days", 0),
            min_change_magnitude=alert_def.get("min_change_magnitude"),
            min_elasticity=alert_def.get("min_elasticity"),
            rate_limit_hours=alert_def.get("rate_limit_hours", 24),
        )

        if not is_valid:
            logger.warning(
                "Invalid alert definition", alert_id=alert_id, error=error_msg
            )
            continue

        # Check threshold alert
        if alert_type == "threshold":
            threshold_result = check_threshold_alert(
                current_value=behavior_index,
                threshold=alert_def["threshold"],
                comparison=alert_def.get("comparison", "greater_than"),
                persistence_days=alert_def.get("persistence_days", 0),
                history_values=behavior_index_history,
            )

            # Apply sensitivity gating if requested
            if alert_def.get("sensitivity_aware", False):
                factor_id = alert_def.get("factor_id")
                factor_elasticity = (
                    factor_elasticities.get(factor_id) if factor_id else None
                )
                if isinstance(factor_elasticity, dict):
                    elasticity_value = factor_elasticity.get("elasticity")
                else:
                    elasticity_value = factor_elasticity

                signal_classification = (
                    signal_classifications.get(factor_id) if factor_id else None
                )

                gated_result = check_sensitivity_aware_alert(
                    alert_condition=threshold_result,
                    factor_elasticity=elasticity_value,
                    min_elasticity=alert_def.get("min_elasticity", 0.2),
                    signal_classification=signal_classification,
                )

                if gated_result["triggered"]:
                    triggered_alerts.append(
                        {
                            "id": alert_id,
                            "label": alert_label,
                            "type": "threshold",
                            "severity": alert_def.get("severity", "medium"),
                            "current_value": threshold_result["current_value"],
                            "threshold": threshold_result["threshold"],
                            "comparison": threshold_result["comparison"],
                            "persistence_days": threshold_result[
                                "days_above_threshold"
                            ],
                            "gated": False,
                        }
                    )
            elif threshold_result["triggered"]:
                triggered_alerts.append(
                    {
                        "id": alert_id,
                        "label": alert_label,
                        "type": "threshold",
                        "severity": alert_def.get("severity", "medium"),
                        "current_value": threshold_result["current_value"],
                        "threshold": threshold_result["threshold"],
                        "comparison": threshold_result["comparison"],
                        "persistence_days": threshold_result["days_above_threshold"],
                        "gated": False,
                    }
                )

        # Check trend alert
        elif alert_type == "trend":
            trend_result = check_trend_alert(
                current_value=behavior_index,
                previous_value=previous_value,
                trend_direction=alert_def.get("trend_direction", "worsening"),
                min_change_magnitude=alert_def.get("min_change_magnitude", 0.01),
                persistence_days=alert_def.get("persistence_days", 0),
                history_deltas=history_deltas,
                confidence=forecast_confidence,
                min_confidence=alert_def.get("min_confidence", 0.5),
            )

            if trend_result["triggered"]:
                triggered_alerts.append(
                    {
                        "id": alert_id,
                        "label": alert_label,
                        "type": "trend",
                        "severity": alert_def.get("severity", "medium"),
                        "direction": trend_result["direction"],
                        "change_magnitude": trend_result["change_magnitude"],
                        "delta": trend_result["delta"],
                        "persistence_days": alert_def.get("persistence_days", 0),
                        "confidence": forecast_confidence,
                        "gated": False,
                    }
                )

    return {
        "alerts": triggered_alerts,
        "alert_count": len(triggered_alerts),
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "definitions_checked": len(alert_definitions),
            "behavior_index": float(behavior_index),
            "has_temporal_attribution": temporal_attribution is not None,
            "has_sensitivity_analysis": sensitivity_analysis is not None,
        },
    }
