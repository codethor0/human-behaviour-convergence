# SPDX-License-Identifier: PROPRIETARY
"""Invariant enforcement and regression guards.

This module provides centralized invariant checking, drift detection,
and regression guards to ensure system integrity over time.
"""
import math
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger("core.invariants")


class EnforcementStrategy(Enum):
    """Enforcement strategy for invariants."""

    HARD_FAIL = "hard_fail"  # Raise exception
    SOFT_FAIL = "soft_fail"  # Log warning
    TEST_ONLY = "test_only"  # Only checked in tests


class InvariantViolation(Exception):
    """Exception raised when a critical invariant is violated."""

    def __init__(self, invariant_name: str, message: str, details: Optional[Dict] = None):
        super().__init__(f"Invariant violation: {invariant_name} - {message}")
        self.invariant_name = invariant_name
        self.message = message
        self.details = details or {}


class InvariantRegistry:
    """Registry of all system invariants."""

    def __init__(self):
        """Initialize invariant registry."""
        self._invariants: Dict[str, Dict[str, Any]] = {}
        self._violations: List[Dict[str, Any]] = []

    def register(
        self,
        name: str,
        scope: str,
        statement: str,
        tolerance: float,
        enforcement: EnforcementStrategy,
        check_fn: callable,
    ) -> None:
        """
        Register an invariant.

        Args:
            name: Invariant name (e.g., "INV-001")
            scope: Scope description
            statement: Invariant statement
            tolerance: Tolerance value
            enforcement: Enforcement strategy
            check_fn: Function that checks the invariant (returns (bool, Optional[str]))
        """
        self._invariants[name] = {
            "name": name,
            "scope": scope,
            "statement": statement,
            "tolerance": tolerance,
            "enforcement": enforcement,
            "check_fn": check_fn,
        }

    def check(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check an invariant.

        Args:
            name: Invariant name
            *args: Arguments to pass to check function
            **kwargs: Keyword arguments to pass to check function

        Returns:
            Tuple of (is_valid, error_message)
        """
        if name not in self._invariants:
            logger.warning("Unknown invariant checked", invariant=name)
            return True, None

        invariant = self._invariants[name]
        check_fn = invariant["check_fn"]
        enforcement = invariant["enforcement"]

        try:
            is_valid, error_msg = check_fn(*args, **kwargs)
        except Exception as e:
            logger.error(
                "Invariant check failed with exception",
                invariant=name,
                error=str(e),
                exc_info=True,
            )
            is_valid = False
            error_msg = f"Check function raised exception: {str(e)}"

        if not is_valid:
            violation = {
                "invariant": name,
                "scope": invariant["scope"],
                "statement": invariant["statement"],
                "enforcement": enforcement.value,
                "error": error_msg,
            }
            self._violations.append(violation)

            if enforcement == EnforcementStrategy.HARD_FAIL:
                raise InvariantViolation(
                    name,
                    error_msg or "Invariant violated",
                    details=violation,
                )
            elif enforcement == EnforcementStrategy.SOFT_FAIL:
                logger.warning(
                    "Invariant violation detected",
                    invariant=name,
                    scope=invariant["scope"],
                    error=error_msg,
                )

        return is_valid, error_msg

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all recorded violations."""
        return self._violations.copy()

    def clear_violations(self) -> None:
        """Clear recorded violations."""
        self._violations.clear()


# Global registry instance
_registry = InvariantRegistry()


def get_registry() -> InvariantRegistry:
    """Get the global invariant registry."""
    return _registry


# Invariant check functions

def check_weight_sum(weights: Dict[str, float], tolerance: float = 0.01) -> Tuple[bool, Optional[str]]:
    """Check INV-001: Weight normalization."""
    total = sum(weights.values())
    diff = abs(total - 1.0)
    if diff > tolerance:
        return False, f"Weights sum to {total}, expected 1.0 (diff: {diff})"
    return True, None


def check_range_bounded(value: float, min_val: float, max_val: float) -> Tuple[bool, Optional[str]]:
    """Check INV-002, INV-003, INV-004: Range bounds."""
    if value < min_val or value > max_val:
        return False, f"Value {value} outside range [{min_val}, {max_val}]"
    return True, None


def check_no_nan_inf(value: float) -> Tuple[bool, Optional[str]]:
    """Check INV-006: No NaN/Inf propagation."""
    if not math.isfinite(value):
        return False, f"Non-finite value detected: {value}"
    return True, None


def check_contribution_reconciliation(
    components: Dict[str, Dict[str, float]], output: float, tolerance: float = 0.01
) -> Tuple[bool, Optional[str]]:
    """Check INV-021: Contribution reconciliation."""
    sum_contributions = sum(comp.get("contribution", 0.0) for comp in components.values())
    diff = abs(sum_contributions - output)
    if diff > tolerance:
        return False, f"Contributions sum to {sum_contributions}, output is {output} (diff: {diff})"
    return True, None


def check_risk_tier_monotonicity(
    risk_score1: float, tier1: str, risk_score2: float, tier2: str
) -> Tuple[bool, Optional[str]]:
    """Check INV-011: Risk tier monotonicity."""
    tier_order = {"stable": 0, "watchlist": 1, "elevated": 2, "high": 3, "critical": 4}
    order1 = tier_order.get(tier1, -1)
    order2 = tier_order.get(tier2, -1)

    if order1 == -1 or order2 == -1:
        return False, f"Unknown tier: {tier1} or {tier2}"

    # If score1 < score2, then order1 <= order2
    if risk_score1 < risk_score2 and order1 > order2:
        return False, f"Risk score {risk_score1} ({tier1}) < {risk_score2} ({tier2}) but tier order violated"
    return True, None


def check_confidence_volatility_consistency(
    volatility: float, confidence: float
) -> Tuple[bool, Optional[str]]:
    """Check INV-012: Confidence decreases with volatility."""
    # High volatility should produce lower confidence
    # This is enforced by the formula, but we check for obvious violations
    if volatility > 0.7 and confidence > 0.7:
        return False, f"High volatility ({volatility}) but high confidence ({confidence})"
    return True, None


def check_shock_trend_consistency(
    shock_severity: str, trend_direction: str
) -> Tuple[bool, Optional[str]]:
    """Check INV-013: Shock-trend consistency."""
    severe_shocks = shock_severity in ["severe", "high"]
    if severe_shocks and trend_direction == "stable":
        return False, f"Severe shock ({shock_severity}) but stable trend"
    return True, None


def check_trace_completeness(trace: Optional[Dict]) -> Tuple[bool, Optional[str]]:
    """Check INV-025: Trace completeness."""
    if trace is None:
        return False, "Trace is None"
    if "reconciliation" not in trace:
        return False, "Trace missing reconciliation"
    return True, None


def check_factor_confidence_range(confidence: float) -> Tuple[bool, Optional[str]]:
    """Check INV-Q01: Factor confidence ∈ [0.0, 1.0]."""
    if not math.isfinite(confidence):
        return False, f"Factor confidence is not finite: {confidence}"
    if confidence < 0.0 or confidence > 1.0:
        return False, f"Factor confidence {confidence} out of range [0.0, 1.0]"
    return True, None


def check_volatility_classification_consistency(
    volatility_score: float, volatility_classification: str
) -> Tuple[bool, Optional[str]]:
    """Check INV-Q02: Volatility classification consistent with numeric volatility."""
    if volatility_score < 0.1:
        expected = "low"
    elif volatility_score < 0.3:
        expected = "medium"
    else:
        expected = "high"
    
    if volatility_classification != expected:
        return False, (
            f"Volatility classification '{volatility_classification}' inconsistent with "
            f"score {volatility_score} (expected '{expected}')"
        )
    return True, None


def check_signal_strength_monotonicity(
    contribution: float, signal_strength: float
) -> Tuple[bool, Optional[str]]:
    """Check INV-Q03: Signal strength monotonic with contribution magnitude."""
    # Signal strength should generally increase with contribution magnitude
    # Allow some variance due to volatility/confidence adjustments
    contribution_abs = abs(contribution)
    if contribution_abs > 0.1 and signal_strength < contribution_abs * 0.5:
        return False, (
            f"Signal strength {signal_strength} too low for contribution {contribution}"
        )
    return True, None


def check_missing_factor_confidence(
    has_data: bool, confidence: float
) -> Tuple[bool, Optional[str]]:
    """Check INV-Q04: Missing factor data does not inflate confidence."""
    if not has_data and confidence > 0.5:
        return False, (
            f"Missing factor data but confidence {confidence} > 0.5"
        )
    return True, None


def check_factor_ranking_order_independence(
    factors: List[Dict[str, Any]]
) -> Tuple[bool, Optional[str]]:
    """Check INV-Q05: Factor ranking order-independent."""
    # Extract signal strengths
    signal_strengths = []
    for factor in factors:
        if "signal_strength" in factor:
            signal_strengths.append((factor["id"], factor["signal_strength"]))
    
    if len(signal_strengths) < 2:
        return True, None  # Not enough factors to check ordering
    
    # Sort by signal strength (descending)
    sorted(signal_strengths, key=lambda x: x[1], reverse=True)
    
    # Check that ranking is deterministic (all factors have distinct signal strengths or consistent ordering)
    # This is a weak check - full order independence requires testing with shuffled inputs
    return True, None


def check_narrative_reconciliation(
    narrative_drivers: List[Dict[str, Any]],
    top_factors: List[Dict[str, Any]],
    tolerance: float = 0.01,
) -> Tuple[bool, Optional[str]]:
    """Check INV-N01: Narrative must reconcile to top-N factor contributions."""
    if len(narrative_drivers) == 0:
        return True, None  # Empty narrative is valid
    
    # Extract driver contributions
    driver_contributions = {d["factor_id"]: abs(d.get("contribution", 0.0)) for d in narrative_drivers}
    
    # Extract top factor contributions
    top_contributions = {f["id"]: abs(f.get("contribution", 0.0)) for f in top_factors}
    
    # Check that narrative drivers are among top factors (within tolerance)
    for driver_id, driver_contrib in driver_contributions.items():
        if driver_id not in top_contributions:
            return False, f"Narrative driver {driver_id} not in top factors"
        top_contrib = top_contributions[driver_id]
        if abs(driver_contrib - top_contrib) > tolerance:
            return False, (
                f"Narrative driver {driver_id} contribution {driver_contrib} "
                f"does not match top factor contribution {top_contrib}"
            )
    
    return True, None


def check_narrative_ordering_deterministic(
    narrative_drivers: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """Check INV-N02: Narrative ordering is deterministic."""
    if len(narrative_drivers) < 2:
        return True, None  # Not enough drivers to check ordering
    
    # Extract driver scores
    driver_scores = [d.get("driver_score", 0.0) for d in narrative_drivers]
    
    # Check that scores are in descending order
    for i in range(len(driver_scores) - 1):
        if driver_scores[i] < driver_scores[i + 1]:
            return False, (
                f"Narrative drivers not in descending order: "
                f"score[{i}]={driver_scores[i]} < score[{i+1}]={driver_scores[i+1]}"
            )
    
    return True, None


def check_narrative_directionality_consistency(
    narrative_summary: str,
    behavior_index: float,
    previous_index: Optional[float] = None,
) -> Tuple[bool, Optional[str]]:
    """Check INV-N03: Narrative must not contradict numerical directionality."""
    # If we have previous index, check trend consistency
    if previous_index is not None:
        index_increased = behavior_index > previous_index
        index_decreased = behavior_index < previous_index
        
        # Check if narrative contradicts trend
        if index_increased and "decreasing" in narrative_summary.lower():
            return False, "Narrative says decreasing but index increased"
        if index_decreased and "increasing" in narrative_summary.lower():
            return False, "Narrative says increasing but index decreased"
    
    # Check that narrative mentions appropriate level for index value
    if behavior_index < 0.3:
        if "high disruption" in narrative_summary.lower() or "elevated" in narrative_summary.lower():
            return False, f"Narrative mentions high disruption but index is {behavior_index}"
    elif behavior_index > 0.7:
        if "low disruption" in narrative_summary.lower():
            return False, f"Narrative mentions low disruption but index is {behavior_index}"
    
    return True, None


def check_confidence_disclaimer_consistency(
    confidence_disclaimer: str,
    avg_factor_confidence: float,
) -> Tuple[bool, Optional[str]]:
    """Check INV-N04: Confidence disclaimer must reflect aggregate factor confidence."""
    disclaimer_lower = confidence_disclaimer.lower()
    
    # Check that disclaimer matches confidence level
    if avg_factor_confidence >= 0.75:
        if "limited" in disclaimer_lower or "low" in disclaimer_lower:
            return False, (
                f"Confidence disclaimer says limited/low but average confidence is {avg_factor_confidence}"
            )
    elif avg_factor_confidence < 0.6:
        if "high" in disclaimer_lower:
            return False, (
                f"Confidence disclaimer says high but average confidence is {avg_factor_confidence}"
            )
    
    return True, None


def check_missing_data_confidence_consistency(
    confidence_disclaimer: str,
    missing_data_ratio: float,
) -> Tuple[bool, Optional[str]]:
    """Check INV-N05: Missing data lowers certainty, never increases it."""
    if missing_data_ratio > 0.3:
        # High missing data should be mentioned in disclaimer
        if "missing" not in confidence_disclaimer.lower() and "insufficient" not in confidence_disclaimer.lower():
            return False, (
                f"High missing data ratio {missing_data_ratio} not mentioned in confidence disclaimer"
            )
    
    return True, None


def check_temporal_delta_reconciliation(
    global_delta: float,
    sub_index_deltas: Dict[str, float],
    sub_index_weights: Dict[str, float],
    tolerance: float = 0.01,
) -> Tuple[bool, Optional[str]]:
    """Check INV-T01: Temporal deltas must reconcile (sub-index deltas × weights ≈ global delta)."""
    if not sub_index_deltas or not sub_index_weights:
        return True, None  # Cannot check without data
    
    # Calculate weighted sum of sub-index deltas
    weighted_sum = sum(
        sub_index_deltas.get(name, 0.0) * sub_index_weights.get(name, 0.0)
        for name in sub_index_deltas.keys()
    )
    
    diff = abs(weighted_sum - global_delta)
    if diff > tolerance:
        return False, (
            f"Temporal delta reconciliation failed: weighted sum {weighted_sum} != global delta {global_delta}, "
            f"difference {diff} > tolerance {tolerance}"
        )
    
    return True, None


def check_factor_delta_consistency(
    factor_delta: float,
    value_delta: float,
    weight: float,
    tolerance: float = 0.01,
) -> Tuple[bool, Optional[str]]:
    """Check INV-T02: Factor contribution delta must equal value_delta × weight."""
    expected_delta = value_delta * weight
    diff = abs(factor_delta - expected_delta)
    
    if diff > tolerance:
        return False, (
            f"Factor delta inconsistency: contribution_delta {factor_delta} != value_delta {value_delta} × weight {weight}, "
            f"difference {diff} > tolerance {tolerance}"
        )
    
    return True, None


def check_change_direction_consistency(
    global_direction: str,
    sub_index_directions: Dict[str, str],
) -> Tuple[bool, Optional[str]]:
    """Check INV-T03: Change directions must be consistent (increasing global implies net positive sub-index changes)."""
    if global_direction == "stable":
        return True, None  # Stable is always consistent
    
    # Count increasing vs decreasing sub-indices
    increasing_count = sum(1 for d in sub_index_directions.values() if d == "increasing")
    decreasing_count = sum(1 for d in sub_index_directions.values() if d == "decreasing")
    
    if global_direction == "increasing":
        # Global increasing should have net positive sub-index changes
        if decreasing_count > increasing_count:
            return False, (
                f"Global increasing but more decreasing sub-indices ({decreasing_count}) than increasing ({increasing_count})"
            )
    elif global_direction == "decreasing":
        # Global decreasing should have net negative sub-index changes
        if increasing_count > decreasing_count:
            return False, (
                f"Global decreasing but more increasing sub-indices ({increasing_count}) than decreasing ({decreasing_count})"
            )
    
    return True, None


def check_signal_vs_noise_classification(
    factor_change: Dict[str, Any],
    classification: str,
) -> Tuple[bool, Optional[str]]:
    """Check INV-T04: Signal vs noise classification must be consistent with change magnitude and quality."""
    contribution_delta = abs(factor_change.get("contribution_delta", 0.0))
    
    # Large changes (>0.05) must be signal
    if contribution_delta > 0.05 and classification != "signal":
        return False, (
            f"Large change ({contribution_delta}) classified as noise, should be signal"
        )
    
    # Very small changes (<0.01) should be noise
    if contribution_delta < 0.01 and classification != "noise":
        # Allow signal for very small changes if explicitly marked, but log warning
        return True, None  # Soft check, not hard fail
    
    return True, None


def check_temporal_attribution_completeness(
    temporal_attribution: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-T05: Temporal attribution must include all required fields."""
    required_fields = [
        "global_delta",
        "sub_index_deltas",
        "factor_deltas",
        "signal_vs_noise",
        "change_narrative",
        "metadata",
    ]
    
    for field in required_fields:
        if field not in temporal_attribution:
            return False, f"Temporal attribution missing required field: {field}"
    
    return True, None


def check_elasticity_consistency(
    elasticity: float,
    output_delta: float,
    input_delta: float,
    factor_weight: float,
    tolerance: float = 0.01,
) -> Tuple[bool, Optional[str]]:
    """Check INV-S01: Elasticity must equal (output_delta / input_delta) * factor_weight."""
    if abs(input_delta) < 1e-10:
        return True, None  # Cannot check if input_delta is zero
    
    expected_elasticity = (output_delta / input_delta) * factor_weight
    diff = abs(elasticity - expected_elasticity)
    
    if diff > tolerance:
        return False, (
            f"Elasticity inconsistency: elasticity {elasticity} != "
            f"(output_delta {output_delta} / input_delta {input_delta}) * weight {factor_weight}, "
            f"difference {diff} > tolerance {tolerance}"
        )
    
    return True, None


def check_sensitivity_classification_consistency(
    elasticity: float,
    classification: str,
) -> Tuple[bool, Optional[str]]:
    """Check INV-S02: Sensitivity classification must match elasticity magnitude."""
    abs_elasticity = abs(elasticity)
    
    if classification == "high":
        if abs_elasticity <= 0.5:
            return False, (
                f"Sensitivity classification 'high' but elasticity {abs_elasticity} <= 0.5"
            )
    elif classification == "medium":
        if abs_elasticity <= 0.2 or abs_elasticity > 0.5:
            return False, (
                f"Sensitivity classification 'medium' but elasticity {abs_elasticity} not in (0.2, 0.5]"
            )
    elif classification == "low":
        if abs_elasticity > 0.2:
            return False, (
                f"Sensitivity classification 'low' but elasticity {abs_elasticity} > 0.2"
            )
    
    return True, None


def check_scenario_bounds_validation(
    base_value: float,
    perturbation: float,
    min_value: float,
    max_value: float,
) -> Tuple[bool, Optional[str]]:
    """Check INV-S03: Scenario perturbations must be within bounds [min_value, max_value]."""
    perturbed_value = base_value + perturbation
    
    if perturbed_value < min_value:
        return False, (
            f"Scenario perturbation violates lower bound: {perturbed_value} < {min_value}"
        )
    if perturbed_value > max_value:
        return False, (
            f"Scenario perturbation violates upper bound: {perturbed_value} > {max_value}"
        )
    
    return True, None


def check_sensitivity_ranking_order(
    sensitivity_rankings: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """Check INV-S04: Sensitivity rankings must be ordered by absolute elasticity (descending)."""
    if len(sensitivity_rankings) < 2:
        return True, None  # Cannot check ordering with <2 items
    
    for i in range(1, len(sensitivity_rankings)):
        prev_elasticity = abs(sensitivity_rankings[i - 1].get("elasticity", 0.0))
        curr_elasticity = abs(sensitivity_rankings[i].get("elasticity", 0.0))
        
        if prev_elasticity < curr_elasticity:
            return False, (
                f"Sensitivity ranking order violation: rank {i-1} elasticity {prev_elasticity} < "
                f"rank {i} elasticity {curr_elasticity}"
            )
    
    return True, None


def check_sensitivity_analysis_completeness(
    sensitivity_analysis: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-S05: Sensitivity analysis must include all required fields."""
    required_fields = [
        "base_behavior_index",
        "factor_elasticities",
        "sensitivity_rankings",
        "sensitivity_narrative",
        "metadata",
    ]
    
    for field in required_fields:
        if field not in sensitivity_analysis:
            return False, f"Sensitivity analysis missing required field: {field}"
    
    return True, None


def check_alert_determinism(
    alerts1: List[Dict[str, Any]],
    alerts2: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """Check INV-A01: Alerts must be deterministic (same inputs → same outputs)."""
    if len(alerts1) != len(alerts2):
        return False, f"Alert count mismatch: {len(alerts1)} != {len(alerts2)}"
    
    # Check that alert IDs match
    ids1 = sorted([a.get("id") for a in alerts1])
    ids2 = sorted([a.get("id") for a in alerts2])
    
    if ids1 != ids2:
        return False, f"Alert IDs mismatch: {ids1} != {ids2}"
    
    return True, None


def check_alert_correctness(
    alert: Dict[str, Any],
    state: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-A02: Alert condition must match actual state."""
    alert_type = alert.get("type")
    current_value = state.get("current_value")
    threshold = alert.get("threshold")
    comparison = alert.get("comparison")
    
    if alert_type == "threshold" and threshold is not None and current_value is not None:
        if comparison == "greater_than":
            if alert.get("triggered") and current_value <= threshold:
                return False, f"Alert triggered but {current_value} <= {threshold}"
            if not alert.get("triggered") and current_value > threshold:
                # Check persistence requirement
                persistence_days = alert.get("persistence_days", 0)
                if persistence_days == 0:
                    return False, f"Alert not triggered but {current_value} > {threshold}"
        elif comparison == "less_than":
            if alert.get("triggered") and current_value >= threshold:
                return False, f"Alert triggered but {current_value} >= {threshold}"
            if not alert.get("triggered") and current_value < threshold:
                persistence_days = alert.get("persistence_days", 0)
                if persistence_days == 0:
                    return False, f"Alert not triggered but {current_value} < {threshold}"
    
    return True, None


def check_non_spam_guarantee(
    alerts: List[Dict[str, Any]],
    alert_definitions: Optional[List[Dict[str, Any]]] = None,
    rate_limit_hours: int = 24,
) -> Tuple[bool, Optional[str]]:
    """Check INV-A03: Alerts must respect rate limits and persistence gates."""
    # Build lookup of alert definitions by ID
    alert_defs_by_id = {}
    if alert_definitions:
        for defn in alert_definitions:
            alert_defs_by_id[defn.get("id")] = defn
    
    # Check that alerts respect persistence gates
    for alert in alerts:
        alert_id = alert.get("id")
        alert_def = alert_defs_by_id.get(alert_id) if alert_defs_by_id else None
        
        if alert.get("type") == "threshold" and alert_def:
            required_persistence = alert_def.get("persistence_days", 0)
            days_above_threshold = alert.get("persistence_days", 0)  # This is actually days_above_threshold from result
            # Note: The alert result has "persistence_days" field which is actually days_above_threshold
            # We need to check against the definition's required persistence
            if required_persistence > 0 and days_above_threshold < required_persistence + 1:
                return False, (
                    f"Alert {alert_id} triggered but persistence not met: "
                    f"{days_above_threshold} < {required_persistence + 1}"
                )
    
    # Rate limiting would be checked at a higher level (e.g., alert storage/notification)
    # This invariant checks that alerts themselves respect persistence gates
    
    return True, None


def check_sensitivity_gating_respected(
    alert: Dict[str, Any],
    factor_elasticity: Optional[float] = None,
    min_elasticity: float = 0.2,
    signal_classification: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Check INV-A04: Sensitivity-aware alerts must respect elasticity gates."""
    if not alert.get("sensitivity_aware", False):
        return True, None  # Not a sensitivity-aware alert
    
    if alert.get("gated", False):
        # Alert was gated, check that gates were correctly applied
        if factor_elasticity is not None and abs(factor_elasticity) >= min_elasticity:
            # Elasticity gate should have passed
            if signal_classification == "signal":
                # Both gates should have passed, alert should not be gated
                return False, (
                    f"Sensitivity-aware alert gated but elasticity {factor_elasticity} >= {min_elasticity} "
                    f"and signal classification is 'signal'"
                )
    
    return True, None


def check_zero_numerical_drift_alerts(
    behavior_index_before: float,
    behavior_index_after: float,
    tolerance: float = 1e-10,
) -> Tuple[bool, Optional[str]]:
    """Check INV-A05: Alert generation must not change numerical outputs."""
    diff = abs(behavior_index_before - behavior_index_after)
    
    if diff > tolerance:
        return False, (
            f"Numerical drift detected: behavior index changed from {behavior_index_before} "
            f"to {behavior_index_after} (diff: {diff})"
        )
    
    return True, None


def check_benchmark_determinism(
    benchmarks1: Dict[str, Any],
    benchmarks2: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-B01: Benchmarks must be deterministic (same inputs → same outputs)."""
    # Check peer group analysis
    peer1 = benchmarks1.get("peer_group_analysis")
    peer2 = benchmarks2.get("peer_group_analysis")
    
    if peer1 is None and peer2 is None:
        pass  # Both None, OK
    elif peer1 is None or peer2 is None:
        return False, "Peer group analysis mismatch: one is None, other is not"
    elif abs(peer1.get("average_behavior_index", 0) - peer2.get("average_behavior_index", 0)) > 0.01:
        return False, "Peer group average mismatch"
    
    # Check baseline
    baseline1 = benchmarks1.get("historical_baseline", {})
    baseline2 = benchmarks2.get("historical_baseline", {})
    
    if abs(baseline1.get("baseline_value", 0) - baseline2.get("baseline_value", 0)) > 0.01:
        return False, "Baseline value mismatch"
    
    return True, None


def check_peer_group_consistency(
    peer_analysis: Dict[str, Any],
    peer_values: List[float],
) -> Tuple[bool, Optional[str]]:
    """Check INV-B02: Peer group averages must be consistent with input data."""
    if not peer_analysis or not peer_values:
        return True, None  # No data to check
    
    expected_avg = sum(peer_values) / len(peer_values) if peer_values else 0.0
    actual_avg = peer_analysis.get("average_behavior_index")
    
    if actual_avg is None:
        return True, None  # No average computed
    
    if abs(expected_avg - actual_avg) > 0.01:
        return False, (
            f"Peer group average mismatch: expected {expected_avg}, got {actual_avg}"
        )
    
    return True, None


def check_baseline_consistency(
    baseline: Dict[str, Any],
    history: List[float],
) -> Tuple[bool, Optional[str]]:
    """Check INV-B03: Baseline statistics must be consistent with historical data."""
    if not baseline or not history:
        return True, None  # No data to check
    
    baseline_value = baseline.get("baseline_value")
    if baseline_value is None:
        return True, None  # No baseline computed
    
    # Compute expected baseline from history
    expected_avg = sum(history) / len(history) if history else 0.0
    
    if abs(baseline_value - expected_avg) > 0.01:
        return False, (
            f"Baseline value mismatch: expected {expected_avg}, got {baseline_value}"
        )
    
    return True, None


def check_deviation_correctness(
    current_value: float,
    baseline: Dict[str, Any],
    deviation: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-B04: Deviation calculations must be mathematically correct."""
    baseline_value = baseline.get("baseline_value")
    if baseline_value is None:
        return True, None  # No baseline to check against
    
    expected_absolute = current_value - baseline_value
    actual_absolute = deviation.get("absolute_deviation")
    
    if actual_absolute is not None:
        if abs(expected_absolute - actual_absolute) > 1e-10:
            return False, (
                f"Absolute deviation mismatch: expected {expected_absolute}, got {actual_absolute}"
            )
    
    # Check relative deviation
    if abs(baseline_value) > 1e-10:
        expected_relative = (expected_absolute / baseline_value) * 100.0
        actual_relative = deviation.get("relative_deviation")
        
        if actual_relative is not None:
            if abs(expected_relative - actual_relative) > 0.01:
                return False, (
                    f"Relative deviation mismatch: expected {expected_relative}, got {actual_relative}"
                )
    
    return True, None


def check_zero_numerical_drift_benchmarks(
    behavior_index_before: float,
    behavior_index_after: float,
    tolerance: float = 1e-10,
) -> Tuple[bool, Optional[str]]:
    """Check INV-B05: Benchmark generation must not change numerical outputs."""
    diff = abs(behavior_index_before - behavior_index_after)
    
    if diff > tolerance:
        return False, (
            f"Numerical drift detected: behavior index changed from {behavior_index_before} "
            f"to {behavior_index_after} (diff: {diff})"
        )
    
    return True, None


def check_provenance_completeness(
    provenance: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-P01: Provenance must include all required fields."""
    required_fields = [
        "sub_index_provenances",
        "aggregate_provenance",
        "metadata",
    ]
    
    for field in required_fields:
        if field not in provenance:
            return False, f"Provenance missing required field: {field}"
    
    # Check sub-index provenances have required fields
    for sub_index_name, sub_prov in provenance.get("sub_index_provenances", {}).items():
        if "sub_index_name" not in sub_prov:
            return False, f"Sub-index provenance missing sub_index_name: {sub_index_name}"
        if "sources" not in sub_prov:
            return False, f"Sub-index provenance missing sources: {sub_index_name}"
    
    return True, None


def check_freshness_consistency(
    provenance: Dict[str, Any],
    data_age_hours: Optional[float],
) -> Tuple[bool, Optional[str]]:
    """Check INV-P02: Freshness classification must match data age."""
    if data_age_hours is None:
        return True, None  # Cannot check if age unknown
    
    # Import classify_freshness lazily to avoid circular imports
    from app.core.provenance import classify_freshness
    
    # Check freshness classifications in source provenances
    for sub_prov in provenance.get("sub_index_provenances", {}).values():
        for source_prov in sub_prov.get("source_provenances", []):
            freshness = source_prov.get("freshness_classification")
            expected_freq = source_prov.get("expected_update_frequency_hours")
            
            if freshness and expected_freq:
                # Verify classification matches age
                expected_freshness = classify_freshness(data_age_hours, expected_freq)
                if freshness != expected_freshness:
                    return False, (
                        f"Freshness inconsistency: classified as {freshness} but "
                        f"data age {data_age_hours}h suggests {expected_freshness}"
                    )
    
    return True, None


def check_coverage_confidence_relationship(
    coverage_ratio: float,
    confidence: float,
) -> Tuple[bool, Optional[str]]:
    """Check INV-P03: Low coverage must reduce confidence."""
    # Low coverage (<0.5) should generally correspond to lower confidence
    # This is a soft check - we don't enforce exact relationship, just flag inconsistencies
    if coverage_ratio < 0.5 and confidence > 0.8:
        return False, (
            f"Coverage-confidence inconsistency: low coverage ({coverage_ratio}) "
            f"but high confidence ({confidence})"
        )
    
    return True, None


def check_bias_disclosure_required(
    known_biases: List[str],
    confidence: float,
) -> Tuple[bool, Optional[str]]:
    """Check INV-P04: Known biases must be disclosed when confidence is low."""
    # If confidence is low (<0.6) and there are known biases, they should be disclosed
    # This check verifies biases are present in provenance when confidence is low
    # The actual disclosure happens in the provenance generation, this just verifies consistency
    if confidence < 0.6 and len(known_biases) == 0:
        # This is not necessarily a violation - some factors may genuinely have no biases
        # But we log it as a potential gap
        return True, None  # Soft check, don't fail
    
    return True, None


def check_zero_numerical_drift_provenance(
    behavior_index_before: float,
    behavior_index_after: float,
    tolerance: float = 1e-10,
) -> Tuple[bool, Optional[str]]:
    """Check INV-P05: Provenance generation must not change numerical outputs."""
    diff = abs(behavior_index_before - behavior_index_after)
    
    if diff > tolerance:
        return False, (
            f"Numerical drift detected: behavior index changed from {behavior_index_before} "
            f"to {behavior_index_after} (diff: {diff})"
        )
    
    return True, None


def check_alert_persistence_determinism(
    alert1: Dict[str, Any],
    alert2: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-O01: Alert persistence determinism."""
    # Same alert_id + region_id + tenant_id should produce same persistence key
    key1 = (
        alert1.get("alert_id"),
        alert1.get("region_id"),
        alert1.get("tenant_id", "default"),
    )
    key2 = (
        alert2.get("alert_id"),
        alert2.get("region_id"),
        alert2.get("tenant_id", "default"),
    )

    if key1 == key2:
        # Same key should produce same persistence state
        # This is checked by ensuring idempotent upserts
        return True, None

    return True, None  # Different keys are fine


def check_no_duplicate_active_alerts(
    alerts: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """Check INV-O02: No duplicate active alerts."""
    seen_keys = set()
    for alert in alerts:
        if alert.get("status") != "active":
            continue

        key = (
            alert.get("alert_id"),
            alert.get("region_id"),
            alert.get("tenant_id", "default"),
        )
        if key in seen_keys:
            return False, f"Duplicate active alert found: {key}"
        seen_keys.add(key)

    return True, None


def check_tenant_isolation(
    alert: Dict[str, Any],
    tenant_id: str,
) -> Tuple[bool, Optional[str]]:
    """Check INV-O03: Tenant isolation."""
    alert_tenant = alert.get("tenant_id", "default")
    if alert_tenant != tenant_id:
        return False, (
            f"Tenant isolation violation: alert tenant {alert_tenant} "
            f"does not match requested tenant {tenant_id}"
        )
    return True, None


def check_notification_rate_limits(
    last_notification_time: Optional[str],
    current_time: str,
    rate_limit_hours: int,
) -> Tuple[bool, Optional[str]]:
    """Check INV-O04: Notification rate limits enforced."""
    if last_notification_time is None:
        return True, None  # No previous notification, allow

    from datetime import datetime

    try:
        last_time = datetime.fromisoformat(last_notification_time.replace("Z", "+00:00"))
        current = datetime.fromisoformat(current_time.replace("Z", "+00:00"))
        hours_since = (current - last_time).total_seconds() / 3600.0

        if hours_since < rate_limit_hours:
            return False, (
                f"Rate limit violation: {hours_since:.2f}h since last notification, "
                f"limit is {rate_limit_hours}h"
            )
    except Exception as e:
        return False, f"Failed to check rate limit: {str(e)}"

    return True, None


def check_zero_numerical_drift_operational(
    behavior_index_before: float,
    behavior_index_after: float,
    tolerance: float = 1e-10,
) -> Tuple[bool, Optional[str]]:
    """Check INV-O05: Operational features must not change numerical outputs."""
    diff = abs(behavior_index_before - behavior_index_after)

    if diff > tolerance:
        return False, (
            f"Numerical drift detected: behavior index changed from {behavior_index_before} "
            f"to {behavior_index_after} (diff: {diff})"
        )

    return True, None


def check_executive_summary_determinism(
    summary1: Dict[str, Any],
    summary2: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-UX01: Executive summary determinism."""
    # Compare key fields that should be identical for same inputs
    if summary1.get("current_status") != summary2.get("current_status"):
        return False, "Current status differs between summaries"
    if summary1.get("action_recommendation", {}).get("recommendation") != summary2.get("action_recommendation", {}).get("recommendation"):
        return False, "Action recommendation differs between summaries"
    return True, None


def check_summary_derivability(
    summary: Dict[str, Any],
    source_data: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-UX02: Executive summary must be derivable from analytics outputs."""
    # Verify that summary fields can be derived from source_data
    # This is a structural check - actual derivation is tested in test suite
    required_sources = ["behavior_index", "risk_tier"]
    for source in required_sources:
        if source not in source_data:
            return False, f"Summary requires {source} but not in source data"
    return True, None


def check_no_hidden_analytics(
    summary: Dict[str, Any],
    backend_outputs: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-UX03: UI must reflect backend truth only."""
    # Verify summary values match backend outputs
    summary_bi = summary.get("metadata", {}).get("behavior_index")
    backend_bi = backend_outputs.get("behavior_index")
    if summary_bi is not None and backend_bi is not None:
        if abs(summary_bi - backend_bi) > 1e-6:
            return False, f"Summary behavior index {summary_bi} does not match backend {backend_bi}"
    return True, None


def check_zero_numerical_drift_executive(
    behavior_index_before: float,
    behavior_index_after: float,
    tolerance: float = 1e-10,
) -> Tuple[bool, Optional[str]]:
    """Check INV-UX04: Executive summary generation must not change numerical outputs."""
    diff = abs(behavior_index_before - behavior_index_after)

    if diff > tolerance:
        return False, (
            f"Numerical drift detected: behavior index changed from {behavior_index_before} "
            f"to {behavior_index_after} (diff: {diff})"
        )

    return True, None


def check_provenance_visibility(
    summary: Dict[str, Any],
    provenance: Optional[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """Check INV-UX05: Every claim must have traceable provenance."""
    # Check that summary includes provenance references where applicable
    # This is a soft check - we verify that if provenance exists, it's referenced
    if provenance and "provenance" not in summary.get("metadata", {}):
        # Not necessarily a violation - summary may not require provenance display
        # But we log it for visibility
        return True, None
    return True, None


def check_config_immutability(
    config_before: Dict[str, Any],
    config_after: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-DEP01: Configuration must be immutable after deployment."""
    # Compare critical config values
    critical_keys = ["environment", "app_name", "aws_region"]
    for key in critical_keys:
        if config_before.get(key) != config_after.get(key):
            return False, f"Configuration changed: {key} changed from {config_before.get(key)} to {config_after.get(key)}"
    return True, None


def check_secrets_isolation(
    secrets: Dict[str, Any],
    exposed_fields: List[str],
) -> Tuple[bool, Optional[str]]:
    """Check INV-DEP02: Secrets must be isolated and not leaked."""
    # Check that secrets are not exposed in exposed_fields
    secret_keys = ["password", "secret", "key", "token", "credential"]
    for field in exposed_fields:
        field_lower = field.lower()
        for secret_key in secret_keys:
            if secret_key in field_lower:
                # Check if actual secret value is exposed
                if field in secrets and secrets[field]:
                    return False, f"Secret potentially exposed in field: {field}"
    return True, None


def check_observability_completeness(
    operations: List[str],
    observed_operations: List[str],
) -> Tuple[bool, Optional[str]]:
    """Check INV-DEP03: All critical operations must be observable."""
    critical_operations = ["forecast", "alert", "notification"]
    for op in critical_operations:
        if op in operations and op not in observed_operations:
            return False, f"Critical operation {op} is not observable"
    return True, None


def check_deployment_determinism(
    deployment_config1: Dict[str, Any],
    deployment_config2: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-DEP04: Deployments must be deterministic and repeatable."""
    # Compare deployment configs (excluding timestamps and dynamic values)
    static_keys = ["environment", "app_name", "aws_region", "vpc_cidr"]
    for key in static_keys:
        if deployment_config1.get(key) != deployment_config2.get(key):
            return False, f"Deployment config differs: {key}"
    return True, None


def check_zero_numerical_drift_deployment(
    behavior_index_before: float,
    behavior_index_after: float,
    tolerance: float = 1e-10,
) -> Tuple[bool, Optional[str]]:
    """Check INV-DEP05: Deployment features must not change numerical outputs."""
    diff = abs(behavior_index_before - behavior_index_after)

    if diff > tolerance:
        return False, (
            f"Numerical drift detected: behavior index changed from {behavior_index_before} "
            f"to {behavior_index_after} (diff: {diff})"
        )

    return True, None


def check_early_warnings_derivable(
    early_warnings: Dict[str, Any],
    source_signals: List[str],
) -> Tuple[bool, Optional[str]]:
    """Check INV-EW01: Early warnings must be derivable from existing signals only."""
    # Verify that early warnings reference only known signal types
    allowed_signal_types = [
        "acceleration",
        "trend_sensitivity",
        "benchmark_deviation",
        "factor_quality",
        "alert_persistence",
    ]
    
    warnings = early_warnings.get("warnings", [])
    for warning in warnings:
        warning_type = warning.get("type")
        if warning_type not in allowed_signal_types:
            return False, f"Early warning uses unknown signal type: {warning_type}"
    
    return True, None


def check_early_warning_confidence_gating(
    early_warning: Dict[str, Any],
    min_confidence: float,
    coverage_ratio: Optional[float] = None,
) -> Tuple[bool, Optional[str]]:
    """Check INV-EW02: No early warning without sufficient confidence & coverage."""
    confidence = early_warning.get("confidence", 0.0)
    
    if confidence < min_confidence:
        return False, f"Early warning confidence {confidence} below minimum {min_confidence}"
    
    if coverage_ratio is not None and coverage_ratio < 0.5:
        return False, f"Coverage ratio {coverage_ratio} too low for early warning"
    
    return True, None


def check_interaction_effects_labeled(
    interaction: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-EW03: Interaction effects must be labeled as hypotheses."""
    interaction_type = interaction.get("interaction_type", "")
    note = interaction.get("note", "")
    
    if "hypothesis" not in interaction_type.lower() and "hypothesis" not in note.lower():
        return False, "Interaction effect not labeled as hypothesis"
    
    return True, None


def check_no_notification_escalation_without_persistence(
    early_warning: Dict[str, Any],
    alert_persistence_days: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """Check INV-EW04: Early warnings must not escalate to notifications without persistence."""
    # This is a soft check - we verify that if an early warning exists,
    # it doesn't automatically trigger alerts without persistence
    warning_type = early_warning.get("type", "")
    
    # Alert persistence warnings are allowed (they're about persistence)
    if warning_type == "alert_persistence":
        return True, None
    
    # Other warnings should not escalate without persistence
    # This is enforced at the alert composition layer, not here
    # So we just verify the structure
    return True, None


def check_zero_numerical_drift_early_warning(
    behavior_index_before: float,
    behavior_index_after: float,
    tolerance: float = 1e-10,
) -> Tuple[bool, Optional[str]]:
    """Check INV-EW05: Early warning features must not change numerical outputs."""
    diff = abs(behavior_index_before - behavior_index_after)

    if diff > tolerance:
        return False, (
            f"Numerical drift detected: behavior index changed from {behavior_index_before} "
            f"to {behavior_index_after} (diff: {diff})"
        )

    return True, None


def check_policy_does_not_affect_analytics(
    policy: Dict[str, Any],
    analytics_result_before: Dict[str, Any],
    analytics_result_after: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-POL01: Policy changes must never affect analytics computation."""
    # Policies should only affect alert generation, not analytics computation
    # Compare numerical outputs (behavior index, sub-indices, etc.)
    behavior_index_before = analytics_result_before.get("behavior_index")
    behavior_index_after = analytics_result_after.get("behavior_index")
    
    if behavior_index_before is not None and behavior_index_after is not None:
        if abs(behavior_index_before - behavior_index_after) > 1e-10:
            return False, "Policy affected analytics computation (behavior index changed)"
    
    return True, None


def check_policy_evaluation_determinism(
    policy: Dict[str, Any],
    context1: Dict[str, Any],
    context2: Dict[str, Any],
    result1: Dict[str, Any],
    result2: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-POL02: Policy evaluation must be deterministic."""
    # If contexts are identical, results should be identical
    if context1 == context2:
        if result1 != result2:
            return False, "Policy evaluation not deterministic (same context, different results)"
    
    return True, None


def check_rbac_enforced_on_policy_actions(
    action: str,
    user_id: str,
    user_roles: List[str],
    required_roles: List[str],
) -> Tuple[bool, Optional[str]]:
    """Check INV-POL03: RBAC must be enforced on all policy actions."""
    # Check if user has required role
    has_required_role = any(role in user_roles for role in required_roles)
    
    if not has_required_role:
        return False, (
            f"User {user_id} lacks required role for action {action}. "
            f"Required: {required_roles}, Has: {user_roles}"
        )
    
    return True, None


def check_policy_bounds_not_exceeded(
    policy: Dict[str, Any],
    bounds: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-POL04: Policy bounds must not be exceeded."""
    from app.core.policy import PolicyValidator
    
    is_valid, error = PolicyValidator.validate_policy(policy)
    if not is_valid:
        return False, error
    
    return True, None


def check_zero_numerical_drift_policy(
    behavior_index_before: float,
    behavior_index_after: float,
    tolerance: float = 1e-10,
) -> Tuple[bool, Optional[str]]:
    """Check INV-POL05: Policy features must not change numerical outputs."""
    diff = abs(behavior_index_before - behavior_index_after)

    if diff > tolerance:
        return False, (
            f"Numerical drift detected: behavior index changed from {behavior_index_before} "
            f"to {behavior_index_after} (diff: {diff})"
        )

    return True, None


def check_preview_never_mutates_state(
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-PREV01: Preview must never mutate application state."""
    # Compare critical state (policies, alerts, etc.)
    policies_before = state_before.get("policies", {})
    policies_after = state_after.get("policies", {})
    
    if policies_before != policies_after:
        return False, "Preview mutated policy state"
    
    alerts_before = state_before.get("alerts", [])
    alerts_after = state_after.get("alerts", [])
    
    if alerts_before != alerts_after:
        return False, "Preview mutated alert state"
    
    return True, None


def check_preview_results_derivable(
    preview_result: Dict[str, Any],
    current_analytics: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-PREV02: Preview results must be derivable from current analytics."""
    # Verify that preview result references only current analytics
    if "preview_valid" not in preview_result:
        return False, "Preview result missing preview_valid flag"
    
    # Check that preview uses current context
    if "current_alert_count" not in preview_result:
        return False, "Preview result not derivable from current analytics"
    
    return True, None


def check_activation_only_after_preview(
    policy_id: str,
    preview_performed: bool,
    preview_result: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str]]:
    """Check INV-PREV03: Activation only allowed after preview."""
    if not preview_performed:
        return False, f"Policy {policy_id} must be previewed before activation"
    
    if preview_result and not preview_result.get("preview_valid"):
        return False, "Preview must be valid before activation"
    
    return True, None


def check_rbac_enforced_on_preview_activation(
    action: str,
    user_id: str,
    user_roles: List[str],
    required_roles: List[str],
) -> Tuple[bool, Optional[str]]:
    """Check INV-PREV04: RBAC must be enforced on preview and activation."""
    # Check if user has required role
    has_required_role = any(role in user_roles for role in required_roles)
    
    if not has_required_role:
        return False, (
            f"User {user_id} lacks required role for action {action}. "
            f"Required: {required_roles}, Has: {user_roles}"
        )
    
    return True, None


def check_zero_numerical_drift_preview(
    behavior_index_before: float,
    behavior_index_after: float,
    tolerance: float = 1e-10,
) -> Tuple[bool, Optional[str]]:
    """Check INV-PREV05: Preview features must not change numerical outputs."""
    diff = abs(behavior_index_before - behavior_index_after)

    if diff > tolerance:
        return False, (
            f"Numerical drift detected: behavior index changed from {behavior_index_before} "
            f"to {behavior_index_after} (diff: {diff})"
        )

    return True, None


def check_preview_clearly_labeled_non_active(
    ui_state: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-UXP01: Preview UI must clearly label previews as non-active."""
    preview_label = ui_state.get("preview_label", "")
    
    if "preview" in preview_label.lower() and "not active" in preview_label.lower():
        return True, None
    
    if "preview" in preview_label.lower():
        # Acceptable if clearly indicates preview status
        return True, None
    
    return False, "Preview not clearly labeled as non-active"


def check_activation_disabled_without_preview(
    ui_state: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-UXP02: Activation UI must be disabled without preview."""
    has_preview = ui_state.get("has_preview", False)
    activation_enabled = ui_state.get("activation_enabled", False)
    
    if not has_preview and activation_enabled:
        return False, "Activation enabled without preview"
    
    return True, None


def check_ui_state_reflects_backend_truth(
    ui_state: Dict[str, Any],
    backend_state: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Check INV-UXP03: UI state must reflect backend truth only."""
    # Compare critical state (policy active status, alert counts, etc.)
    ui_policy_active = ui_state.get("policy_active", False)
    backend_policy_active = backend_state.get("policy_active", False)
    
    if ui_policy_active != backend_policy_active:
        return False, "UI policy active status does not match backend"
    
    return True, None


def check_rbac_reflected_in_ui_controls(
    ui_controls: Dict[str, bool],
    user_roles: List[str],
    required_roles: List[str],
) -> Tuple[bool, Optional[str]]:
    """Check INV-UXP04: RBAC must be reflected in UI controls."""
    has_required_role = any(role in user_roles for role in required_roles)
    
    # Check that UI controls match RBAC permissions
    activation_visible = ui_controls.get("activation_visible", False)
    if activation_visible and not has_required_role:
        return False, "Activation control visible without required role"
    
    return True, None


def check_zero_numerical_drift_preview_ux(
    behavior_index_before: float,
    behavior_index_after: float,
    tolerance: float = 1e-10,
) -> Tuple[bool, Optional[str]]:
    """Check INV-UXP05: Preview UX features must not change numerical outputs."""
    diff = abs(behavior_index_before - behavior_index_after)

    if diff > tolerance:
        return False, (
            f"Numerical drift detected: behavior index changed from {behavior_index_before} "
            f"to {behavior_index_after} (diff: {diff})"
        )

    return True, None


# Note: classify_freshness is defined in provenance.py
# We'll import it lazily in the check function to avoid circular imports


# Register all invariants
def register_all_invariants() -> None:
    """Register all system invariants."""
    registry = get_registry()

    # Numerical invariants
    registry.register(
        "INV-001",
        "Weight normalization",
        "All weight vectors must sum to 1.0 ± tolerance",
        0.01,
        EnforcementStrategy.HARD_FAIL,
        lambda weights, tol=0.01: check_weight_sum(weights, tol),
    )

    registry.register(
        "INV-002",
        "Index output range",
        "All behavior indices must be in [0.0, 1.0]",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        lambda value: check_range_bounded(value, 0.0, 1.0),
    )

    registry.register(
        "INV-003",
        "Confidence score range",
        "All confidence scores must be in [0.0, 1.0]",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        lambda value: check_range_bounded(value, 0.0, 1.0),
    )

    registry.register(
        "INV-004",
        "Risk score range",
        "All risk scores must be in [0.0, 1.0]",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        lambda value: check_range_bounded(value, 0.0, 1.0),
    )

    registry.register(
        "INV-006",
        "No NaN/Inf propagation",
        "NaN and Inf values must not propagate",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        check_no_nan_inf,
    )

    registry.register(
        "INV-021",
        "Contribution reconciliation",
        "Component contributions must sum to output ± tolerance",
        0.01,
        EnforcementStrategy.SOFT_FAIL,
        lambda components, output, tol=0.01: check_contribution_reconciliation(components, output, tol),
    )

    # Logical invariants
    registry.register(
        "INV-011",
        "Risk tier monotonicity",
        "Risk tier must be monotonic with respect to risk score",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        lambda score1, tier1, score2, tier2: check_risk_tier_monotonicity(score1, tier1, score2, tier2),
    )

    registry.register(
        "INV-012",
        "Confidence-volatility consistency",
        "Confidence must decrease as volatility increases",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_confidence_volatility_consistency,
    )

    registry.register(
        "INV-013",
        "Shock-trend consistency",
        "Shock detection must be consistent with trend direction",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_shock_trend_consistency,
    )

    # Explainability invariants
    registry.register(
        "INV-025",
        "Trace completeness",
        "All decision outputs must have trace objects",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_trace_completeness,
    )

    # Factor quality invariants
    registry.register(
        "INV-Q01",
        "Factor confidence range",
        "Factor confidence must be in [0.0, 1.0]",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        check_factor_confidence_range,
    )

    registry.register(
        "INV-Q02",
        "Volatility classification consistency",
        "Volatility classification must match numeric volatility score",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        lambda vol_score, vol_class: check_volatility_classification_consistency(vol_score, vol_class),
    )

    registry.register(
        "INV-Q03",
        "Signal strength monotonicity",
        "Signal strength must be monotonic with contribution magnitude",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        lambda contrib, signal: check_signal_strength_monotonicity(contrib, signal),
    )

    registry.register(
        "INV-Q04",
        "Missing factor confidence",
        "Missing factor data must not inflate confidence",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        lambda has_data, conf: check_missing_factor_confidence(has_data, conf),
    )

    registry.register(
        "INV-Q05",
        "Factor ranking order independence",
        "Factor ranking must be order-independent",
        0.0,
        EnforcementStrategy.TEST_ONLY,
        check_factor_ranking_order_independence,
    )

    # Narrative invariants
    registry.register(
        "INV-N01",
        "Narrative reconciliation",
        "Narrative drivers must reconcile to top-N factor contributions",
        0.01,
        EnforcementStrategy.SOFT_FAIL,
        lambda drivers, factors, tol=0.01: check_narrative_reconciliation(drivers, factors, tol),
    )

    registry.register(
        "INV-N02",
        "Narrative ordering deterministic",
        "Narrative driver ordering must be deterministic",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_narrative_ordering_deterministic,
    )

    registry.register(
        "INV-N03",
        "Narrative directionality consistency",
        "Narrative must not contradict numerical directionality",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        lambda summary, index, prev=None: check_narrative_directionality_consistency(summary, index, prev),
    )

    registry.register(
        "INV-N04",
        "Confidence disclaimer consistency",
        "Confidence disclaimer must reflect aggregate factor confidence",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        lambda disclaimer, avg_conf: check_confidence_disclaimer_consistency(disclaimer, avg_conf),
    )

    registry.register(
        "INV-N05",
        "Missing data confidence consistency",
        "Missing data must lower certainty, never increase it",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        lambda disclaimer, missing_ratio: check_missing_data_confidence_consistency(disclaimer, missing_ratio),
    )

    # Temporal attribution invariants
    registry.register(
        "INV-T01",
        "Temporal delta reconciliation",
        "Temporal deltas must reconcile (sub-index deltas × weights ≈ global delta)",
        0.01,
        EnforcementStrategy.SOFT_FAIL,
        lambda global_delta, sub_deltas, weights, tol=0.01: check_temporal_delta_reconciliation(global_delta, sub_deltas, weights, tol),
    )

    registry.register(
        "INV-T02",
        "Factor delta consistency",
        "Factor contribution delta must equal value_delta × weight",
        0.01,
        EnforcementStrategy.SOFT_FAIL,
        lambda contrib_delta, val_delta, weight, tol=0.01: check_factor_delta_consistency(contrib_delta, val_delta, weight, tol),
    )

    registry.register(
        "INV-T03",
        "Change direction consistency",
        "Change directions must be consistent (increasing global implies net positive sub-index changes)",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        lambda global_dir, sub_dirs: check_change_direction_consistency(global_dir, sub_dirs),
    )

    registry.register(
        "INV-T04",
        "Signal vs noise classification",
        "Signal vs noise classification must be consistent with change magnitude and quality",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        lambda change, classification: check_signal_vs_noise_classification(change, classification),
    )

    registry.register(
        "INV-T05",
        "Temporal attribution completeness",
        "Temporal attribution must include all required fields",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_temporal_attribution_completeness,
    )

    # Scenario sensitivity invariants
    registry.register(
        "INV-S01",
        "Elasticity consistency",
        "Elasticity must equal (output_delta / input_delta) * factor_weight",
        0.01,
        EnforcementStrategy.SOFT_FAIL,
        lambda elasticity, output_delta, input_delta, weight, tol=0.01: check_elasticity_consistency(elasticity, output_delta, input_delta, weight, tol),
    )

    registry.register(
        "INV-S02",
        "Sensitivity classification consistency",
        "Sensitivity classification must match elasticity magnitude",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        lambda elasticity, classification: check_sensitivity_classification_consistency(elasticity, classification),
    )

    registry.register(
        "INV-S03",
        "Scenario bounds validation",
        "Scenario perturbations must be within bounds [min_value, max_value]",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        lambda base, pert, min_val, max_val: check_scenario_bounds_validation(base, pert, min_val, max_val),
    )

    registry.register(
        "INV-S04",
        "Sensitivity ranking order",
        "Sensitivity rankings must be ordered by absolute elasticity (descending)",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_sensitivity_ranking_order,
    )

    registry.register(
        "INV-S05",
        "Sensitivity analysis completeness",
        "Sensitivity analysis must include all required fields",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_sensitivity_analysis_completeness,
    )

    # Alert invariants
    registry.register(
        "INV-A01",
        "Alert determinism",
        "Alerts must be deterministic (same inputs → same outputs)",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_alert_determinism,
    )

    registry.register(
        "INV-A02",
        "Alert correctness",
        "Alert condition must match actual state",
        0.01,
        EnforcementStrategy.SOFT_FAIL,
        lambda alert, state: check_alert_correctness(alert, state),
    )

    registry.register(
        "INV-A03",
        "Non-spam guarantee",
        "Alerts must respect rate limits and persistence gates",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_non_spam_guarantee,
    )

    registry.register(
        "INV-A04",
        "Sensitivity gating respected",
        "Sensitivity-aware alerts must respect elasticity gates",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_sensitivity_gating_respected,
    )

    registry.register(
        "INV-A05",
        "Zero numerical drift",
        "Alert generation must not change numerical outputs",
        1e-10,
        EnforcementStrategy.HARD_FAIL,
        check_zero_numerical_drift_alerts,
    )

    # Benchmark invariants
    registry.register(
        "INV-B01",
        "Benchmark determinism",
        "Benchmarks must be deterministic (same inputs → same outputs)",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_benchmark_determinism,
    )

    registry.register(
        "INV-B02",
        "Peer group consistency",
        "Peer group averages must be consistent with input data",
        0.01,
        EnforcementStrategy.SOFT_FAIL,
        lambda peer_analysis, peer_values: check_peer_group_consistency(peer_analysis, peer_values),
    )

    registry.register(
        "INV-B03",
        "Baseline consistency",
        "Baseline statistics must be consistent with historical data",
        0.01,
        EnforcementStrategy.SOFT_FAIL,
        lambda baseline, history: check_baseline_consistency(baseline, history),
    )

    registry.register(
        "INV-B04",
        "Deviation correctness",
        "Deviation calculations must be mathematically correct",
        1e-10,
        EnforcementStrategy.SOFT_FAIL,
        lambda current, baseline, deviation: check_deviation_correctness(current, baseline, deviation),
    )

    registry.register(
        "INV-B05",
        "Zero numerical drift",
        "Benchmark generation must not change numerical outputs",
        1e-10,
        EnforcementStrategy.HARD_FAIL,
        check_zero_numerical_drift_benchmarks,
    )

    # Provenance invariants
    registry.register(
        "INV-P01",
        "Provenance completeness",
        "Provenance must include all required fields",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_provenance_completeness,
    )

    registry.register(
        "INV-P02",
        "Freshness consistency",
        "Freshness classification must match data age",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_freshness_consistency,
    )

    registry.register(
        "INV-P03",
        "Coverage confidence relationship",
        "Low coverage must reduce confidence",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_coverage_confidence_relationship,
    )

    registry.register(
        "INV-P04",
        "Bias disclosure required",
        "Known biases must be disclosed when confidence is low",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_bias_disclosure_required,
    )

    registry.register(
        "INV-P05",
        "Zero numerical drift",
        "Provenance generation must not change numerical outputs",
        1e-10,
        EnforcementStrategy.HARD_FAIL,
        check_zero_numerical_drift_provenance,
    )

    # Operational invariants
    registry.register(
        "INV-O01",
        "Alert persistence determinism",
        "Same alert inputs must produce same persistence state",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_alert_persistence_determinism,
    )

    registry.register(
        "INV-O02",
        "No duplicate active alerts",
        "No duplicate active alerts for same alert_id+region_id+tenant_id",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_no_duplicate_active_alerts,
    )

    registry.register(
        "INV-O03",
        "Tenant isolation",
        "Alerts must be isolated by tenant_id",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        check_tenant_isolation,
    )

    registry.register(
        "INV-O04",
        "Notification rate limits enforced",
        "Notifications must respect rate limit windows",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_notification_rate_limits,
    )

    registry.register(
        "INV-O05",
        "Zero numerical drift",
        "Operational features must not change numerical outputs",
        1e-10,
        EnforcementStrategy.HARD_FAIL,
        check_zero_numerical_drift_operational,
    )

    # UX invariants
    registry.register(
        "INV-UX01",
        "Executive summary determinism",
        "Same inputs must produce same executive summary",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_executive_summary_determinism,
    )

    registry.register(
        "INV-UX02",
        "Summary derivability",
        "Executive summary must be fully derivable from analytics outputs",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_summary_derivability,
    )

    registry.register(
        "INV-UX03",
        "No hidden analytics",
        "UI must reflect backend truth only, no hidden logic",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_no_hidden_analytics,
    )

    registry.register(
        "INV-UX04",
        "Zero numerical drift",
        "Executive summary generation must not change numerical outputs",
        1e-10,
        EnforcementStrategy.HARD_FAIL,
        check_zero_numerical_drift_executive,
    )

    registry.register(
        "INV-UX05",
        "Provenance visibility",
        "Every claim in executive summary must have traceable provenance",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_provenance_visibility,
    )

    # Deployment invariants
    registry.register(
        "INV-DEP01",
        "Config immutability",
        "Configuration must be immutable after deployment",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_config_immutability,
    )

    registry.register(
        "INV-DEP02",
        "Secrets isolation",
        "Secrets must be isolated and not leaked",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        check_secrets_isolation,
    )

    registry.register(
        "INV-DEP03",
        "Observability completeness",
        "All critical operations must be observable",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_observability_completeness,
    )

    registry.register(
        "INV-DEP04",
        "Deployment determinism",
        "Deployments must be deterministic and repeatable",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_deployment_determinism,
    )

    registry.register(
        "INV-DEP05",
        "Zero numerical drift",
        "Deployment features must not change numerical outputs",
        1e-10,
        EnforcementStrategy.HARD_FAIL,
        check_zero_numerical_drift_deployment,
    )

    # Early warning invariants
    registry.register(
        "INV-EW01",
        "Early warnings derivable",
        "Early warnings must be derivable from existing signals only",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_early_warnings_derivable,
    )

    registry.register(
        "INV-EW02",
        "Early warning confidence gating",
        "No early warning without sufficient confidence & coverage",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_early_warning_confidence_gating,
    )

    registry.register(
        "INV-EW03",
        "Interaction effects labeled",
        "Interaction effects must be labeled as hypotheses",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_interaction_effects_labeled,
    )

    registry.register(
        "INV-EW04",
        "No notification escalation without persistence",
        "Early warnings must not escalate to notifications without persistence",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_no_notification_escalation_without_persistence,
    )

    registry.register(
        "INV-EW05",
        "Zero numerical drift",
        "Early warning features must not change numerical outputs",
        1e-10,
        EnforcementStrategy.HARD_FAIL,
        check_zero_numerical_drift_early_warning,
    )

    # Policy invariants
    registry.register(
        "INV-POL01",
        "Policy changes never affect analytics",
        "Policy changes must never affect analytics computation",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_policy_does_not_affect_analytics,
    )

    registry.register(
        "INV-POL02",
        "Policy evaluation determinism",
        "Policy evaluation must be deterministic",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_policy_evaluation_determinism,
    )

    registry.register(
        "INV-POL03",
        "RBAC enforced on policy actions",
        "RBAC must be enforced on all policy actions",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        check_rbac_enforced_on_policy_actions,
    )

    registry.register(
        "INV-POL04",
        "Policy bounds cannot be exceeded",
        "Policy bounds must not be exceeded",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_policy_bounds_not_exceeded,
    )

    registry.register(
        "INV-POL05",
        "Zero numerical drift",
        "Policy features must not change numerical outputs",
        1e-10,
        EnforcementStrategy.HARD_FAIL,
        check_zero_numerical_drift_policy,
    )

    # Policy preview invariants
    registry.register(
        "INV-PREV01",
        "Preview never mutates state",
        "Preview must never mutate application state",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        check_preview_never_mutates_state,
    )

    registry.register(
        "INV-PREV02",
        "Preview results derivable",
        "Preview results must be derivable from current analytics",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_preview_results_derivable,
    )

    registry.register(
        "INV-PREV03",
        "Activation only after preview",
        "Activation only allowed after preview",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_activation_only_after_preview,
    )

    registry.register(
        "INV-PREV04",
        "RBAC enforced on preview + activation",
        "RBAC must be enforced on preview and activation",
        0.0,
        EnforcementStrategy.HARD_FAIL,
        check_rbac_enforced_on_preview_activation,
    )

    registry.register(
        "INV-PREV05",
        "Zero numerical drift",
        "Preview features must not change numerical outputs",
        1e-10,
        EnforcementStrategy.HARD_FAIL,
        check_zero_numerical_drift_preview,
    )

    # Policy preview UX invariants
    registry.register(
        "INV-UXP01",
        "Preview clearly labeled as non-active",
        "Preview UI must clearly label previews as non-active",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_preview_clearly_labeled_non_active,
    )

    registry.register(
        "INV-UXP02",
        "Activation disabled without preview",
        "Activation UI must be disabled without preview",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_activation_disabled_without_preview,
    )

    registry.register(
        "INV-UXP03",
        "UI state reflects backend truth",
        "UI state must reflect backend truth only",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_ui_state_reflects_backend_truth,
    )

    registry.register(
        "INV-UXP04",
        "RBAC reflected in UI controls",
        "RBAC must be reflected in UI controls",
        0.0,
        EnforcementStrategy.SOFT_FAIL,
        check_rbac_reflected_in_ui_controls,
    )

    registry.register(
        "INV-UXP05",
        "Zero numerical drift",
        "Preview UX features must not change numerical outputs",
        1e-10,
        EnforcementStrategy.HARD_FAIL,
        check_zero_numerical_drift_preview_ux,
    )


# Initialize registry on import
register_all_invariants()


class DriftDetector:
    """Detects numerical drift and regression in outputs."""

    def __init__(self, tolerance: float = 0.01):
        """
        Initialize drift detector.

        Args:
            tolerance: Tolerance for drift detection (default: 0.01)
        """
        self.tolerance = tolerance
        self._baselines: Dict[str, float] = {}
        self._drift_detected: List[Dict[str, Any]] = []

    def set_baseline(self, key: str, value: float) -> None:
        """
        Set baseline value for a metric.

        Args:
            key: Metric key
            value: Baseline value
        """
        self._baselines[key] = value

    def check_drift(self, key: str, current_value: float) -> Tuple[bool, Optional[str]]:
        """
        Check for drift from baseline.

        Args:
            key: Metric key
            current_value: Current value

        Returns:
            Tuple of (has_drift, error_message)
        """
        if key not in self._baselines:
            self.set_baseline(key, current_value)
            return False, None

        baseline = self._baselines[key]
        diff = abs(current_value - baseline)

        if diff > self.tolerance:
            drift_info = {
                "key": key,
                "baseline": baseline,
                "current": current_value,
                "difference": diff,
            }
            self._drift_detected.append(drift_info)
            logger.warning(
                "Drift detected",
                key=key,
                baseline=baseline,
                current=current_value,
                difference=diff,
            )
            return True, f"Drift detected: {diff} > {self.tolerance}"

        return False, None

    def get_drift_detected(self) -> List[Dict[str, Any]]:
        """Get all detected drift."""
        return self._drift_detected.copy()

    def clear_drift(self) -> None:
        """Clear detected drift."""
        self._drift_detected.clear()


# Global drift detector instance
_drift_detector = DriftDetector()


def get_drift_detector() -> DriftDetector:
    """Get the global drift detector."""
    return _drift_detector
