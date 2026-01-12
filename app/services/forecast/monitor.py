# SPDX-License-Identifier: PROPRIETARY
"""Model Drift & Forecast Confidence Monitoring.

Tracks forecast accuracy, model drift, and confidence scores.
"""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger("forecast.monitor")


class ForecastMonitor:
    """Monitors forecast quality and model drift."""

    def __init__(self, drift_threshold: float = 0.15):
        """
        Initialize forecast monitor.

        Args:
            drift_threshold: Threshold for drift detection (default: 0.15)
        """
        self.drift_threshold = drift_threshold
        self._confidence_traces: Dict[str, Dict] = {}  # Store traces by index name

    def calculate_confidence(
        self,
        history_df: pd.DataFrame,
        forecast_df: Optional[pd.DataFrame] = None,
        index_columns: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Calculate confidence scores for each index.

        Args:
            history_df: Historical data
            forecast_df: Forecast data (optional, for residual tracking)
            index_columns: List of index columns to monitor

        Returns:
            Dictionary mapping index names to confidence scores (0-1)
        """
        if history_df.empty or len(history_df) == 0:
            return {}

        if index_columns is None:
            index_columns = [
                "economic_stress",
                "environmental_stress",
                "mobility_activity",
                "digital_attention",
                "public_health_stress",
                "political_stress",
                "crime_stress",
                "misinformation_stress",
                "social_cohesion_stress",
            ]

        confidence_scores = {}

        for index_col in index_columns:
            if index_col not in history_df.columns:
                continue

            try:
                series = pd.to_numeric(history_df[index_col], errors="coerce").dropna()
                if len(series) < 7:
                    confidence_scores[index_col] = 0.5  # Default for insufficient data
                    continue
            except Exception as e:
                logger.warning(
                    f"Failed to process index {index_col} for confidence", error=str(e)
                )
                confidence_scores[index_col] = 0.5
                continue

            # Calculate confidence based on:
            # 1. Data completeness
            # 2. Volatility (lower volatility = higher confidence)
            # 3. Trend stability
            # 4. Forecast accuracy (if available)

            completeness = self._calculate_completeness(series)
            stability = self._calculate_stability(series)
            forecast_accuracy = (
                self._calculate_forecast_accuracy(series, forecast_df, index_col)
                if forecast_df is not None
                else 0.5
            )

            # Weighted combination
            confidence = (
                (completeness * 0.3) + (stability * 0.4) + (forecast_accuracy * 0.3)
            )

            confidence_scores[index_col] = float(np.clip(confidence, 0.0, 1.0))

            # Create trace for explainability
            try:
                from app.core.trace import create_confidence_trace

                self._confidence_traces[index_col] = create_confidence_trace(
                    index=index_col,
                    confidence=confidence_scores[index_col],
                    completeness=completeness,
                    stability=stability,
                    forecast_accuracy=forecast_accuracy,
                    data_points=len(series),
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create confidence trace for {index_col}", error=str(e)
                )
                # Create minimal trace on error
                self._confidence_traces[index_col] = {
                    "reconciliation": {"valid": False, "error": str(e)}
                }

        logger.info(
            "Confidence scores calculated",
            indices=len(confidence_scores),
            avg_confidence=(
                np.mean(list(confidence_scores.values())) if confidence_scores else 0.0
            ),
        )

        return confidence_scores

    def detect_drift(
        self,
        history_df: pd.DataFrame,
        index_columns: Optional[List[str]] = None,
        window_size: int = 14,
    ) -> Dict[str, float]:
        """
        Detect model drift for each index.

        Args:
            history_df: Historical data
            index_columns: List of index columns to monitor
            window_size: Window size for drift detection

        Returns:
            Dictionary mapping index names to drift scores (0-1)
        """
        if history_df.empty:
            return {}

        if index_columns is None:
            index_columns = [
                "economic_stress",
                "environmental_stress",
                "mobility_activity",
                "digital_attention",
                "public_health_stress",
                "political_stress",
                "crime_stress",
                "misinformation_stress",
                "social_cohesion_stress",
            ]

        drift_scores = {}

        for index_col in index_columns:
            if index_col not in history_df.columns:
                continue

            series = history_df[index_col].dropna()
            if len(series) < window_size * 2:
                drift_scores[index_col] = 0.0  # No drift if insufficient data
                continue

            # Compare recent window to historical baseline
            recent = series.tail(window_size)
            baseline = series.head(window_size)

            # Calculate drift as difference in distribution
            recent_mean = recent.mean()
            baseline_mean = baseline.mean()
            recent_std = recent.std()
            baseline_std = baseline.std()

            # Drift score based on mean shift and variance change
            mean_shift = abs(recent_mean - baseline_mean)
            std_change = abs(recent_std - baseline_std) if baseline_std > 0 else 0.0

            # Normalize and combine
            drift = (mean_shift * 0.7) + (std_change * 0.3)

            drift_scores[index_col] = float(np.clip(drift, 0.0, 1.0))

        logger.info(
            "Drift detection completed",
            indices=len(drift_scores),
            avg_drift=np.mean(list(drift_scores.values())) if drift_scores else 0.0,
        )

        return drift_scores

    def _calculate_completeness(self, series: pd.Series) -> float:
        """Calculate data completeness score."""
        total = len(series)
        non_null = series.notna().sum()
        return float(non_null / total) if total > 0 else 0.0

    def _calculate_stability(self, series: pd.Series) -> float:
        """Calculate stability score (inverse of volatility)."""
        if len(series) < 2:
            return 0.5

        # Calculate coefficient of variation
        mean = series.mean()
        std = series.std()

        if mean == 0 or pd.isna(mean) or pd.isna(std):
            return 0.5

        cv = std / mean

        # Convert to stability score (lower CV = higher stability)
        stability = 1.0 / (1.0 + cv)

        return float(np.clip(stability, 0.0, 1.0))

    def _calculate_forecast_accuracy(
        self,
        history_series: pd.Series,
        forecast_df: pd.DataFrame,
        index_col: str,
    ) -> float:
        """Calculate forecast accuracy (if actuals available)."""
        # This is a placeholder - in production, you'd compare forecast to actuals
        # For now, return a default score
        return 0.7

    def get_confidence_trace(self, index_name: str) -> Optional[Dict]:
        """
        Get confidence trace for a specific index.

        Args:
            index_name: Name of the index (e.g., "economic_stress")

        Returns:
            Trace dictionary or None if not found
        """
        return self._confidence_traces.get(index_name)
