# SPDX-License-Identifier: PROPRIETARY
"""Tests for factor quality and signal strength metrics."""

import pandas as pd

from app.core.behavior_index import BehaviorIndexComputer
from app.core.factor_quality import (
    calculate_factor_confidence,
    calculate_factor_volatility,
    calculate_factor_persistence,
    calculate_factor_trend,
    calculate_signal_strength,
    compute_factor_quality_metrics,
)
from app.core.invariants import get_registry


class TestFactorConfidence:
    """Test factor confidence calculation."""

    def test_confidence_with_data(self):
        """Test confidence calculation when data is available."""
        confidence = calculate_factor_confidence(
            factor_value=0.6,
            has_data=True,
            data_freshness_days=1.0,
            stability_score=0.8,
        )
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be high with fresh, stable data

    def test_confidence_without_data(self):
        """Test confidence calculation when data is missing."""
        confidence = calculate_factor_confidence(
            factor_value=0.5,
            has_data=False,
        )
        assert confidence == 0.3  # Low confidence for missing data

    def test_confidence_stale_data(self):
        """Test confidence decreases with stale data."""
        fresh_conf = calculate_factor_confidence(
            factor_value=0.6,
            has_data=True,
            data_freshness_days=1.0,
        )
        stale_conf = calculate_factor_confidence(
            factor_value=0.6,
            has_data=True,
            data_freshness_days=60.0,
        )
        assert fresh_conf > stale_conf

    def test_confidence_range(self):
        """Test confidence is always in [0.0, 1.0]."""
        registry = get_registry()

        # Test various scenarios
        test_cases = [
            (0.5, True, 1.0, 1.0),
            (0.5, True, 60.0, 0.0),
            (0.5, False, None, None),
        ]

        for value, has_data, freshness, stability in test_cases:
            confidence = calculate_factor_confidence(
                factor_value=value,
                has_data=has_data,
                data_freshness_days=freshness,
                stability_score=stability,
            )
            assert 0.0 <= confidence <= 1.0
            # Check INV-Q01
            is_valid, _ = registry.check("INV-Q01", confidence)
            assert is_valid


class TestFactorVolatility:
    """Test factor volatility calculation."""

    def test_volatility_low(self):
        """Test low volatility classification."""
        values = pd.Series([0.5, 0.51, 0.49, 0.52, 0.48])
        volatility_score, classification = calculate_factor_volatility(values)
        assert classification == "low"
        assert volatility_score < 0.1

    def test_volatility_medium(self):
        """Test medium volatility classification."""
        values = pd.Series([0.3, 0.5, 0.4, 0.6, 0.35])
        volatility_score, classification = calculate_factor_volatility(values)
        assert classification == "medium"
        assert 0.1 <= volatility_score < 0.3

    def test_volatility_high(self):
        """Test high volatility classification."""
        values = pd.Series([0.1, 0.9, 0.2, 0.8, 0.15])
        volatility_score, classification = calculate_factor_volatility(values)
        assert classification == "high"
        assert volatility_score >= 0.3

    def test_volatility_consistency(self):
        """Test volatility classification matches score (INV-Q02)."""
        registry = get_registry()

        values = pd.Series([0.5, 0.6, 0.4, 0.55, 0.45])
        volatility_score, classification = calculate_factor_volatility(values)

        # Check INV-Q02
        is_valid, _ = registry.check("INV-Q02", volatility_score, classification)
        assert is_valid

    def test_volatility_empty_series(self):
        """Test volatility with empty series."""
        values = pd.Series([])
        volatility_score, classification = calculate_factor_volatility(values)
        assert volatility_score == 0.0
        assert classification == "low"

    def test_volatility_single_value(self):
        """Test volatility with single value."""
        values = pd.Series([0.5])
        volatility_score, classification = calculate_factor_volatility(values)
        assert volatility_score == 0.0
        assert classification == "low"


