# SPDX-License-Identifier: PROPRIETARY
"""Tests for narrative intelligence layer."""

import pandas as pd

from app.core.behavior_index import BehaviorIndexComputer
from app.core.narrative import (
    compose_narrative,
    generate_assessment_summary,
    generate_confidence_disclaimer,
    generate_emerging_risks,
    generate_persistent_risks,
    generate_primary_drivers,
    generate_stabilizing_factors,
)
from app.core.invariants import get_registry


class TestPrimaryDrivers:
    """Test primary driver generation."""

    def test_primary_drivers_ranked_by_score(self):
        """Test that primary drivers are ranked by driver score."""
        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "market_volatility",
                        "label": "Market Volatility",
                        "contribution": 0.2,
                        "signal_strength": 0.15,
                        "confidence": 0.8,
                        "persistence": 30,
                    },
                    {
                        "id": "consumer_sentiment",
                        "label": "Consumer Sentiment",
                        "contribution": 0.1,
                        "signal_strength": 0.08,
                        "confidence": 0.7,
                        "persistence": 20,
                    },
                ],
            }
        }

        drivers = generate_primary_drivers(subindex_details, top_n=2)

        assert len(drivers) == 2
        assert drivers[0]["driver_score"] >= drivers[1]["driver_score"]
        assert drivers[0]["factor_id"] == "market_volatility"

    def test_primary_drivers_filters_low_contribution(self):
        """Test that factors with low contribution are filtered out."""
        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "market_volatility",
                        "label": "Market Volatility",
                        "contribution": 0.2,
                        "signal_strength": 0.15,
                        "confidence": 0.8,
                        "persistence": 30,
                    },
                    {
                        "id": "noise_factor",
                        "label": "Noise Factor",
                        "contribution": 0.005,  # Below threshold
                        "signal_strength": 0.001,
                        "confidence": 0.5,
                        "persistence": 1,
                    },
                ],
            }
        }

        drivers = generate_primary_drivers(subindex_details, top_n=5)

        assert len(drivers) == 1
        assert drivers[0]["factor_id"] == "market_volatility"

    def test_primary_drivers_reconciliation(self):
        """Test INV-N01: Narrative drivers reconcile to top factors."""
        registry = get_registry()

        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "market_volatility",
                        "label": "Market Volatility",
                        "contribution": 0.2,
                        "signal_strength": 0.15,
                        "confidence": 0.8,
                        "persistence": 30,
                    },
                ],
            }
        }

        drivers = generate_primary_drivers(subindex_details, top_n=3)
        top_factors = subindex_details["economic_stress"]["components"]

        is_valid, _ = registry.check("INV-N01", drivers, top_factors)
        assert is_valid


class TestStabilizingFactors:
    """Test stabilizing factor generation."""

    def test_stabilizing_factors_activity_index(self):
        """Test that activity indices with positive contribution are stabilizing."""
        subindex_details = {
            "mobility_activity": {
                "value": 0.7,
                "components": [
                    {
                        "id": "mobility_index",
                        "label": "Mobility Index",
                        "contribution": 0.15,
                        "signal_strength": 0.12,
                        "confidence": 0.8,
                        "trend": "stable",
                    },
                ],
            }
        }

        stabilizers = generate_stabilizing_factors(subindex_details, behavior_index=0.4)

        assert len(stabilizers) == 1
        assert stabilizers[0]["factor_id"] == "mobility_index"

    def test_stabilizing_factors_improving_trend(self):
        """Test that factors with improving trend are stabilizing."""
        subindex_details = {
            "economic_stress": {
                "value": 0.3,
                "components": [
                    {
                        "id": "market_volatility",
                        "label": "Market Volatility",
                        "contribution": 0.1,
                        "signal_strength": 0.08,
                        "confidence": 0.7,
                        "trend": "improving",
                    },
                ],
            }
        }

        stabilizers = generate_stabilizing_factors(subindex_details, behavior_index=0.4)

        assert len(stabilizers) == 1
        assert stabilizers[0]["trend"] == "improving"


