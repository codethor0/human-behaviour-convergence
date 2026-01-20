# SPDX-License-Identifier: PROPRIETARY
"""Tests for scenario sensitivity and counterfactual analysis."""

import pandas as pd

from app.core.behavior_index import BehaviorIndexComputer
from app.core.scenario_sensitivity import (
    calculate_factor_elasticity,
    compose_sensitivity_analysis,
    compute_sensitivity_ranking,
    generate_sensitivity_narrative,
    validate_scenario_bounds,
)
from app.core.invariants import get_registry


class TestFactorElasticity:
    """Test factor elasticity calculation."""

    def test_elasticity_positive_change(self):
        """Test elasticity with positive change."""
        elasticity_data = calculate_factor_elasticity(
            base_behavior_index=0.5,
            perturbed_behavior_index=0.6,
            base_factor_value=0.5,
            perturbed_factor_value=0.7,
            factor_weight=0.4,
        )

        assert abs(elasticity_data["input_delta"] - 0.2) < 1e-9
        assert abs(elasticity_data["output_delta"] - 0.1) < 1e-9
        assert abs(elasticity_data["elasticity"] - 0.2) < 1e-9  # (0.1 / 0.2) * 0.4
        assert elasticity_data["sensitivity_classification"] in [
            "low",
            "medium",
            "high",
        ]

    def test_elasticity_negative_change(self):
        """Test elasticity with negative change."""
        elasticity_data = calculate_factor_elasticity(
            base_behavior_index=0.6,
            perturbed_behavior_index=0.5,
            base_factor_value=0.7,
            perturbed_factor_value=0.5,
            factor_weight=0.4,
        )

        assert abs(elasticity_data["input_delta"] - (-0.2)) < 1e-9
        assert abs(elasticity_data["output_delta"] - (-0.1)) < 1e-9
        assert elasticity_data["sensitivity_classification"] in [
            "low",
            "medium",
            "high",
        ]

    def test_elasticity_zero_input_delta(self):
        """Test elasticity with zero input delta."""
        elasticity_data = calculate_factor_elasticity(
            base_behavior_index=0.5,
            perturbed_behavior_index=0.5,
            base_factor_value=0.5,
            perturbed_factor_value=0.5,
            factor_weight=0.4,
        )

        assert elasticity_data["elasticity"] == 0.0
        assert elasticity_data["sensitivity_classification"] == "none"

    def test_elasticity_consistency(self):
        """Test INV-S01: Elasticity consistency."""
        registry = get_registry()

        output_delta = 0.1
        input_delta = 0.2
        factor_weight = 0.4
        elasticity = (output_delta / input_delta) * factor_weight

        is_valid, _ = registry.check(
            "INV-S01", elasticity, output_delta, input_delta, factor_weight
        )
        assert is_valid

    def test_sensitivity_classification_high(self):
        """Test sensitivity classification for high elasticity."""
        elasticity_data = calculate_factor_elasticity(
            base_behavior_index=0.5,
            perturbed_behavior_index=0.8,
            base_factor_value=0.5,
            perturbed_factor_value=0.6,
            factor_weight=1.0,  # High weight to get high elasticity
        )

        assert elasticity_data["sensitivity_classification"] == "high"
        assert elasticity_data["is_non_linear"] is True

    def test_sensitivity_classification_consistency(self):
        """Test INV-S02: Sensitivity classification consistency."""
        registry = get_registry()

        elasticity = 0.6  # High elasticity
        classification = "high"

        is_valid, _ = registry.check("INV-S02", elasticity, classification)
        assert is_valid


class TestSensitivityRanking:
    """Test sensitivity ranking computation."""

    def test_compute_sensitivity_ranking(self):
        """Test sensitivity ranking computation."""
        factor_elasticities = {
            "factor_a": {
                "elasticity": 0.1,
                "sensitivity_classification": "low",
                "is_non_linear": False,
            },
            "factor_b": {
                "elasticity": 0.6,
                "sensitivity_classification": "high",
                "is_non_linear": True,
            },
            "factor_c": {
                "elasticity": 0.3,
                "sensitivity_classification": "medium",
                "is_non_linear": False,
            },
        }

        rankings = compute_sensitivity_ranking(factor_elasticities)

        assert len(rankings) == 3
        assert rankings[0]["factor_id"] == "factor_b"  # Highest elasticity
        assert rankings[1]["factor_id"] == "factor_c"
        assert rankings[2]["factor_id"] == "factor_a"

    def test_sensitivity_ranking_order(self):
        """Test INV-S04: Sensitivity ranking order."""
        registry = get_registry()

        rankings = [
            {"factor_id": "a", "elasticity": 0.6},
            {"factor_id": "b", "elasticity": 0.3},
            {"factor_id": "c", "elasticity": 0.1},
        ]

        is_valid, _ = registry.check("INV-S04", rankings)
        assert is_valid


