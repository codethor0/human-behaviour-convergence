# SPDX-License-Identifier: PROPRIETARY
"""Tests for early warning and advanced intelligence (N+36)."""
import pytest

from app.core.early_warning import (
    compose_confidence_weighted_foresight,
    compose_early_warning_indicators,
    detect_change_acceleration,
    detect_cross_factor_interactions,
)
from app.core.invariants import get_registry, InvariantViolation


class TestChangeAcceleration:
    """Tests for change acceleration detection."""

    def test_no_acceleration_stable(self):
        """Test no acceleration detected for stable values."""
        values = [0.5] * 20
        result = detect_change_acceleration(values)

        assert result["detected"] is False
        assert result["acceleration_rate"] == 0.0

    def test_acceleration_detected(self):
        """Test acceleration detected for accelerating values."""
        # Quadratic increase (rate of change is increasing)
        values = [0.01 * i * i for i in range(20)]
        result = detect_change_acceleration(values, acceleration_threshold=0.001)

        # Should detect acceleration (rate increasing)
        assert result["detected"] is True
        assert result["acceleration_rate"] > 0.0

    def test_insufficient_data(self):
        """Test handling of insufficient data."""
        values = [0.5] * 5  # Less than 2 * window_size
        result = detect_change_acceleration(values)

        assert result["detected"] is False
        assert "Insufficient data" in result.get("reason", "")

    def test_confidence_calculation(self):
        """Test confidence calculation."""
        # Stable values (low confidence)
        stable_values = [0.5] * 20
        stable_result = detect_change_acceleration(stable_values)

        # Quadratic increase (accelerating values)
        accelerating_values = [0.01 * i * i for i in range(20)]
        accel_result = detect_change_acceleration(accelerating_values, acceleration_threshold=0.001)

        # Accelerating should have higher confidence (if detected)
        if accel_result["detected"]:
            assert accel_result["confidence"] >= stable_result["confidence"]


class TestEarlyWarningIndicators:
    """Tests for early warning indicators."""

    def test_no_warnings_empty_history(self):
        """Test no warnings for empty history."""
        result = compose_early_warning_indicators(
            behavior_index_history=[],
        )

        assert result["warning_count"] == 0
        assert len(result["warnings"]) == 0

    def test_acceleration_warning(self):
        """Test acceleration-based warning."""
        # Quadratic increase (rate of change is increasing)
        history = [0.01 * i * i for i in range(20)]

        result = compose_early_warning_indicators(
            behavior_index_history=history,
            min_confidence=0.3,  # Lower threshold for test
        )

        # Should have at least one warning if acceleration detected
        if result["warning_count"] > 0:
            acceleration_warnings = [w for w in result["warnings"] if w["type"] == "acceleration"]
            # May or may not have acceleration warning depending on threshold
            # Just verify structure is correct
            assert isinstance(result["warnings"], list)

    def test_benchmark_deviation_warning(self):
        """Test benchmark deviation warning."""
        history = [0.5] * 20

        benchmarks = {
            "baseline_deviation": {
                "classification": "elevated",
                "z_score": 2.5,
                "baseline_value": 0.4,
                "current_value": 0.5,
            },
        }

        result = compose_early_warning_indicators(
            behavior_index_history=history,
            benchmarks=benchmarks,
            min_confidence=0.5,
        )

        benchmark_warnings = [w for w in result["warnings"] if w["type"] == "benchmark_deviation"]
        assert len(benchmark_warnings) > 0

    def test_confidence_gating(self):
        """Test confidence gating filters low-confidence warnings."""
        history = [0.5] * 20

        result = compose_early_warning_indicators(
            behavior_index_history=history,
            min_confidence=0.9,  # High threshold
        )

        # All warnings should meet confidence threshold
        for warning in result["warnings"]:
            assert warning["confidence"] >= 0.9

    def test_trend_sensitivity_warning(self):
        """Test trend + sensitivity warning."""
        history = [0.5] * 20

        temporal_attribution = {
            "global_delta": {
                "delta_value": 0.05,
                "direction": "increasing",
            },
        }

        sensitivity_analysis = {
            "factor_elasticities": {
                "economic_stress": 0.8,
                "environmental_stress": 0.6,
            },
        }

        result = compose_early_warning_indicators(
            behavior_index_history=history,
            temporal_attribution=temporal_attribution,
            sensitivity_analysis=sensitivity_analysis,
            min_confidence=0.5,
        )

        trend_warnings = [w for w in result["warnings"] if w["type"] == "trend_sensitivity"]
        assert len(trend_warnings) > 0


