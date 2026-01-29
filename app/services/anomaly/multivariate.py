# SPDX-License-Identifier: PROPRIETARY
"""Layer 3 anomaly detection: multivariate (Mahalanobis-style) and regime consistency.

Feature vector: [behavior_index, economic_stress, environmental_stress, ...].
Uses diagonal covariance: D^2 = sum_i ((x_i - mu_i) / sigma_i)^2.
Anomaly when D^2 > threshold (empirical percentile or fixed).
"""
from collections import deque
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger("anomaly.multivariate")

DEFAULT_WINDOW_SIZE = 500
DEFAULT_MD_THRESHOLD = (
    15.0  # Squared distance threshold (e.g. ~3.9 per dim for 10 dims)
)


class MultivariateTracker:
    """Tracks per-region feature vectors and computes Mahalanobis-style (diagonal) score."""

    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        md_threshold: float = DEFAULT_MD_THRESHOLD,
    ):
        self.window_size = window_size
        self.md_threshold = md_threshold
        self._history: Dict[str, deque] = {}
        self._ndim: int = 0

    def _get_window(self, region: str) -> deque:
        if region not in self._history:
            self._history[region] = deque(maxlen=self.window_size)
        return self._history[region]

    def update(self, region: str, feature_vector: List[float]) -> Dict[str, Any]:
        """
        Append feature vector and return multivariate anomaly metrics.

        feature_vector: list of floats (e.g. [behavior_index, economic_stress, ...]).
        Returns: md_score (squared distance), md_anomaly (0 or 1).
        """
        try:
            vec = [float(x) for x in feature_vector]
        except (TypeError, ValueError):
            return self._empty_result()

        if not vec:
            return self._empty_result()

        win = self._get_window(region)
        win.append(tuple(vec))
        n = len(win)
        ndim = len(vec)
        if n < ndim + 1:
            return self._result(md_score=0.0, md_anomaly=0)

        # Mean and std per dimension
        rows = list(win)
        mean_vec = []
        std_vec = []
        for j in range(ndim):
            col = [rows[i][j] for i in range(n)]
            mu = sum(col) / n
            var = sum((x - mu) ** 2 for x in col) / n
            sigma = var**0.5 if var > 0 else 1.0
            mean_vec.append(mu)
            std_vec.append(sigma)

        # Squared Mahalanobis (diagonal)
        d2 = 0.0
        for j in range(ndim):
            if std_vec[j] > 0:
                z = (vec[j] - mean_vec[j]) / std_vec[j]
                d2 += z * z

        md_anomaly = 1 if d2 > self.md_threshold else 0
        return self._result(md_score=d2, md_anomaly=md_anomaly)

    def _empty_result(self) -> Dict[str, Any]:
        return self._result(md_score=0.0, md_anomaly=0)

    def _result(self, md_score: float, md_anomaly: int) -> Dict[str, Any]:
        return {"md_score": md_score, "md_anomaly": md_anomaly}
