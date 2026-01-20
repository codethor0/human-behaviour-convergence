# SPDX-License-Identifier: PROPRIETARY
"""Tests for explainability, attribution, and decision traceability."""
import math

import numpy as np
import pandas as pd

from app.core.trace import (
    create_behavior_index_trace,
    create_confidence_trace,
    create_convergence_trace,
    create_risk_trace,
    ensure_order_independence,
    sanitize_trace,
    validate_reconciliation,
)
from app.services.convergence.engine import ConvergenceEngine
from app.services.forecast.monitor import ForecastMonitor
from app.services.risk.classifier import RiskClassifier
from app.services.shocks.detector import ShockDetector


class TestContributionReconciliation:
    """Test that component contributions sum to outputs."""

    def test_risk_trace_reconciliation(self):
        """Risk trace contributions must sum to risk_score."""
        trace = create_risk_trace(
            tier="elevated",
            risk_score=0.6,
            base_risk=0.5,
            shock_adjustment=0.05,
            convergence_adjustment=0.03,
            trend_adjustment=0.02,
            shock_events=[],
            convergence_score=57.5,
            trend_direction="increasing",
        )

        reconciliation = trace["reconciliation"]
        assert reconciliation["valid"], (
            f"Risk trace reconciliation failed: sum={reconciliation['sum']}, "
            f"output={reconciliation['output']}, diff={reconciliation['difference']}"
        )

    def test_confidence_trace_reconciliation(self):
        """Confidence trace contributions must sum to confidence."""
        # Calculate expected unclipped confidence
        completeness = 0.9
        stability = 0.8
        forecast_accuracy = 0.6
        unclipped = (completeness * 0.3) + (stability * 0.4) + (forecast_accuracy * 0.3)
        # This equals 0.77, which gets clipped to 0.75

        trace = create_confidence_trace(
            index="economic_stress",
            confidence=0.75,  # Clipped
            completeness=completeness,
            stability=stability,
            forecast_accuracy=forecast_accuracy,
            data_points=30,
            unclipped_confidence=unclipped,  # Use unclipped for reconciliation
        )

        reconciliation = trace["reconciliation"]
        assert reconciliation["valid"], (
            f"Confidence trace reconciliation failed: sum={reconciliation['sum']}, "
            f"output={reconciliation['output']}, diff={reconciliation['difference']}"
        )

    def test_behavior_index_trace_reconciliation(self):
        """Behavior index trace contributions must sum to behavior_index."""
        contributions = {
            "economic_stress": {"value": 0.6, "weight": 0.25, "contribution": 0.15},
            "environmental_stress": {"value": 0.5, "weight": 0.25, "contribution": 0.125},
            "mobility_activity": {"value": 0.4, "weight": 0.2, "contribution": 0.12},  # Inverted
            "digital_attention": {"value": 0.3, "weight": 0.15, "contribution": 0.045},
            "public_health_stress": {"value": 0.5, "weight": 0.15, "contribution": 0.075},
        }
        weights = {k: contributions[k]["weight"] for k in contributions.keys()}

        # Calculate expected behavior_index
        expected = sum(c["contribution"] for c in contributions.values())

        trace = create_behavior_index_trace(
            behavior_index=expected,
            contributions=contributions,
            weights=weights,
        )

        reconciliation = trace["reconciliation"]
        assert reconciliation["valid"], (
            f"Behavior index trace reconciliation failed: sum={reconciliation['sum']}, "
            f"output={reconciliation['output']}, diff={reconciliation['difference']}"
        )

    def test_convergence_trace_reconciliation(self):
        """Convergence trace must reconcile score with correlations."""
        correlations = [0.7, 0.8, 0.6, 0.75]
        avg_correlation = sum(abs(c) for c in correlations) / len(correlations)
        expected_score = avg_correlation * 100.0

        trace = create_convergence_trace(
            score=expected_score,
            correlations=correlations,
            indices=["economic_stress", "environmental_stress"],
        )

        reconciliation = trace["reconciliation"]
        assert reconciliation["valid"], (
            f"Convergence trace reconciliation failed: calculated={reconciliation['calculated_score']}, "
            f"output={reconciliation['output']}, diff={reconciliation['difference']}"
        )


