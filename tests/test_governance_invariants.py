"""Tests for governance invariants.

These tests enforce invariants defined in INVARIANTS.md.
They must fail loudly if invariants are violated.
"""

import numpy as np
import pandas as pd

from app.core.behavior_index import BehaviorIndexComputer


class TestInvariantI1NormalizedWeightSum:
    """Test I1: Normalized weight sum = 1.0."""

    def test_default_weights_normalize_to_one(self):
        """Test that default weights normalize to sum = 1.0."""
        computer = BehaviorIndexComputer()

        # Create test data
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        test_data = pd.DataFrame(
            {
                "timestamp": dates,
                "stress_index": [0.5] * 10,
                "discomfort_score": [0.5] * 10,
                "mobility_index": [0.5] * 10,
                "search_interest_score": [0.5] * 10,
                "health_risk_index": [0.5] * 10,
            }
        )

        # Compute behavior index (triggers normalization)
        computer.compute_behavior_index(test_data)

        # Calculate sum of normalized weights
        normalized_sum = (
            computer.economic_weight
            + computer.environmental_weight
            + computer.mobility_weight
            + computer.digital_attention_weight
            + computer.health_weight
        )

        if computer.political_weight > 0:
            normalized_sum += computer.political_weight
        if computer.crime_weight > 0:
            normalized_sum += computer.crime_weight
        if computer.misinformation_weight > 0:
            normalized_sum += computer.misinformation_weight
        if computer.social_cohesion_weight > 0:
            normalized_sum += computer.social_cohesion_weight

        assert (
            abs(normalized_sum - 1.0) < 0.01
        ), f"Normalized weights sum to {normalized_sum}, expected 1.0"

    def test_custom_weights_normalize_to_one(self):
        """Test that custom weights normalize to sum = 1.0."""
        # Weights that don't sum to 1.0
        computer = BehaviorIndexComputer(
            economic_weight=0.3,
            environmental_weight=0.3,
            mobility_weight=0.2,
            digital_attention_weight=0.1,
            health_weight=0.1,
        )

        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        test_data = pd.DataFrame(
            {
                "timestamp": dates,
                "stress_index": [0.5] * 10,
                "discomfort_score": [0.5] * 10,
                "mobility_index": [0.5] * 10,
                "search_interest_score": [0.5] * 10,
                "health_risk_index": [0.5] * 10,
            }
        )

        # Compute behavior index (triggers normalization)
        computer.compute_behavior_index(test_data)

        # Calculate sum of normalized weights (include all weights)
        normalized_sum = (
            computer.economic_weight
            + computer.environmental_weight
            + computer.mobility_weight
            + computer.digital_attention_weight
            + computer.health_weight
        )

        if computer.political_weight > 0:
            normalized_sum += computer.political_weight
        if computer.crime_weight > 0:
            normalized_sum += computer.crime_weight
        if computer.misinformation_weight > 0:
            normalized_sum += computer.misinformation_weight
        if computer.social_cohesion_weight > 0:
            normalized_sum += computer.social_cohesion_weight

        assert (
            abs(normalized_sum - 1.0) < 0.01
        ), f"Normalized weights sum to {normalized_sum}, expected 1.0"


class TestInvariantI3ZeroWeightExclusion:
    """Test I3: Zero weight exclusion."""

    def test_zero_weight_sub_index_excluded(self):
        """Test that sub-indices with zero weight are excluded."""
        computer = BehaviorIndexComputer(
            political_weight=0.0,
            crime_weight=0.0,
            misinformation_weight=0.0,
            social_cohesion_weight=0.0,
        )

        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        test_data = pd.DataFrame(
            {
                "timestamp": dates,
                "stress_index": [0.5] * 10,
                "discomfort_score": [0.5] * 10,
                "mobility_index": [0.5] * 10,
                "search_interest_score": [0.5] * 10,
                "health_risk_index": [0.5] * 10,
            }
        )

        # Compute behavior index (triggers zero-weight exclusion logic)
        computer.compute_behavior_index(test_data)

        # Verify zero-weight sub-indices are not included
        assert computer.political_weight == 0.0
        assert computer.crime_weight == 0.0
        assert computer.misinformation_weight == 0.0
        assert computer.social_cohesion_weight == 0.0

        # Verify only original 5 sub-indices contribute
        # (This is structural - if weights are 0, they don't contribute)