class TestEmergingRisks:
    """Test emerging risk generation."""

    def test_emerging_risks_high_volatility_low_persistence(self):
        """Test that high volatility, low persistence factors are emerging risks."""
        subindex_details = {
            "digital_attention": {
                "value": 0.6,
                "components": [
                    {
                        "id": "search_interest",
                        "label": "Search Interest",
                        "contribution": 0.1,
                        "volatility_classification": "high",
                        "persistence": 5,
                        "trend": "worsening",
                        "signal_strength": 0.05,
                    },
                ],
            }
        }

        emerging = generate_emerging_risks(subindex_details)

        assert len(emerging) == 1
        assert emerging[0]["factor_id"] == "search_interest"
        assert emerging[0]["volatility_classification"] == "high"
        assert emerging[0]["persistence"] < 14

    def test_emerging_risks_filters_low_signal(self):
        """Test that low signal strength factors are filtered out."""
        subindex_details = {
            "digital_attention": {
                "value": 0.6,
                "components": [
                    {
                        "id": "noise",
                        "label": "Noise",
                        "contribution": 0.01,
                        "volatility_classification": "high",
                        "persistence": 3,
                        "trend": "worsening",
                        "signal_strength": 0.001,  # Below threshold
                    },
                ],
            }
        }

        emerging = generate_emerging_risks(subindex_details)

        assert len(emerging) == 0


class TestPersistentRisks:
    """Test persistent risk generation."""

    def test_persistent_risks_high_persistence(self):
        """Test that high persistence factors are persistent risks."""
        subindex_details = {
            "environmental_stress": {
                "value": 0.6,
                "components": [
                    {
                        "id": "weather_discomfort",
                        "label": "Weather Discomfort",
                        "contribution": 0.15,
                        "persistence": 45,
                        "trend": "stable",
                        "signal_strength": 0.12,
                    },
                ],
            }
        }

        persistent = generate_persistent_risks(
            subindex_details, min_persistence_days=30
        )

        assert len(persistent) == 1
        assert persistent[0]["factor_id"] == "weather_discomfort"
        assert persistent[0]["persistence"] >= 30

    def test_persistent_risks_sorted_by_persistence(self):
        """Test that persistent risks are sorted by persistence."""
        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "factor_30",
                        "label": "Factor 30",
                        "contribution": 0.1,
                        "persistence": 30,
                        "trend": "stable",
                        "signal_strength": 0.08,
                    },
                    {
                        "id": "factor_60",
                        "label": "Factor 60",
                        "contribution": 0.15,
                        "persistence": 60,
                        "trend": "stable",
                        "signal_strength": 0.12,
                    },
                ],
            }
        }

        persistent = generate_persistent_risks(
            subindex_details, min_persistence_days=30
        )

        assert len(persistent) == 2
        assert persistent[0]["persistence"] >= persistent[1]["persistence"]


class TestConfidenceDisclaimer:
    """Test confidence disclaimer generation."""

    def test_confidence_disclaimer_high_confidence(self):
        """Test disclaimer for high confidence factors."""
        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "market_volatility",
                        "label": "Market Volatility",
                        "contribution": 0.2,
                        "confidence": 0.85,
                        "volatility_classification": "low",
                    },
                ],
            }
        }

        disclaimer = generate_confidence_disclaimer(
            subindex_details, behavior_index=0.5
        )

        assert "high" in disclaimer.lower() or "moderate" in disclaimer.lower()

    def test_confidence_disclaimer_missing_data(self):
        """Test disclaimer mentions missing data when present."""
        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "market_volatility",
                        "label": "Market Volatility",
                        "contribution": 0.2,
                        # No confidence field (missing data)
                    },
                ],
            }
        }

        disclaimer = generate_confidence_disclaimer(
            subindex_details, behavior_index=0.5
        )

        # Should handle missing data gracefully
        assert isinstance(disclaimer, str)
        assert len(disclaimer) > 0