class TestFactorPersistence:
    """Test factor persistence calculation."""

    def test_persistence_consecutive_days(self):
        """Test persistence counts consecutive days."""
        contributions = pd.Series([0.02, 0.03, 0.015, 0.025, 0.02])
        persistence = calculate_factor_persistence(contributions, threshold=0.01)
        assert persistence == 5  # All above threshold

    def test_persistence_partial(self):
        """Test persistence with some below threshold."""
        contributions = pd.Series([0.02, 0.03, 0.005, 0.015, 0.02])
        persistence = calculate_factor_persistence(contributions, threshold=0.01)
        assert persistence == 2  # Last two above threshold

    def test_persistence_zero(self):
        """Test persistence with all below threshold."""
        contributions = pd.Series([0.005, 0.003, 0.002])
        persistence = calculate_factor_persistence(contributions, threshold=0.01)
        assert persistence == 0

    def test_persistence_empty(self):
        """Test persistence with empty series."""
        contributions = pd.Series([])
        persistence = calculate_factor_persistence(contributions)
        assert persistence == 0


class TestFactorTrend:
    """Test factor trend calculation."""

    def test_trend_improving(self):
        """Test improving trend detection."""
        values = pd.Series([0.8, 0.7, 0.6, 0.5, 0.4])
        trend = calculate_factor_trend(values)
        assert trend == "improving"

    def test_trend_worsening(self):
        """Test worsening trend detection."""
        values = pd.Series([0.2, 0.3, 0.4, 0.5, 0.6])
        trend = calculate_factor_trend(values)
        assert trend == "worsening"

    def test_trend_stable(self):
        """Test stable trend detection."""
        values = pd.Series([0.5, 0.51, 0.49, 0.52, 0.48])
        trend = calculate_factor_trend(values)
        assert trend == "stable"

    def test_trend_empty(self):
        """Test trend with empty series."""
        values = pd.Series([])
        trend = calculate_factor_trend(values)
        assert trend == "stable"

    def test_trend_single_value(self):
        """Test trend with single value."""
        values = pd.Series([0.5])
        trend = calculate_factor_trend(values)
        assert trend == "stable"


class TestSignalStrength:
    """Test signal strength calculation."""

    def test_signal_strength_high_contribution(self):
        """Test signal strength with high contribution."""
        signal = calculate_signal_strength(
            contribution=0.2,
            volatility_score=0.1,
            confidence=0.8,
        )
        assert signal > 0.1

    def test_signal_strength_low_contribution(self):
        """Test signal strength with low contribution."""
        signal = calculate_signal_strength(
            contribution=0.01,
            volatility_score=0.1,
            confidence=0.8,
        )
        assert signal < 0.1

    def test_signal_strength_high_volatility_reduces_signal(self):
        """Test that high volatility reduces signal strength."""
        low_vol_signal = calculate_signal_strength(
            contribution=0.2,
            volatility_score=0.05,
            confidence=0.8,
        )
        high_vol_signal = calculate_signal_strength(
            contribution=0.2,
            volatility_score=0.5,
            confidence=0.8,
        )
        assert low_vol_signal > high_vol_signal

    def test_signal_strength_monotonicity(self):
        """Test signal strength monotonicity (INV-Q03)."""
        registry = get_registry()

        contrib1 = 0.1
        contrib2 = 0.2

        signal1 = calculate_signal_strength(contrib1, 0.1, 0.8)
        signal2 = calculate_signal_strength(contrib2, 0.1, 0.8)

        # Signal strength should increase with contribution
        assert signal2 > signal1

        # Check INV-Q03
        is_valid, _ = registry.check("INV-Q03", contrib1, signal1)
        assert is_valid
        is_valid, _ = registry.check("INV-Q03", contrib2, signal2)
        assert is_valid

    def test_signal_strength_handles_nan(self):
        """Test signal strength handles NaN/inf gracefully."""
        signal = calculate_signal_strength(
            contribution=float("nan"),
            volatility_score=0.1,
            confidence=0.8,
        )
        assert signal == 0.0


