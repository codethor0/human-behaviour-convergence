# SPDX-License-Identifier: PROPRIETARY
"""Tests for logical consistency and cross-component invariants."""

import numpy as np
import pandas as pd

from app.services.convergence.engine import ConvergenceEngine
from app.services.forecast.monitor import ForecastMonitor
from app.services.risk.classifier import RiskClassifier
from app.services.shocks.detector import ShockDetector


class TestRiskTierMonotonicity:
    """Test that risk tiers are monotonic with respect to risk score."""

    def test_risk_tier_monotonic(self):
        """Higher risk score must map to higher tier."""
        classifier = RiskClassifier()

        scores = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        tiers = []

        for score in scores:
            result = classifier.classify_risk(behavior_index=score)
            tiers.append(result["tier"])

        # Tiers must be non-decreasing
        tier_order = {"stable": 0, "watchlist": 1, "elevated": 2, "high": 3, "critical": 4}
        tier_values = [tier_order[t] for t in tiers]

        for i in range(len(tier_values) - 1):
            assert tier_values[i] <= tier_values[i + 1], (
                f"Risk tier regression: score {scores[i]} -> {tiers[i]}, "
                f"score {scores[i+1]} -> {tiers[i+1]}"
            )

    def test_risk_tier_boundaries(self):
        """Risk tiers must respect threshold boundaries."""
        classifier = RiskClassifier()

        # Test that tiers respect thresholds when risk_score matches thresholds
        # Use neutral adjustments (convergence_score=50.0, trend="stable") so risk_score ≈ behavior_index
        test_cases = [
            (0.0, "stable"),
            (0.35, "watchlist"),  # Above 0.3 threshold
            (0.60, "elevated"),  # Above 0.5 threshold
            (0.75, "high"),  # Above 0.7 threshold
            (0.90, "critical"),  # Above 0.85 threshold
        ]

        for score, expected_tier in test_cases:
            result = classifier.classify_risk(
                behavior_index=score,
                convergence_score=50.0,  # Neutral (adjustment = 0.0)
                trend_direction="stable",  # No adjustment
            )
            # Verify tier matches expectation
            # With neutral adjustments, risk_score should equal behavior_index
            assert abs(result["risk_score"] - score) < 0.01, (
                f"Risk score should equal behavior_index with neutral adjustments: "
                f"expected={score}, actual={result['risk_score']:.3f}"
            )
            assert result["tier"] == expected_tier, (
                f"Tier threshold violation: behavior_index={score}, "
                f"risk_score={result['risk_score']:.3f} should map to {expected_tier}, "
                f"got {result['tier']}"
            )


class TestConfidenceVolatilityConsistency:
    """Test that confidence decreases as volatility increases."""

    def test_confidence_decreases_with_volatility(self):
        """Higher volatility must produce lower confidence."""
        monitor = ForecastMonitor()

        # Create series with different volatilities
        low_volatility = pd.Series([0.5] * 20 + [0.51] * 20)  # Very stable
        high_volatility = pd.Series(
            np.random.uniform(0.0, 1.0, 40)
        )  # High variance

        low_conf = monitor._calculate_stability(low_volatility)
        high_conf = monitor._calculate_stability(high_volatility)

        # Low volatility should have higher stability (confidence component)
        assert low_conf > high_conf, (
            f"Volatility inconsistency: low_vol stability={low_conf}, "
            f"high_vol stability={high_conf}"
        )

    def test_confidence_decreases_with_missing_data(self):
        """Lower completeness must produce lower confidence."""
        monitor = ForecastMonitor()

        # Create series with different completeness
        complete = pd.Series([0.5] * 20)
        incomplete = pd.Series([0.5] * 10 + [np.nan] * 10)

        df_complete = pd.DataFrame(
            {"timestamp": pd.date_range("2024-01-01", periods=20), "economic_stress": complete}
        )
        df_incomplete = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=20),
                "economic_stress": incomplete,
            }
        )

        conf_complete = monitor.calculate_confidence(df_complete).get("economic_stress", 0.0)
        conf_incomplete = monitor.calculate_confidence(df_incomplete).get(
            "economic_stress", 0.0
        )

        # Complete data should have higher confidence
        assert conf_complete >= conf_incomplete, (
            f"Completeness inconsistency: complete={conf_complete}, "
            f"incomplete={conf_incomplete}"
        )