class TestAssessmentSummary:
    """Test assessment summary generation."""

    def test_assessment_summary_includes_level(self):
        """Test that summary includes behavior index level."""
        behavior_index = 0.4
        primary_drivers = [
            {
                "factor_label": "Market Volatility",
                "contribution": 0.2,
            }
        ]
        stabilizing_factors = []
        emerging_risks = []
        persistent_risks = []
        confidence_disclaimer = "Overall confidence in this assessment is high."

        summary = generate_assessment_summary(
            behavior_index,
            primary_drivers,
            stabilizing_factors,
            emerging_risks,
            persistent_risks,
            confidence_disclaimer,
        )

        assert (
            "moderate disruption" in summary.lower() or "disruption" in summary.lower()
        )

    def test_assessment_summary_includes_drivers(self):
        """Test that summary includes primary drivers."""
        behavior_index = 0.5
        primary_drivers = [
            {
                "factor_label": "Market Volatility",
                "contribution": 0.2,
            }
        ]
        stabilizing_factors = []
        emerging_risks = []
        persistent_risks = []
        confidence_disclaimer = "Overall confidence in this assessment is high."

        summary = generate_assessment_summary(
            behavior_index,
            primary_drivers,
            stabilizing_factors,
            emerging_risks,
            persistent_risks,
            confidence_disclaimer,
        )

        assert "market volatility" in summary.lower()

    def test_assessment_summary_includes_stabilizers(self):
        """Test that summary includes stabilizing factors."""
        behavior_index = 0.5
        primary_drivers = []
        stabilizing_factors = [
            {
                "factor_label": "Mobility Index",
                "contribution": 0.15,
            }
        ]
        emerging_risks = []
        persistent_risks = []
        confidence_disclaimer = "Overall confidence in this assessment is high."

        summary = generate_assessment_summary(
            behavior_index,
            primary_drivers,
            stabilizing_factors,
            emerging_risks,
            persistent_risks,
            confidence_disclaimer,
        )

        assert "mobility" in summary.lower() or "dampening" in summary.lower()


class TestNarrativeDeterminism:
    """Test narrative determinism."""

    def test_narrative_deterministic(self):
        """Test that narrative generation is deterministic."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [0.6] * 10,
                "discomfort_score": [0.7] * 10,
                "mobility_index": [0.5] * 10,
                "search_interest_score": [0.5] * 10,
                "health_risk_index": [0.5] * 10,
            }
        )

        df = computer.compute_behavior_index(harmonized)
        details = computer.get_subindex_details(df, 9, include_quality_metrics=True)

        narrative1 = compose_narrative(0.5, details)
        narrative2 = compose_narrative(0.5, details)

        assert narrative1["assessment_summary"] == narrative2["assessment_summary"]
        assert len(narrative1["primary_drivers"]) == len(narrative2["primary_drivers"])

    def test_narrative_ordering_deterministic(self):
        """Test INV-N02: Narrative ordering is deterministic."""
        registry = get_registry()

        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "factor1",
                        "label": "Factor 1",
                        "contribution": 0.2,
                        "signal_strength": 0.15,
                        "confidence": 0.8,
                        "persistence": 30,
                    },
                    {
                        "id": "factor2",
                        "label": "Factor 2",
                        "contribution": 0.1,
                        "signal_strength": 0.08,
                        "confidence": 0.7,
                        "persistence": 20,
                    },
                ],
            }
        }

        drivers = generate_primary_drivers(subindex_details, top_n=5)

        is_valid, _ = registry.check("INV-N02", drivers)
        assert is_valid


class TestNoSemanticDrift:
    """Test that narrative doesn't introduce semantic drift."""

    def test_global_index_unchanged_with_narrative(self):
        """Test that global index is unchanged when narrative is generated."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [0.6] * 10,
                "discomfort_score": [0.7] * 10,
                "mobility_index": [0.5] * 10,
                "search_interest_score": [0.5] * 10,
                "health_risk_index": [0.5] * 10,
            }
        )

        df_before = computer.compute_behavior_index(harmonized)
        global_before = float(df_before["behavior_index"].iloc[9])

        details = computer.get_subindex_details(
            df_before, 9, include_quality_metrics=True
        )
        narrative = compose_narrative(global_before, details)

        df_after = computer.compute_behavior_index(harmonized)
        global_after = float(df_after["behavior_index"].iloc[9])

        assert abs(global_before - global_after) < 1e-10
        assert narrative is not None  # Narrative generated successfully

    def test_sub_indices_unchanged_with_narrative(self):
        """Test that sub-indices are unchanged when narrative is generated."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [0.6] * 10,
                "discomfort_score": [0.7] * 10,
                "mobility_index": [0.5] * 10,
                "search_interest_score": [0.5] * 10,
                "health_risk_index": [0.5] * 10,
            }
        )

        df = computer.compute_sub_indices(harmonized)
        economic_before = float(df["economic_stress"].iloc[9])

        details = computer.get_subindex_details(df, 9, include_quality_metrics=True)
        narrative = compose_narrative(0.5, details)

        economic_after = float(df["economic_stress"].iloc[9])

        assert abs(economic_before - economic_after) < 1e-10
        assert narrative is not None


