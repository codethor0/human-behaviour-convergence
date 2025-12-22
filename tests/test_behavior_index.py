# SPDX-License-Identifier: PROPRIETARY
"""Tests for Behavior Index computation."""
import pandas as pd

from app.core.behavior_index import BehaviorIndexComputer


class TestBehaviorIndexComputer:
    """Test Behavior Index computation."""

    def test_compute_behavior_index_produces_sub_indices(self):
        """Test that behavior index computation produces expected sub-indices."""
        computer = BehaviorIndexComputer()
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=5, freq="D"),
                "stress_index": [0.3, 0.5, 0.7, 0.4, 0.6],
                "discomfort_score": [0.2, 0.4, 0.6, 0.3, 0.5],
                "mobility_index": [0.8, 0.6, 0.4, 0.7, 0.5],
                "search_interest_score": [0.5, 0.6, 0.7, 0.4, 0.5],
                "health_risk_index": [0.3, 0.4, 0.5, 0.2, 0.4],
            }
        )

        result = computer.compute_behavior_index(df)

        # Verify sub-indices are present in the result
        assert "economic_stress" in result.columns
        assert "environmental_stress" in result.columns
        assert "mobility_activity" in result.columns
        assert "digital_attention" in result.columns
        assert "public_health_stress" in result.columns

        # Verify sub-indices are in valid range
        for col in [
            "economic_stress",
            "environmental_stress",
            "mobility_activity",
            "digital_attention",
            "public_health_stress",
        ]:
            assert all(result[col] >= 0.0)
            assert all(result[col] <= 1.0)

    def test_compute_sub_indices_with_missing_data(self):
        """Test sub-index computation with missing data defaults to 0.5."""
        computer = BehaviorIndexComputer()
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=3, freq="D"),
                "stress_index": [0.3, None, 0.7],
                "discomfort_score": [0.2, 0.4, None],
            }
        )

        result = computer.compute_sub_indices(df)

        assert result["economic_stress"].iloc[0] == 0.3
        assert result["economic_stress"].iloc[1] == 0.5  # Default for missing
        assert result["economic_stress"].iloc[2] == 0.7

        assert result["environmental_stress"].iloc[0] == 0.2
        assert result["environmental_stress"].iloc[1] == 0.4
        assert result["environmental_stress"].iloc[2] == 0.5  # Default for missing

        # Missing indices default to 0.5
        assert all(result["mobility_activity"] == 0.5)
        assert all(result["digital_attention"] == 0.5)
        assert all(result["public_health_stress"] == 0.5)

    def test_compute_behavior_index_basic(self):
        """Test basic behavior index computation."""
        computer = BehaviorIndexComputer()
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=3, freq="D"),
                "stress_index": [0.4, 0.5, 0.6],
                "discomfort_score": [0.3, 0.4, 0.5],
                "mobility_index": [0.7, 0.6, 0.5],
                "search_interest_score": [0.5, 0.5, 0.5],
                "health_risk_index": [0.3, 0.4, 0.5],
            }
        )

        result = computer.compute_behavior_index(df)

        assert "behavior_index" in result.columns
        assert all(result["behavior_index"] >= 0.0)
        assert all(result["behavior_index"] <= 1.0)

        # Verify sub-indices are present
        assert "economic_stress" in result.columns
        assert "environmental_stress" in result.columns

    def test_compute_behavior_index_mobility_inversion(self):
        """Test that mobility activity is inverted in behavior index."""
        computer = BehaviorIndexComputer()
        # High mobility (0.9) should reduce behavior_index
        # Low mobility (0.1) should increase behavior_index
        df_high_mobility = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=1, freq="D"),
                "stress_index": [0.5],
                "discomfort_score": [0.5],
                "mobility_index": [0.9],  # High activity
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df_low_mobility = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=1, freq="D"),
                "stress_index": [0.5],
                "discomfort_score": [0.5],
                "mobility_index": [0.1],  # Low activity
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        result_high = computer.compute_behavior_index(df_high_mobility)
        result_low = computer.compute_behavior_index(df_low_mobility)

        # Lower mobility should result in higher behavior_index (more disruption)
        assert (
            result_low["behavior_index"].iloc[0] > result_high["behavior_index"].iloc[0]
        )

    def test_compute_behavior_index_weights_normalization(self):
        """Test that weights are normalized if they don't sum to 1.0."""
        # Weights sum to 0.5, should be normalized
        computer = BehaviorIndexComputer(
            economic_weight=0.1,
            environmental_weight=0.1,
            mobility_weight=0.1,
            digital_attention_weight=0.1,
            health_weight=0.1,
        )

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=1, freq="D"),
                "stress_index": [0.5],
                "discomfort_score": [0.5],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        result = computer.compute_behavior_index(df)
        # Should still compute successfully (weights normalized internally)
        assert "behavior_index" in result.columns

    def test_get_sub_indices_dict(self):
        """Test extraction of sub-indices as dictionary."""
        computer = BehaviorIndexComputer()
        row = pd.Series(
            {
                "economic_stress": 0.4,
                "environmental_stress": 0.3,
                "mobility_activity": 0.7,
                "digital_attention": 0.5,
                "public_health_stress": 0.6,
            }
        )

        sub_indices = computer.get_sub_indices_dict(row)

        # Verify all expected sub-indices are present
        assert "economic_stress" in sub_indices
        assert "environmental_stress" in sub_indices
        assert "mobility_activity" in sub_indices
        assert "digital_attention" in sub_indices
        assert "public_health_stress" in sub_indices

        # Verify values are in valid range
        for key, value in sub_indices.items():
            assert 0.0 <= value <= 1.0

    def test_get_contribution_analysis(self):
        """Test contribution analysis computation."""
        computer = BehaviorIndexComputer()
        row = pd.Series(
            {
                "behavior_index": 0.5,
                "economic_stress": 0.4,
                "environmental_stress": 0.3,
                "mobility_activity": 0.7,
                "digital_attention": 0.5,
                "public_health_stress": 0.6,
            }
        )

        contributions = computer.get_contribution_analysis(row)

        assert "economic_stress" in contributions
        assert "environmental_stress" in contributions
        assert "mobility_activity" in contributions
        assert "digital_attention" in contributions
        assert "public_health_stress" in contributions

        # Each contribution should be a dict with value, weight, and contribution
        for key, contrib_dict in contributions.items():
            assert isinstance(contrib_dict, dict)
            assert "value" in contrib_dict
            assert "weight" in contrib_dict
            assert "contribution" in contrib_dict
            assert contrib_dict["contribution"] >= 0

    def test_behavior_index_clipping(self):
        """Test that behavior index is clipped to [0.0, 1.0]."""
        computer = BehaviorIndexComputer()
        # Create extreme values that might push index outside [0, 1]
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=1, freq="D"),
                "stress_index": [1.0],  # Maximum stress
                "discomfort_score": [1.0],  # Maximum discomfort
                "mobility_index": [0.0],  # Minimum activity
                "search_interest_score": [1.0],  # Maximum attention
                "health_risk_index": [1.0],  # Maximum health stress
            }
        )

        result = computer.compute_behavior_index(df)

        assert result["behavior_index"].iloc[0] <= 1.0
        assert result["behavior_index"].iloc[0] >= 0.0