class TestShockTrendConsistency:
    """Test that shock detection is consistent with trend direction."""

    def test_severe_shock_with_trend(self):
        """Severe shocks should correspond to trend changes."""
        detector = ShockDetector()
        classifier = RiskClassifier()

        # Create data with severe shock
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        values = [0.5] * 20 + [0.9] * 10  # Sudden jump (severe shock)

        shocks = detector.detect_shocks(
            pd.DataFrame({"timestamp": dates, "economic_stress": values})
        )

        # Find severe shocks
        severe_shocks = [s for s in shocks if s.get("severity") in ["high", "severe"]]

        if severe_shocks:
            # Classify risk with trend direction
            # Trend should be "increasing" if shock is positive
            result = classifier.classify_risk(
                behavior_index=0.7,
                shock_events=shocks,
                trend_direction="increasing",  # Should match positive shock
            )

            # Risk should be elevated due to shocks
            assert result["risk_score"] > 0.7, (
                f"Shock-trend inconsistency: severe shocks but risk_score={result['risk_score']}"
            )


class TestConvergenceConsistency:
    """Test that convergence score is consistent with component alignment."""

    def test_high_convergence_implies_alignment(self):
        """High convergence score must imply indices are moving together."""
        engine = ConvergenceEngine()

        # Create aligned indices (high correlation)
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        base_trend = np.linspace(0.3, 0.7, 30)
        noise = np.random.normal(0, 0.05, 30)

        df_aligned = pd.DataFrame(
            {
                "timestamp": dates,
                "economic_stress": base_trend + noise,
                "environmental_stress": base_trend + noise * 0.8,  # Highly correlated
                "public_health_stress": base_trend + noise * 0.9,
            }
        )

        result = engine.analyze_convergence(df_aligned)

        # High convergence should produce high score
        assert result["score"] > 50.0, (
            f"Convergence inconsistency: aligned indices but score={result['score']}"
        )

        # Should have reinforcing signals
        assert len(result["reinforcing_signals"]) > 0, (
            "Convergence inconsistency: aligned indices but no reinforcing signals"
        )

    def test_low_convergence_implies_divergence(self):
        """Low convergence score must imply indices are uncorrelated (not moving together)."""
        engine = ConvergenceEngine()

        # Create uncorrelated indices (random, independent)
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        np.random.seed(42)  # For reproducibility
        trend1 = np.random.uniform(0.0, 1.0, 30)
        trend2 = np.random.uniform(0.0, 1.0, 30)  # Independent random

        df_uncorrelated = pd.DataFrame(
            {
                "timestamp": dates,
                "economic_stress": trend1,
                "environmental_stress": trend2,  # Uncorrelated
            }
        )

        result = engine.analyze_convergence(df_uncorrelated)

        # Uncorrelated indices should produce lower score than perfectly correlated
        # Note: Convergence uses absolute correlation, so perfect negative correlation (-1.0)
        # still produces high score (indices moving together, just opposite directions)
        # But uncorrelated (near 0) should produce lower score
        assert result["score"] < 80.0, (
            f"Convergence inconsistency: uncorrelated indices but score={result['score']}"
        )


class TestRiskScoreConsistency:
    """Test that risk score is consistent with its components."""

    def test_risk_score_components(self):
        """Final risk score must equal base + adjustments (clipped)."""
        classifier = RiskClassifier()

        result = classifier.classify_risk(
            behavior_index=0.6,
            shock_events=[{"severity": "moderate", "delta": 0.1}],
            convergence_score=70.0,
            trend_direction="increasing",
        )

        # Verify components sum correctly
        expected = (
            result["base_risk"]
            + result["shock_adjustment"]
            + result["convergence_adjustment"]
            + result["trend_adjustment"]
        )
        expected_clipped = max(0.0, min(1.0, expected))

        assert abs(result["risk_score"] - expected_clipped) < 0.01, (
            f"Risk score inconsistency: expected={expected_clipped}, "
            f"actual={result['risk_score']}"
        )

    def test_risk_score_bounds(self):
        """Risk score must be in [0.0, 1.0] regardless of adjustments."""
        classifier = RiskClassifier()

        # Test with extreme adjustments
        result1 = classifier.classify_risk(
            behavior_index=0.0,
            shock_events=[{"severity": "severe", "delta": 0.5}] * 5,  # Large positive
            convergence_score=100.0,
            trend_direction="increasing",
        )

        result2 = classifier.classify_risk(
            behavior_index=1.0,
            convergence_score=0.0,
            trend_direction="decreasing",
        )

        assert 0.0 <= result1["risk_score"] <= 1.0
        assert 0.0 <= result2["risk_score"] <= 1.0


