# SPDX-License-Identifier: PROPRIETARY
"""Tests for deployment and compliance features (N+35)."""
import os
from unittest.mock import patch

import pytest

from app.core.observability import (
    ObservabilityManager,
    get_observability_manager,
)
from app.core.secrets import (
    SecretsManager,
    get_secrets_manager,
)
from app.core.invariants import get_registry


class TestObservabilityManager:
    """Tests for observability manager."""

    def test_observability_manager_init(self):
        """Test observability manager initialization."""
        manager = ObservabilityManager()
        assert manager.metrics is not None
        assert "forecast_count" in manager.metrics

    def test_record_forecast(self):
        """Test recording forecast metric."""
        manager = ObservabilityManager()
        manager.record_forecast("test_region", 150.0, True)

        assert manager.metrics["forecast_count"] == 1
        assert len(manager.metrics["forecast_latency_ms"]) == 1
        assert manager.metrics["forecast_latency_ms"][0] == 150.0

    def test_record_alert(self):
        """Test recording alert metric."""
        manager = ObservabilityManager()
        manager.record_alert("alert1", "test_region", 2)

        assert manager.metrics["alert_count"] == 2

    def test_record_notification_success(self):
        """Test recording successful notification."""
        manager = ObservabilityManager()
        manager.record_notification("email", True, 50.0)

        assert manager.metrics["notification_success_count"] == 1
        assert manager.metrics["notification_failure_count"] == 0

    def test_record_notification_failure(self):
        """Test recording failed notification."""
        manager = ObservabilityManager()
        manager.record_notification("webhook", False)

        assert manager.metrics["notification_success_count"] == 0
        assert manager.metrics["notification_failure_count"] == 1

    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        manager = ObservabilityManager()
        manager.record_forecast("test_region", 100.0, True)
        manager.record_forecast("test_region", 200.0, True)
        manager.record_alert("alert1", "test_region", 1)
        manager.record_notification("email", True)
        manager.record_notification("webhook", False)

        summary = manager.get_metrics_summary()

        assert summary["forecast_count"] == 2
        assert summary["alert_count"] == 1
        assert summary["notification_success_count"] == 1
        assert summary["notification_failure_count"] == 1
        assert summary["avg_forecast_latency_ms"] == 150.0
        assert summary["notification_success_rate"] == 0.5

    def test_trace_forecast_to_alert_to_notify(self):
        """Test tracing forecast → alert → notify flow."""
        manager = ObservabilityManager()

        with manager.trace_forecast_to_alert_to_notify(
            "test_region", "forecast1"
        ) as trace:
            assert "trace_id" in trace
            assert trace["region_id"] == "test_region"
            assert trace["forecast_id"] == "forecast1"


class TestSecretsManager:
    """Tests for secrets manager."""

    def test_secrets_manager_init(self):
        """Test secrets manager initialization."""
        manager = SecretsManager(backend="env")
        assert manager.backend == "env"

    @patch.dict(os.environ, {"TEST_SECRET": "test_value"})
    def test_get_secret_from_env(self):
        """Test getting secret from environment."""
        manager = SecretsManager(backend="env")
        value = manager.get_secret("TEST_SECRET")
        assert value == "test_value"

    def test_get_secret_default(self):
        """Test getting secret with default."""
        manager = SecretsManager(backend="env")
        value = manager.get_secret("NONEXISTENT_SECRET", default="default_value")
        assert value == "default_value"

    @patch.dict(os.environ, {"SECRET1": "value1", "SECRET2": "value2"})
    def test_validate_secrets(self):
        """Test validating required secrets."""
        manager = SecretsManager(backend="env")
        validation = manager.validate_secrets(["SECRET1", "SECRET2", "MISSING_SECRET"])

        assert validation["SECRET1"] is True
        assert validation["SECRET2"] is True
        assert validation["MISSING_SECRET"] is False


