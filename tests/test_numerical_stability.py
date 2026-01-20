# SPDX-License-Identifier: PROPRIETARY
"""Tests for numerical stability, invariants, and semantic correctness."""
import math

import numpy as np
import pandas as pd

from app.core.behavior_index import BehaviorIndexComputer
from app.services.convergence.engine import ConvergenceEngine
from app.services.forecast.monitor import ForecastMonitor
from app.services.risk.classifier import RiskClassifier
from app.services.shocks.detector import ShockDetector


class TestWeightNormalization:
    """Test that weights are always normalized correctly."""

    def test_weights_sum_to_one(self):
        """Weights must sum to 1.0 ± 0.01."""
        computer = BehaviorIndexComputer(
            economic_weight=0.3,
            environmental_weight=0.3,
            mobility_weight=0.2,
            digital_attention_weight=0.15,
            health_weight=0.15,
        )

        # Sum all weights (including optional ones that default to 0.0)
        total = (
            computer.economic_weight
            + computer.environmental_weight
            + computer.mobility_weight
            + computer.digital_attention_weight
            + computer.health_weight
            + computer.political_weight
            + computer.crime_weight
            + computer.misinformation_weight
            + computer.social_cohesion_weight
        )

        assert abs(total - 1.0) <= 0.01

    def test_weights_normalize_when_off(self):
        """Weights must normalize when sum != 1.0."""
        computer = BehaviorIndexComputer(
            economic_weight=0.5,
            environmental_weight=0.5,
            mobility_weight=0.5,  # Sum = 1.5 (without optional weights)
            digital_attention_weight=0.15,
            health_weight=0.15,
        )

        # Sum all weights
        total = (
            computer.economic_weight
            + computer.environmental_weight
            + computer.mobility_weight
            + computer.digital_attention_weight
            + computer.health_weight
            + computer.political_weight
            + computer.crime_weight
            + computer.misinformation_weight
            + computer.social_cohesion_weight
        )

        assert abs(total - 1.0) <= 0.01

    def test_zero_total_weight_fallback(self):
        """Zero total weight must handle gracefully without crashing."""
        computer = BehaviorIndexComputer(
            economic_weight=0.0,
            environmental_weight=0.0,
            mobility_weight=0.0,
            digital_attention_weight=0.0,
            health_weight=0.0,
        )

        # When all weights are 0, system should either:
        # 1. Use defaults (if total_weight <= 0 triggers fallback)
        # 2. Normalize to 0 (mathematically valid but not useful)
        # The critical invariant is: system must not crash and produce valid outputs

        # Verify system produces valid output even with zero weights
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [0.5] * 10,
                "discomfort_score": [0.5] * 10,
            }
        )

        result = computer.compute_behavior_index(df)

        # Must produce valid output (no NaN, in range)
        assert not result["behavior_index"].isna().any()
        assert (result["behavior_index"] >= 0.0).all()
        assert (result["behavior_index"] <= 1.0).all()


class TestRangeInvariants:
    """Test that all outputs are in valid ranges."""

    def test_behavior_index_in_range(self):
        """Behavior index must be in [0.0, 1.0]."""
        computer = BehaviorIndexComputer()

        # Create test data with extreme values
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [2.0, -1.0, 0.5, 1.5, 0.0] * 2,  # Out of range
                "discomfort_score": [0.5] * 10,
            }
        )

        result = computer.compute_behavior_index(df)

        # All indices must be in [0.0, 1.0]
        assert (result["behavior_index"] >= 0.0).all()
        assert (result["behavior_index"] <= 1.0).all()
        assert (result["economic_stress"] >= 0.0).all()
        assert (result["economic_stress"] <= 1.0).all()

    def test_confidence_scores_in_range(self):
        """Confidence scores must be in [0.0, 1.0]."""
        monitor = ForecastMonitor()

        # Create test data
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=20),
                "economic_stress": np.random.uniform(0.0, 1.0, 20),
            }
        )

        scores = monitor.calculate_confidence(df)

        for score in scores.values():
            assert 0.0 <= score <= 1.0

    def test_risk_scores_in_range(self):
        """Risk scores must be in [0.0, 1.0]."""
        classifier = RiskClassifier()

        # Test with extreme values
        result = classifier.classify_risk(
            behavior_index=2.0,  # Out of range
            convergence_score=150.0,  # Out of range
        )

        assert 0.0 <= result["risk_score"] <= 1.0
        assert 0.0 <= result["base_risk"] <= 1.0


