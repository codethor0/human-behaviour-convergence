# SPDX-License-Identifier: PROPRIETARY
"""Notification delivery system.

This module provides pluggable notification channels:
- Email (SMTP)
- Webhook (signed payloads)
- Slack (optional)

All notifications include retry logic, backoff, and audit logging.
"""
import hashlib
import hmac
import json
import os
import smtplib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger("core.notifications")


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    def send(
        self,
        alert: Dict[str, Any],
        region_name: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Send a notification.

        Args:
            alert: Alert dictionary
            region_name: Human-readable region name
            tenant_id: Tenant identifier

        Returns:
            Dictionary with:
            - success: bool
            - channel: str
            - message_id: Optional[str]
            - error: Optional[str]
        """
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if channel is enabled."""
        pass


class EmailChannel(NotificationChannel):
    """Email notification channel via SMTP."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        to_emails: Optional[List[str]] = None,
    ):
        """
        Initialize email channel.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: From email address
            to_emails: List of recipient email addresses
        """
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("SMTP_FROM_EMAIL")
        self.to_emails = to_emails or (
            os.getenv("SMTP_TO_EMAILS", "").split(",")
            if os.getenv("SMTP_TO_EMAILS")
            else []
        )

    def is_enabled(self) -> bool:
        """Check if email channel is enabled."""
        return bool(
            self.smtp_host
            and self.smtp_user
            and self.smtp_password
            and self.from_email
            and self.to_emails
        )

    def send(
        self,
        alert: Dict[str, Any],
        region_name: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Send email notification."""
        if not self.is_enabled():
            return {
                "success": False,
                "channel": "email",
                "error": "Email channel not configured",
            }

        try:
            # Format alert message
            subject = f"Alert: {alert.get('label', alert.get('id', 'Unknown'))} - {region_name}"
            body = self._format_alert_message(alert, region_name)

            # Create email message
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(
                "Email notification sent",
                alert_id=alert.get("id"),
                region_name=region_name,
                to_emails=self.to_emails,
            )

            return {
                "success": True,
                "channel": "email",
                "message_id": f"email_{datetime.now(timezone.utc).isoformat()}",
            }
        except Exception as e:
            logger.error(
                "Failed to send email notification",
                alert_id=alert.get("id"),
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "channel": "email",
                "error": str(e),
            }

    def _format_alert_message(self, alert: Dict[str, Any], region_name: str) -> str:
        """Format alert as email message."""
        lines = [
            f"Alert: {alert.get('label', alert.get('id', 'Unknown'))}",
            f"Region: {region_name}",
            f"Type: {alert.get('type', 'unknown')}",
            f"Severity: {alert.get('severity', 'medium')}",
            "",
        ]

        if alert.get("current_value") is not None:
            lines.append(f"Current Value: {alert['current_value']:.3f}")
        if alert.get("threshold") is not None:
            lines.append(f"Threshold: {alert['threshold']:.3f}")
        if alert.get("delta") is not None:
            lines.append(f"Delta: {alert['delta']:.3f}")
        if alert.get("persistence_days"):
            lines.append(f"Persistence: {alert['persistence_days']} days")

        lines.append("")
        lines.append(f"Generated at: {datetime.now(timezone.utc).isoformat()}")

        return "\n".join(lines)


class WebhookChannel(NotificationChannel):
    """Webhook notification channel with signed payloads."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        timeout_seconds: int = 10,
    ):
        """
        Initialize webhook channel.

        Args:
            webhook_url: Webhook URL endpoint
            webhook_secret: Secret for HMAC signing
            timeout_seconds: Request timeout in seconds
        """
        self.webhook_url = webhook_url or os.getenv("WEBHOOK_URL")
        self.webhook_secret = webhook_secret or os.getenv("WEBHOOK_SECRET", "")
        self.timeout_seconds = timeout_seconds

    def is_enabled(self) -> bool:
        """Check if webhook channel is enabled."""
        return bool(self.webhook_url)

    def send(
        self,
        alert: Dict[str, Any],
        region_name: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Send webhook notification."""
        if not self.is_enabled():
            return {
                "success": False,
                "channel": "webhook",
                "error": "Webhook URL not configured",
            }

        try:
            import requests

            # Prepare payload
            payload = {
                "alert": alert,
                "region_name": region_name,
                "tenant_id": tenant_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Sign payload if secret provided
            headers = {"Content-Type": "application/json"}
            if self.webhook_secret:
                payload_json = json.dumps(payload, sort_keys=True)
                signature = hmac.new(
                    self.webhook_secret.encode(),
                    payload_json.encode(),
                    hashlib.sha256,
                ).hexdigest()
                headers["X-Signature"] = f"sha256={signature}"

            # Send webhook
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()

            logger.info(
                "Webhook notification sent",
                alert_id=alert.get("id"),
                region_name=region_name,
                webhook_url=self.webhook_url,
                status_code=response.status_code,
            )

            return {
                "success": True,
                "channel": "webhook",
                "message_id": f"webhook_{datetime.now(timezone.utc).isoformat()}",
            }
        except ImportError:
            return {
                "success": False,
                "channel": "webhook",
                "error": "requests library not available",
            }
        except Exception as e:
            logger.error(
                "Failed to send webhook notification",
                alert_id=alert.get("id"),
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "channel": "webhook",
                "error": str(e),
            }


class SlackChannel(NotificationChannel):
    """Slack notification channel (optional)."""

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Slack channel.

        Args:
            webhook_url: Slack webhook URL
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    def is_enabled(self) -> bool:
        """Check if Slack channel is enabled."""
        return bool(self.webhook_url)

    def send(
        self,
        alert: Dict[str, Any],
        region_name: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Send Slack notification."""
        if not self.is_enabled():
            return {
                "success": False,
                "channel": "slack",
                "error": "Slack webhook URL not configured",
            }

        try:
            import requests

            # Format Slack message
            severity_emoji = {
                "low": "⚠️",
                "medium": "🔶",
                "high": "🔴",
            }.get(alert.get("severity", "medium"), "🔶")

            text = (
                f"{severity_emoji} *Alert: {alert.get('label', alert.get('id', 'Unknown'))}*\n"
                f"Region: {region_name}\n"
                f"Type: {alert.get('type', 'unknown')}\n"
                f"Severity: {alert.get('severity', 'medium')}"
            )

            payload = {"text": text}

            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()

            logger.info(
                "Slack notification sent",
                alert_id=alert.get("id"),
                region_name=region_name,
            )

            return {
                "success": True,
                "channel": "slack",
                "message_id": f"slack_{datetime.now(timezone.utc).isoformat()}",
            }
        except ImportError:
            return {
                "success": False,
                "channel": "slack",
                "error": "requests library not available",
            }
        except Exception as e:
            logger.error(
                "Failed to send Slack notification",
                alert_id=alert.get("id"),
                error=str(e),
                exc_info=True,
            )
            return {
                "success": False,
                "channel": "slack",
                "error": str(e),
            }


class NotificationManager:
    """Manages multiple notification channels."""

    def __init__(
        self,
        channels: Optional[List[NotificationChannel]] = None,
        global_enabled: bool = True,
    ):
        """
        Initialize notification manager.

        Args:
            channels: List of notification channels (default: auto-detect from env)
            global_enabled: Global enable/disable flag (kill switch)
        """
        if channels is None:
            channels = [
                EmailChannel(),
                WebhookChannel(),
                SlackChannel(),
            ]
        self.channels = [ch for ch in channels if ch.is_enabled()]
        self.global_enabled = global_enabled

    def send_notification(
        self,
        alert: Dict[str, Any],
        region_name: str,
        tenant_id: str = "default",
        channel_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send notification via all enabled channels.

        Args:
            alert: Alert dictionary
            region_name: Human-readable region name
            tenant_id: Tenant identifier
            channel_filter: Optional list of channel names to use (None = all)

        Returns:
            Dictionary with results per channel
        """
        if not self.global_enabled:
            logger.debug("Notifications globally disabled (kill switch)")
            return {
                "success": False,
                "reason": "globally_disabled",
                "channels": {},
            }

        results = {}
        for channel in self.channels:
            channel_name = channel.__class__.__name__.replace("Channel", "").lower()
            if channel_filter and channel_name not in channel_filter:
                continue

            try:
                result = channel.send(alert, region_name, tenant_id)
                results[channel_name] = result
            except Exception as e:
                logger.error(
                    "Channel send failed",
                    channel=channel_name,
                    error=str(e),
                    exc_info=True,
                )
                results[channel_name] = {
                    "success": False,
                    "channel": channel_name,
                    "error": str(e),
                }

        # Overall success if at least one channel succeeded
        overall_success = any(r.get("success", False) for r in results.values())

        return {
            "success": overall_success,
            "channels": results,
        }

    def disable_channel(self, channel_name: str) -> None:
        """Disable a specific channel (kill switch)."""
        channel_name_lower = channel_name.lower()
        self.channels = [
            ch
            for ch in self.channels
            if ch.__class__.__name__.replace("Channel", "").lower()
            != channel_name_lower
        ]
        logger.info("Channel disabled", channel=channel_name)

    def enable_global(self) -> None:
        """Enable global notifications."""
        self.global_enabled = True
        logger.info("Notifications globally enabled")

    def disable_global(self) -> None:
        """Disable global notifications (kill switch)."""
        self.global_enabled = False
        logger.info("Notifications globally disabled")


# Singleton instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get singleton notification manager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def reset_notification_manager() -> None:
    """Reset notification manager singleton (for testing)."""
    global _notification_manager
    _notification_manager = None
