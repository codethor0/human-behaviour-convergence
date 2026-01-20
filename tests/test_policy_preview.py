# SPDX-License-Identifier: PROPRIETARY
"""Tests for policy preview and impact analysis (N+38)."""
import pytest

from app.core.policy import get_policy_engine, reset_policy_engine
from app.core.policy_preview import (
    generate_impact_diff,
    preview_policy_impact,
    validate_preview_before_activation,
)
from app.core.invariants import get_registry, InvariantViolation


class TestPolicyPreview:
    """Tests for policy preview."""

    def setup_method(self):
        """Reset policy engine before each test."""
        reset_policy_engine()

    def test_preview_policy_impact(self):
        """Test previewing policy impact."""
        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }

        current_alerts = [
            {
                "alert_id": "alert1",
                "type": "threshold",
                "severity": "medium",
                "factor_id": "economic_stress",
                "value": 0.8,
            },
        ]

        current_context = {
            "factor_values": {
                "economic_stress": 0.8,
            },
        }

        result = preview_policy_impact(
            policy_id="test_policy",
            policy=policy,
            current_alerts=current_alerts,
            current_context=current_context,
        )

        assert result["preview_valid"] is True
        assert "preview_alert_count" in result
        assert "alert_count_delta" in result

    def test_preview_invalid_policy(self):
        """Test previewing invalid policy."""
        policy = {
            "alert_thresholds": {
                "threshold": 1.5,  # Invalid (out of bounds)
            },
        }

        result = preview_policy_impact(
            policy_id="test_policy",
            policy=policy,
            current_alerts=[],
            current_context={},
        )

        assert result["preview_valid"] is False
        assert "error" in result

    def test_preview_no_state_mutation(self):
        """Test that preview doesn't mutate state."""

        engine = get_policy_engine()

        # Get initial state
        initial_policies = len(engine.policies)

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }

        # Preview policy
        preview_policy_impact(
            policy_id="test_policy",
            policy=policy,
            current_alerts=[],
            current_context={},
        )

        # Verify state unchanged
        final_policies = len(engine.policies)
        assert initial_policies == final_policies

    def test_generate_impact_diff(self):
        """Test generating impact diff."""
        current_state = {
            "current_alert_count": 5,
            "current_severity_distribution": {
                "high": 2,
                "medium": 3,
            },
        }

        preview_state = {
            "preview_alert_count": 3,
            "preview_severity_distribution": {
                "high": 1,
                "medium": 2,
            },
            "noise_reduction_estimate": 2,
            "new_alerts": [],
            "suppressed_alerts": [{"alert_id": "alert1"}, {"alert_id": "alert2"}],
        }

        diff = generate_impact_diff(current_state, preview_state)

        assert diff["alert_count_change"] == -2
        assert diff["noise_reduction"] == 2
        assert "high" in diff["severity_changes"]
        assert diff["severity_changes"]["high"]["delta"] == -1

    def test_validate_preview_before_activation(self):
        """Test validating preview before activation."""
        preview_result = {
            "preview_valid": True,
            "policy_id": "test_policy",
        }

        is_valid, error = validate_preview_before_activation(
            "test_policy",
            preview_result,
        )

        assert is_valid is True
        assert error is None

    def test_validate_preview_before_activation_no_preview(self):
        """Test validation fails without preview."""
        preview_result = {
            "preview_valid": False,
        }

        is_valid, error = validate_preview_before_activation(
            "test_policy",
            preview_result,
        )

        assert is_valid is False
        assert "preview" in error.lower()