class TestNarrativeDirectionality:
    """Test narrative directionality consistency."""

    def test_narrative_directionality_consistency(self):
        """Test INV-N03: Narrative must not contradict numerical directionality."""
        registry = get_registry()

        summary = "The region shows moderate disruption driven primarily by market volatility."
        behavior_index = 0.4

        is_valid, _ = registry.check("INV-N03", summary, behavior_index)
        assert is_valid

    def test_narrative_contradicts_high_index(self):
        """Test that narrative mentioning low disruption contradicts high index."""
        registry = get_registry()

        summary = "The region shows low disruption."
        behavior_index = 0.8

        is_valid, error_msg = registry.check("INV-N03", summary, behavior_index)
        assert not is_valid
        assert "low disruption" in error_msg.lower()


class TestBackwardCompatibility:
    """Test backward compatibility."""

    def test_narrative_optional(self):
        """Test that narrative is optional and doesn't break old consumers."""
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
        details = computer.get_subindex_details(df, 0, include_quality_metrics=False)

        # Old consumers can still access value and components without narrative
        assert "economic_stress" in details
        assert "value" in details["economic_stress"]
        assert "components" in details["economic_stress"]

        # Narrative can be generated separately if needed
        narrative = compose_narrative(0.5, details)
        assert narrative is not None
        assert "assessment_summary" in narrative


class TestNarrativeComposition:
    """Test complete narrative composition."""

    def test_compose_narrative_complete(self):
        """Test that compose_narrative returns all required fields."""
        computer = BehaviorIndexComputer()

        harmonized = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=10),
                "stress_index": [0.6] * 10,
                "discomfort_score": [0.7] * 10,
                "mobility_index": [0.5] * 10,
                "search_interest_score": [0.5] * 10,
                "health_risk_index": [0.5] * 10,
            }
        )

        df = computer.compute_behavior_index(harmonized)
        details = computer.get_subindex_details(df, 9, include_quality_metrics=True)

        narrative = compose_narrative(0.5, details)

        assert "assessment_summary" in narrative
        assert "primary_drivers" in narrative
        assert "stabilizing_factors" in narrative
        assert "emerging_risks" in narrative
        assert "persistent_risks" in narrative
        assert "confidence_disclaimer" in narrative
        assert "metadata" in narrative

        assert isinstance(narrative["assessment_summary"], str)
        assert isinstance(narrative["primary_drivers"], list)
        assert isinstance(narrative["stabilizing_factors"], list)
        assert isinstance(narrative["emerging_risks"], list)
        assert isinstance(narrative["persistent_risks"], list)
        assert isinstance(narrative["confidence_disclaimer"], str)
        assert "generated_at" in narrative["metadata"]
        assert "version" in narrative["metadata"]
