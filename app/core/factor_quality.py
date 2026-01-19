# SPDX-License-Identifier: PROPRIETARY
"""Factor quality and signal strength metrics.

This module computes quality metrics for factors to enable decision-useful
explainability without changing numerical outputs.
"""
import math
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import structlog

logger = structlog.get_logger("core.factor_quality")


def calculate_factor_confidence(
    factor_value: float,
    has_data: bool,
    data_freshness_days: Optional[float] = None,
    stability_score: Optional[float] = None,
) -> float:
    """
    Calculate confidence score for a factor.

    Confidence is based on:
    - Data completeness (has_data)
    - Data freshness (if available)
    - Stability (if available)

    Args:
        factor_value: Current factor value
        has_data: Whether factor has actual data (not default/fallback)
        data_freshness_days: Days since last data update (None if unknown)
        stability_score: Stability score from historical variance (None if unavailable)

    Returns:
        Confidence score in [0.0, 1.0]
    """
    if not has_data:
        return 0.3  # Low confidence for missing/default data

    confidence = 0.5  # Base confidence

    # Freshness component (0.0 to 0.3)
    if data_freshness_days is not None:
        if data_freshness_days <= 1:
            freshness_score = 0.3
        elif data_freshness_days <= 7:
            freshness_score = 0.2
        elif data_freshness_days <= 30:
            freshness_score = 0.1
        else:
            freshness_score = 0.0
        confidence += freshness_score
    else:
        # Assume moderate freshness if unknown
        confidence += 0.15

    # Stability component (0.0 to 0.2)
    if stability_score is not None:
        # stability_score is typically 1.0 - coefficient_of_variation
        # Higher stability = higher confidence
        confidence += stability_score * 0.2
    else:
        # Assume moderate stability if unknown
        confidence += 0.1

    return max(0.0, min(1.0, confidence))


def calculate_factor_volatility(
    factor_values: pd.Series,
    window_days: int = 30,
) -> Tuple[float, str]:
    """
    Calculate volatility and classification for a factor.

    Args:
        factor_values: Historical factor values (time series)
        window_days: Number of days to consider for volatility

    Returns:
        Tuple of (volatility_score, classification)
        - volatility_score: Coefficient of variation (0.0 to inf, typically 0.0-2.0)
        - classification: "low", "medium", or "high"
    """
    if len(factor_values) < 2:
        return 0.0, "low"

    # Use most recent window_days if available
    recent_values = (
        factor_values.tail(window_days)
        if len(factor_values) > window_days
        else factor_values
    )

    # Remove NaN/inf
    clean_values = recent_values.dropna()
    clean_values = clean_values[clean_values.apply(lambda x: math.isfinite(x))]

    if len(clean_values) < 2:
        return 0.0, "low"

    mean_val = clean_values.mean()
    if abs(mean_val) < 1e-10:
        return 0.0, "low"

    std_val = clean_values.std()
    coefficient_of_variation = std_val / abs(mean_val)

    # Classify volatility
    if coefficient_of_variation < 0.1:
        classification = "low"
    elif coefficient_of_variation < 0.3:
        classification = "medium"
    else:
        classification = "high"

    return float(coefficient_of_variation), classification


def calculate_factor_persistence(
    factor_contributions: pd.Series,
    threshold: float = 0.01,
) -> int:
    """
    Calculate persistence (days factor has materially contributed).

    Args:
        factor_contributions: Historical factor contributions (time series)
        threshold: Minimum contribution to count as "material"

    Returns:
        Number of consecutive days factor has contributed above threshold
    """
    if len(factor_contributions) == 0:
        return 0

    # Count consecutive days from most recent backward
    persistence = 0
    for contribution in reversed(factor_contributions):
        if pd.isna(contribution) or not math.isfinite(contribution):
            break
        if abs(contribution) >= threshold:
            persistence += 1
        else:
            break

    return persistence