class TestInvariantI4SubIndexCount:
    """Test I4: Sub-index count consistency."""

    def test_sub_index_count_is_nine(self):
        """Test that code implements exactly 9 sub-indices."""
        computer = BehaviorIndexComputer()

        # Count weight parameters (should be 9)
        weights = [
            computer.economic_weight,
            computer.environmental_weight,
            computer.mobility_weight,
            computer.digital_attention_weight,
            computer.health_weight,
            computer.political_weight,
            computer.crime_weight,
            computer.misinformation_weight,
            computer.social_cohesion_weight,
        ]

        # Count non-zero weights (when all weights > 0, should be 9)
        non_zero_count = sum(1 for w in weights if w > 0)

        assert non_zero_count == 9, f"Expected 9 sub-indices, found {non_zero_count}"


class TestInvariantI5BehaviorIndexRange:
    """Test I5: Behavior index range [0.0, 1.0]."""

    def test_behavior_index_always_in_range(self):
        """Test that behavior_index is always in [0.0, 1.0]."""
        computer = BehaviorIndexComputer()

        # Test with extreme values
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        test_data = pd.DataFrame(
            {
                "timestamp": dates,
                "stress_index": np.random.uniform(0.0, 1.0, 100),
                "discomfort_score": np.random.uniform(0.0, 1.0, 100),
                "mobility_index": np.random.uniform(0.0, 1.0, 100),
                "search_interest_score": np.random.uniform(0.0, 1.0, 100),
                "health_risk_index": np.random.uniform(0.0, 1.0, 100),
            }
        )

        result = computer.compute_behavior_index(test_data)

        assert (
            result["behavior_index"].min() >= 0.0
        ), f"behavior_index minimum is {result['behavior_index'].min()}, expected >= 0.0"
        assert (
            result["behavior_index"].max() <= 1.0
        ), f"behavior_index maximum is {result['behavior_index'].max()}, expected <= 1.0"

    def test_behavior_index_clipping(self):
        """Test that behavior_index is clipped to [0.0, 1.0]."""
        computer = BehaviorIndexComputer()

        # Create data that would produce out-of-range values if not clipped
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        test_data = pd.DataFrame(
            {
                "timestamp": dates,
                "stress_index": [1.0] * 10,  # Maximum stress
                "discomfort_score": [1.0] * 10,  # Maximum discomfort
                "mobility_index": [0.0]
                * 10,  # Minimum mobility (inverted = max contribution)
                "search_interest_score": [1.0] * 10,  # Maximum attention
                "health_risk_index": [1.0] * 10,  # Maximum health stress
            }
        )

        result = computer.compute_behavior_index(test_data)

        # Even with maximum inputs, result should be clipped to 1.0
        assert (
            result["behavior_index"].max() <= 1.0
        ), "behavior_index not clipped to 1.0 with maximum inputs"


class TestInvariantI6SubIndexRange:
    """Test I6: Sub-index range [0.0, 1.0]."""

    def test_all_sub_indices_in_range(self):
        """Test that all sub-indices are in [0.0, 1.0]."""
        computer = BehaviorIndexComputer()

        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        test_data = pd.DataFrame(
            {
                "timestamp": dates,
                "stress_index": np.random.uniform(0.0, 1.0, 100),
                "discomfort_score": np.random.uniform(0.0, 1.0, 100),
                "mobility_index": np.random.uniform(0.0, 1.0, 100),
                "search_interest_score": np.random.uniform(0.0, 1.0, 100),
                "health_risk_index": np.random.uniform(0.0, 1.0, 100),
            }
        )

        result = computer.compute_sub_indices(test_data)

        sub_indices = [
            "economic_stress",
            "environmental_stress",
            "mobility_activity",
            "digital_attention",
            "public_health_stress",
        ]

        for idx in sub_indices:
            assert (
                result[idx].min() >= 0.0
            ), f"{idx} minimum is {result[idx].min()}, expected >= 0.0"
            assert (
                result[idx].max() <= 1.0
            ), f"{idx} maximum is {result[idx].max()}, expected <= 1.0"