class TestNaNInfHandling:
    """Test that NaN and Inf values are handled correctly."""

    def test_nan_in_inputs(self):
        """NaN inputs must not propagate."""
        computer = BehaviorIndexComputer()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [np.nan, 0.5, np.inf, -np.inf, 0.3] * 2,
                "discomfort_score": [0.5] * 10,
            }
        )

        result = computer.compute_behavior_index(df)

        # No NaN or Inf in output
        assert not result["behavior_index"].isna().any()
        assert result["behavior_index"].apply(math.isfinite).all()

    def test_nan_in_confidence_calculation(self):
        """NaN in confidence calculation must be handled."""
        monitor = ForecastMonitor()

        # Create data with NaN and Inf (ensure exactly 20 values)
        economic_values = ([np.nan, 0.5, np.inf] * 6) + [0.5, 0.5]  # 18 + 2 = 20
        assert len(economic_values) == 20

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=20),
                "economic_stress": economic_values,
            }
        )

        scores = monitor.calculate_confidence(df)

        # All scores must be finite
        for score in scores.values():
            assert math.isfinite(score)
            assert 0.0 <= score <= 1.0

    def test_nan_in_convergence(self):
        """NaN in convergence calculation must be handled."""
        engine = ConvergenceEngine()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=20),
                "economic_stress": [np.nan, 0.5] * 10,
                "environmental_stress": [0.5, np.nan] * 10,
            }
        )

        result = engine.analyze_convergence(df)

        # Score must be finite
        assert math.isfinite(result["score"])
        assert 0.0 <= result["score"] <= 100.0


class TestDivisionByZero:
    """Test that division by zero is prevented."""

    def test_zero_mean_in_stability(self):
        """Zero mean must not cause division by zero."""
        monitor = ForecastMonitor()

        # Series with zero mean
        series = pd.Series([0.0] * 20)

        stability = monitor._calculate_stability(series)

        # Must return valid value (0.5 default)
        assert math.isfinite(stability)
        assert 0.0 <= stability <= 1.0

    def test_zero_std_in_z_score(self):
        """Zero std must not cause division by zero."""
        detector = ShockDetector()

        # Series with zero std (all same value)
        series = pd.Series([0.5] * 20, index=pd.date_range("2024-01-01", periods=20))

        shocks = detector._detect_z_score_shocks(series, "test_index")

        # Must not crash
        assert isinstance(shocks, list)

    def test_zero_total_in_normalization(self):
        """Zero total must not cause division by zero."""
        computer = BehaviorIndexComputer()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [0.0] * 10,  # All zeros
                "discomfort_score": [0.0] * 10,
            }
        )

        result = computer.compute_behavior_index(df)

        # Must produce valid output
        assert not result["behavior_index"].isna().any()


class TestOrderIndependence:
    """Test that calculations are order-independent."""

    def test_behavior_index_order_independent(self):
        """Behavior index must be same regardless of input order."""
        computer = BehaviorIndexComputer()

        # Create data
        base_data = {
            "timestamp": pd.date_range("2024-01-01", periods=10),
            "stress_index": np.random.uniform(0.0, 1.0, 10),
            "discomfort_score": np.random.uniform(0.0, 1.0, 10),
        }

        df1 = pd.DataFrame(base_data)
        df2 = df1.copy()
        df2 = df2.sample(frac=1).sort_index()  # Shuffle and re-sort

        result1 = computer.compute_behavior_index(df1)
        result2 = computer.compute_behavior_index(df2)

        # Results should be identical (sorted by timestamp)
        pd.testing.assert_frame_equal(
            result1.sort_values("timestamp"),
            result2.sort_values("timestamp"),
            check_exact=False,
            rtol=1e-10,
        )

    def test_convergence_order_independent(self):
        """Convergence score must be same regardless of column order."""
        engine = ConvergenceEngine()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=20),
                "economic_stress": np.random.uniform(0.0, 1.0, 20),
                "environmental_stress": np.random.uniform(0.0, 1.0, 20),
            }
        )

        # Calculate with different column orders
        result1 = engine.analyze_convergence(
            df, index_columns=["economic_stress", "environmental_stress"]
        )
        result2 = engine.analyze_convergence(
            df, index_columns=["environmental_stress", "economic_stress"]
        )

        # Scores should be identical (correlation is symmetric)
        assert abs(result1["score"] - result2["score"]) < 1e-10