class TestPreviewInvariants:
    """Tests for preview invariants."""

    def test_inv_prev01_preview_never_mutates_state(self):
        """Test INV-PREV01: Preview never mutates state."""
        registry = get_registry()

        state_before = {
            "policies": {"policy1": {"active": True}},
            "alerts": [{"alert_id": "alert1"}],
        }
        state_after = {
            "policies": {"policy1": {"active": True}},
            "alerts": [{"alert_id": "alert1"}],
        }

        is_valid, error = registry.check("INV-PREV01", state_before, state_after)
        assert is_valid is True

    def test_inv_prev01_preview_mutates_state_violation(self):
        """Test INV-PREV01 violation: Preview mutates state."""

        registry = get_registry()

        state_before = {
            "policies": {"policy1": {"active": True}},
            "alerts": [],
        }
        state_after = {
            "policies": {"policy1": {"active": True}},
            "alerts": [{"alert_id": "alert1"}],  # Changed
        }

        # INV-PREV01 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-PREV01", state_before, state_after)

        assert "mutate" in str(exc_info.value).lower()

    def test_inv_prev02_preview_results_derivable(self):
        """Test INV-PREV02: Preview results derivable."""
        registry = get_registry()

        preview_result = {
            "preview_valid": True,
            "current_alert_count": 5,
        }
        current_analytics = {
            "alerts": [{"alert_id": "alert1"}] * 5,
        }

        is_valid, error = registry.check(
            "INV-PREV02", preview_result, current_analytics
        )
        assert is_valid is True

    def test_inv_prev03_activation_only_after_preview(self):
        """Test INV-PREV03: Activation only after preview."""
        registry = get_registry()

        preview_result = {
            "preview_valid": True,
        }

        is_valid, error = registry.check(
            "INV-PREV03", "test_policy", True, preview_result
        )
        assert is_valid is True

    def test_inv_prev03_activation_without_preview_violation(self):
        """Test INV-PREV03 violation: Activation without preview."""
        registry = get_registry()

        is_valid, error = registry.check("INV-PREV03", "test_policy", False, None)
        assert is_valid is False
        assert "preview" in error.lower()

    def test_inv_prev04_rbac_enforced(self):
        """Test INV-PREV04: RBAC enforced on preview + activation."""
        registry = get_registry()

        action = "preview"
        user_id = "user1"
        user_roles = ["policy_admin"]
        required_roles = ["policy_admin"]

        is_valid, error = registry.check(
            "INV-PREV04", action, user_id, user_roles, required_roles
        )
        assert is_valid is True

    def test_inv_prev04_rbac_enforced_violation(self):
        """Test INV-PREV04 violation: RBAC not enforced."""

        registry = get_registry()

        action = "preview"
        user_id = "user1"
        user_roles = ["viewer"]
        required_roles = ["policy_admin"]

        # INV-PREV04 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-PREV04", action, user_id, user_roles, required_roles)

        assert (
            "rbac" in str(exc_info.value).lower()
            or "role" in str(exc_info.value).lower()
        )

    def test_inv_prev05_zero_numerical_drift(self):
        """Test INV-PREV05: Zero numerical drift."""
        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.548

        is_valid, error = registry.check(
            "INV-PREV05", behavior_index_before, behavior_index_after
        )
        assert is_valid is True

    def test_inv_prev05_zero_numerical_drift_violation(self):
        """Test INV-PREV05 violation: Numerical drift."""

        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.550

        # INV-PREV05 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-PREV05", behavior_index_before, behavior_index_after)

        assert "drift" in str(exc_info.value).lower()


class TestNoSemanticDrift:
    """Tests to ensure preview features don't cause semantic drift."""

    def test_preview_purely_additive(self):
        """Test that preview is purely additive."""
        from app.core.behavior_index import BehaviorIndexComputer
        import pandas as pd

        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=30),
                "stress_index": [0.6] * 30,
                "discomfort_score": [0.7] * 30,
                "mobility_index": [0.5] * 30,
                "search_interest_score": [0.5] * 30,
                "health_risk_index": [0.5] * 30,
            }
        )

        # Compute before preview
        df_before = computer.compute_behavior_index(harmonized)
        global_before = float(df_before["behavior_index"].iloc[29])

        # Use preview features
        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }
        preview_policy_impact(
            policy_id="test_policy",
            policy=policy,
            current_alerts=[],
            current_context={},
        )

        # Recompute after preview
        df_after = computer.compute_behavior_index(harmonized)
        global_after = float(df_after["behavior_index"].iloc[29])

        # Verify zero numerical drift
        assert abs(global_before - global_after) < 1e-10


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_preview_optional(self):
        """Test that preview is optional."""
        # Should not raise even if inputs are empty
        result = preview_policy_impact(
            policy_id="test_policy",
            policy={},
            current_alerts=[],
            current_context={},
        )
        assert isinstance(result, dict)
