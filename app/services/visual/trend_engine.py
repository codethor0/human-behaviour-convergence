# SPDX-License-Identifier: PROPRIETARY
"""Trendline & Slope Engine for trend analysis."""
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger("visual.trend")


class TrendEngine:
    """Generates trendline and slope data for indices."""

    def __init__(self, short_window: int = 7, long_window: int = 30):
        """
        Initialize trend engine.

        Args:
            short_window: Window size for short-term trends (default: 7 days)
            long_window: Window size for long-term trends (default: 30 days)
        """
        self.short_window = short_window
        self.long_window = long_window

    def calculate_trends(
        self,
        history_df: pd.DataFrame,
        indices: Optional[List[str]] = None,
    ) -> Dict:
        """
        Calculate trends for all indices.

        Args:
            history_df: DataFrame with timestamp and index columns
            indices: List of index names to analyze

        Returns:
            Dictionary with trend data for each index
        """
        if history_df.empty:
            return {}

        if indices is None:
            indices = [
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

        trends = {}

        for index_name in indices:
            if index_name not in history_df.columns:
                continue

            series = history_df[index_name].dropna()
            if len(series) < 2:
                continue

            # Calculate 7-day slope
            slope_7d = self._calculate_slope(series, self.short_window)

            # Calculate 30-day moving average
            ma_30d = (
                series.rolling(window=min(self.long_window, len(series)))
                .mean()
                .iloc[-1]
                if len(series) >= 7
                else series.mean()
            )

            # Determine trend direction
            direction = self._determine_direction(slope_7d)

            # Detect breakouts
            breakout = self._detect_breakout(series)

            trends[index_name] = {
                "slope_7d": float(slope_7d),
                "slope_30d": (
                    float(
                        self._calculate_slope(
                            series, min(self.long_window, len(series))
                        )
                    )
                    if len(series) >= 7
                    else 0.0
                ),
                "moving_average_30d": float(ma_30d),
                "current_value": float(series.iloc[-1]),
                "direction": direction,
                "breakout_detected": breakout is not None,
                "breakout_date": breakout,
            }

        logger.info("Trends calculated", indices=len(trends))

        return trends

    def _calculate_slope(self, series: pd.Series, window: int) -> float:
        """Calculate slope over a window."""
        if len(series) < window:
            window = len(series)

        if window < 2:
            return 0.0

        recent = series.tail(window)
        if len(recent) < 2:
            return 0.0

        # Linear regression slope
        x = np.arange(len(recent))
        y = recent.values

        # Calculate slope using least squares
        slope = np.polyfit(x, y, 1)[0]

        return float(slope)

    def _determine_direction(self, slope: float, threshold: float = 0.001) -> str:
        """Determine trend direction from slope."""
        if slope > threshold:
            return "increasing"
        elif slope < -threshold:
            return "decreasing"
        else:
            return "stable"

    def _detect_breakout(
        self, series: pd.Series, threshold: float = 0.15
    ) -> Optional[str]:
        """Detect significant breakouts in the series."""
        if len(series) < 2:
            return None

        # Calculate day-over-day changes
        changes = series.diff().abs()

        # Find significant changes
        significant = changes[changes > threshold]

        if len(significant) > 0:
            # Return the most recent significant change date
            latest_breakout_idx = significant.index[-1]
            if hasattr(latest_breakout_idx, "isoformat"):
                return latest_breakout_idx.isoformat()
            elif isinstance(series.index, pd.DatetimeIndex):
                return str(latest_breakout_idx)
            else:
                return datetime.now().isoformat()

        return None
