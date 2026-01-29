# SPDX-License-Identifier: PROPRIETARY
"""Derived Metrics for Storytelling Visualizations.

Computes derived metrics from base metrics to support storytelling dashboards.
All metrics use new names to avoid breaking existing functionality.
"""
from typing import Dict, Optional

import structlog

logger = structlog.get_logger("storytelling.derived_metrics")

# Try to import Prometheus client, but don't fail if unavailable
try:
    from prometheus_client import Gauge

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning(
        "Prometheus client not available, derived metrics will not be emitted"
    )

if PROMETHEUS_AVAILABLE:
    # Rate-of-change metrics
    behavior_index_delta_7d_gauge = Gauge(
        "behavior_index_delta_7d", "7-day change in behavior index", ["region"]
    )

    behavior_index_delta_30d_gauge = Gauge(
        "behavior_index_delta_30d", "30-day change in behavior index", ["region"]
    )

    behavior_index_delta_90d_gauge = Gauge(
        "behavior_index_delta_90d", "90-day change in behavior index", ["region"]
    )

    # Volatility metrics
    behavior_index_volatility_30d_gauge = Gauge(
        "behavior_index_volatility_30d",
        "30-day volatility (standard deviation) of behavior index",
        ["region"],
    )

    stability_score_gauge = Gauge(
        "stability_score",
        "Stability score (inverse of volatility, higher = more stable)",
        ["region"],
    )

    # Forecast diagnostics (if forecast metrics exist)
    forecast_error_absolute_gauge = Gauge(
        "forecast_error_absolute",
        "Absolute forecast error (|actual - forecast|)",
        ["region", "model"],
    )

    forecast_error_pct_gauge = Gauge(
        "forecast_error_pct",
        "Percentage forecast error ((actual - forecast) / actual * 100)",
        ["region", "model"],
    )
else:
    behavior_index_delta_7d_gauge = None
    behavior_index_delta_30d_gauge = None
    behavior_index_delta_90d_gauge = None
    behavior_index_volatility_30d_gauge = None
    stability_score_gauge = None
    forecast_error_absolute_gauge = None
    forecast_error_pct_gauge = None


def compute_derived_metrics(
    current_behavior_index: float,
    region: str,
    historical_values: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Compute derived metrics for storytelling.

    Args:
        current_behavior_index: Current behavior index value
        region: Region identifier
        historical_values: Optional dict with keys like '7d_ago', '30d_ago', '90d_ago'

    Returns:
        Dictionary of derived metric values
    """
    if not PROMETHEUS_AVAILABLE:
        return {}

    derived = {}

    # Compute deltas if historical values available
    if historical_values:
        if "7d_ago" in historical_values:
            delta_7d = current_behavior_index - historical_values["7d_ago"]
            derived["delta_7d"] = delta_7d
            if behavior_index_delta_7d_gauge:
                behavior_index_delta_7d_gauge.labels(region=region).set(delta_7d)

        if "30d_ago" in historical_values:
            delta_30d = current_behavior_index - historical_values["30d_ago"]
            derived["delta_30d"] = delta_30d
            if behavior_index_delta_30d_gauge:
                behavior_index_delta_30d_gauge.labels(region=region).set(delta_30d)

        if "90d_ago" in historical_values:
            delta_90d = current_behavior_index - historical_values["90d_ago"]
            derived["delta_90d"] = delta_90d
            if behavior_index_delta_90d_gauge:
                behavior_index_delta_90d_gauge.labels(region=region).set(delta_90d)

    return derived


def compute_volatility_metrics(region: str, volatility_30d: float) -> None:
    """
    Emit volatility and stability metrics.

    Args:
        region: Region identifier
        volatility_30d: 30-day standard deviation of behavior index
    """
    if not PROMETHEUS_AVAILABLE:
        return

    if behavior_index_volatility_30d_gauge:
        behavior_index_volatility_30d_gauge.labels(region=region).set(volatility_30d)

    # Stability score is inverse of volatility (normalized)
    # Higher volatility = lower stability
    # Normalize to 0-1 range (assuming max volatility of 0.5)
    max_volatility = 0.5
    stability_score = max(0.0, 1.0 - (volatility_30d / max_volatility))

    if stability_score_gauge:
        stability_score_gauge.labels(region=region).set(stability_score)


def compute_forecast_error_metrics(
    region: str, model: str, actual: float, forecast: float
) -> None:
    """
    Emit forecast error metrics.

    Args:
        region: Region identifier
        model: Model name
        actual: Actual behavior index value
        forecast: Forecasted behavior index value
    """
    if not PROMETHEUS_AVAILABLE:
        return

    if actual == 0:
        logger.warning(
            "Cannot compute percentage error: actual value is zero", region=region
        )
        return

    error_absolute = abs(actual - forecast)
    error_pct = ((actual - forecast) / actual) * 100

    if forecast_error_absolute_gauge:
        forecast_error_absolute_gauge.labels(region=region, model=model).set(
            error_absolute
        )

    if forecast_error_pct_gauge:
        forecast_error_pct_gauge.labels(region=region, model=model).set(error_pct)
