# SPDX-License-Identifier: PROPRIETARY
"""Layer 2 anomaly detection: seasonal bands and residual-based outliers.

Uses rolling EWMA as baseline (trend proxy). Bands = baseline +/- k_band * rolling_std.
Residual = value - baseline. Residual z-score = residual / std(residuals); anomaly if |z| > k_residual.
"""
from collections import deque
from typing import Any, Dict

import structlog

logger = structlog.get_logger("anomaly.seasonal")

DEFAULT_WINDOW_SIZE = 500
DEFAULT_EWMA_ALPHA = 0.1  # Smoothing for baseline
DEFAULT_BAND_K = 2.0  # Number of std devs for upper/lower band
DEFAULT_RESIDUAL_K = 2.5  # Z-score threshold for residual anomaly


class SeasonalResidualTracker:
    """Tracks per-region baseline (EWMA), bands, and residual z-score."""

    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        ewma_alpha: float = DEFAULT_EWMA_ALPHA,
        band_k: float = DEFAULT_BAND_K,
        residual_k: float = DEFAULT_RESIDUAL_K,
    ):
        self.window_size = window_size
        self.ewma_alpha = ewma_alpha
        self.band_k = band_k
        self.residual_k = residual_k
        self._values: Dict[str, deque] = {}
        self._baseline: Dict[str, float] = {}
        self._residuals: Dict[str, deque] = {}

    def _get_value_window(self, region: str) -> deque:
        if region not in self._values:
            self._values[region] = deque(maxlen=self.window_size)
        return self._values[region]

    def _get_residual_window(self, region: str) -> deque:
        if region not in self._residuals:
            self._residuals[region] = deque(maxlen=self.window_size)
        return self._residuals[region]

    def update(self, region: str, value: float) -> Dict[str, Any]:
        """
        Append value, update EWMA baseline and residual history.
        Returns: baseline, upper_band, lower_band, residual, residual_zscore,
                 seasonal_anomaly (1 if outside band), residual_anomaly (1 if |residual_z| > k).
        """
        try:
            value = float(value)
        except (TypeError, ValueError):
            return self._empty_result()

        val_win = self._get_value_window(region)
        res_win = self._get_residual_window(region)

        # Initialize baseline with first value
        if region not in self._baseline:
            self._baseline[region] = value
        prev_baseline = self._baseline[region]
        baseline = self.ewma_alpha * value + (1.0 - self.ewma_alpha) * prev_baseline
        self._baseline[region] = baseline

        residual = value - baseline
        val_win.append(value)
        res_win.append(residual)
        n = len(val_win)

        if n < 2:
            return self._result(
                baseline=baseline,
                upper_band=baseline,
                lower_band=baseline,
                residual=residual,
                residual_zscore=0.0,
                seasonal_anomaly=0,
                residual_anomaly=0,
            )

        # Rolling std of values (for band width)
        arr = list(val_win)
        mean_v = sum(arr) / n
        var_v = sum((x - mean_v) ** 2 for x in arr) / n
        std_v = var_v**0.5 if var_v > 0 else 0.0
        band_half = self.band_k * std_v
        upper_band = baseline + band_half
        lower_band = baseline - band_half
        seasonal_anomaly = 1 if value < lower_band or value > upper_band else 0

        # Residual z-score
        res_list = list(res_win)
        mean_r = sum(res_list) / len(res_list)
        var_r = sum((x - mean_r) ** 2 for x in res_list) / len(res_list)
        std_r = var_r**0.5 if var_r > 0 else 0.0
        residual_zscore = (residual - mean_r) / std_r if std_r > 0 else 0.0
        residual_anomaly = 1 if abs(residual_zscore) > self.residual_k else 0

        return self._result(
            baseline=baseline,
            upper_band=upper_band,
            lower_band=lower_band,
            residual=residual,
            residual_zscore=residual_zscore,
            seasonal_anomaly=seasonal_anomaly,
            residual_anomaly=residual_anomaly,
        )

    def _empty_result(self) -> Dict[str, Any]:
        return self._result(
            baseline=0.0,
            upper_band=0.0,
            lower_band=0.0,
            residual=0.0,
            residual_zscore=0.0,
            seasonal_anomaly=0,
            residual_anomaly=0,
        )

    def _result(
        self,
        baseline: float,
        upper_band: float,
        lower_band: float,
        residual: float,
        residual_zscore: float,
        seasonal_anomaly: int,
        residual_anomaly: int,
    ) -> Dict[str, Any]:
        return {
            "baseline": baseline,
            "upper_band": upper_band,
            "lower_band": lower_band,
            "residual": residual,
            "residual_zscore": residual_zscore,
            "seasonal_anomaly": seasonal_anomaly,
            "residual_anomaly": residual_anomaly,
        }