class TestDeploymentInvariants:
    """Tests for deployment invariants."""

    def test_inv_dep01_config_immutability(self):
        """Test INV-DEP01: Config immutability."""
        registry = get_registry()

        config_before = {
            "environment": "prod",
            "app_name": "hbc",
            "aws_region": "us-east-1",
        }
        config_after = {
            "environment": "prod",
            "app_name": "hbc",
            "aws_region": "us-east-1",
        }

        is_valid, error = registry.check("INV-DEP01", config_before, config_after)
        assert is_valid is True

    def test_inv_dep01_config_immutability_violation(self):
        """Test INV-DEP01 violation: Config changed."""
        registry = get_registry()

        config_before = {
            "environment": "prod",
            "app_name": "hbc",
        }
        config_after = {
            "environment": "dev",  # Changed
            "app_name": "hbc",
        }

        is_valid, error = registry.check("INV-DEP01", config_before, config_after)
        assert is_valid is False
        assert "environment" in error.lower()

    def test_inv_dep02_secrets_isolation(self):
        """Test INV-DEP02: Secrets isolation."""
        registry = get_registry()

        secrets = {
            "password": "secret123",
            "api_key": "key123",
        }
        exposed_fields = ["username", "region_id"]  # No secrets

        is_valid, error = registry.check("INV-DEP02", secrets, exposed_fields)
        assert is_valid is True

    def test_inv_dep02_secrets_isolation_violation(self):
        """Test INV-DEP02 violation: Secret exposed."""
        from app.core.invariants import InvariantViolation

        registry = get_registry()

        secrets = {
            "password": "secret123",
        }
        exposed_fields = ["password"]  # Secret exposed

        # INV-DEP02 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-DEP02", secrets, exposed_fields)

        assert (
            "exposed" in str(exc_info.value).lower()
            or "secret" in str(exc_info.value).lower()
        )

    def test_inv_dep03_observability_completeness(self):
        """Test INV-DEP03: Observability completeness."""
        registry = get_registry()

        operations = ["forecast", "alert", "notification"]
        observed_operations = ["forecast", "alert", "notification"]

        is_valid, error = registry.check("INV-DEP03", operations, observed_operations)
        assert is_valid is True

    def test_inv_dep03_observability_completeness_violation(self):
        """Test INV-DEP03 violation: Operation not observable."""
        registry = get_registry()

        operations = ["forecast", "alert", "notification"]
        observed_operations = ["forecast", "alert"]  # Missing notification

        is_valid, error = registry.check("INV-DEP03", operations, observed_operations)
        assert is_valid is False
        assert "notification" in error.lower()

    def test_inv_dep04_deployment_determinism(self):
        """Test INV-DEP04: Deployment determinism."""
        registry = get_registry()

        config1 = {
            "environment": "prod",
            "app_name": "hbc",
            "aws_region": "us-east-1",
        }
        config2 = {
            "environment": "prod",
            "app_name": "hbc",
            "aws_region": "us-east-1",
        }

        is_valid, error = registry.check("INV-DEP04", config1, config2)
        assert is_valid is True

    def test_inv_dep05_zero_numerical_drift(self):
        """Test INV-DEP05: Zero numerical drift."""
        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.548

        is_valid, error = registry.check(
            "INV-DEP05", behavior_index_before, behavior_index_after
        )
        assert is_valid is True

    def test_inv_dep05_zero_numerical_drift_violation(self):
        """Test INV-DEP05 violation: Numerical drift."""
        from app.core.invariants import InvariantViolation

        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.550  # Changed

        # INV-DEP05 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-DEP05", behavior_index_before, behavior_index_after)

        assert (
            "drift" in str(exc_info.value).lower()
            or "changed" in str(exc_info.value).lower()
        )


class TestNoSemanticDrift:
    """Tests to ensure deployment features don't cause semantic drift."""

    def test_observability_purely_additive(self):
        """Test that observability is purely additive."""
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

        # Compute before observability
        df_before = computer.compute_behavior_index(harmonized)
        global_before = float(df_before["behavior_index"].iloc[29])

        # Record observability metrics
        manager = get_observability_manager()
        manager.record_forecast("test_region", 100.0, True)

        # Recompute after observability
        df_after = computer.compute_behavior_index(harmonized)
        global_after = float(df_after["behavior_index"].iloc[29])

        # Verify zero numerical drift
        assert abs(global_before - global_after) < 1e-10

    def test_secrets_management_purely_additive(self):
        """Test that secrets management is purely additive."""
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

        # Compute before secrets management
        df_before = computer.compute_behavior_index(harmonized)
        global_before = float(df_before["behavior_index"].iloc[29])

        # Use secrets manager
        secrets_manager = get_secrets_manager()
        secrets_manager.get_secret("TEST_SECRET", default="default")

        # Recompute after secrets management
        df_after = computer.compute_behavior_index(harmonized)
        global_after = float(df_after["behavior_index"].iloc[29])

        # Verify zero numerical drift
        assert abs(global_before - global_after) < 1e-10


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_observability_optional(self):
        """Test that observability is optional."""
        manager = ObservabilityManager()
        # Should not raise even if metrics are empty
        summary = manager.get_metrics_summary()
        assert isinstance(summary, dict)

    def test_secrets_manager_optional(self):
        """Test that secrets manager is optional."""
        manager = SecretsManager(backend="env")
        # Should not raise even if secrets missing
        value = manager.get_secret("NONEXISTENT", default="default")
        assert value == "default"
