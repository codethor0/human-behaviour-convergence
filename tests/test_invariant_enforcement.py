# SPDX-License-Identifier: PROPRIETARY
"""Tests for invariant enforcement and regression guards."""
import pytest

from app.core.invariants import (
    EnforcementStrategy,
    InvariantViolation,
    check_confidence_volatility_consistency,
    check_contribution_reconciliation,
    check_no_nan_inf,
    check_range_bounded,
    check_risk_tier_monotonicity,
    check_shock_trend_consistency,
    check_trace_completeness,
    check_weight_sum,
    get_drift_detector,
    get_registry,
    register_all_invariants,
)


class TestInvariantRegistry:
    """Test invariant registry functionality."""

    def test_registry_initialization(self):
        """Registry should be initialized with all invariants."""
        registry = get_registry()
        assert registry is not None

        # Clear violations and re-register to ensure clean state
        registry.clear_violations()
        register_all_invariants()

        # Check that some invariants are registered
        violations = registry.get_violations()
        assert violations == []  # Should be empty initially

    def test_invariant_check_passes(self):
        """Valid inputs should pass invariant checks."""
        registry = get_registry()
        register_all_invariants()

        # Check INV-001: Weight normalization
        weights = {"a": 0.5, "b": 0.3, "c": 0.2}
        is_valid, error = registry.check("INV-001", weights)
        assert is_valid
        assert error is None

        # Check INV-002: Range bounds
        is_valid, error = registry.check("INV-002", 0.5)
        assert is_valid
        assert error is None

    def test_invariant_check_fails(self):
        """Invalid inputs should fail invariant checks."""
        registry = get_registry()
        registry.clear_violations()
        register_all_invariants()

        # Check INV-001: Weight normalization (should fail, HARD_FAIL raises exception)
        weights = {"a": 0.5, "b": 0.3, "c": 0.1}  # Sums to 0.9
        with pytest.raises(InvariantViolation):
            registry.check("INV-001", weights)

        # Check INV-002: Range bounds (should fail, HARD_FAIL raises exception)
        with pytest.raises(InvariantViolation):
            registry.check("INV-002", 1.5)  # Outside [0, 1]

    def test_hard_fail_raises_exception(self):
        """HARD_FAIL invariants should raise exceptions."""
        registry = get_registry()
        register_all_invariants()

        # INV-002 is HARD_FAIL
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-002", 1.5)

        assert exc_info.value.invariant_name == "INV-002"

    def test_soft_fail_logs_warning(self):
        """SOFT_FAIL invariants should log warnings but not raise."""
        registry = get_registry()
        register_all_invariants()

        # INV-021 is SOFT_FAIL
        components = {"a": {"contribution": 0.3}, "b": {"contribution": 0.2}}
        output = 0.7  # Mismatch
        is_valid, error = registry.check("INV-021", components, output)
        assert not is_valid
        # Should not raise exception

        violations = registry.get_violations()
        assert len(violations) > 0
        assert violations[-1]["invariant"] == "INV-021"


