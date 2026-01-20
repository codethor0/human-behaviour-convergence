# SPDX-License-Identifier: PROPRIETARY
"""Tests for policy engine (N+37)."""
import pytest

from app.core.policy import (
    PolicyValidator,
    get_policy_engine,
    reset_policy_engine,
)
from app.core.invariants import get_registry, InvariantViolation


class TestPolicyValidator:
    """Tests for policy validator."""

    def test_validate_valid_policy(self):
        """Test validation of valid policy."""
        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }

        is_valid, error = PolicyValidator.validate_policy(policy)
        assert is_valid is True
        assert error is None

    def test_validate_invalid_structure(self):
        """Test validation of invalid structure."""
        policy = "not a dict"

        is_valid, error = PolicyValidator.validate_policy(policy)
        assert is_valid is False
        assert "dictionary" in error.lower()

    def test_validate_threshold_out_of_bounds(self):
        """Test validation of threshold out of bounds."""
        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 1.5,  # Out of bounds (> 1.0)
                "direction": "above",
            },
        }

        is_valid, error = PolicyValidator.validate_policy(policy)
        assert is_valid is False
        assert "bounds" in error.lower()

    def test_validate_persistence_days_out_of_bounds(self):
        """Test validation of persistence days out of bounds."""
        policy = {
            "persistence_windows": {
                "alert_type": "threshold",
                "days": 100,  # Out of bounds (> 30)
            },
        }

        is_valid, error = PolicyValidator.validate_policy(policy)
        assert is_valid is False
        assert "bounds" in error.lower()


class TestPolicyEngine:
    """Tests for policy engine."""

    def setup_method(self):
        """Reset policy engine before each test."""
        reset_policy_engine()

    def test_create_policy(self):
        """Test creating a policy."""
        engine = get_policy_engine()

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }

        success, error = engine.create_policy(
            policy_id="test_policy",
            policy=policy,
            created_by="user1",
            tenant_id="tenant1",
        )

        assert success is True
        assert error is None

        # Verify policy exists
        stored_policy = engine.get_policy("test_policy", tenant_id="tenant1")
        assert stored_policy is not None
        assert stored_policy["policy_id"] == "test_policy"
        assert stored_policy["version"] == 1
        assert stored_policy["active"] is False

    def test_create_policy_invalid(self):
        """Test creating invalid policy."""
        engine = get_policy_engine()

        policy = {
            "alert_thresholds": {
                "threshold": 1.5,  # Invalid
            },
        }

        success, error = engine.create_policy(
            policy_id="test_policy",
            policy=policy,
            created_by="user1",
        )

        assert success is False
        assert error is not None

    def test_update_policy(self):
        """Test updating a policy."""
        engine = get_policy_engine()

        # Create policy
        policy1 = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }
        engine.create_policy("test_policy", policy1, "user1")

        # Update policy
        policy2 = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.8,  # Changed
                "direction": "above",
            },
        }

        success, error = engine.update_policy("test_policy", policy2, "user1")

        assert success is True
        assert error is None

        # Verify version incremented
        stored_policy = engine.get_policy("test_policy")
        assert stored_policy["version"] == 2

        # Verify versions exist
        versions = engine.get_policy_versions("test_policy")
        assert len(versions) == 2

    def test_activate_policy(self):
        """Test activating a policy."""
        engine = get_policy_engine()

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }
        engine.create_policy("test_policy", policy, "user1")

        success, error = engine.activate_policy("test_policy", "user1")

        assert success is True
        assert error is None

        stored_policy = engine.get_policy("test_policy")
        assert stored_policy["active"] is True

    def test_deactivate_policy(self):
        """Test deactivating a policy."""
        engine = get_policy_engine()

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }
        engine.create_policy("test_policy", policy, "user1")
        engine.activate_policy("test_policy", "user1")

        success, error = engine.deactivate_policy("test_policy", "user1")

        assert success is True
        assert error is None

        stored_policy = engine.get_policy("test_policy")
        assert stored_policy["active"] is False

    def test_rollback_policy(self):
        """Test rolling back a policy."""
        engine = get_policy_engine()

        # Create and update policy
        policy1 = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }
        engine.create_policy("test_policy", policy1, "user1")

        policy2 = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.8,
                "direction": "above",
            },
        }
        engine.update_policy("test_policy", policy2, "user1")

        # Rollback to version 1
        success, error = engine.rollback_policy("test_policy", 1, "user1")

        assert success is True
        assert error is None

        stored_policy = engine.get_policy("test_policy")
        assert stored_policy["version"] == 1
        assert stored_policy["policy"]["alert_thresholds"]["threshold"] == 0.7

    def test_evaluate_policy(self):
        """Test evaluating a policy."""
        engine = get_policy_engine()

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }
        engine.create_policy("test_policy", policy, "user1")
        engine.activate_policy("test_policy", "user1")

        context = {
            "factor_values": {
                "economic_stress": 0.8,  # Above threshold
            },
        }

        result = engine.evaluate_policy("test_policy", context)

        assert result["evaluated"] is True
        assert len(result["matches"]) > 0

    def test_evaluate_policy_inactive(self):
        """Test evaluating inactive policy."""
        engine = get_policy_engine()

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }
        engine.create_policy("test_policy", policy, "user1")
        # Don't activate

        context = {
            "factor_values": {
                "economic_stress": 0.8,
            },
        }

        result = engine.evaluate_policy("test_policy", context)

        assert result["evaluated"] is False
        assert "inactive" in result["reason"].lower()

    def test_tenant_isolation(self):
        """Test tenant isolation."""
        engine = get_policy_engine()

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }

        # Create policy for tenant1
        engine.create_policy("test_policy", policy, "user1", tenant_id="tenant1")

        # Try to get policy from tenant2
        stored_policy = engine.get_policy("test_policy", tenant_id="tenant2")
        assert stored_policy is None

        # Get policy from tenant1
        stored_policy = engine.get_policy("test_policy", tenant_id="tenant1")
        assert stored_policy is not None