class TestFactorQualityMetricsIntegration:
    """Test integrated factor quality metrics computation."""

    def test_compute_all_metrics(self):
        """Test computation of all quality metrics."""
        factor_values = pd.Series([0.5, 0.6, 0.55, 0.65, 0.6])
        factor_contributions = pd.Series([0.1, 0.12, 0.11, 0.13, 0.12])

        metrics = compute_factor_quality_metrics(
            factor_id="test_factor",
            current_value=0.6,
            current_contribution=0.12,
            factor_values_series=factor_values,
            factor_contributions_series=factor_contributions,
            has_data=True,
            data_freshness_days=1.0,
        )

        assert "confidence" in metrics
        assert "volatility" in metrics
        assert "volatility_classification" in metrics
        assert "persistence" in metrics
        assert "trend" in metrics
        assert "signal_strength" in metrics

        assert 0.0 <= metrics["confidence"] <= 1.0
        assert metrics["volatility_classification"] in ["low", "medium", "high"]
        assert metrics["persistence"] >= 0
        assert metrics["trend"] in ["improving", "worsening", "stable"]
        assert metrics["signal_strength"] >= 0.0

    def test_compute_metrics_missing_data(self):
        """Test quality metrics with missing data."""
        metrics = compute_factor_quality_metrics(
            factor_id="test_factor",
            current_value=0.5,
            current_contribution=0.1,
            factor_values_series=None,
            factor_contributions_series=None,
            has_data=False,
        )

        # Confidence should be low for missing data
        assert metrics["confidence"] <= 0.5
        assert metrics["volatility_classification"] == "low"
        assert metrics["persistence"] == 0
        assert metrics["trend"] == "stable"

    def test_missing_data_confidence_invariant(self):
        """Test INV-Q04: Missing data does not inflate confidence."""
        registry = get_registry()

        metrics = compute_factor_quality_metrics(
            factor_id="test_factor",
            current_value=0.5,
            current_contribution=0.1,
            has_data=False,
        )

        # Check INV-Q04
        is_valid, _ = registry.check("INV-Q04", False, metrics["confidence"])
        assert is_valid


class TestHierarchicalQualityReconciliation:
    """Test quality metrics with hierarchical reconciliation."""

    def test_quality_metrics_preserve_reconciliation(self):
        """Test that quality metrics don't break factor reconciliation."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=5),
                "stress_index": [0.5, 0.6, 0.55, 0.65, 0.6],
                "discomfort_score": [0.5, 0.5, 0.5, 0.5, 0.5],
                "mobility_index": [0.5, 0.5, 0.5, 0.5, 0.5],
                "search_interest_score": [0.5, 0.5, 0.5, 0.5, 0.5],
                "health_risk_index": [0.5, 0.5, 0.5, 0.5, 0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)

        # Get details with quality metrics
        details = computer.get_subindex_details(df, 4, include_quality_metrics=True)

        # Verify reconciliation still holds
        economic = details["economic_stress"]
        factor_sum = sum(f["contribution"] for f in economic["components"])
        assert abs(factor_sum - economic["value"]) <= 0.01

        # Verify quality metrics are present
        for factor in economic["components"]:
            assert "confidence" in factor
            assert "volatility_classification" in factor
            assert "persistence" in factor
            assert "trend" in factor
            assert "signal_strength" in factor


class TestNoSemanticDriftQuality:
    """Test that quality metrics don't introduce semantic drift."""

    def test_global_index_unchanged_with_quality(self):
        """Test that global index is unchanged when quality metrics are computed."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=5),
                "stress_index": [0.6, 0.6, 0.6, 0.6, 0.6],
                "discomfort_score": [0.7, 0.7, 0.7, 0.7, 0.7],
                "mobility_index": [0.5, 0.5, 0.5, 0.5, 0.5],
                "search_interest_score": [0.5, 0.5, 0.5, 0.5, 0.5],
                "health_risk_index": [0.5, 0.5, 0.5, 0.5, 0.5],
            }
        )

        df = computer.compute_behavior_index(harmonized)
        global_index_before = float(df["behavior_index"].iloc[4])

        # Get details with quality metrics
        computer.get_subindex_details(df, 4, include_quality_metrics=True)

        # Recompute to ensure no side effects
        df_after = computer.compute_behavior_index(harmonized)
        global_index_after = float(df_after["behavior_index"].iloc[4])

        assert abs(global_index_before - global_index_after) < 1e-10

    def test_sub_indices_unchanged_with_quality(self):
        """Test that sub-indices are unchanged when quality metrics are computed."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=5),
                "stress_index": [0.6, 0.6, 0.6, 0.6, 0.6],
                "discomfort_score": [0.7, 0.7, 0.7, 0.7, 0.7],
                "mobility_index": [0.5, 0.5, 0.5, 0.5, 0.5],
                "search_interest_score": [0.5, 0.5, 0.5, 0.5, 0.5],
                "health_risk_index": [0.5, 0.5, 0.5, 0.5, 0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)
        economic_before = float(df["economic_stress"].iloc[4])
        environmental_before = float(df["environmental_stress"].iloc[4])

        # Get details with quality metrics
        details = computer.get_subindex_details(df, 4, include_quality_metrics=True)

        # Verify sub-index values unchanged
        assert abs(details["economic_stress"]["value"] - economic_before) < 1e-10
        assert (
            abs(details["environmental_stress"]["value"] - environmental_before) < 1e-10
        )