class TestInvariantCheckFunctions:
    """Test individual invariant check functions."""

    def test_check_weight_sum_valid(self):
        """Valid weight sum should pass."""
        weights = {"a": 0.5, "b": 0.3, "c": 0.2}
        is_valid, error = check_weight_sum(weights)
        assert is_valid
        assert error is None

    def test_check_weight_sum_invalid(self):
        """Invalid weight sum should fail."""
        weights = {"a": 0.5, "b": 0.3, "c": 0.1}  # Sums to 0.9
        is_valid, error = check_weight_sum(weights, tolerance=0.01)
        assert not is_valid
        assert "0.9" in error

    def test_check_range_bounded_valid(self):
        """Value in range should pass."""
        is_valid, error = check_range_bounded(0.5, 0.0, 1.0)
        assert is_valid
        assert error is None

    def test_check_range_bounded_invalid(self):
        """Value outside range should fail."""
        is_valid, error = check_range_bounded(1.5, 0.0, 1.0)
        assert not is_valid
        assert "1.5" in error

    def test_check_no_nan_inf_valid(self):
        """Finite value should pass."""
        is_valid, error = check_no_nan_inf(0.5)
        assert is_valid
        assert error is None

    def test_check_no_nan_inf_invalid(self):
        """NaN/Inf should fail."""
        is_valid, error = check_no_nan_inf(float("nan"))
        assert not is_valid
        assert "nan" in error.lower()

        is_valid, error = check_no_nan_inf(float("inf"))
        assert not is_valid
        assert "inf" in error.lower()

    def test_check_contribution_reconciliation_valid(self):
        """Valid reconciliation should pass."""
        components = {"a": {"contribution": 0.3}, "b": {"contribution": 0.2}}
        output = 0.5
        is_valid, error = check_contribution_reconciliation(components, output)
        assert is_valid
        assert error is None

    def test_check_contribution_reconciliation_invalid(self):
        """Invalid reconciliation should fail."""
        components = {"a": {"contribution": 0.3}, "b": {"contribution": 0.2}}
        output = 0.7  # Mismatch
        is_valid, error = check_contribution_reconciliation(components, output)
        assert not is_valid
        assert "0.5" in error or "0.7" in error

    def test_check_risk_tier_monotonicity_valid(self):
        """Monotonic tiers should pass."""
        is_valid, error = check_risk_tier_monotonicity(0.3, "watchlist", 0.6, "elevated")
        assert is_valid
        assert error is None

    def test_check_risk_tier_monotonicity_invalid(self):
        """Non-monotonic tiers should fail."""
        # score1=0.3 (elevated, order=2) < score2=0.6 (watchlist, order=1)
        # This violates monotonicity: lower score but higher tier
        is_valid, error = check_risk_tier_monotonicity(0.3, "elevated", 0.6, "watchlist")
        assert not is_valid
        assert error is not None
        assert "violated" in error.lower()

    def test_check_confidence_volatility_consistency_valid(self):
        """Consistent confidence-volatility should pass."""
        is_valid, error = check_confidence_volatility_consistency(0.3, 0.8)  # Low vol, high conf
        assert is_valid
        assert error is None

    def test_check_confidence_volatility_consistency_invalid(self):
        """Inconsistent confidence-volatility should fail."""
        is_valid, error = check_confidence_volatility_consistency(0.8, 0.8)  # High vol, high conf
        assert not is_valid
        assert error is not None

    def test_check_shock_trend_consistency_valid(self):
        """Consistent shock-trend should pass."""
        is_valid, error = check_shock_trend_consistency("severe", "increasing")
        assert is_valid
        assert error is None

    def test_check_shock_trend_consistency_invalid(self):
        """Inconsistent shock-trend should fail."""
        is_valid, error = check_shock_trend_consistency("severe", "stable")
        assert not is_valid
        assert error is not None

    def test_check_trace_completeness_valid(self):
        """Complete trace should pass."""
        trace = {"output": {}, "reconciliation": {}}
        is_valid, error = check_trace_completeness(trace)
        assert is_valid
        assert error is None

    def test_check_trace_completeness_invalid(self):
        """Incomplete trace should fail."""
        is_valid, error = check_trace_completeness(None)
        assert not is_valid
        assert "None" in error

        trace = {"output": {}}  # Missing reconciliation
        is_valid, error = check_trace_completeness(trace)
        assert not is_valid
        assert "reconciliation" in error


