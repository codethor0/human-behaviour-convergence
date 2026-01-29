# SPDX-License-Identifier: PROPRIETARY
"""Univariate anomaly detection (Layer 1): static bounds and rolling z-score.

Formulas:
- Static bounds: percentile_low and percentile_high over rolling window.
- static_anomaly = 1 if value < lower_bound or value > upper_bound else 0.
- z_t = (x_t - mean_window) / std_window  (0 if std_window == 0).
- zscore_anomaly = 1 if |z_t| > zscore_k else 0.
"""
from collections import deque
from typing import Any, Dict

import structlog

logger = structlog.get_logger("anomaly.univariate")

# Default window size (number of observations per region)
DEFAULT_WINDOW_SIZE = 500
# Percentiles for static bounds (5th and 95th)
DEFAULT_PERCENTILE_LOW = 5.0
DEFAULT_PERCENTILE_HIGH = 95.0
# Z-score threshold (e.g. 2.5 => flag if |z| > 2.5)
DEFAULT_ZSCORE_K = 2.5


class UnivariateAnomalyTracker:
    """Tracks per-region rolling window and computes static + z-score anomaly metrics."""

    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        percentile_low: float = DEFAULT_PERCENTILE_LOW,
        percentile_high: float = DEFAULT_PERCENTILE_HIGH,
        zscore_k: float = DEFAULT_ZSCORE_K,
    ):
        self.window_size = window_size
        self.percentile_low = percentile_low
        self.percentile_high = percentile_high
        self.zscore_k = zscore_k
        self._windows: Dict[str, deque] = {}

    def _get_window(self, region: str) -> deque:
        if region not in self._windows:
            self._windows[region] = deque(maxlen=self.window_size)
        return self._windows[region]

    def update(
        self,
        region: str,
        value: float,
    ) -> Dict[str, Any]:
        """
        Append value for region and return anomaly metrics.

        Returns dict with:
          - static_upper_bound, static_lower_bound (float)
          - static_anomaly (0 or 1)
          - zscore (float)
          - zscore_anomaly (0 or 1)
        """
        try:
            value = float(value)
        except (TypeError, ValueError):
            return self._empty_result()

        win = self._get_window(region)
        win.append(value)
        n = len(win)
        if n < 2:
            return self._result(
                static_upper=value,
                static_lower=value,
                static_anomaly=0,
                zscore=0.0,
                zscore_anomaly=0,
            )

        arr = list(win)
        mean_w = sum(arr) / n
        variance = sum((x - mean_w) ** 2 for x in arr) / n
        std_w = variance**0.5 if variance > 0 else 0.0

        # Static bounds from percentiles
        sorted_arr = sorted(arr)
        idx_low = max(0, int((self.percentile_low / 100.0) * (n - 1)))
        idx_high = min(n - 1, int((self.percentile_high / 100.0) * (n - 1)))
        static_lower = sorted_arr[idx_low]
        static_upper = sorted_arr[idx_high]

        static_anomaly = 1 if value < static_lower or value > static_upper else 0

        # Z-score
        zscore = (value - mean_w) / std_w if std_w > 0 else 0.0
        zscore_anomaly = 1 if abs(zscore) > self.zscore_k else 0

        return self._result(
            static_upper=static_upper,
            static_lower=static_lower,
            static_anomaly=static_anomaly,
            zscore=zscore,
            zscore_anomaly=zscore_anomaly,
        )

    def _empty_result(self) -> Dict[str, Any]:
        return self._result(
            static_upper=0.0,
            static_lower=0.0,
            static_anomaly=0,
            zscore=0.0,
            zscore_anomaly=0,
        )

    def _result(
        self,
        static_upper: float,
        static_lower: float,
        static_anomaly: int,
        zscore: float,
        zscore_anomaly: int,
    ) -> Dict[str, Any]:
        return {
            "static_upper_bound": static_upper,
            "static_lower_bound": static_lower,
            "static_anomaly": static_anomaly,
            "zscore": zscore,
            "zscore_anomaly": zscore_anomaly,
        }
