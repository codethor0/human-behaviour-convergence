# SPDX-License-Identifier: MIT
"""Unit tests for anomaly detection layers (univariate, seasonal, multivariate)."""

from app.services.anomaly.multivariate import MultivariateTracker
from app.services.anomaly.seasonal import SeasonalResidualTracker
from app.services.anomaly.univariate import UnivariateAnomalyTracker


class TestUnivariateAnomalyTracker:
    """Layer 1: static bounds and z-score."""

    def test_small_window_returns_bounds_and_zero_anomaly(self):
        tracker = UnivariateAnomalyTracker(
            window_size=10, percentile_low=5, percentile_high=95, zscore_k=2.5
        )
        for i in range(5):
            tracker.update("r1", 0.5 + i * 0.01)
        out = tracker.update("r1", 0.52)
        assert "static_upper_bound" in out and "static_lower_bound" in out
        assert out["static_anomaly"] in (0, 1)
        assert "zscore" in out and "zscore_anomaly" in out

    def test_outlier_above_bounds_flags_static_anomaly(self):
        tracker = UnivariateAnomalyTracker(
            window_size=20, percentile_low=10, percentile_high=90, zscore_k=3.0
        )
        for _ in range(20):
            tracker.update("r1", 0.4)
        out = tracker.update("r1", 0.99)
        assert out["static_anomaly"] == 1

    def test_zscore_anomaly_when_far_from_mean(self):
        tracker = UnivariateAnomalyTracker(window_size=30, zscore_k=2.0)
        for _ in range(30):
            tracker.update("r1", 0.5)
        out = tracker.update("r1", 0.5 + 3.0 * 0.1)
        assert "zscore_anomaly" in out
        assert out["zscore_anomaly"] in (0, 1)


class TestSeasonalResidualTracker:
    """Layer 2: EWMA baseline, bands, residual z-score."""

    def test_returns_baseline_and_bands(self):
        tracker = SeasonalResidualTracker(
            window_size=15, ewma_alpha=0.2, band_k=2.0, residual_k=2.5
        )
        for i in range(10):
            tracker.update("r1", 0.5)
        out = tracker.update("r1", 0.52)
        assert "baseline" in out and "upper_band" in out and "lower_band" in out
        assert "residual" in out and "residual_zscore" in out
        assert out["seasonal_anomaly"] in (0, 1) and out["residual_anomaly"] in (0, 1)

    def test_seasonal_anomaly_when_outside_band(self):
        tracker = SeasonalResidualTracker(window_size=20, band_k=1.0, residual_k=3.0)
        for _ in range(20):
            tracker.update("r1", 0.5)
        out = tracker.update("r1", 0.5 + 2.0)
        assert out["seasonal_anomaly"] == 1


class TestMultivariateTracker:
    """Layer 3: Mahalanobis-style (diagonal) score."""

    def test_insufficient_points_returns_zero_anomaly(self):
        tracker = MultivariateTracker(window_size=20, md_threshold=15.0)
        vec = [0.5, 0.4, 0.6]
        for _ in range(3):
            tracker.update("r1", vec)
        out = tracker.update("r1", vec)
        assert out["md_anomaly"] == 0
        assert out["md_score"] == 0.0

    def test_returns_md_score_and_anomaly(self):
        tracker = MultivariateTracker(window_size=15, md_threshold=15.0)
        ndim = 5
        for _ in range(20):
            tracker.update("r1", [0.5] * ndim)
        out = tracker.update("r1", [0.5] * ndim)
        assert "md_score" in out and "md_anomaly" in out
        assert out["md_score"] >= 0
        assert out["md_anomaly"] in (0, 1)

    def test_outlier_vector_flags_anomaly(self):
        tracker = MultivariateTracker(window_size=30, md_threshold=5.0)
        ndim = 4
        for _ in range(35):
            tracker.update("r1", [0.5] * ndim)
        outlier = [0.5 + 5.0] * ndim
        out = tracker.update("r1", outlier)
        assert out["md_score"] > 5.0
        assert out["md_anomaly"] == 1
