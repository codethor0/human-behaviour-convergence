# SPDX-License-Identifier: PROPRIETARY
"""Policy preview and impact analysis.

This module provides:
- Policy preview mode (evaluate without activating)
- Impact diff (before vs after comparison)
- Safe activation workflow

Preview never mutates state and is fully derivable from current analytics.
Zero numerical drift is a HARD invariant.
"""
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.core.policy import PolicyEngine

logger = structlog.get_logger("core.policy_preview")


def preview_policy_impact(
    policy_id: str,
    policy: Dict[str, Any],
    current_alerts: List[Dict[str, Any]],
    current_context: Dict[str, Any],
    tenant_id: str = "default",
) -> Dict[str, Any]:
    """
    Preview policy impact without activating.

    Shows:
    - Which alerts would fire
    - Which would be suppressed
    - Alert count delta
    - Severity distribution delta
    - Noise reduction estimate

    Args:
        policy_id: Policy identifier
        policy: Policy definition to preview
        current_alerts: Current active alerts
        current_context: Current evaluation context (factor values, etc.)
        tenant_id: Tenant identifier

    Returns:
        Dictionary with preview results
    """
    # Create temporary policy engine for preview (doesn't mutate main engine)
    preview_engine = PolicyEngine()

    # Create temporary policy for preview
    preview_policy_id = f"preview_{policy_id}"
    success, error = preview_engine.create_policy(
        policy_id=preview_policy_id,
        policy=policy,
        created_by="preview_user",
        tenant_id=tenant_id,
    )

    if not success:
        return {
            "preview_valid": False,
            "error": error,
        }

    # Activate preview policy temporarily
    preview_engine.activate_policy(preview_policy_id, "preview_user", tenant_id)

    # Evaluate preview policy against current context
    preview_result = preview_engine.evaluate_policy(
        preview_policy_id,
        current_context,
        tenant_id,
    )

    # Simulate alert generation with preview policy
    preview_alerts = []
    if preview_result.get("evaluated") and preview_result.get("matches"):
        for match in preview_result["matches"]:
            if match["type"] == "alert_threshold":
                preview_alerts.append(
                    {
                        "alert_id": f"preview_{match['factor_id']}_threshold",
                        "type": "threshold",
                        "severity": "medium",
                        "factor_id": match["factor_id"],
                        "value": match["value"],
                        "threshold": match["threshold"],
                    }
                )

    # Compare current vs preview
    current_alert_count = len(current_alerts)
    preview_alert_count = len(preview_alerts)
    alert_count_delta = preview_alert_count - current_alert_count

    # Severity distribution
    current_severity_dist = {}
    for alert in current_alerts:
        severity = alert.get("severity", "unknown")
        current_severity_dist[severity] = current_severity_dist.get(severity, 0) + 1

    preview_severity_dist = {}
    for alert in preview_alerts:
        severity = alert.get("severity", "unknown")
        preview_severity_dist[severity] = preview_severity_dist.get(severity, 0) + 1

    # Noise reduction estimate (alerts that would be suppressed)
    suppressed_alerts = []
    for current_alert in current_alerts:
        # Check if this alert would still fire under preview policy
        alert_factor = current_alert.get("factor_id")
        if alert_factor:
            factor_value = current_context.get("factor_values", {}).get(
                alert_factor, 0.0
            )
            policy_threshold = policy.get("alert_thresholds", {}).get("threshold")
            policy_direction = policy.get("alert_thresholds", {}).get("direction")

            if policy_threshold is not None:
                would_fire = False
                if policy_direction == "above" and factor_value > policy_threshold:
                    would_fire = True
                elif policy_direction == "below" and factor_value < policy_threshold:
                    would_fire = True

                if not would_fire:
                    suppressed_alerts.append(current_alert)

    noise_reduction_estimate = len(suppressed_alerts)

    return {
        "preview_valid": True,
        "policy_id": policy_id,
        "current_alert_count": current_alert_count,
        "preview_alert_count": preview_alert_count,
        "alert_count_delta": alert_count_delta,
        "current_severity_distribution": current_severity_dist,
        "preview_severity_distribution": preview_severity_dist,
        "noise_reduction_estimate": noise_reduction_estimate,
        "suppressed_alerts": suppressed_alerts,
        "new_alerts": preview_alerts,
        "preview_alerts": preview_alerts,
    }


def generate_impact_diff(
    current_state: Dict[str, Any],
    preview_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate before/after impact diff.

    Args:
        current_state: Current state (alerts, metrics, etc.)
        preview_state: Preview state (with proposed policy)

    Returns:
        Dictionary with diff results
    """
    diff = {
        "alert_count_change": preview_state.get("preview_alert_count", 0)
        - current_state.get("current_alert_count", 0),
        "severity_changes": {},
        "noise_reduction": preview_state.get("noise_reduction_estimate", 0),
        "new_alerts_count": len(preview_state.get("new_alerts", [])),
        "suppressed_alerts_count": len(preview_state.get("suppressed_alerts", [])),
    }

    # Severity distribution changes
    current_severity = current_state.get("current_severity_distribution", {})
    preview_severity = preview_state.get("preview_severity_distribution", {})

    all_severities = set(current_severity.keys()) | set(preview_severity.keys())
    for severity in all_severities:
        current_count = current_severity.get(severity, 0)
        preview_count = preview_severity.get(severity, 0)
        if current_count != preview_count:
            diff["severity_changes"][severity] = {
                "current": current_count,
                "preview": preview_count,
                "delta": preview_count - current_count,
            }

    return diff


def validate_preview_before_activation(
    policy_id: str,
    preview_result: Dict[str, Any],
    tenant_id: str = "default",
) -> Tuple[bool, Optional[str]]:
    """
    Validate that preview was performed before activation.

    Args:
        policy_id: Policy identifier
        preview_result: Preview result (must be valid)
        tenant_id: Tenant identifier

    Returns:
        (is_valid, error_message)
    """
    if not preview_result.get("preview_valid"):
        return False, "Policy must be previewed before activation"

    # Check that preview was recent (within last hour)
    # This is a simplified check - in production, track preview timestamps
    return True, None