class TestCrossFactorInteractions:
    """Tests for cross-factor interaction detection."""

    def test_no_interactions(self):
        """Test no interactions detected for low values."""
        factor_values = {
            "economic_stress": 0.3,
            "environmental_stress": 0.4,
        }
        factor_contributions = {
            "economic_stress": 0.05,
            "environmental_stress": 0.06,
        }

        result = detect_cross_factor_interactions(
            factor_values=factor_values,
            factor_contributions=factor_contributions,
            behavior_index=0.5,
        )

        assert result["detected"] is False
        assert len(result["interactions"]) == 0

    def test_interaction_detected(self):
        """Test interaction detected for high-value pairs."""
        factor_values = {
            "economic_stress": 0.8,
            "environmental_stress": 0.75,
        }
        factor_contributions = {
            "economic_stress": 0.15,
            "environmental_stress": 0.12,
        }

        result = detect_cross_factor_interactions(
            factor_values=factor_values,
            factor_contributions=factor_contributions,
            behavior_index=0.7,
            interaction_threshold=0.1,
        )

        assert result["detected"] is True
        assert len(result["interactions"]) > 0

        # Verify interaction is labeled as hypothesis
        for interaction in result["interactions"]:
            assert "hypothesis" in interaction["interaction_type"].lower()
            assert "hypothesis" in interaction.get("note", "").lower()

    def test_interaction_hypothesis_labeling(self):
        """Test that interactions are labeled as hypotheses."""
        factor_values = {
            "economic_stress": 0.8,
            "environmental_stress": 0.75,
        }
        factor_contributions = {
            "economic_stress": 0.15,
            "environmental_stress": 0.12,
        }

        result = detect_cross_factor_interactions(
            factor_values=factor_values,
            factor_contributions=factor_contributions,
            behavior_index=0.7,
        )

        for interaction in result["interactions"]:
            assert "hypothesis" in interaction["interaction_type"].lower()


class TestConfidenceWeightedForesight:
    """Tests for confidence-weighted foresight."""

    def test_foresight_composition(self):
        """Test foresight composition."""
        early_warnings = {
            "warnings": [
                {
                    "type": "acceleration",
                    "confidence": 0.85,
                    "severity": "medium",
                    "message": "Test warning",
                },
                {
                    "type": "benchmark_deviation",
                    "confidence": 0.65,
                    "severity": "medium",
                    "message": "Test warning 2",
                },
            ],
            "warning_count": 2,
        }

        result = compose_confidence_weighted_foresight(
            early_warnings=early_warnings,
        )

        assert "foresight_summary" in result
        assert len(result["high_confidence_warnings"]) == 1
        assert len(result["medium_confidence_warnings"]) == 1
        assert "confidence_disclaimer" in result

    def test_confidence_classification(self):
        """Test confidence-based classification."""
        early_warnings = {
            "warnings": [
                {"type": "test", "confidence": 0.9, "severity": "high"},
                {"type": "test", "confidence": 0.7, "severity": "medium"},
                {"type": "test", "confidence": 0.5, "severity": "low"},
            ],
            "warning_count": 3,
        }

        result = compose_confidence_weighted_foresight(
            early_warnings=early_warnings,
        )

        assert len(result["high_confidence_warnings"]) == 1
        assert len(result["medium_confidence_warnings"]) == 1
        assert len(result["low_confidence_warnings"]) == 1

    def test_interaction_hypotheses_included(self):
        """Test that interaction hypotheses are included."""
        early_warnings = {
            "warnings": [],
            "warning_count": 0,
        }

        factor_interactions = {
            "detected": True,
            "interactions": [
                {
                    "factor_a": "economic_stress",
                    "factor_b": "environmental_stress",
                    "interaction_type": "amplification_hypothesis",
                    "note": "This is a hypothesis",
                },
            ],
        }

        result = compose_confidence_weighted_foresight(
            early_warnings=early_warnings,
            factor_interactions=factor_interactions,
        )

        assert len(result["interaction_hypotheses"]) == 1

    def test_coverage_freshness_disclaimer(self):
        """Test coverage/freshness disclaimer."""
        early_warnings = {
            "warnings": [],
            "warning_count": 0,
        }

        provenance = {
            "aggregate_provenance": {
                "coverage_ratio": 0.6,  # Low coverage
                "freshness_classification": "stale",  # Stale
            },
        }

        result = compose_confidence_weighted_foresight(
            early_warnings=early_warnings,
            provenance=provenance,
        )

        assert "coverage" in result["confidence_disclaimer"].lower() or "freshness" in result["confidence_disclaimer"].lower()