class TestDriftDetection:
    """Test drift detection functionality."""

    def test_drift_detector_initialization(self):
        """Drift detector should initialize correctly."""
        detector = get_drift_detector()
        assert detector is not None
        assert detector.tolerance == 0.01

    def test_set_baseline(self):
        """Setting baseline should work."""
        detector = get_drift_detector()
        detector.set_baseline("test_metric", 0.5)
        assert detector._baselines["test_metric"] == 0.5

    def test_check_drift_no_baseline(self):
        """Checking drift without baseline should set baseline."""
        detector = get_drift_detector()
        detector.clear_drift()
        has_drift, error = detector.check_drift("new_metric", 0.5)
        assert not has_drift
        assert error is None
        assert "new_metric" in detector._baselines

    def test_check_drift_no_drift(self):
        """Checking drift within tolerance should pass."""
        detector = get_drift_detector()
        detector.set_baseline("test", 0.5)
        has_drift, error = detector.check_drift("test", 0.505)  # Within tolerance
        assert not has_drift
        assert error is None

    def test_check_drift_detected(self):
        """Checking drift beyond tolerance should detect drift."""
        detector = get_drift_detector()
        detector.set_baseline("test", 0.5)
        detector.clear_drift()
        has_drift, error = detector.check_drift("test", 0.6)  # Beyond tolerance
        assert has_drift
        assert error is not None
        assert len(detector.get_drift_detected()) > 0

    def test_get_drift_detected(self):
        """Getting detected drift should return list."""
        detector = get_drift_detector()
        detector.set_baseline("test", 0.5)
        detector.clear_drift()
        detector.check_drift("test", 0.6)
        drift_list = detector.get_drift_detected()
        assert len(drift_list) > 0
        assert drift_list[0]["key"] == "test"


class TestMetaInvariantViolations:
    """Meta-tests that intentionally violate invariants to verify detection."""

    def test_meta_weight_sum_violation(self):
        """Intentionally violate weight sum to verify detection."""
        registry = get_registry()
        register_all_invariants()

        # Violate INV-001 (HARD_FAIL raises exception)
        weights = {"a": 0.5, "b": 0.3}  # Sums to 0.8
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-001", weights)
        assert "INV-001" in str(exc_info.value)
        assert "0.8" in str(exc_info.value) or "1.0" in str(exc_info.value)

    def test_meta_range_violation(self):
        """Intentionally violate range bounds to verify detection."""
        registry = get_registry()
        register_all_invariants()

        # Violate INV-002 (should raise exception)
        with pytest.raises(InvariantViolation):
            registry.check("INV-002", 1.5)

    def test_meta_nan_propagation_violation(self):
        """Intentionally violate NaN/Inf check to verify detection."""
        registry = get_registry()
        register_all_invariants()

        # Violate INV-006 (should raise exception)
        with pytest.raises(InvariantViolation):
            registry.check("INV-006", float("nan"))

    def test_meta_reconciliation_violation(self):
        """Intentionally violate reconciliation to verify detection."""
        registry = get_registry()
        register_all_invariants()

        # Violate INV-021 (should log warning, not raise)
        components = {"a": {"contribution": 0.3}, "b": {"contribution": 0.2}}
        output = 0.7  # Mismatch
        is_valid, error = registry.check("INV-021", components, output)
        assert not is_valid
        # Should not raise (SOFT_FAIL)

    def test_meta_trace_completeness_violation(self):
        """Intentionally violate trace completeness to verify detection."""
        registry = get_registry()
        register_all_invariants()

        # Violate INV-025 (should log warning, not raise)
        is_valid, error = registry.check("INV-025", None)
        assert not is_valid
        # Should not raise (SOFT_FAIL)

    def test_meta_confidence_volatility_violation(self):
        """Intentionally violate confidence-volatility to verify detection."""
        registry = get_registry()
        register_all_invariants()

        # Violate INV-012 (should log warning, not raise)
        is_valid, error = registry.check("INV-012", 0.8, 0.8)  # High vol, high conf
        assert not is_valid
        # Should not raise (SOFT_FAIL)

    def test_meta_shock_trend_violation(self):
        """Intentionally violate shock-trend consistency to verify detection."""
        registry = get_registry()
        register_all_invariants()

        # Violate INV-013 (should log warning, not raise)
        is_valid, error = registry.check("INV-013", "severe", "stable")
        assert not is_valid
        # Should not raise (SOFT_FAIL)
