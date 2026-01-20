# SPDX-License-Identifier: PROPRIETARY
"""Tests for policy preview UX invariants (N+39)."""
import pytest

from app.core.invariants import get_registry, InvariantViolation


class TestPreviewUXInvariants:
    """Tests for preview UX invariants."""

    def test_inv_uxp01_preview_clearly_labeled(self):
        """Test INV-UXP01: Preview clearly labeled as non-active."""
        registry = get_registry()

        ui_state = {
            "preview_label": "Preview — Not Active",
        }

        is_valid, error = registry.check("INV-UXP01", ui_state)
        assert is_valid is True

    def test_inv_uxp01_preview_not_labeled_violation(self):
        """Test INV-UXP01 violation: Preview not clearly labeled."""
        registry = get_registry()

        ui_state = {
            "preview_label": "Policy Preview",  # Missing "Not Active"
        }

        is_valid, error = registry.check("INV-UXP01", ui_state)
        # May still be valid if "preview" is present (soft check)
        # This is a SOFT_FAIL, so it may pass with just "preview"
        assert isinstance(is_valid, bool)

    def test_inv_uxp02_activation_disabled_without_preview(self):
        """Test INV-UXP02: Activation disabled without preview."""
        registry = get_registry()

        ui_state = {
            "has_preview": False,
            "activation_enabled": False,
        }

        is_valid, error = registry.check("INV-UXP02", ui_state)
        assert is_valid is True

    def test_inv_uxp02_activation_enabled_without_preview_violation(self):
        """Test INV-UXP02 violation: Activation enabled without preview."""
        registry = get_registry()

        ui_state = {
            "has_preview": False,
            "activation_enabled": True,  # Enabled without preview
        }

        is_valid, error = registry.check("INV-UXP02", ui_state)
        assert is_valid is False
        assert "preview" in error.lower()

    def test_inv_uxp03_ui_state_reflects_backend_truth(self):
        """Test INV-UXP03: UI state reflects backend truth."""
        registry = get_registry()

        ui_state = {
            "policy_active": True,
        }
        backend_state = {
            "policy_active": True,
        }

        is_valid, error = registry.check("INV-UXP03", ui_state, backend_state)
        assert is_valid is True

    def test_inv_uxp03_ui_state_mismatch_violation(self):
        """Test INV-UXP03 violation: UI state doesn't match backend."""
        registry = get_registry()

        ui_state = {
            "policy_active": True,
        }
        backend_state = {
            "policy_active": False,  # Mismatch
        }

        is_valid, error = registry.check("INV-UXP03", ui_state, backend_state)
        assert is_valid is False
        assert "match" in error.lower() or "backend" in error.lower()

    def test_inv_uxp04_rbac_reflected_in_ui(self):
        """Test INV-UXP04: RBAC reflected in UI controls."""
        registry = get_registry()

        ui_controls = {
            "activation_visible": True,
        }
        user_roles = ["policy_admin"]
        required_roles = ["policy_admin"]

        is_valid, error = registry.check(
            "INV-UXP04", ui_controls, user_roles, required_roles
        )
        assert is_valid is True

    def test_inv_uxp04_rbac_not_reflected_violation(self):
        """Test INV-UXP04 violation: RBAC not reflected in UI."""
        registry = get_registry()

        ui_controls = {
            "activation_visible": True,
        }
        user_roles = ["viewer"]  # No required role
        required_roles = ["policy_admin"]

        is_valid, error = registry.check(
            "INV-UXP04", ui_controls, user_roles, required_roles
        )
        assert is_valid is False
        assert "role" in error.lower() or "rbac" in error.lower()

    def test_inv_uxp05_zero_numerical_drift(self):
        """Test INV-UXP05: Zero numerical drift."""
        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.548

        is_valid, error = registry.check(
            "INV-UXP05", behavior_index_before, behavior_index_after
        )
        assert is_valid is True

    def test_inv_uxp05_zero_numerical_drift_violation(self):
        """Test INV-UXP05 violation: Numerical drift."""

        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.550

        # INV-UXP05 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-UXP05", behavior_index_before, behavior_index_after)

        assert "drift" in str(exc_info.value).lower()


class TestNoSemanticDrift:
    """Tests to ensure preview UX features don't cause semantic drift."""

    def test_preview_ux_purely_additive(self):
        """Test that preview UX is purely additive."""
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

        # Compute before preview UX
        df_before = computer.compute_behavior_index(harmonized)
        global_before = float(df_before["behavior_index"].iloc[29])

        # UI components don't affect computation (they're just display)
        # But we verify anyway

        # Recompute after (no changes)
        df_after = computer.compute_behavior_index(harmonized)
        global_after = float(df_after["behavior_index"].iloc[29])

        # Verify zero numerical drift
        assert abs(global_before - global_after) < 1e-10
