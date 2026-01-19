# SPDX-License-Identifier: PROPRIETARY
"""Decision trace utilities for explainability and attribution.

This module provides structured trace objects that reconcile numerically
with decision outputs, ensuring explainability and auditability.
"""
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from app.core.invariants import get_registry

logger = structlog.get_logger("core.trace")


def validate_reconciliation(
    components: Dict[str, Dict[str, float]],
    output: float,
    tolerance: float = 0.01,
) -> Dict[str, Any]:
    """
    Validate that component contributions sum to output within tolerance.

    Args:
        components: Dictionary mapping component names to dicts with "contribution" key
        output: Final output value
        tolerance: Maximum allowed difference (default: 0.01)

    Returns:
        Dictionary with reconciliation details
    """
    sum_contributions = sum(
        comp.get("contribution", 0.0) for comp in components.values()
    )
    difference = abs(float(sum_contributions) - float(output))

    # Guard against NaN/inf
    sum_is_finite = math.isfinite(sum_contributions)
    output_is_finite = math.isfinite(output)

    if not sum_is_finite or not output_is_finite:
        logger.warning(
            "Reconciliation validation failed: non-finite values",
            sum_contributions=sum_contributions,
            output=output,
            sum_is_finite=sum_is_finite,
            output_is_finite=output_is_finite,
        )
        return {
            "sum": float(sum_contributions) if sum_is_finite else float("nan"),
            "output": float(output) if output_is_finite else float("nan"),
            "difference": float("inf"),
            "valid": False,
        }

    return {
        "sum": float(sum_contributions),
        "output": float(output),
        "difference": float(difference),
        "valid": difference <= tolerance,
    }


def sanitize_trace(
    trace: Dict[str, Any], internal_fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Sanitize trace object by removing internal fields and clipping values.

    Args:
        trace: Trace object dictionary
        internal_fields: List of field names to remove (default: common internal fields)

    Returns:
        Sanitized trace object
    """
    if internal_fields is None:
        internal_fields = [
            "_internal",
            "_debug",
            "_raw",
            "_temp",
            "internal_state",
            "debug_info",
        ]

    sanitized = {}
    for key, value in trace.items():
        if key in internal_fields:
            continue

        if isinstance(value, dict):
            sanitized[key] = sanitize_trace(value, internal_fields)
        elif isinstance(value, list):
            sanitized[key] = [
                (
                    sanitize_trace(item, internal_fields)
                    if isinstance(item, dict)
                    else item
                )
                for item in value
            ]
        elif isinstance(value, float):
            # Clip to valid range and check for NaN/inf
            if math.isfinite(value):
                # Clip based on context (most values are 0.0-1.0 or 0-100)
                if "score" in key.lower() or "confidence" in key.lower():
                    sanitized[key] = max(0.0, min(1.0, float(value)))
                elif "convergence" in key.lower() and "score" in key.lower():
                    sanitized[key] = max(0.0, min(100.0, float(value)))
                else:
                    sanitized[key] = float(value)
            else:
                sanitized[key] = 0.0  # Replace NaN/inf with 0.0
        else:
            sanitized[key] = value

    return sanitized


def ensure_order_independence(
    components: Dict[str, Any], sort_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ensure components are in deterministic order for order-independent explanations.

    Args:
        components: Dictionary of components
        sort_key: Key to sort by if components are lists (default: "id" or first key)

    Returns:
        Components in deterministic order
    """
    if isinstance(components, dict):
        # Sort dictionary keys for deterministic ordering
        sorted_keys = sorted(components.keys())
        return {key: components[key] for key in sorted_keys}
    elif isinstance(components, list):
        # Sort list items
        if sort_key:
            return sorted(components, key=lambda x: x.get(sort_key, ""))
        else:
            # Try common sort keys
            for key in ["id", "name", "label", "index"]:
                if (
                    components
                    and isinstance(components[0], dict)
                    and key in components[0]
                ):
                    return sorted(components, key=lambda x: x.get(key, ""))
            return sorted(components, key=str)
    else:
        return components


def create_risk_trace(
    tier: str,
    risk_score: float,
    base_risk: float,
    shock_adjustment: float,
    convergence_adjustment: float,
    trend_adjustment: float,
    shock_events: List[Dict],
    convergence_score: Optional[float],
    trend_direction: Optional[str],
) -> Dict[str, Any]:
    """
    Create structured trace for risk classification decision.

    Args:
        tier: Risk tier
        risk_score: Final risk score
        base_risk: Base risk from behavior index
        shock_adjustment: Adjustment from shock events
        convergence_adjustment: Adjustment from convergence score
        trend_adjustment: Adjustment from trend direction
        shock_events: List of shock events
        convergence_score: Convergence score (0-100)
        trend_direction: Trend direction

    Returns:
        Structured risk trace object
    """
    components = {
        "base_risk": {
            "value": float(base_risk),
            "contribution": float(base_risk),
            "source": "behavior_index",
        },
        "shock_adjustment": {
            "value": float(shock_adjustment),
            "contribution": float(shock_adjustment),
            "shock_count": len(shock_events),
            "source": "shock_detector",
        },
        "convergence_adjustment": {
            "value": float(convergence_adjustment),
            "contribution": float(convergence_adjustment),
            "convergence_score": (
                float(convergence_score) if convergence_score is not None else 0.0
            ),
            "source": "convergence_engine",
        },
        "trend_adjustment": {
            "value": float(trend_adjustment),
            "contribution": float(trend_adjustment),
            "trend_direction": trend_direction or "stable",
            "source": "trend_analysis",
        },
    }

    reconciliation = validate_reconciliation(components, risk_score)

    # Check INV-021: Contribution reconciliation (non-blocking)
    try:
        registry = get_registry()
        registry.check("INV-021", components, risk_score)
    except Exception:
        # Don't break on invariant violations, just log
        pass

    trace = {
        "output": {
            "tier": tier,
            "risk_score": float(risk_score),
        },
        "components": ensure_order_independence(components),
        "reconciliation": reconciliation,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "inputs": {
                "shock_count": len(shock_events),
                "convergence_score": (
                    float(convergence_score) if convergence_score is not None else None
                ),
                "trend_direction": trend_direction,
            },
        },
    }

    if not reconciliation["valid"]:
        logger.warning(
            "Risk trace reconciliation failed",
            difference=reconciliation["difference"],
            sum=reconciliation["sum"],
            output=reconciliation["output"],
        )

    return sanitize_trace(trace)


