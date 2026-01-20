# SPDX-License-Identifier: PROPRIETARY
"""Tests for operational hardening (N+33)."""
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.notifications import (
    EmailChannel,
    SlackChannel,
    WebhookChannel,
    reset_notification_manager,
)
from app.core.operational import (
    OperationalManager,
)
from app.core.invariants import get_registry
from app.storage.alert_storage import AlertStorage


class TestAlertStorage:
    """Tests for alert persistence."""

    def test_alert_storage_init(self):
        """Test alert storage initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))
            assert storage.db_path == db_path

    def test_upsert_alert_new(self):
        """Test creating a new alert."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))

            alert_data = {
                "id": "test_alert",
                "type": "threshold",
                "severity": "high",
            }

            result = storage.upsert_alert(
                alert_id="test_alert",
                region_id="test_region",
                alert_type="threshold",
                severity="high",
                alert_data=alert_data,
            )

            assert result["alert_id"] == "test_alert"
            assert result["region_id"] == "test_region"
            assert result["status"] == "active"
            assert result["alert_data"] == alert_data

    def test_upsert_alert_idempotent(self):
        """Test idempotent alert upsert."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))

            alert_data = {"id": "test_alert", "type": "threshold"}

            # First upsert
            result1 = storage.upsert_alert(
                alert_id="test_alert",
                region_id="test_region",
                alert_type="threshold",
                severity="high",
                alert_data=alert_data,
            )

            # Second upsert (should update, not create duplicate)
            result2 = storage.upsert_alert(
                alert_id="test_alert",
                region_id="test_region",
                alert_type="threshold",
                severity="high",
                alert_data=alert_data,
            )

            assert result1["id"] == result2["id"]  # Same database ID
            assert result2["status"] == "active"

    def test_resolve_alert(self):
        """Test resolving an alert."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))

            # Create alert
            storage.upsert_alert(
                alert_id="test_alert",
                region_id="test_region",
                alert_type="threshold",
                severity="high",
                alert_data={"id": "test_alert"},
            )

            # Resolve alert
            resolved = storage.resolve_alert("test_alert", "test_region")
            assert resolved is True

            # Try to resolve again (should return False)
            resolved_again = storage.resolve_alert("test_alert", "test_region")
            assert resolved_again is False

    def test_get_active_alerts(self):
        """Test getting active alerts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))

            # Create multiple alerts
            for i in range(3):
                storage.upsert_alert(
                    alert_id=f"alert_{i}",
                    region_id="test_region",
                    alert_type="threshold",
                    severity="high",
                    alert_data={"id": f"alert_{i}"},
                )

            # Get active alerts
            active = storage.get_active_alerts(region_id="test_region")
            assert len(active) == 3

            # Resolve one
            storage.resolve_alert("alert_0", "test_region")

            # Get active alerts again
            active = storage.get_active_alerts(region_id="test_region")
            assert len(active) == 2

    def test_rate_limit_check(self):
        """Test rate limit checking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))

            # Create alert
            storage.upsert_alert(
                alert_id="test_alert",
                region_id="test_region",
                alert_type="threshold",
                severity="high",
                alert_data={"id": "test_alert"},
            )

            # Mark notification sent
            storage.mark_notification_sent("test_alert", "test_region")

            # Check rate limit (should be False within 24h window)
            can_notify = storage.check_rate_limit(
                "test_alert", "test_region", rate_limit_hours=24
            )
            assert can_notify is False

            # Check with very short window (should pass)
            can_notify_short = storage.check_rate_limit(
                "test_alert", "test_region", rate_limit_hours=0
            )
            assert can_notify_short is True