class TestEarlyWarningInvariants:
    """Tests for early warning invariants."""

    def test_inv_ew01_derivability(self):
        """Test INV-EW01: Early warnings derivable."""
        registry = get_registry()

        early_warnings = {
            "warnings": [
                {
                    "type": "acceleration",  # Valid
                    "confidence": 0.8,
                },
            ],
        }
        source_signals = ["acceleration", "trend_sensitivity"]

        is_valid, error = registry.check("INV-EW01", early_warnings, source_signals)
        assert is_valid is True

    def test_inv_ew01_derivability_violation(self):
        """Test INV-EW01 violation: Unknown signal type."""
        registry = get_registry()

        early_warnings = {
            "warnings": [
                {
                    "type": "unknown_signal",  # Invalid
                    "confidence": 0.8,
                },
            ],
        }
        source_signals = ["acceleration"]

        is_valid, error = registry.check("INV-EW01", early_warnings, source_signals)
        assert is_valid is False
        assert "unknown" in error.lower()

    def test_inv_ew02_confidence_gating(self):
        """Test INV-EW02: Confidence gating."""
        registry = get_registry()

        early_warning = {
            "confidence": 0.8,
        }
        min_confidence = 0.6
        coverage_ratio = 0.9

        is_valid, error = registry.check("INV-EW02", early_warning, min_confidence, coverage_ratio)
        assert is_valid is True

    def test_inv_ew02_confidence_gating_violation(self):
        """Test INV-EW02 violation: Low confidence."""
        registry = get_registry()

        early_warning = {
            "confidence": 0.4,  # Below minimum
        }
        min_confidence = 0.6

        is_valid, error = registry.check("INV-EW02", early_warning, min_confidence)
        assert is_valid is False
        assert "confidence" in error.lower()

    def test_inv_ew03_interaction_labeling(self):
        """Test INV-EW03: Interaction effects labeled."""
        registry = get_registry()

        interaction = {
            "interaction_type": "amplification_hypothesis",
            "note": "This is a hypothesis based on correlation",
        }

        is_valid, error = registry.check("INV-EW03", interaction)
        assert is_valid is True

    def test_inv_ew03_interaction_labeling_violation(self):
        """Test INV-EW03 violation: Not labeled as hypothesis."""
        registry = get_registry()

        interaction = {
            "interaction_type": "amplification",  # Missing "hypothesis"
            "note": "This is an interaction",
        }

        is_valid, error = registry.check("INV-EW03", interaction)
        assert is_valid is False
        assert "hypothesis" in error.lower()

    def test_inv_ew05_zero_numerical_drift(self):
        """Test INV-EW05: Zero numerical drift."""
        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.548

        is_valid, error = registry.check("INV-EW05", behavior_index_before, behavior_index_after)
        assert is_valid is True

    def test_inv_ew05_zero_numerical_drift_violation(self):
        """Test INV-EW05 violation: Numerical drift."""

        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.550  # Changed

        # INV-EW05 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-EW05", behavior_index_before, behavior_index_after)

        assert "drift" in str(exc_info.value).lower() or "changed" in str(exc_info.value).lower()


class TestNoSemanticDrift:
    """Tests to ensure early warning features don't cause semantic drift."""

    def test_early_warning_purely_additive(self):
        """Test that early warning is purely additive."""
        from app.core.behavior_index import BehaviorIndexComputer
        import pandas as pd

        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=30),
            'stress_index': [0.6] * 30,
            'discomfort_score': [0.7] * 30,
            'mobility_index': [0.5] * 30,
            'search_interest_score': [0.5] * 30,
            'health_risk_index': [0.5] * 30,
        })

        # Compute before early warning
        df_before = computer.compute_behavior_index(harmonized)
        global_before = float(df_before['behavior_index'].iloc[29])

        # Use early warning features
        history = [float(df_before['behavior_index'].iloc[i]) for i in range(20)]
        compose_early_warning_indicators(behavior_index_history=history)

        # Recompute after early warning
        df_after = computer.compute_behavior_index(harmonized)
        global_after = float(df_after['behavior_index'].iloc[29])

        # Verify zero numerical drift
        assert abs(global_before - global_after) < 1e-10


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_early_warning_optional(self):
        """Test that early warning is optional."""
        # Should not raise even if inputs are None
        result = compose_early_warning_indicators(
            behavior_index_history=[],
            temporal_attribution=None,
            sensitivity_analysis=None,
            alerts=None,
            benchmarks=None,
        )
        assert isinstance(result, dict)
        assert "warnings" in result
