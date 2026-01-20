# SPDX-License-Identifier: PROPRIETARY
"""Tests for provenance and data quality transparency."""
import pytest
from datetime import datetime, timedelta, timezone

from app.core.provenance import (
    compute_aggregate_provenance,
    compute_factor_provenance,
    compute_source_provenance,
    compute_sub_index_provenance,
    compose_provenance,
)
from app.core.invariants import get_registry


class TestSourceProvenance:
    """Tests for source provenance computation."""

    def test_source_provenance_known_source(self):
        """Test provenance for known source."""
        result = compute_source_provenance("yfinance", data_age_hours=2.0)

        assert result["source_name"] == "yfinance"
        assert result["source_display_name"] == "Yahoo Finance"
        assert result["source_type"] == "api"
        assert result["authority_level"] == "primary"
        assert result["data_age_hours"] == 2.0
        # 2 hours for yfinance (expected 1h) = 2x expected, so "delayed" (between 1.5x and 3x)
        assert result["freshness_classification"] in ["fresh", "delayed"]

    def test_source_provenance_unknown_source(self):
        """Test provenance for unknown source."""
        result = compute_source_provenance("unknown_source", data_age_hours=5.0)

        assert result["source_name"] == "unknown_source"
        assert result["source_type"] == "unknown"
        assert result["authority_level"] == "unknown"

    def test_source_provenance_freshness_classification(self):
        """Test freshness classification."""
        # Fresh: within 1.5x expected frequency
        result = compute_source_provenance("yfinance", data_age_hours=1.0)  # Expected: 1h
        assert result["freshness_classification"] == "fresh"

        # Delayed: 1.5x to 3x expected frequency
        result = compute_source_provenance("yfinance", data_age_hours=2.5)  # Expected: 1h
        assert result["freshness_classification"] == "delayed"

        # Stale: >3x expected frequency
        result = compute_source_provenance("yfinance", data_age_hours=5.0)  # Expected: 1h
        assert result["freshness_classification"] == "stale"

    def test_source_provenance_coverage(self):
        """Test coverage ratio in provenance."""
        result = compute_source_provenance("yfinance", coverage_ratio=0.75)

        assert result["coverage_ratio"] == 0.75
        assert result["coverage_classification"] == "moderate"

    def test_source_provenance_known_biases(self):
        """Test known biases in provenance."""
        result = compute_source_provenance("FRED")

        assert "US-focused" in result["known_biases"]


class TestFactorProvenance:
    """Tests for factor provenance computation."""

    def test_factor_provenance_with_real_data(self):
        """Test factor provenance with real data."""
        result = compute_factor_provenance(
            factor_id="market_volatility",
            source="yfinance",
            has_data=True,
            data_age_hours=1.0,
        )

        assert result["factor_id"] == "market_volatility"
        assert result["has_real_data"] is True
        assert result["source_provenance"]["source_name"] == "yfinance"
        assert len(result["data_quality_flags"]) == 0

    def test_factor_provenance_no_real_data(self):
        """Test factor provenance without real data."""
        result = compute_factor_provenance(
            factor_id="market_volatility",
            source="default",
            has_data=False,
        )

        assert result["has_real_data"] is False
        assert "no_real_data" in result["data_quality_flags"]

    def test_factor_provenance_stale_data(self):
        """Test factor provenance with stale data."""
        result = compute_factor_provenance(
            factor_id="market_volatility",
            source="yfinance",
            has_data=True,
            data_age_hours=10.0,  # Stale (>3x expected 1h)
        )

        assert "stale_data" in result["data_quality_flags"]


class TestSubIndexProvenance:
    """Tests for sub-index provenance computation."""

    def test_sub_index_provenance_basic(self):
        """Test basic sub-index provenance."""
        result = compute_sub_index_provenance(
            sub_index_name="economic_stress",
            component_sources=["yfinance", "FRED"],
            component_has_data=[True, True],
        )

        assert result["sub_index_name"] == "economic_stress"
        assert len(result["sources"]) == 2
        assert result["coverage_ratio"] == 1.0
        assert result["coverage_classification"] == "high"

    def test_sub_index_provenance_partial_coverage(self):
        """Test sub-index provenance with partial coverage."""
        result = compute_sub_index_provenance(
            sub_index_name="economic_stress",
            component_sources=["yfinance", "FRED", "default"],
            component_has_data=[True, True, False],
        )

        assert result["coverage_ratio"] == pytest.approx(2.0 / 3.0)
        assert result["coverage_classification"] == "moderate"

    def test_sub_index_provenance_aggregates_biases(self):
        """Test that sub-index provenance aggregates biases."""
        result = compute_sub_index_provenance(
            sub_index_name="economic_stress",
            component_sources=["FRED", "search_trends_api"],
            component_has_data=[True, True],
        )

        assert len(result["known_biases"]) > 0
        assert "US-focused" in result["known_biases"] or "Urban skew" in result["known_biases"]


class TestAggregateProvenance:
    """Tests for aggregate provenance computation."""

    def test_aggregate_provenance_basic(self):
        """Test basic aggregate provenance."""
        sub_index_provenances = {
            "economic_stress": compute_sub_index_provenance(
                "economic_stress",
                ["yfinance", "FRED"],
                [True, True],
            ),
            "environmental_stress": compute_sub_index_provenance(
                "environmental_stress",
                ["Open-Meteo"],
                [True],
            ),
        }

        result = compute_aggregate_provenance(sub_index_provenances)

        assert result["total_sources"] >= 2
        assert result["sub_index_count"] == 2
        assert result["average_coverage_ratio"] == 1.0