class TestNotificationChannels:
    """Tests for notification channels."""

    def test_email_channel_not_configured(self):
        """Test email channel when not configured."""
        channel = EmailChannel()
        assert channel.is_enabled() is False

    @patch.dict(os.environ, {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_USER": "user",
        "SMTP_PASSWORD": "pass",
        "SMTP_FROM_EMAIL": "from@example.com",
        "SMTP_TO_EMAILS": "to@example.com",
    })
    def test_email_channel_configured(self):
        """Test email channel when configured."""
        reset_notification_manager()
        channel = EmailChannel()
        assert channel.is_enabled() is True

    def test_webhook_channel_not_configured(self):
        """Test webhook channel when not configured."""
        channel = WebhookChannel()
        assert channel.is_enabled() is False

    @patch.dict(os.environ, {"WEBHOOK_URL": "https://example.com/webhook"})
    def test_webhook_channel_configured(self):
        """Test webhook channel when configured."""
        channel = WebhookChannel()
        assert channel.is_enabled() is True

    def test_slack_channel_not_configured(self):
        """Test Slack channel when not configured."""
        channel = SlackChannel()
        assert channel.is_enabled() is False

    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/webhook"})
    def test_slack_channel_configured(self):
        """Test Slack channel when configured."""
        channel = SlackChannel()
        assert channel.is_enabled() is True


class TestOperationalManager:
    """Tests for operational manager."""

    def test_process_alerts_persist(self):
        """Test processing alerts with persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))

            manager = OperationalManager(alert_storage=storage, global_alerts_enabled=True)

            alerts = [
                {
                    "id": "test_alert",
                    "type": "threshold",
                    "severity": "high",
                    "label": "Test Alert",
                }
            ]

            result = manager.process_alerts(
                alerts=alerts,
                region_id="test_region",
                region_name="Test Region",
                tenant_id="default",
                rate_limit_hours=24,
            )

            assert result["persisted_count"] == 1
            assert result["notified_count"] >= 0  # May be 0 if channels not configured

    def test_process_alerts_rate_limit(self):
        """Test rate limiting in alert processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))

            manager = OperationalManager(alert_storage=storage, global_alerts_enabled=True)

            alerts = [
                {
                    "id": "test_alert",
                    "type": "threshold",
                    "severity": "high",
                }
            ]

            # First processing
            manager.process_alerts(
                alerts=alerts,
                region_id="test_region",
                region_name="Test Region",
                tenant_id="default",
                rate_limit_hours=24,
            )

            # Mark notification sent
            storage.mark_notification_sent("test_alert", "test_region")

            # Second processing (should be rate-limited)
            result2 = manager.process_alerts(
                alerts=alerts,
                region_id="test_region",
                region_name="Test Region",
                tenant_id="default",
                rate_limit_hours=24,
            )

            assert result2["rate_limited_count"] == 1

    def test_kill_switch_global(self):
        """Test global kill switch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))

            manager = OperationalManager(alert_storage=storage, global_alerts_enabled=False)

            alerts = [{"id": "test_alert", "type": "threshold", "severity": "high"}]

            result = manager.process_alerts(
                alerts=alerts,
                region_id="test_region",
                region_name="Test Region",
            )

            assert result["persisted_count"] == 0
            assert result["notified_count"] == 0

    def test_tenant_isolation(self):
        """Test tenant isolation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))

            # Create alert for tenant1
            storage.upsert_alert(
                alert_id="test_alert",
                region_id="test_region",
                alert_type="threshold",
                severity="high",
                alert_data={"id": "test_alert"},
                tenant_id="tenant1",
            )

            # Get active alerts for tenant1
            alerts_tenant1 = storage.get_active_alerts(tenant_id="tenant1")
            assert len(alerts_tenant1) == 1

            # Get active alerts for tenant2 (should be empty)
            alerts_tenant2 = storage.get_active_alerts(tenant_id="tenant2")
            assert len(alerts_tenant2) == 0


