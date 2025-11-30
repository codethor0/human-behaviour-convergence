# SPDX-License-Identifier: PROPRIETARY
"""Tests for subindex component details extraction."""
import pandas as pd

from app.core.behavior_index import BehaviorIndexComputer


class TestSubIndexDetails:
    """Test suite for subindex component details."""

    def test_get_subindex_details_economic(self):
        """Test extraction of economic stress component details."""
        computer = BehaviorIndexComputer()

        # Create a DataFrame with economic components
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=5, freq="D"),
                "stress_index": [0.6, 0.7, 0.5, 0.8, 0.6],
                "fred_consumer_sentiment": [0.4, 0.5, 0.3, 0.6, 0.4],
                "fred_unemployment": [0.3, 0.4, 0.2, 0.5, 0.3],
                "discomfort_score": [0.2, 0.3, 0.1, 0.4, 0.2],
                "mobility_index": [0.7, 0.8, 0.6, 0.9, 0.7],
                "search_interest_score": [0.4, 0.5, 0.3, 0.6, 0.4],
                "health_risk_index": [0.3, 0.4, 0.2, 0.5, 0.3],
            }
        )

        # Compute behavior index (this sets component metadata in attrs)
        df = computer.compute_behavior_index(df)

        # Extract details for first row
        details = computer.get_subindex_details(df, 0)

        assert "economic_stress" in details
        assert details["economic_stress"]["value"] > 0
        assert len(details["economic_stress"]["components"]) >= 1
        assert "market_volatility" in [
            c["id"] for c in details["economic_stress"]["components"]
        ]

        # Check component structure
        for comp in details["economic_stress"]["components"]:
            assert "id" in comp
            assert "label" in comp
            assert "value" in comp
            assert "weight" in comp
            assert "source" in comp
            assert 0 <= comp["value"] <= 1
            assert 0 <= comp["weight"] <= 1

    def test_get_subindex_details_all_subindices(self):
        """Test extraction of all sub-index component details."""
        computer = BehaviorIndexComputer()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=3, freq="D"),
                "stress_index": [0.5, 0.6, 0.5],
                "discomfort_score": [0.3, 0.4, 0.3],
                "mobility_index": [0.7, 0.8, 0.7],
                "search_interest_score": [0.4, 0.5, 0.4],
                "health_risk_index": [0.3, 0.4, 0.3],
            }
        )

        df = computer.compute_behavior_index(df)
        details = computer.get_subindex_details(df, 0)

        # Check all sub-indices have details
        assert "economic_stress" in details
        assert "environmental_stress" in details
        assert "mobility_activity" in details
        assert "digital_attention" in details
        assert "public_health_stress" in details

        # Check each has components
        for sub_idx in details.values():
            assert "value" in sub_idx
            assert "components" in sub_idx
            assert len(sub_idx["components"]) > 0

    def test_get_subindex_details_component_consistency(self):
        """Test that component values are consistent with sub-index values."""
        computer = BehaviorIndexComputer()

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2025-01-01", periods=3, freq="D"),
                "stress_index": [0.5, 0.6, 0.5],
                "discomfort_score": [0.3, 0.4, 0.3],
                "mobility_index": [0.7, 0.8, 0.7],
                "search_interest_score": [0.4, 0.5, 0.4],
                "health_risk_index": [0.3, 0.4, 0.3],
            }
        )

        df = computer.compute_behavior_index(df)
        details = computer.get_subindex_details(df, 0)

        # Environmental stress should match discomfort_score
        env_value = details["environmental_stress"]["value"]
        env_component = details["environmental_stress"]["components"][0]["value"]
        assert (
            abs(env_value - env_component) < 0.01
        )  # Should match within float tolerance
