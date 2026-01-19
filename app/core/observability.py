# SPDX-License-Identifier: PROPRIETARY
"""Observability and SRE readiness.

This module provides structured logging, metrics, and traces for production
deployment without changing any numerical computations.

Zero numerical drift is a HARD invariant.
"""
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger("core.observability")


class ObservabilityManager:
    """
    Manages observability: structured logs, metrics, traces.

    This class ensures:
    - Structured logging (no sensitive payloads)
    - Metrics collection (alert throughput, notification failures, latency)
    - Traces for forecast → alert → notify flow
    - Health check readiness
    """

    def __init__(self):
        """Initialize observability manager."""
        self.metrics = {
            "forecast_count": 0,
            "alert_count": 0,
            "notification_success_count": 0,
            "notification_failure_count": 0,
            "forecast_latency_ms": [],
            "alert_processing_latency_ms": [],
        }
        self._metrics_lock = None
        try:
            import threading

            self._metrics_lock = threading.Lock()
        except ImportError:
            pass

    def record_forecast(
        self,
        region_id: str,
        latency_ms: float,
        success: bool,
    ) -> None:
        """
        Record forecast metric.

        Args:
            region_id: Region identifier
            latency_ms: Forecast latency in milliseconds
            success: Whether forecast succeeded
        """
        if self._metrics_lock:
            with self._metrics_lock:
                self.metrics["forecast_count"] += 1
                self.metrics["forecast_latency_ms"].append(latency_ms)
                # Keep only last 1000 latency measurements
                if len(self.metrics["forecast_latency_ms"]) > 1000:
                    self.metrics["forecast_latency_ms"] = self.metrics[
                        "forecast_latency_ms"
                    ][-1000:]
        else:
            self.metrics["forecast_count"] += 1
            self.metrics["forecast_latency_ms"].append(latency_ms)
            if len(self.metrics["forecast_latency_ms"]) > 1000:
                self.metrics["forecast_latency_ms"] = self.metrics[
                    "forecast_latency_ms"
                ][-1000:]

        logger.info(
            "forecast_recorded",
            region_id=region_id,
            latency_ms=latency_ms,
            success=success,
        )

    def record_alert(
        self,
        alert_id: str,
        region_id: str,
        alert_count: int,
    ) -> None:
        """
        Record alert metric.

        Args:
            alert_id: Alert identifier
            region_id: Region identifier
            alert_count: Number of alerts triggered
        """
        if self._metrics_lock:
            with self._metrics_lock:
                self.metrics["alert_count"] += alert_count
        else:
            self.metrics["alert_count"] += alert_count

        logger.info(
            "alert_recorded",
            alert_id=alert_id,
            region_id=region_id,
            alert_count=alert_count,
        )

    def record_notification(
        self,
        channel: str,
        success: bool,
        latency_ms: Optional[float] = None,
    ) -> None:
        """
        Record notification metric.

        Args:
            channel: Notification channel (email, webhook, slack)
            success: Whether notification succeeded
            latency_ms: Notification latency in milliseconds (optional)
        """
        if self._metrics_lock:
            with self._metrics_lock:
                if success:
                    self.metrics["notification_success_count"] += 1
                else:
                    self.metrics["notification_failure_count"] += 1
        else:
            if success:
                self.metrics["notification_success_count"] += 1
            else:
                self.metrics["notification_failure_count"] += 1

        logger.info(
            "notification_recorded",
            channel=channel,
            success=success,
            latency_ms=latency_ms,
        )

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary.

        Returns:
            Dictionary with aggregated metrics
        """
        forecast_latencies = self.metrics.get("forecast_latency_ms", [])
        avg_latency = (
            sum(forecast_latencies) / len(forecast_latencies)
            if forecast_latencies
            else 0.0
        )

        return {
            "forecast_count": self.metrics.get("forecast_count", 0),
            "alert_count": self.metrics.get("alert_count", 0),
            "notification_success_count": self.metrics.get(
                "notification_success_count", 0
            ),
            "notification_failure_count": self.metrics.get(
                "notification_failure_count", 0
            ),
            "avg_forecast_latency_ms": avg_latency,
            "notification_success_rate": (
                self.metrics.get("notification_success_count", 0)
                / max(
                    self.metrics.get("notification_success_count", 0)
                    + self.metrics.get("notification_failure_count", 0),
                    1,
                )
            ),
        }

    @contextmanager
    def trace_forecast_to_alert_to_notify(
        self,
        region_id: str,
        forecast_id: Optional[str] = None,
    ):
        """
        Context manager for tracing forecast → alert → notify flow.

        Args:
            region_id: Region identifier
            forecast_id: Optional forecast identifier

        Yields:
            Trace context dictionary
        """
        trace_id = f"trace_{int(time.time() * 1000)}"
        start_time = time.time()

        trace_context = {
            "trace_id": trace_id,
            "region_id": region_id,
            "forecast_id": forecast_id,
            "start_time": start_time,
        }

        logger.info(
            "trace_started",
            trace_id=trace_id,
            region_id=region_id,
            forecast_id=forecast_id,
        )

        try:
            yield trace_context
        finally:
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "trace_completed",
                trace_id=trace_id,
                region_id=region_id,
                duration_ms=duration_ms,
            )


# Singleton instance
_observability_manager: Optional[ObservabilityManager] = None


def get_observability_manager() -> ObservabilityManager:
    """Get singleton observability manager instance."""
    global _observability_manager
    if _observability_manager is None:
        _observability_manager = ObservabilityManager()
    return _observability_manager


def reset_observability_manager() -> None:
    """Reset observability manager singleton (for testing)."""
    global _observability_manager
    _observability_manager = None