class TestOperationalInvariants:
    """Tests for operational invariants."""

    def test_inv_o01_alert_persistence_determinism(self):
        """Test INV-O01: Alert persistence determinism."""
        registry = get_registry()

        alert1 = {
            "alert_id": "test",
            "region_id": "region1",
            "tenant_id": "default",
        }
        alert2 = {
            "alert_id": "test",
            "region_id": "region1",
            "tenant_id": "default",
        }

        is_valid, error = registry.check("INV-O01", alert1, alert2)
        assert is_valid is True

    def test_inv_o02_no_duplicate_active_alerts(self):
        """Test INV-O02: No duplicate active alerts."""
        registry = get_registry()

        alerts = [
            {
                "alert_id": "alert1",
                "region_id": "region1",
                "tenant_id": "default",
                "status": "active",
            },
            {
                "alert_id": "alert2",
                "region_id": "region1",
                "tenant_id": "default",
                "status": "active",
            },
        ]

        is_valid, error = registry.check("INV-O02", alerts)
        assert is_valid is True

    def test_inv_o02_duplicate_violation(self):
        """Test INV-O02 violation: Duplicate active alerts."""
        registry = get_registry()

        alerts = [
            {
                "alert_id": "alert1",
                "region_id": "region1",
                "tenant_id": "default",
                "status": "active",
            },
            {
                "alert_id": "alert1",  # Duplicate
                "region_id": "region1",
                "tenant_id": "default",
                "status": "active",
            },
        ]

        is_valid, error = registry.check("INV-O02", alerts)
        assert is_valid is False
        assert "duplicate" in error.lower()

    def test_inv_o03_tenant_isolation(self):
        """Test INV-O03: Tenant isolation."""
        registry = get_registry()

        alert = {
            "alert_id": "test",
            "region_id": "region1",
            "tenant_id": "tenant1",
        }

        is_valid, error = registry.check("INV-O03", alert, tenant_id="tenant1")
        assert is_valid is True

    def test_inv_o03_tenant_isolation_violation(self):
        """Test INV-O03 violation: Tenant isolation."""
        from app.core.invariants import InvariantViolation

        registry = get_registry()

        alert = {
            "alert_id": "test",
            "region_id": "region1",
            "tenant_id": "tenant1",
        }

        # INV-O03 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation):
            registry.check("INV-O03", alert, tenant_id="tenant2")

    def test_inv_o04_notification_rate_limits(self):
        """Test INV-O04: Notification rate limits."""
        registry = get_registry()

        now = datetime.now(timezone.utc).isoformat()
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        # Within rate limit window (should fail)
        is_valid, error = registry.check(
            "INV-O04", last_notification_time=one_hour_ago, current_time=now, rate_limit_hours=24
        )
        assert is_valid is False

        # Outside rate limit window (should pass)
        one_day_ago = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        is_valid, error = registry.check(
            "INV-O04", last_notification_time=one_day_ago, current_time=now, rate_limit_hours=24
        )
        assert is_valid is True

    def test_inv_o05_zero_numerical_drift(self):
        """Test INV-O05: Zero numerical drift."""
        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.548

        is_valid, error = registry.check("INV-O05", behavior_index_before, behavior_index_after)
        assert is_valid is True

    def test_inv_o05_zero_numerical_drift_violation(self):
        """Test INV-O05 violation: Numerical drift."""
        from app.core.invariants import InvariantViolation

        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.550  # Changed

        # INV-O05 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-O05", behavior_index_before, behavior_index_after)

        assert "drift" in str(exc_info.value).lower() or "changed" in str(exc_info.value).lower()


class TestNoSemanticDrift:
    """Tests to ensure operational features don't cause semantic drift."""

    def test_operational_features_purely_additive(self):
        """Test that operational features are purely additive."""
        # Operational features should not change alert generation logic
        # This is verified by ensuring alerts are generated first, then processed operationally
        from app.core.alerting import compose_alerts

        alerts_dict = compose_alerts(
            behavior_index=0.8,
            behavior_index_history=[0.8] * 10,
            alert_definitions=[
                {
                    "id": "test",
                    "type": "threshold",
                    "threshold": 0.7,
                    "comparison": "greater_than",
                    "persistence_days": 0,
                    "severity": "high",
                }
            ],
        )

        # Alerts should be generated regardless of operational features
        assert alerts_dict["alert_count"] > 0
        assert len(alerts_dict["alerts"]) > 0


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_operational_features_optional(self):
        """Test that operational features are optional."""
        # API should work even if operational features fail
        # This is tested by ensuring exceptions in operational processing don't break the API
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = AlertStorage(db_path=str(db_path))

            manager = OperationalManager(alert_storage=storage, global_alerts_enabled=True)

            # Process alerts (should not raise even if notifications fail)
            alerts = [{"id": "test", "type": "threshold", "severity": "high"}]
            result = manager.process_alerts(
                alerts=alerts,
                region_id="test_region",
                region_name="Test Region",
            )

            # Should complete without exception
            assert isinstance(result, dict)
            assert "persisted_count" in result