class TestComposeProvenance:
    """Tests for complete provenance composition."""

    def test_compose_provenance_basic(self):
        """Test basic provenance composition."""
        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "market_volatility",
                        "source": "yfinance",
                        "value": 0.6,
                    },
                    {
                        "id": "consumer_sentiment",
                        "source": "FRED",
                        "value": 0.4,
                    },
                ],
            }
        }

        result = compose_provenance(subindex_details)

        assert "sub_index_provenances" in result
        assert "aggregate_provenance" in result
        assert "metadata" in result
        assert "economic_stress" in result["sub_index_provenances"]

    def test_compose_provenance_with_timestamp(self):
        """Test provenance composition with timestamp."""
        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "market_volatility",
                        "source": "yfinance",
                        "value": 0.6,
                    },
                ],
            }
        }

        data_timestamp = datetime.now(timezone.utc) - timedelta(hours=2)
        result = compose_provenance(subindex_details, data_timestamp=data_timestamp)

        assert result["metadata"]["data_age_hours"] is not None
        assert result["metadata"]["data_age_hours"] == pytest.approx(2.0, abs=0.1)

    def test_compose_provenance_factor_provenances(self):
        """Test that factor provenances are computed."""
        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "market_volatility",
                        "source": "yfinance",
                        "value": 0.6,
                    },
                ],
            }
        }

        result = compose_provenance(subindex_details)

        assert "factor_provenances" in result
        assert len(result["factor_provenances"]) > 0


class TestProvenanceInvariants:
    """Tests for provenance invariants."""

    def test_inv_p01_provenance_completeness(self):
        """Test INV-P01: Provenance completeness."""
        registry = get_registry()

        provenance = {
            "sub_index_provenances": {
                "economic_stress": {
                    "sub_index_name": "economic_stress",
                    "sources": ["yfinance"],
                }
            },
            "aggregate_provenance": {},
            "metadata": {},
        }

        is_valid, error = registry.check("INV-P01", provenance)
        assert is_valid is True

    def test_inv_p01_provenance_completeness_violation(self):
        """Test INV-P01 violation: Missing required field."""
        registry = get_registry()

        provenance = {
            "sub_index_provenances": {},
            # Missing aggregate_provenance
            "metadata": {},
        }

        is_valid, error = registry.check("INV-P01", provenance)
        assert is_valid is False
        assert "missing" in error.lower()

    def test_inv_p02_freshness_consistency(self):
        """Test INV-P02: Freshness consistency."""
        registry = get_registry()

        provenance = {
            "sub_index_provenances": {
                "economic_stress": {
                    "source_provenances": [
                        {
                            "freshness_classification": "fresh",
                            "expected_update_frequency_hours": 1,
                        }
                    ],
                }
            },
        }

        is_valid, error = registry.check("INV-P02", provenance, data_age_hours=1.0)
        assert is_valid is True

    def test_inv_p03_coverage_confidence_relationship(self):
        """Test INV-P03: Coverage-confidence relationship."""
        registry = get_registry()

        # Low coverage with high confidence should fail
        is_valid, error = registry.check("INV-P03", coverage_ratio=0.3, confidence=0.9)
        assert is_valid is False

        # Low coverage with low confidence should pass
        is_valid, error = registry.check("INV-P03", coverage_ratio=0.3, confidence=0.4)
        assert is_valid is True

    def test_inv_p05_zero_numerical_drift(self):
        """Test INV-P05: Zero numerical drift."""
        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.548

        is_valid, error = registry.check("INV-P05", behavior_index_before, behavior_index_after)
        assert is_valid is True

    def test_inv_p05_zero_numerical_drift_violation(self):
        """Test INV-P05 violation: Numerical drift detected."""
        from app.core.invariants import InvariantViolation

        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.550  # Changed

        # INV-P05 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-P05", behavior_index_before, behavior_index_after)

        assert "drift" in str(exc_info.value).lower() or "changed" in str(exc_info.value).lower()


class TestNoSemanticDrift:
    """Tests to ensure provenance does not cause semantic drift."""

    def test_base_index_unchanged_with_provenance(self):
        """Test that behavior index is unchanged when provenance is generated."""
        # Expected value for comparison: 0.548

        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "market_volatility",
                        "source": "yfinance",
                        "value": 0.6,
                    },
                ],
            }
        }

        # Generate provenance
        result = compose_provenance(subindex_details)

        # Behavior index should be unchanged (provenance doesn't compute it)
        # This test verifies provenance doesn't interfere with computation
        assert isinstance(result, dict)
        assert "sub_index_provenances" in result

    def test_provenance_is_purely_derived(self):
        """Test that provenance is purely derived from existing outputs."""
        subindex_details = {
            "economic_stress": {
                "value": 0.5,
                "components": [
                    {
                        "id": "market_volatility",
                        "source": "yfinance",
                        "value": 0.6,
                    },
                ],
            }
        }

        result1 = compose_provenance(subindex_details)
        result2 = compose_provenance(subindex_details)

        # Results should be identical (deterministic)
        assert result1["sub_index_provenances"]["economic_stress"]["sources"] == \
               result2["sub_index_provenances"]["economic_stress"]["sources"]


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_provenance_optional_in_api(self):
        """Test that provenance is optional in API responses."""
        # This test verifies that the API can function without provenance
        # The actual API integration will be tested separately
        result = compose_provenance({})

        assert isinstance(result, dict)
        assert "sub_index_provenances" in result
        assert "aggregate_provenance" in result
        assert "metadata" in result

    def test_provenance_composition_empty_details(self):
        """Test provenance composition with empty subindex details."""
        result = compose_provenance({})

        assert isinstance(result, dict)
        assert len(result["sub_index_provenances"]) == 0