class TestMissingDataNeutrality:
    """Test that missing data uses neutral defaults."""

    def test_missing_data_defaults(self):
        """Missing data must use neutral defaults (0.5)."""
        computer = BehaviorIndexComputer()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                # Missing stress_index and discomfort_score
            }
        )

        result = computer.compute_behavior_index(df)

        # Should use defaults (0.5)
        assert (result["economic_stress"] == 0.5).all()
        assert (result["environmental_stress"] == 0.5).all()

    def test_adding_neutral_data_no_change(self):
        """Adding neutral data (0.5) must not change output."""
        computer = BehaviorIndexComputer()

        # Base data
        df_base = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [0.3] * 10,
                "discomfort_score": [0.7] * 10,
            }
        )

        # Add neutral data
        df_with_neutral = df_base.copy()
        df_with_neutral["mobility_index"] = [0.5] * 10  # Neutral

        result_base = computer.compute_behavior_index(df_base)
        result_with_neutral = computer.compute_behavior_index(df_with_neutral)

        # Economic and environmental stress should be unchanged
        pd.testing.assert_series_equal(
            result_base["economic_stress"],
            result_with_neutral["economic_stress"],
            check_exact=False,
            rtol=1e-10,
        )


class TestExtremeValues:
    """Test that extreme but valid values are handled correctly."""

    def test_extreme_values_clipped(self):
        """Extreme values must be clipped to valid range."""
        computer = BehaviorIndexComputer()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [1e10, -1e10, 0.5] * 3 + [0.5],  # Extreme values
                "discomfort_score": [0.5] * 10,
            }
        )

        result = computer.compute_behavior_index(df)

        # All values must be in [0.0, 1.0]
        assert (result["behavior_index"] >= 0.0).all()
        assert (result["behavior_index"] <= 1.0).all()

    def test_very_small_values(self):
        """Very small values must be handled correctly."""
        computer = BehaviorIndexComputer()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [1e-10, 0.0, 0.5] * 3 + [0.5],
                "discomfort_score": [0.5] * 10,
            }
        )

        result = computer.compute_behavior_index(df)

        # Must produce valid output
        assert not result["behavior_index"].isna().any()
        assert (result["behavior_index"] >= 0.0).all()


class TestCorrelationMatrixInvariants:
    """Test correlation matrix invariants."""

    def test_correlation_matrix_symmetric(self):
        """Correlation matrix must be symmetric."""
        engine = ConvergenceEngine()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=20),
                "economic_stress": np.random.uniform(0.0, 1.0, 20),
                "environmental_stress": np.random.uniform(0.0, 1.0, 20),
            }
        )

        corr_matrix = engine._calculate_correlation_matrix(
            df[["economic_stress", "environmental_stress"]]
        )

        # Must be symmetric
        pd.testing.assert_frame_equal(
            corr_matrix, corr_matrix.T, check_exact=False, rtol=1e-10
        )

    def test_correlation_matrix_diagonal_one(self):
        """Correlation matrix diagonal must be 1.0."""
        engine = ConvergenceEngine()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=20),
                "economic_stress": np.random.uniform(0.0, 1.0, 20),
            }
        )

        corr_matrix = engine._calculate_correlation_matrix(df[["economic_stress"]])

        # Diagonal must be 1.0
        assert abs(corr_matrix.iloc[0, 0] - 1.0) < 1e-10


class TestRiskTierMonotonicity:
    """Test that risk tiers are monotonic."""

    def test_risk_tier_monotonic(self):
        """Higher risk score must map to higher tier."""
        classifier = RiskClassifier()

        scores = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        tiers = []

        for score in scores:
            result = classifier.classify_risk(behavior_index=score)
            tiers.append(result["tier"])

        # Tiers must be non-decreasing
        tier_order = {
            "stable": 0,
            "watchlist": 1,
            "elevated": 2,
            "high": 3,
            "critical": 4,
        }
        tier_values = [tier_order[t] for t in tiers]

        for i in range(len(tier_values) - 1):
            assert tier_values[i] <= tier_values[i + 1]