class TestBackwardCompatibilityQuality:
    """Test backward compatibility with quality metrics."""

    def test_quality_metrics_optional(self):
        """Test that quality metrics are optional and don't break old consumers."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.5],
                "discomfort_score": [0.5],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)

        # Get details without quality metrics
        details_no_quality = computer.get_subindex_details(
            df, 0, include_quality_metrics=False
        )

        # Get details with quality metrics
        details_with_quality = computer.get_subindex_details(
            df, 0, include_quality_metrics=True
        )

        # Old consumers can still access value and contribution
        economic_no_quality = details_no_quality["economic_stress"]
        economic_with_quality = details_with_quality["economic_stress"]

        assert economic_no_quality["value"] == economic_with_quality["value"]
        assert len(economic_no_quality["components"]) == len(
            economic_with_quality["components"]
        )

        # Old consumers can ignore quality fields
        factor_no_quality = economic_no_quality["components"][0]
        factor_with_quality = economic_with_quality["components"][0]

        assert "id" in factor_no_quality
        assert "value" in factor_no_quality
        assert "contribution" in factor_no_quality

        # Quality fields are optional
        if "confidence" in factor_with_quality:
            assert 0.0 <= factor_with_quality["confidence"] <= 1.0

    def test_quality_metrics_backward_compatible_schema(self):
        """Test that API schema remains backward compatible."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=5),
                "stress_index": [0.5, 0.5, 0.5, 0.5, 0.5],
                "discomfort_score": [0.5, 0.5, 0.5, 0.5, 0.5],
                "mobility_index": [0.5, 0.5, 0.5, 0.5, 0.5],
                "search_interest_score": [0.5, 0.5, 0.5, 0.5, 0.5],
                "health_risk_index": [0.5, 0.5, 0.5, 0.5, 0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)
        details = computer.get_subindex_details(df, 4, include_quality_metrics=True)

        # Verify all required fields still present
        for sub_index_name, sub_index_details in details.items():
            assert "value" in sub_index_details
            assert "components" in sub_index_details
            assert "reconciliation" in sub_index_details

            for factor in sub_index_details["components"]:
                assert "id" in factor
                assert "value" in factor
                assert "weight" in factor
                assert "contribution" in factor
                assert "source" in factor

                # Quality fields are optional additions
                if "confidence" in factor:
                    assert 0.0 <= factor["confidence"] <= 1.0


class TestOrderIndependenceQuality:
    """Test order independence of quality metrics."""

    def test_factor_ranking_order_independent(self):
        """Test that factor ranking by signal strength is order-independent."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=5),
                "stress_index": [0.6, 0.6, 0.6, 0.6, 0.6],
                "fred_consumer_sentiment": [0.4, 0.4, 0.4, 0.4, 0.4],
                "discomfort_score": [0.5, 0.5, 0.5, 0.5, 0.5],
                "mobility_index": [0.5, 0.5, 0.5, 0.5, 0.5],
                "search_interest_score": [0.5, 0.5, 0.5, 0.5, 0.5],
                "health_risk_index": [0.5, 0.5, 0.5, 0.5, 0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)

        # Get details multiple times
        details1 = computer.get_subindex_details(df, 4, include_quality_metrics=True)
        details2 = computer.get_subindex_details(df, 4, include_quality_metrics=True)

        # Factor IDs should be in same order
        factors1 = [f["id"] for f in details1["economic_stress"]["components"]]
        factors2 = [f["id"] for f in details2["economic_stress"]["components"]]

        assert factors1 == factors2

        # Signal strengths should be identical
        if len(factors1) > 1:
            signal1 = [
                f["signal_strength"] for f in details1["economic_stress"]["components"]
            ]
            signal2 = [
                f["signal_strength"] for f in details2["economic_stress"]["components"]
            ]
            assert signal1 == signal2