class TestPolicyInvariants:
    """Tests for policy invariants."""

    def test_inv_pol01_policy_does_not_affect_analytics(self):
        """Test INV-POL01: Policy changes never affect analytics."""
        registry = get_registry()

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }

        analytics_before = {"behavior_index": 0.548}
        analytics_after = {"behavior_index": 0.548}  # Unchanged

        is_valid, error = registry.check(
            "INV-POL01", policy, analytics_before, analytics_after
        )
        assert is_valid is True

    def test_inv_pol01_policy_affects_analytics_violation(self):
        """Test INV-POL01 violation: Policy affects analytics."""
        registry = get_registry()

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }

        analytics_before = {"behavior_index": 0.548}
        analytics_after = {"behavior_index": 0.550}  # Changed

        is_valid, error = registry.check(
            "INV-POL01", policy, analytics_before, analytics_after
        )
        assert is_valid is False
        assert "analytics" in error.lower()

    def test_inv_pol02_policy_evaluation_determinism(self):
        """Test INV-POL02: Policy evaluation determinism."""
        registry = get_registry()

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }

        context1 = {"factor_values": {"economic_stress": 0.8}}
        context2 = {"factor_values": {"economic_stress": 0.8}}  # Same
        result1 = {"evaluated": True, "matches": []}
        result2 = {"evaluated": True, "matches": []}  # Same

        is_valid, error = registry.check(
            "INV-POL02", policy, context1, context2, result1, result2
        )
        assert is_valid is True

    def test_inv_pol03_rbac_enforced(self):
        """Test INV-POL03: RBAC enforced on policy actions."""
        registry = get_registry()

        action = "activate"
        user_id = "user1"
        user_roles = ["policy_admin"]
        required_roles = ["policy_admin"]

        is_valid, error = registry.check(
            "INV-POL03", action, user_id, user_roles, required_roles
        )
        assert is_valid is True

    def test_inv_pol03_rbac_enforced_violation(self):
        """Test INV-POL03 violation: RBAC not enforced."""

        registry = get_registry()

        action = "activate"
        user_id = "user1"
        user_roles = ["viewer"]  # No required role
        required_roles = ["policy_admin"]

        # INV-POL03 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-POL03", action, user_id, user_roles, required_roles)

        assert (
            "rbac" in str(exc_info.value).lower()
            or "role" in str(exc_info.value).lower()
        )

    def test_inv_pol04_policy_bounds_not_exceeded(self):
        """Test INV-POL04: Policy bounds not exceeded."""
        registry = get_registry()

        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,  # Within bounds
                "direction": "above",
            },
        }

        bounds = {"threshold": {"min": 0.1, "max": 0.9}}

        is_valid, error = registry.check("INV-POL04", policy, bounds)
        assert is_valid is True

    def test_inv_pol05_zero_numerical_drift(self):
        """Test INV-POL05: Zero numerical drift."""
        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.548

        is_valid, error = registry.check(
            "INV-POL05", behavior_index_before, behavior_index_after
        )
        assert is_valid is True

    def test_inv_pol05_zero_numerical_drift_violation(self):
        """Test INV-POL05 violation: Numerical drift."""

        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.550  # Changed

        # INV-POL05 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-POL05", behavior_index_before, behavior_index_after)

        assert (
            "drift" in str(exc_info.value).lower()
            or "changed" in str(exc_info.value).lower()
        )


class TestNoSemanticDrift:
    """Tests to ensure policy features don't cause semantic drift."""

    def test_policy_purely_additive(self):
        """Test that policy is purely additive."""
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

        # Compute before policy
        df_before = computer.compute_behavior_index(harmonized)
        global_before = float(df_before["behavior_index"].iloc[29])

        # Use policy engine
        from app.core.policy import get_policy_engine

        engine = get_policy_engine()
        policy = {
            "alert_thresholds": {
                "factor_id": "economic_stress",
                "threshold": 0.7,
                "direction": "above",
            },
        }
        engine.create_policy("test_policy", policy, "user1")

        # Recompute after policy
        df_after = computer.compute_behavior_index(harmonized)
        global_after = float(df_after["behavior_index"].iloc[29])

        # Verify zero numerical drift
        assert abs(global_before - global_after) < 1e-10


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_policy_optional(self):
        """Test that policy is optional."""
        from app.core.policy import get_policy_engine

        engine = get_policy_engine()
        # Should not raise even if no policies exist
        policy = engine.get_policy("nonexistent")
        assert policy is None