class TestConvergenceAdjustmentConsistency:
    """Test that convergence adjustment is consistent with convergence score."""

    def test_high_convergence_increases_risk(self):
        """High convergence score (>50) should increase risk."""
        classifier = RiskClassifier()

        result_low = classifier.classify_risk(
            behavior_index=0.5, convergence_score=30.0
        )
        result_high = classifier.classify_risk(
            behavior_index=0.5, convergence_score=80.0
        )

        # High convergence should produce higher risk
        assert result_high["risk_score"] >= result_low["risk_score"], (
            f"Convergence adjustment inconsistency: high convergence "
            f"({result_high['risk_score']}) < low convergence ({result_low['risk_score']})"
        )

    def test_convergence_adjustment_range(self):
        """Convergence adjustment must be in [-0.1, 0.2]."""
        classifier = RiskClassifier()

        for score in [0.0, 25.0, 50.0, 75.0, 100.0]:
            result = classifier.classify_risk(behavior_index=0.5, convergence_score=score)
            adjustment = result["convergence_adjustment"]

            assert -0.1 <= adjustment <= 0.2, (
                f"Convergence adjustment out of range: {adjustment} for score {score}"
            )


class TestTrendAdjustmentConsistency:
    """Test that trend adjustment matches trend direction."""

    def test_increasing_trend_increases_risk(self):
        """Increasing trend must increase risk."""
        classifier = RiskClassifier()

        result_stable = classifier.classify_risk(
            behavior_index=0.5, trend_direction="stable"
        )
        result_increasing = classifier.classify_risk(
            behavior_index=0.5, trend_direction="increasing"
        )

        assert result_increasing["risk_score"] > result_stable["risk_score"], (
            f"Trend adjustment inconsistency: increasing trend "
            f"({result_increasing['risk_score']}) <= stable ({result_stable['risk_score']})"
        )

    def test_decreasing_trend_decreases_risk(self):
        """Decreasing trend must decrease risk."""
        classifier = RiskClassifier()

        result_stable = classifier.classify_risk(
            behavior_index=0.5, trend_direction="stable"
        )
        result_decreasing = classifier.classify_risk(
            behavior_index=0.5, trend_direction="decreasing"
        )

        assert result_decreasing["risk_score"] < result_stable["risk_score"], (
            f"Trend adjustment inconsistency: decreasing trend "
            f"({result_decreasing['risk_score']}) >= stable ({result_stable['risk_score']})"
        )


class TestShockSeverityConsistency:
    """Test that shock severity matches delta magnitude."""

    def test_severe_shock_has_large_delta(self):
        """Severe shocks must have larger deltas than mild shocks."""
        detector = ShockDetector()

        # Create data with different shock magnitudes
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        mild_shock = [0.5] * 20 + [0.55] * 10  # Small delta
        severe_shock = [0.5] * 20 + [0.85] * 10  # Large delta

        shocks_mild = detector.detect_shocks(
            pd.DataFrame({"timestamp": dates, "economic_stress": mild_shock})
        )
        shocks_severe = detector.detect_shocks(
            pd.DataFrame({"timestamp": dates, "economic_stress": severe_shock})
        )

        # Severe shock should have higher severity
        if shocks_severe:
            severe_severities = [s.get("severity") for s in shocks_severe]
            if "severe" in severe_severities or "high" in severe_severities:
                # Verify mild shock doesn't have severe severity
                if shocks_mild:
                    mild_severities = [s.get("severity") for s in shocks_mild]
                    assert "severe" not in mild_severities, (
                        "Shock severity inconsistency: mild shock classified as severe"
                    )