class TestOrderIndependence:
    """Test that explanations are order-independent."""

    def test_risk_trace_order_independence(self):
        """Risk trace must be identical regardless of shock event order."""
        shocks1 = [
            {"severity": "moderate", "delta": 0.1, "timestamp": "2024-01-01"},
            {"severity": "high", "delta": 0.2, "timestamp": "2024-01-02"},
        ]
        shocks2 = [
            {"severity": "high", "delta": 0.2, "timestamp": "2024-01-02"},
            {"severity": "moderate", "delta": 0.1, "timestamp": "2024-01-01"},
        ]

        trace1 = create_risk_trace(
            tier="elevated",
            risk_score=0.6,
            base_risk=0.5,
            shock_adjustment=0.1,
            convergence_adjustment=0.0,
            trend_adjustment=0.0,
            shock_events=shocks1,
            convergence_score=50.0,
            trend_direction="stable",
        )

        trace2 = create_risk_trace(
            tier="elevated",
            risk_score=0.6,
            base_risk=0.5,
            shock_adjustment=0.1,
            convergence_adjustment=0.0,
            trend_adjustment=0.0,
            shock_events=shocks2,
            convergence_score=50.0,
            trend_direction="stable",
        )

        # Components should be in deterministic order
        assert trace1["components"] == trace2["components"], (
            "Risk trace components should be order-independent"
        )

    def test_behavior_index_trace_order_independence(self):
        """Behavior index trace must be identical regardless of contribution order."""
        contributions1 = {
            "economic_stress": {"value": 0.6, "weight": 0.25, "contribution": 0.15},
            "environmental_stress": {"value": 0.5, "weight": 0.25, "contribution": 0.125},
        }
        contributions2 = {
            "environmental_stress": {"value": 0.5, "weight": 0.25, "contribution": 0.125},
            "economic_stress": {"value": 0.6, "weight": 0.25, "contribution": 0.15},
        }

        trace1 = create_behavior_index_trace(
            behavior_index=0.275,
            contributions=contributions1,
            weights={"economic_stress": 0.25, "environmental_stress": 0.25},
        )

        trace2 = create_behavior_index_trace(
            behavior_index=0.275,
            contributions=contributions2,
            weights={"environmental_stress": 0.25, "economic_stress": 0.25},
        )

        # Components should be in deterministic order (sorted by key)
        assert trace1["components"] == trace2["components"], (
            "Behavior index trace components should be order-independent"
        )

    def test_ensure_order_independence(self):
        """Test order independence utility function."""
        components1 = {"b": 1, "a": 2, "c": 3}
        components2 = {"c": 3, "a": 2, "b": 1}

        ordered1 = ensure_order_independence(components1)
        ordered2 = ensure_order_independence(components2)

        assert ordered1 == ordered2, "Components should be in deterministic order"
        assert list(ordered1.keys()) == ["a", "b", "c"], "Keys should be sorted"


