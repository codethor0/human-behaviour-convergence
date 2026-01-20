# SPDX-License-Identifier: PROPRIETARY
"""Tests for hierarchical contribution expansion (factor-level explainability)."""
import math

import pandas as pd

from app.core.behavior_index import BehaviorIndexComputer


class TestFactorReconciliation:
    """Test factor-level reconciliation (Factor → Sub-Index)."""

    def test_economic_stress_factors_reconcile(self):
        """Test that economic stress factors sum to sub-index value."""
        computer = BehaviorIndexComputer()

        # Create harmonized data with multiple economic components
        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.6],  # Market volatility
                "fred_consumer_sentiment": [0.4],
                "fred_unemployment": [0.5],
                "fred_jobless_claims": [0.3],
                "discomfort_score": [0.5],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)
        details = computer.get_subindex_details(df, 0)

        economic_details = details["economic_stress"]
        factor_sum = sum(f["contribution"] for f in economic_details["components"])
        sub_index_value = economic_details["value"]

        # Factors should reconcile to sub-index (± tolerance)
        assert (
            abs(factor_sum - sub_index_value) <= 0.01
        ), f"Factor sum {factor_sum} does not reconcile with sub-index {sub_index_value}"
        assert economic_details["reconciliation"][
            "valid"
        ], "Reconciliation should be valid"

    def test_environmental_stress_factors_reconcile(self):
        """Test that environmental stress factors sum to sub-index value."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.5],
                "discomfort_score": [0.7],
                "usgs_earthquake_intensity": [0.3],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)
        details = computer.get_subindex_details(df, 0)

        environmental_details = details["environmental_stress"]
        factor_sum = sum(f["contribution"] for f in environmental_details["components"])
        sub_index_value = environmental_details["value"]

        assert abs(factor_sum - sub_index_value) <= 0.01
        assert environmental_details["reconciliation"]["valid"]

    def test_mobility_activity_factors_reconcile(self):
        """Test that mobility activity factors sum to sub-index value."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.5],
                "discomfort_score": [0.5],
                "mobility_index": [0.8],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)
        details = computer.get_subindex_details(df, 0)

        mobility_details = details["mobility_activity"]
        factor_sum = sum(f["contribution"] for f in mobility_details["components"])
        sub_index_value = mobility_details["value"]

        assert abs(factor_sum - sub_index_value) <= 0.01
        assert mobility_details["reconciliation"]["valid"]

    def test_digital_attention_factors_reconcile(self):
        """Test that digital attention factors sum to sub-index value."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.5],
                "discomfort_score": [0.5],
                "mobility_index": [0.5],
                "search_interest_score": [0.6],
                "gdelt_tone_score": [0.4],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)
        details = computer.get_subindex_details(df, 0)

        digital_details = details["digital_attention"]
        factor_sum = sum(f["contribution"] for f in digital_details["components"])
        sub_index_value = digital_details["value"]

        assert abs(factor_sum - sub_index_value) <= 0.01
        assert digital_details["reconciliation"]["valid"]

    def test_public_health_stress_factors_reconcile(self):
        """Test that public health stress factors sum to sub-index value."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.5],
                "discomfort_score": [0.5],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.7],
                "owid_health_stress": [0.3],
            }
        )

        df = computer.compute_sub_indices(harmonized)
        details = computer.get_subindex_details(df, 0)

        health_details = details["public_health_stress"]
        factor_sum = sum(f["contribution"] for f in health_details["components"])
        sub_index_value = health_details["value"]

        assert abs(factor_sum - sub_index_value) <= 0.01
        assert health_details["reconciliation"]["valid"]


class TestGlobalStability:
    """Test that global outputs remain unchanged after factor expansion."""

    def test_global_index_unchanged(self):
        """Test that global behavior index is identical before/after factor expansion."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.6],
                "fred_consumer_sentiment": [0.4],
                "discomfort_score": [0.7],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_behavior_index(harmonized)
        global_index_before = float(df["behavior_index"].iloc[0])

        # Get details (this should not change the global index)
        computer.get_subindex_details(df, 0)

        # Recompute to ensure no side effects
        df_after = computer.compute_behavior_index(harmonized)
        global_index_after = float(df_after["behavior_index"].iloc[0])

        assert (
            abs(global_index_before - global_index_after) < 1e-10
        ), "Global index should be unchanged"

    def test_sub_indices_unchanged(self):
        """Test that sub-index values are identical before/after factor expansion."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.6],
                "discomfort_score": [0.7],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)
        economic_before = float(df["economic_stress"].iloc[0])
        environmental_before = float(df["environmental_stress"].iloc[0])

        # Get details
        details = computer.get_subindex_details(df, 0)

        # Verify details match original values
        assert abs(details["economic_stress"]["value"] - economic_before) < 1e-10
        assert (
            abs(details["environmental_stress"]["value"] - environmental_before) < 1e-10
        )


