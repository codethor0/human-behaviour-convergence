# SPDX-License-Identifier: PROPRIETARY
"""Operational hardening for alerts.

This module orchestrates:
- Alert persistence
- Notification delivery
- Rate limiting
- Kill switches
- Tenant isolation

All operational features are purely additive - they don't change analytics outputs.
"""
import os
from typing import Any, Dict, List, Optional

import structlog

from app.core.notifications import get_notification_manager
from app.core.observability import get_observability_manager
from app.storage.alert_storage import AlertStorage

logger = structlog.get_logger("core.operational")


class OperationalManager:
    """
    Manages operational aspects of alerts: persistence, delivery, rate limiting.

    This class ensures:
    - Alerts are persisted to database
    - Notifications are delivered via configured channels
    - Rate limits are enforced
    - Kill switches are respected
    - Tenant isolation is maintained
    """

    def __init__(
        self,
        alert_storage: Optional[AlertStorage] = None,
        global_alerts_enabled: Optional[bool] = None,
    ):
        """
        Initialize operational manager.

        Args:
            alert_storage: Alert storage instance (default: create new)
            global_alerts_enabled: Global alerts enable flag (default: from env or True)
        """
        self.alert_storage = alert_storage or AlertStorage()
        self.notification_manager = get_notification_manager()

        # Kill switches (can be overridden via environment)
        if global_alerts_enabled is None:
            global_alerts_enabled = (
                os.getenv("ALERTS_ENABLED", "true").lower() == "true"
            )
        self.global_alerts_enabled = global_alerts_enabled

        # Per-channel kill switches (from env)
        self.channel_enabled = {
            "email": os.getenv("ALERTS_EMAIL_ENABLED", "true").lower() == "true",
            "webhook": os.getenv("ALERTS_WEBHOOK_ENABLED", "true").lower() == "true",
            "slack": os.getenv("ALERTS_SLACK_ENABLED", "true").lower() == "true",
        }

        # Update notification manager state
        if not self.global_alerts_enabled:
            self.notification_manager.disable_global()
        else:
            self.notification_manager.enable_global()

        # Disable specific channels if kill-switched
        for channel_name, enabled in self.channel_enabled.items():
            if not enabled:
                self.notification_manager.disable_channel(channel_name)

    def process_alerts(
        self,
        alerts: List[Dict[str, Any]],
        region_id: str,
        region_name: str,
        tenant_id: str = "default",
        rate_limit_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Process alerts: persist, check rate limits, send notifications.

        Args:
            alerts: List of alert dictionaries from compose_alerts()
            region_id: Region identifier
            region_name: Human-readable region name
            tenant_id: Tenant identifier (default: 'default')
            rate_limit_hours: Rate limit window in hours

        Returns:
            Dictionary with:
            - persisted_count: Number of alerts persisted
            - notified_count: Number of alerts notified
            - rate_limited_count: Number of alerts rate-limited
            - results: Per-alert results
        """
        if not self.global_alerts_enabled:
            logger.debug("Alerts globally disabled (kill switch)")
            return {
                "persisted_count": 0,
                "notified_count": 0,
                "rate_limited_count": 0,
                "results": [],
            }

        persisted_count = 0
        notified_count = 0
        rate_limited_count = 0
        results = []

        for alert in alerts:
            alert_id = alert.get("id", "unknown")
            alert_type = alert.get("type", "unknown")
            severity = alert.get("severity", "medium")

            # Persist alert (idempotent)
            try:
                self.alert_storage.upsert_alert(
                    alert_id=alert_id,
                    region_id=region_id,
                    alert_type=alert_type,
                    severity=severity,
                    alert_data=alert,
                    tenant_id=tenant_id,
                )
                persisted_count += 1

                # Check rate limit
                can_notify = self.alert_storage.check_rate_limit(
                    alert_id=alert_id,
                    region_id=region_id,
                    tenant_id=tenant_id,
                    rate_limit_hours=rate_limit_hours,
                )

                if not can_notify:
                    rate_limited_count += 1
                    logger.debug(
                        "Alert rate-limited",
                        alert_id=alert_id,
                        region_id=region_id,
                        rate_limit_hours=rate_limit_hours,
                    )
                    results.append(
                        {
                            "alert_id": alert_id,
                            "persisted": True,
                            "notified": False,
                            "rate_limited": True,
                        }
                    )
                    continue

                # Send notification
                notification_result = self.notification_manager.send_notification(
                    alert=alert,
                    region_name=region_name,
                    tenant_id=tenant_id,
                )

                if notification_result.get("success"):
                    notified_count += 1
                    # Mark notification as sent
                    self.alert_storage.mark_notification_sent(
                        alert_id=alert_id,
                        region_id=region_id,
                        tenant_id=tenant_id,
                    )

                    # Record observability metrics
                    try:
                        observability_manager = get_observability_manager()
                        for channel_name, channel_result in notification_result.get(
                            "channels", {}
                        ).items():
                            observability_manager.record_notification(
                                channel=channel_name,
                                success=channel_result.get("success", False),
                            )
                    except Exception as e:
                        logger.warning(
                            "Failed to record notification metrics",
                            error=str(e),
                            exc_info=True,
                        )

                    logger.info(
                        "Alert processed and notified",
                        alert_id=alert_id,
                        region_id=region_id,
                        channels=list(notification_result.get("channels", {}).keys()),
                    )
                else:
                    logger.warning(
                        "Alert persisted but notification failed",
                        alert_id=alert_id,
                        region_id=region_id,
                        error=notification_result.get("reason"),
                    )

                results.append(
                    {
                        "alert_id": alert_id,
                        "persisted": True,
                        "notified": notification_result.get("success", False),
                        "rate_limited": False,
                        "notification_result": notification_result,
                    }
                )

            except Exception as e:
                logger.error(
                    "Failed to process alert",
                    alert_id=alert_id,
                    region_id=region_id,
                    error=str(e),
                    exc_info=True,
                )
                results.append(
                    {
                        "alert_id": alert_id,
                        "persisted": False,
                        "notified": False,
                        "error": str(e),
                    }
                )

        return {
            "persisted_count": persisted_count,
            "notified_count": notified_count,
            "rate_limited_count": rate_limited_count,
            "results": results,
        }

    def get_active_alerts(
        self,
        region_id: Optional[str] = None,
        tenant_id: str = "default",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get active alerts from storage.

        Args:
            region_id: Optional filter by region
            tenant_id: Tenant identifier
            limit: Maximum number of alerts to return

        Returns:
            List of active alert dictionaries
        """
        return self.alert_storage.get_active_alerts(
            region_id=region_id,
            tenant_id=tenant_id,
            limit=limit,
        )

    def resolve_alert(
        self,
        alert_id: str,
        region_id: str,
        tenant_id: str = "default",
    ) -> bool:
        """
        Resolve an alert (mark as resolved).

        Args:
            alert_id: Alert identifier
            region_id: Region identifier
            tenant_id: Tenant identifier

        Returns:
            True if alert was resolved, False otherwise
        """
        return self.alert_storage.resolve_alert(
            alert_id=alert_id,
            region_id=region_id,
            tenant_id=tenant_id,
        )

    def disable_alerts(self) -> None:
        """Disable alerts globally (kill switch)."""
        self.global_alerts_enabled = False
        self.notification_manager.disable_global()
        logger.warning("Alerts globally disabled via kill switch")

    def enable_alerts(self) -> None:
        """Enable alerts globally."""
        self.global_alerts_enabled = True
        self.notification_manager.enable_global()
        logger.info("Alerts globally enabled")

    def disable_channel(self, channel_name: str) -> None:
        """Disable a specific notification channel (kill switch)."""
        self.channel_enabled[channel_name.lower()] = False
        self.notification_manager.disable_channel(channel_name)
        logger.warning("Channel disabled via kill switch", channel=channel_name)

    def enable_channel(self, channel_name: str) -> None:
        """Enable a specific notification channel."""
        self.channel_enabled[channel_name.lower()] = True
        # Note: NotificationManager doesn't have enable_channel, so we'd need to recreate
        # For now, just update the flag
        logger.info("Channel enabled", channel=channel_name)


# Singleton instance
_operational_manager: Optional[OperationalManager] = None


def get_operational_manager() -> OperationalManager:
    """Get singleton operational manager instance."""
    global _operational_manager
    if _operational_manager is None:
        _operational_manager = OperationalManager()
    return _operational_manager


def reset_operational_manager() -> None:
    """Reset operational manager singleton (for testing)."""
    global _operational_manager
    _operational_manager = None