class TestNoContradictions:
    """Test that explanations don't contradict logical invariants."""

    def test_risk_trace_no_contradiction(self):
        """Risk trace must not contradict risk tier monotonicity."""
        trace_low = create_risk_trace(
            tier="stable",
            risk_score=0.2,
            base_risk=0.2,
            shock_adjustment=0.0,
            convergence_adjustment=0.0,
            trend_adjustment=0.0,
            shock_events=[],
            convergence_score=50.0,
            trend_direction="stable",
        )

        trace_high = create_risk_trace(
            tier="critical",
            risk_score=0.9,
            base_risk=0.9,
            shock_adjustment=0.0,
            convergence_adjustment=0.0,
            trend_adjustment=0.0,
            shock_events=[],
            convergence_score=50.0,
            trend_direction="stable",
        )

        # Verify tier order matches risk score order
        tier_order = {"stable": 0, "watchlist": 1, "elevated": 2, "high": 3, "critical": 4}
        assert tier_order[trace_low["output"]["tier"]] < tier_order[trace_high["output"]["tier"]], (
            "Risk trace tier order must match risk score order"
        )
        assert trace_low["output"]["risk_score"] < trace_high["output"]["risk_score"], (
            "Risk trace risk scores must be ordered correctly"
        )

    def test_confidence_trace_no_contradiction(self):
        """Confidence trace must not contradict volatility relationship."""
        # Low volatility should produce high confidence
        trace_low_vol = create_confidence_trace(
            index="test",
            confidence=0.8,
            completeness=0.9,
            stability=0.9,  # High stability (low volatility)
            forecast_accuracy=0.7,
            data_points=30,
        )

        # High volatility should produce lower confidence
        trace_high_vol = create_confidence_trace(
            index="test",
            confidence=0.5,
            completeness=0.9,
            stability=0.2,  # Low stability (high volatility)
            forecast_accuracy=0.7,
            data_points=30,
        )

        assert trace_low_vol["output"]["confidence"] > trace_high_vol["output"]["confidence"], (
            "Confidence trace must respect volatility relationship"
        )


class TestNoLeaks:
    """Test that explanations don't leak internal state."""

    def test_sanitize_trace_removes_internal_fields(self):
        """Sanitize must remove internal fields."""
        trace = {
            "output": {"value": 0.5},
            "components": {"a": {"contribution": 0.3}},
            "_internal": "secret",
            "_debug": {"key": "value"},
            "public": "safe",
        }

        sanitized = sanitize_trace(trace)

        assert "_internal" not in sanitized
        assert "_debug" not in sanitized
        assert "public" in sanitized
        assert "output" in sanitized

    def test_sanitize_trace_clips_values(self):
        """Sanitize must clip values to valid ranges."""
        trace = {
            "output": {"confidence": 1.5, "score": -0.5},  # Out of range
            "components": {"a": {"contribution": float("inf")}},
        }

        sanitized = sanitize_trace(trace)

        assert 0.0 <= sanitized["output"]["confidence"] <= 1.0
        assert sanitized["output"]["score"] >= 0.0  # May be clipped
        assert math.isfinite(sanitized["components"]["a"]["contribution"])

    def test_sanitize_trace_handles_nan(self):
        """Sanitize must replace NaN/inf with defaults."""
        trace = {
            "output": {"value": float("nan")},
            "components": {"a": {"contribution": float("inf")}},
        }

        sanitized = sanitize_trace(trace)

        assert math.isfinite(sanitized["output"]["value"])
        assert math.isfinite(sanitized["components"]["a"]["contribution"])