class TestSemanticDrift:
    """Test that explanations are expanded, not altered."""

    def test_explanations_expanded_not_altered(self):
        """Test that factor expansion adds detail without changing meaning."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.6],
                "fred_consumer_sentiment": [0.4],
                "discomfort_score": [0.7],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_behavior_index(harmonized)
        details = computer.get_subindex_details(df, 0)

        # Verify all sub-indices have factor breakdowns
        for sub_index_name in [
            "economic_stress",
            "environmental_stress",
            "mobility_activity",
            "digital_attention",
            "public_health_stress",
        ]:
            assert sub_index_name in details
            assert "components" in details[sub_index_name]
            assert len(details[sub_index_name]["components"]) > 0
            assert "reconciliation" in details[sub_index_name]

            # Verify each factor has required fields
            for factor in details[sub_index_name]["components"]:
                assert "id" in factor
                assert "value" in factor
                assert "weight" in factor
                assert "contribution" in factor
                assert "source" in factor

                # Verify contribution is calculated correctly
                expected_contribution = factor["value"] * factor["weight"]
                assert abs(factor["contribution"] - expected_contribution) < 1e-10


class TestBackwardCompatibility:
    """Test that existing consumers continue to work."""

    def test_old_trace_consumers_still_work(self):
        """Test that trace objects without factor contributions still work."""
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

        df = computer.compute_behavior_index(harmonized)
        details = computer.get_subindex_details(df, 0)

        # Old consumers can access value and components
        economic = details["economic_stress"]
        assert "value" in economic
        assert "components" in economic

        # Components can be accessed without contribution field (backward compatible)
        for component in economic["components"]:
            assert "id" in component
            assert "value" in component
            assert "weight" in component
            # Contribution is optional for backward compatibility
            if "contribution" in component:
                assert isinstance(component["contribution"], (int, float))


class TestOrderIndependence:
    """Test that factor ordering is deterministic."""

    def test_factor_ordering_deterministic(self):
        """Test that factors are in deterministic order."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.6],
                "fred_consumer_sentiment": [0.4],
                "fred_unemployment": [0.5],
                "fred_jobless_claims": [0.3],
                "discomfort_score": [0.5],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)

        # Get details multiple times
        details1 = computer.get_subindex_details(df, 0)
        details2 = computer.get_subindex_details(df, 0)

        # Factor IDs should be in the same order
        factors1 = [f["id"] for f in details1["economic_stress"]["components"]]
        factors2 = [f["id"] for f in details2["economic_stress"]["components"]]

        assert factors1 == factors2, "Factor ordering should be deterministic"


class TestMissingFactorSafety:
    """Test that missing factors are handled safely."""

    def test_missing_factor_neutral_contribution(self):
        """Test that missing factors result in neutral contribution, not crash."""
        computer = BehaviorIndexComputer()

        # Create data with missing FRED indicators
        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.6],  # Only market volatility
                "discomfort_score": [0.5],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)
        details = computer.get_subindex_details(df, 0)

        # Should still have economic_stress with at least one factor
        assert "economic_stress" in details
        assert len(details["economic_stress"]["components"]) > 0

        # All factors should have valid contributions
        for factor in details["economic_stress"]["components"]:
            assert not math.isnan(factor["contribution"])
            assert not math.isinf(factor["contribution"])
            assert 0.0 <= factor["contribution"] <= 1.0

    def test_missing_data_no_crash(self):
        """Test that missing data doesn't cause crashes."""
        computer = BehaviorIndexComputer()

        # Minimal data
        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.5],
            }
        )

        df = computer.compute_sub_indices(harmonized)

        # Should not crash
        details = computer.get_subindex_details(df, 0)

        # Should have at least economic_stress
        assert "economic_stress" in details
        assert details["economic_stress"]["reconciliation"]["valid"]


class TestHierarchicalReconciliation:
    """Test hierarchical reconciliation (Factor → Sub-Index → Global)."""

    def test_hierarchical_reconciliation_complete(self):
        """Test that factors reconcile transitively to global index."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=1),
                "stress_index": [0.6],
                "fred_consumer_sentiment": [0.4],
                "discomfort_score": [0.7],
                "mobility_index": [0.5],
                "search_interest_score": [0.5],
                "health_risk_index": [0.5],
            }
        )

        df = computer.compute_behavior_index(harmonized)
        row = df.iloc[0]

        # Get factor details
        details = computer.get_subindex_details(df, 0)

        # Get contribution analysis (Sub-Index → Global)
        contributions = computer.get_contribution_analysis(row)

        # Verify Factor → Sub-Index reconciliation
        for sub_index_name, sub_index_details in details.items():
            if sub_index_name in contributions:
                # Skip if components don't have contribution field (backward compatibility)
                if not sub_index_details["components"]:
                    continue
                if "contribution" not in sub_index_details["components"][0]:
                    continue

                factor_sum = sum(
                    f["contribution"] for f in sub_index_details["components"]
                )
                sub_index_value = sub_index_details["value"]
                assert (
                    abs(factor_sum - sub_index_value) <= 0.01
                ), f"{sub_index_name}: factors {factor_sum} != sub-index {sub_index_value}"

        # Verify Sub-Index → Global reconciliation (already tested elsewhere)
        global_index = float(row["behavior_index"])
        contribution_sum = sum(
            contrib["contribution"] for contrib in contributions.values()
        )
        assert (
            abs(contribution_sum - global_index) <= 0.01
        ), f"Sub-indices {contribution_sum} != global index {global_index}"