class TestScenarioBounds:
    """Test scenario bounds validation."""

    def test_validate_scenario_bounds_valid(self):
        """Test validation of valid scenario bounds."""
        is_valid, warning = validate_scenario_bounds(
            "test_factor",
            base_value=0.5,
            perturbation=0.1,
            min_value=0.0,
            max_value=1.0,
        )

        assert is_valid is True
        assert warning is None

    def test_validate_scenario_bounds_lower_violation(self):
        """Test validation detects lower bound violation."""
        is_valid, warning = validate_scenario_bounds(
            "test_factor",
            base_value=0.1,
            perturbation=-0.2,  # Would result in -0.1
            min_value=0.0,
            max_value=1.0,
        )

        assert is_valid is False
        assert warning is not None
        assert "out of bounds" in warning.lower()

    def test_validate_scenario_bounds_upper_violation(self):
        """Test validation detects upper bound violation."""
        is_valid, warning = validate_scenario_bounds(
            "test_factor",
            base_value=0.9,
            perturbation=0.2,  # Would result in 1.1
            min_value=0.0,
            max_value=1.0,
        )

        assert is_valid is False
        assert warning is not None

    def test_validate_scenario_bounds_large_perturbation_warning(self):
        """Test validation warns on large perturbations."""
        is_valid, warning = validate_scenario_bounds(
            "test_factor",
            base_value=0.2,
            perturbation=0.6,  # Large perturbation but within bounds (0.2 + 0.6 = 0.8 < 1.0)
            min_value=0.0,
            max_value=1.0,
        )

        assert is_valid is True  # Still valid, but warns
        assert warning is not None
        assert "large perturbation" in warning.lower()

    def test_scenario_bounds_validation_invariant(self):
        """Test INV-S03: Scenario bounds validation."""
        registry = get_registry()

        base_value = 0.5
        perturbation = 0.1
        min_value = 0.0
        max_value = 1.0

        is_valid, _ = registry.check(
            "INV-S03", base_value, perturbation, min_value, max_value
        )
        assert is_valid


class TestSensitivityNarrative:
    """Test sensitivity narrative generation."""

    def test_generate_sensitivity_narrative(self):
        """Test sensitivity narrative generation."""
        rankings = [
            {
                "factor_id": "market_volatility",
                "elasticity": 0.6,
                "is_non_linear": True,
            },
            {
                "factor_id": "employment_delta",
                "elasticity": 0.3,
                "is_non_linear": False,
            },
            {
                "factor_id": "consumer_sentiment",
                "elasticity": 0.1,
                "is_non_linear": False,
            },
        ]

        narrative = generate_sensitivity_narrative(rankings, top_n=3)

        assert len(narrative) > 0
        assert (
            "market volatility" in narrative.lower()
            or "market_volatility" in narrative.lower()
        )
        assert "non-linear" in narrative.lower()

    def test_generate_sensitivity_narrative_empty(self):
        """Test narrative generation with empty rankings."""
        narrative = generate_sensitivity_narrative([])

        assert "unavailable" in narrative.lower()


class TestSensitivityAnalysisComposition:
    """Test complete sensitivity analysis composition."""

    def test_compose_sensitivity_analysis(self):
        """Test that compose_sensitivity_analysis returns all required fields."""
        factor_elasticities = {
            "factor_a": {
                "elasticity": 0.3,
                "output_delta": 0.1,
                "input_delta": 0.2,
                "sensitivity_classification": "medium",
                "is_non_linear": False,
            }
        }

        analysis = compose_sensitivity_analysis(
            base_behavior_index=0.5,
            factor_elasticities=factor_elasticities,
        )

        assert "base_behavior_index" in analysis
        assert "factor_elasticities" in analysis
        assert "sensitivity_rankings" in analysis
        assert "sensitivity_narrative" in analysis
        assert "metadata" in analysis

    def test_sensitivity_analysis_completeness(self):
        """Test INV-S05: Sensitivity analysis completeness."""
        registry = get_registry()

        analysis = {
            "base_behavior_index": 0.5,
            "factor_elasticities": {},
            "sensitivity_rankings": [],
            "sensitivity_narrative": "",
            "metadata": {},
        }

        is_valid, _ = registry.check("INV-S05", analysis)
        assert is_valid


class TestNoSemanticDrift:
    """Test that sensitivity analysis doesn't introduce semantic drift."""

    def test_base_index_unchanged_with_sensitivity(self):
        """Test that base index is unchanged when sensitivity analysis is computed."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=20),
                "stress_index": [0.6] * 20,
                "discomfort_score": [0.7] * 20,
                "mobility_index": [0.5] * 20,
                "search_interest_score": [0.5] * 20,
                "health_risk_index": [0.5] * 20,
            }
        )

        df_before = computer.compute_behavior_index(harmonized)
        base_index_before = float(df_before["behavior_index"].iloc[19])

        # Compute sensitivity analysis (simplified - would need actual perturbation)
        factor_elasticities = {
            "test_factor": {
                "elasticity": 0.3,
                "output_delta": 0.05,
                "input_delta": 0.1,
                "sensitivity_classification": "medium",
                "is_non_linear": False,
            }
        }
        analysis = compose_sensitivity_analysis(base_index_before, factor_elasticities)

        # Recompute to ensure no side effects
        df_after = computer.compute_behavior_index(harmonized)
        base_index_after = float(df_after["behavior_index"].iloc[19])

        assert abs(base_index_before - base_index_after) < 1e-10
        assert analysis is not None


class TestBackwardCompatibility:
    """Test backward compatibility."""

    def test_sensitivity_analysis_optional(self):
        """Test that sensitivity analysis is optional and doesn't break old consumers."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [0.5] * 10,
                "discomfort_score": [0.5] * 10,
                "mobility_index": [0.5] * 10,
                "search_interest_score": [0.5] * 10,
                "health_risk_index": [0.5] * 10,
            }
        )

        df = computer.compute_behavior_index(harmonized)
        base_index = float(df["behavior_index"].iloc[9])

        # Old consumers can still access behavior index without sensitivity analysis
        assert base_index >= 0.0
        assert base_index <= 1.0

        # Sensitivity analysis can be computed separately if needed
        factor_elasticities = {}
        analysis = compose_sensitivity_analysis(base_index, factor_elasticities)
        assert analysis is not None
        assert "base_behavior_index" in analysis