class TestTraceCompleteness:
    """Test that all decisions have trace objects."""

    def test_risk_classification_has_trace(self):
        """Risk classification must return trace."""
        classifier = RiskClassifier()

        result = classifier.classify_risk(
            behavior_index=0.6,
            shock_events=[{"severity": "moderate", "delta": 0.1}],
            convergence_score=70.0,
            trend_direction="increasing",
        )

        assert "trace" in result, "Risk classification must include trace"
        assert "reconciliation" in result["trace"], "Trace must include reconciliation"
        assert result["trace"]["reconciliation"]["valid"], (
            "Risk trace reconciliation must be valid"
        )

    def test_confidence_calculation_has_trace(self):
        """Confidence calculation must create trace."""
        monitor = ForecastMonitor()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=30),
                "economic_stress": np.random.uniform(0.0, 1.0, 30),
            }
        )

        monitor.calculate_confidence(df)
        trace = monitor.get_confidence_trace("economic_stress")

        assert trace is not None, "Confidence calculation must create trace"
        assert "reconciliation" in trace, "Trace must include reconciliation"

    def test_convergence_analysis_has_trace(self):
        """Convergence analysis must return trace."""
        engine = ConvergenceEngine()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=30),
                "economic_stress": np.random.uniform(0.0, 1.0, 30),
                "environmental_stress": np.random.uniform(0.0, 1.0, 30),
            }
        )

        result = engine.analyze_convergence(df)

        assert "trace" in result, "Convergence analysis must include trace"
        assert "reconciliation" in result["trace"], "Trace must include reconciliation"

    def test_shock_detection_has_trace(self):
        """Shock detection must create trace."""
        detector = ShockDetector()

        dates = pd.date_range("2024-01-01", periods=30)
        values = [0.5] * 20 + [0.9] * 10  # Shock at end
        df = pd.DataFrame({"timestamp": dates, "economic_stress": values})

        detector.detect_shocks(df)
        trace = detector.get_shock_trace("economic_stress")

        assert trace is not None, "Shock detection must create trace"
        assert "reconciliation" in trace, "Trace must include reconciliation"


class TestReconciliationValidation:
    """Test reconciliation validation utility."""

    def test_validate_reconciliation_valid(self):
        """Reconciliation validation must pass for valid sums."""
        components = {
            "a": {"contribution": 0.3},
            "b": {"contribution": 0.2},
        }
        output = 0.5

        result = validate_reconciliation(components, output)

        assert result["valid"]
        assert abs(result["difference"]) <= 0.01

    def test_validate_reconciliation_invalid(self):
        """Reconciliation validation must fail for mismatched sums."""
        components = {
            "a": {"contribution": 0.3},
            "b": {"contribution": 0.2},
        }
        output = 0.7  # Mismatch

        result = validate_reconciliation(components, output)

        assert not result["valid"]
        assert result["difference"] > 0.01

    def test_validate_reconciliation_handles_nan(self):
        """Reconciliation validation must handle NaN/inf."""
        components = {
            "a": {"contribution": float("nan")},
            "b": {"contribution": 0.2},
        }
        output = 0.5

        result = validate_reconciliation(components, output)

        assert not result["valid"]
        # Sum should be NaN (not replaced with 0.0)
        assert math.isnan(result["sum"]) or not math.isfinite(result["sum"])


class TestTraceIntegration:
    """Test trace integration with actual decision surfaces."""

    def test_risk_classification_trace_integration(self):
        """Risk classification trace must reconcile with output."""
        classifier = RiskClassifier()

        result = classifier.classify_risk(
            behavior_index=0.6,
            convergence_score=70.0,
            trend_direction="increasing",
        )

        trace = result["trace"]
        reconciliation = trace["reconciliation"]

        assert reconciliation["valid"], (
            f"Risk trace reconciliation failed: sum={reconciliation['sum']}, "
            f"output={reconciliation['output']}"
        )

        # Verify components match result
        assert abs(trace["components"]["base_risk"]["value"] - result["base_risk"]) < 0.01
        assert (
            abs(trace["components"]["shock_adjustment"]["value"] - result["shock_adjustment"])
            < 0.01
        )

    def test_confidence_trace_integration(self):
        """Confidence trace must reconcile with output."""
        monitor = ForecastMonitor()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=30),
                "economic_stress": np.random.uniform(0.0, 1.0, 30),
            }
        )

        scores = monitor.calculate_confidence(df)
        trace = monitor.get_confidence_trace("economic_stress")

        assert trace is not None
        reconciliation = trace["reconciliation"]

        assert reconciliation["valid"], (
            f"Confidence trace reconciliation failed: sum={reconciliation['sum']}, "
            f"output={reconciliation['output']}"
        )

        # Verify output matches score
        assert abs(trace["output"]["confidence"] - scores["economic_stress"]) < 0.01