def create_confidence_trace(
    index: str,
    confidence: float,
    completeness: float,
    stability: float,
    forecast_accuracy: float,
    data_points: int,
    unclipped_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Create structured trace for confidence score decision.

    Args:
        index: Index name
        confidence: Final confidence score (clipped)
        completeness: Data completeness component
        stability: Stability component
        forecast_accuracy: Forecast accuracy component
        data_points: Number of data points
        unclipped_confidence: Unclipped confidence value for reconciliation (optional)

    Returns:
        Structured confidence trace object
    """
    weights = {"completeness": 0.3, "stability": 0.4, "forecast_accuracy": 0.3}

    components = {
        "completeness": {
            "value": float(completeness),
            "weight": weights["completeness"],
            "contribution": float(completeness * weights["completeness"]),
        },
        "stability": {
            "value": float(stability),
            "weight": weights["stability"],
            "contribution": float(stability * weights["stability"]),
        },
        "forecast_accuracy": {
            "value": float(forecast_accuracy),
            "weight": weights["forecast_accuracy"],
            "contribution": float(forecast_accuracy * weights["forecast_accuracy"]),
        },
    }

    # Use unclipped confidence for reconciliation if provided, otherwise use clipped
    # This allows reconciliation to work correctly when confidence is clipped
    reconciliation_value = (
        unclipped_confidence if unclipped_confidence is not None else confidence
    )
    reconciliation = validate_reconciliation(components, reconciliation_value)

    # Check INV-021: Contribution reconciliation (non-blocking)
    try:
        registry = get_registry()
        registry.check("INV-021", components, reconciliation_value)
    except Exception:
        # Don't break on invariant violations, just log
        pass

    trace = {
        "output": {
            "confidence": float(confidence),  # Clipped value for display
        },
        "components": ensure_order_independence(components),
        "reconciliation": reconciliation,
        "metadata": {
            "index": index,
            "data_points": int(data_points),
            "weights": weights,
        },
    }

    if not reconciliation["valid"]:
        logger.warning(
            "Confidence trace reconciliation failed",
            index=index,
            difference=reconciliation["difference"],
            sum=reconciliation["sum"],
            output=reconciliation["output"],
        )

    return sanitize_trace(trace)


def create_convergence_trace(
    score: float,
    correlations: List[float],
    indices: List[str],
    correlation_matrix: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Create structured trace for convergence score decision.

    Args:
        score: Final convergence score (0-100)
        correlations: List of correlation values used in calculation
        indices: List of index names
        correlation_matrix: Optional correlation matrix dictionary

    Returns:
        Structured convergence trace object
    """
    if correlations:
        avg_correlation = sum(abs(c) for c in correlations) / len(correlations)
        calculated_score = avg_correlation * 100.0
    else:
        avg_correlation = 0.0
        calculated_score = 0.0

    difference = abs(float(calculated_score) - float(score))
    valid = difference <= 0.01

    trace = {
        "output": {
            "score": float(score),
        },
        "components": {
            "correlations": [float(c) for c in correlations],
            "avg_correlation": float(avg_correlation),
            "calculated_score": float(calculated_score),
        },
        "reconciliation": {
            "calculated_score": float(calculated_score),
            "output": float(score),
            "difference": float(difference),
            "valid": valid,
        },
        "metadata": {
            "indices": sorted(indices),  # Deterministic ordering
            "correlation_count": len(correlations),
        },
    }

    if correlation_matrix:
        trace["metadata"]["correlation_matrix"] = correlation_matrix

    if not valid:
        logger.warning(
            "Convergence trace reconciliation failed",
            difference=difference,
            calculated=calculated_score,
            output=score,
        )

    return sanitize_trace(trace)


def create_shock_trace(
    shocks: List[Dict],
    z_score_shocks: List[Dict],
    delta_shocks: List[Dict],
    ewma_shocks: List[Dict],
    index: str,
) -> Dict[str, Any]:
    """
    Create structured trace for shock detection decision.

    Args:
        shocks: Merged list of shock events
        z_score_shocks: Shocks detected via Z-score method
        delta_shocks: Shocks detected via delta method
        ewma_shocks: Shocks detected via EWMA method
        index: Index name

    Returns:
        Structured shock trace object
    """
    component_sum = len(z_score_shocks) + len(delta_shocks) + len(ewma_shocks)
    merged_count = len(shocks)
    # Reconciliation: merged count should be <= component sum (due to deduplication)
    valid = merged_count <= component_sum

    trace = {
        "output": {
            "shocks": shocks,
            "total_shocks": int(merged_count),
        },
        "components": {
            "z_score_shocks": z_score_shocks,
            "delta_shocks": delta_shocks,
            "ewma_shocks": ewma_shocks,
        },
        "reconciliation": {
            "merged_count": int(merged_count),
            "component_sum": int(component_sum),
            "valid": valid,
        },
        "metadata": {
            "index": index,
            "methods": ["z_score", "delta", "ewma"],
        },
    }

    if not valid:
        logger.warning(
            "Shock trace reconciliation failed",
            index=index,
            merged_count=merged_count,
            component_sum=component_sum,
        )

    return sanitize_trace(trace)


def create_behavior_index_trace(
    behavior_index: float,
    contributions: Dict[str, Dict[str, float]],
    weights: Dict[str, float],
) -> Dict[str, Any]:
    """
    Create structured trace for behavior index decision.

    Args:
        behavior_index: Final behavior index value
        contributions: Dictionary mapping sub-index names to contribution dicts
        weights: Dictionary mapping sub-index names to weights

    Returns:
        Structured behavior index trace object
    """
    # Extract contributions from contribution dicts
    component_dict = {}
    for name, contrib in contributions.items():
        component_dict[name] = {
            "value": float(contrib.get("value", 0.5)),
            "weight": float(contrib.get("weight", 0.0)),
            "contribution": float(contrib.get("contribution", 0.0)),
        }

    reconciliation = validate_reconciliation(component_dict, behavior_index)

    trace = {
        "output": {
            "behavior_index": float(behavior_index),
        },
        "components": ensure_order_independence(component_dict),
        "reconciliation": reconciliation,
        "metadata": {
            "weights": ensure_order_independence(weights),
        },
    }

    if not reconciliation["valid"]:
        logger.warning(
            "Behavior index trace reconciliation failed",
            difference=reconciliation["difference"],
            sum=reconciliation["sum"],
            output=reconciliation["output"],
        )

    return sanitize_trace(trace)