def calculate_factor_trend(
    factor_values: pd.Series,
    window_days: int = 14,
) -> str:
    """
    Calculate trend direction for a factor.

    Args:
        factor_values: Historical factor values (time series)
        window_days: Number of days to consider for trend

    Returns:
        "improving", "worsening", or "stable"
    """
    if len(factor_values) < 2:
        return "stable"

    # Use most recent window_days if available
    recent_values = (
        factor_values.tail(window_days)
        if len(factor_values) > window_days
        else factor_values
    )

    # Remove NaN/inf
    clean_values = recent_values.dropna()
    clean_values = clean_values[clean_values.apply(lambda x: math.isfinite(x))]

    if len(clean_values) < 2:
        return "stable"

    # Simple linear trend
    first_half = clean_values[: len(clean_values) // 2].mean()
    second_half = clean_values[len(clean_values) // 2 :].mean()

    diff = second_half - first_half
    threshold = 0.05  # 5% change threshold

    if diff > threshold:
        return "worsening"
    elif diff < -threshold:
        return "improving"
    else:
        return "stable"


def calculate_signal_strength(
    contribution: float,
    volatility_score: float,
    confidence: float,
) -> float:
    """
    Calculate signal strength (variance-adjusted contribution magnitude).

    Signal strength = contribution * confidence / (1 + volatility)

    Args:
        contribution: Factor contribution to sub-index
        volatility_score: Volatility coefficient of variation
        confidence: Factor confidence score

    Returns:
        Signal strength score (typically 0.0-1.0, can exceed 1.0 for high contributions)
    """
    if (
        not math.isfinite(contribution)
        or not math.isfinite(volatility_score)
        or not math.isfinite(confidence)
    ):
        return 0.0

    # Normalize volatility (add 1 to avoid division by zero)
    volatility_adjustment = 1.0 + volatility_score

    # Signal strength = contribution * confidence / volatility_adjustment
    signal = abs(contribution) * confidence / volatility_adjustment

    return float(signal)


def compute_factor_quality_metrics(
    factor_id: str,
    current_value: float,
    current_contribution: float,
    factor_values_series: Optional[pd.Series] = None,
    factor_contributions_series: Optional[pd.Series] = None,
    has_data: bool = True,
    data_freshness_days: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute all quality metrics for a factor.

    Args:
        factor_id: Factor identifier
        current_value: Current factor value
        current_contribution: Current factor contribution
        factor_values_series: Historical factor values (optional)
        factor_contributions_series: Historical factor contributions (optional)
        has_data: Whether factor has actual data
        data_freshness_days: Days since last data update

    Returns:
        Dictionary with quality metrics:
        - confidence: float [0.0, 1.0]
        - volatility: float (coefficient of variation)
        - volatility_classification: str ("low", "medium", "high")
        - persistence: int (days)
        - trend: str ("improving", "worsening", "stable")
        - signal_strength: float
    """
    # Calculate stability if we have historical values
    stability_score = None
    if factor_values_series is not None and len(factor_values_series) > 1:
        clean_values = factor_values_series.dropna()
        clean_values = clean_values[clean_values.apply(lambda x: math.isfinite(x))]
        if len(clean_values) > 1:
            mean_val = clean_values.mean()
            if abs(mean_val) > 1e-10:
                std_val = clean_values.std()
                cv = std_val / abs(mean_val)
                # Stability = 1 - normalized CV (clipped)
                stability_score = max(0.0, min(1.0, 1.0 - min(cv, 1.0)))

    # Calculate confidence
    confidence = calculate_factor_confidence(
        current_value,
        has_data,
        data_freshness_days,
        stability_score,
    )

    # Calculate volatility
    if factor_values_series is not None:
        volatility_score, volatility_classification = calculate_factor_volatility(
            factor_values_series
        )
    else:
        volatility_score = 0.0
        volatility_classification = "low"

    # Calculate persistence
    if factor_contributions_series is not None:
        persistence = calculate_factor_persistence(factor_contributions_series)
    else:
        persistence = 0

    # Calculate trend
    if factor_values_series is not None:
        trend = calculate_factor_trend(factor_values_series)
    else:
        trend = "stable"

    # Calculate signal strength
    signal_strength = calculate_signal_strength(
        current_contribution,
        volatility_score,
        confidence,
    )

    return {
        "confidence": float(confidence),
        "volatility": float(volatility_score),
        "volatility_classification": volatility_classification,
        "persistence": int(persistence),
        "trend": trend,
        "signal_strength": float(signal_strength),
    }
