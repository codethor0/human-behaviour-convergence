# SPDX-License-Identifier: PROPRIETARY
"""Real-Time Event Shock Detection Layer (RSEDL).

Detects sudden spikes, outliers, and structural breaks in behavioral indices.
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger("shocks.detector")


class ShockDetector:
    """Detects and classifies shock events in behavioral indices."""

    def __init__(
        self,
        z_score_threshold: float = 2.5,
        delta_threshold: float = 0.15,
        window_size: int = 7,
    ):
        """
        Initialize shock detector.

        Args:
            z_score_threshold: Z-score threshold for outlier detection (default: 2.5)
            delta_threshold: Minimum delta for shock classification (default: 0.15)
            window_size: Rolling window size for baseline calculation (default: 7 days)
        """
        self.z_score_threshold = z_score_threshold
        self.delta_threshold = delta_threshold
        self.window_size = window_size

    def detect_shocks(
        self,
        history_df: pd.DataFrame,
        index_columns: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Detect shock events across all indices.

        Args:
            history_df: DataFrame with timestamp and index columns
            index_columns: List of index column names to monitor (default: all stress indices)

        Returns:
            List of shock event dictionaries
        """
        if history_df.empty or len(history_df) == 0:
            return []

        if index_columns is None:
            # Default to all stress indices
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

        shock_events = []

        for index_col in index_columns:
            if index_col not in history_df.columns:
                continue

            try:
                series = history_df[index_col].dropna()
                if len(series) < self.window_size + 1:
                    continue

                # Ensure series is numeric
                series = pd.to_numeric(series, errors="coerce").dropna()
                if len(series) < self.window_size + 1:
                    continue
            except Exception as e:
                logger.warning(f"Failed to process index {index_col}", error=str(e))
                continue

            # Detect shocks using multiple methods
            z_score_shocks = self._detect_z_score_shocks(series, index_col)
            delta_shocks = self._detect_delta_shocks(series, index_col)
            ewma_shocks = self._detect_ewma_shocks(series, index_col)

            # Combine and deduplicate shocks
            all_shocks = z_score_shocks + delta_shocks + ewma_shocks
            shock_events.extend(self._merge_shocks(all_shocks))

        # Sort by timestamp
        shock_events.sort(key=lambda x: x["timestamp"])

        logger.info(
            "Shock detection completed",
            total_shocks=len(shock_events),
            indices_monitored=len(index_columns),
        )

        return shock_events

    def _detect_z_score_shocks(self, series: pd.Series, index_name: str) -> List[Dict]:
        """Detect shocks using Z-score method."""
        shocks = []
        if len(series) < self.window_size:
            return shocks

        # Calculate rolling mean and std
        rolling_mean = series.rolling(window=self.window_size, min_periods=1).mean()
        rolling_std = series.rolling(window=self.window_size, min_periods=1).std()

        # Calculate Z-scores
        z_scores = (series - rolling_mean) / (
            rolling_std + 1e-8
        )  # Add small epsilon to avoid division by zero

        # Find outliers
        outlier_mask = np.abs(z_scores) > self.z_score_threshold

        for idx in series.index[outlier_mask]:
            z_score = z_scores.loc[idx]
            value = series.loc[idx]
            delta = value - rolling_mean.loc[idx]

            severity = self._classify_severity(abs(z_score), abs(delta))

            # Get timestamp from history DataFrame if available
            timestamp = self._get_timestamp_from_index(series, idx)

            shocks.append(
                {
                    "index": index_name,
                    "method": "z_score",
                    "severity": severity,
                    "delta": float(delta),
                    "z_score": float(z_score),
                    "value": float(value),
                    "timestamp": timestamp,
                }
            )

        return shocks

    def _detect_delta_shocks(self, series: pd.Series, index_name: str) -> List[Dict]:
        """Detect shocks using delta (change) method."""
        shocks = []
        if len(series) < 2:
            return shocks

        # Calculate day-over-day changes
        deltas = series.diff().abs()

        # Find significant deltas
        significant_deltas = deltas[deltas > self.delta_threshold]

        for idx in significant_deltas.index:
            delta = series.diff().loc[idx]
            value = series.loc[idx]
            prev_value = series.shift(1).loc[idx]

            severity = self._classify_severity(abs(delta), abs(delta))

            shocks.append(
                {
                    "index": index_name,
                    "method": "delta",
                    "severity": severity,
                    "delta": float(delta),
                    "value": float(value),
                    "previous_value": (
                        float(prev_value) if not pd.isna(prev_value) else None
                    ),
                    "timestamp": self._get_timestamp_from_index(series, idx),
                }
            )

        return shocks

    def _detect_ewma_shocks(
        self, series: pd.Series, index_name: str, alpha: float = 0.3
    ) -> List[Dict]:
        """Detect shocks using Exponential Weighted Moving Average (EWMA)."""
        shocks = []
        if len(series) < self.window_size:
            return shocks

        # Calculate EWMA
        ewma = series.ewm(alpha=alpha, adjust=False).mean()

        # Calculate deviation from EWMA
        deviation = (series - ewma).abs()
        threshold = (
            deviation.rolling(window=self.window_size).std() * self.z_score_threshold
        )

        # Find significant deviations
        shock_mask = deviation > threshold

        for idx in series.index[shock_mask]:
            delta = series.loc[idx] - ewma.loc[idx]
            value = series.loc[idx]

            severity = self._classify_severity(abs(delta), abs(delta))

            shocks.append(
                {
                    "index": index_name,
                    "method": "ewma",
                    "severity": severity,
                    "delta": float(delta),
                    "value": float(value),
                    "ewma_value": float(ewma.loc[idx]),
                    "timestamp": self._get_timestamp_from_index(series, idx),
                }
            )

        return shocks

    def _classify_severity(self, z_score_or_delta: float, delta: float) -> str:
        """Classify shock severity based on magnitude."""
        if z_score_or_delta >= 3.0 or delta >= 0.30:
            return "severe"
        elif z_score_or_delta >= 2.5 or delta >= 0.20:
            return "high"
        elif z_score_or_delta >= 2.0 or delta >= 0.15:
            return "moderate"
        else:
            return "mild"

    def _merge_shocks(self, shocks: List[Dict]) -> List[Dict]:
        """Merge duplicate shocks detected by multiple methods."""
        if not shocks:
            return []

        # Group by timestamp and index
        merged = {}
        for shock in shocks:
            key = (shock["timestamp"], shock["index"])
            if key not in merged:
                merged[key] = shock
            else:
                # Keep the shock with higher severity
                existing = merged[key]
                severity_order = {"mild": 1, "moderate": 2, "high": 3, "severe": 4}
                if severity_order.get(shock["severity"], 0) > severity_order.get(
                    existing["severity"], 0
                ):
                    merged[key] = shock

        return list(merged.values())

    def _get_timestamp_from_index(self, series: pd.Series, idx) -> str:
        """Extract timestamp from series index or use current time."""
        try:
            # Try to get timestamp from index
            if isinstance(series.index, pd.DatetimeIndex):
                ts = series.index[series.index.get_loc(idx)]
            elif hasattr(series.index, "get_level_values"):
                # MultiIndex case - check if timestamp level exists
                try:
                    timestamps = series.index.get_level_values("timestamp")
                    pos = series.index.get_loc(idx)
                    if pos < len(timestamps):
                        ts = timestamps[pos]
                    else:
                        ts = datetime.now()
                except (KeyError, AttributeError):
                    # Not a MultiIndex with timestamp level
                    ts = datetime.now()
            else:
                # Regular index - try to get from position
                try:
                    # If index is integer-based, use position
                    if isinstance(idx, (int, np.integer)):
                        ts = datetime.now() - timedelta(days=len(series) - int(idx))
                    else:
                        ts = datetime.now()
                except Exception:
                    ts = datetime.now()
        except Exception:
            # Fallback to current time
            ts = datetime.now()

        if isinstance(ts, str):
            return ts
        elif isinstance(ts, pd.Timestamp):
            return ts.isoformat()
        elif isinstance(ts, datetime):
            return ts.isoformat()
        else:
            return datetime.now().isoformat()

    def _get_timestamp(self, series: pd.Series, idx) -> str:
        """Extract timestamp from series index or use current time."""
        try:
            # Try to get timestamp from index
            if isinstance(series.index, pd.DatetimeIndex):
                ts = series.index[idx]
            elif hasattr(series.index, "get_level_values"):
                # MultiIndex case - check if timestamp level exists
                try:
                    timestamps = series.index.get_level_values("timestamp")
                    if idx < len(timestamps):
                        ts = timestamps[idx]
                    else:
                        ts = datetime.now()
                except (KeyError, AttributeError):
                    # Not a MultiIndex with timestamp level
                    ts = datetime.now()
            else:
                # Regular index - try to get from position
                try:
                    # If index is integer-based, use position
                    if isinstance(idx, (int, np.integer)):
                        ts = datetime.now() - timedelta(days=len(series) - idx)
                    else:
                        ts = datetime.now()
                except Exception:
                    ts = datetime.now()
        except Exception:
            # Fallback to current time
            ts = datetime.now()

        if isinstance(ts, str):
            return ts
        elif isinstance(ts, pd.Timestamp):
            return ts.isoformat()
        elif isinstance(ts, datetime):
            return ts.isoformat()
        else:
            return datetime.now().isoformat()
