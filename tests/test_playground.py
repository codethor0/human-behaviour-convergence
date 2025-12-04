# SPDX-License-Identifier: PROPRIETARY
"""Tests for playground functionality."""
import pytest

from app.core.playground import (
    apply_scenario,
    compare_regions,
    recompute_behavior_index_from_sub_indices,
)


class TestPlaygroundHelpers:
    """Test helper functions for playground."""

    def test_apply_scenario_no_scenario(self):
        """Test apply_scenario with no scenario (should return copy)."""
        sub_indices = {
            "economic_stress": 0.5,
            "environmental_stress": 0.4,
            "mobility_activity": 0.6,
            "digital_attention": 0.5,
            "public_health_stress": 0.5,
        }
        result = apply_scenario(sub_indices, None)
        assert result == sub_indices
        assert result is not sub_indices  # Should be a copy

    def test_apply_scenario_with_offsets(self):
        """Test apply_scenario with offsets."""
        sub_indices = {
            "economic_stress": 0.5,
            "environmental_stress": 0.4,
            "mobility_activity": 0.6,
            "digital_attention": 0.5,
            "public_health_stress": 0.5,
        }
        scenario = {
            "economic_stress_offset": 0.2,
            "digital_attention_offset": 0.1,
        }
        result = apply_scenario(sub_indices, scenario)

        assert result["economic_stress"] == 0.7  # 0.5 + 0.2
        assert result["environmental_stress"] == 0.4  # Unchanged
        assert result["digital_attention"] == 0.6  # 0.5 + 0.1
        assert result["mobility_activity"] == 0.6  # Unchanged
        assert result["public_health_stress"] == 0.5  # Unchanged

    def test_apply_scenario_clamping(self):
        """Test that scenario offsets are clamped to [0.0, 1.0]."""
        sub_indices = {
            "economic_stress": 0.9,
            "environmental_stress": 0.1,
        }
        scenario = {
            "economic_stress_offset": 0.2,  # Would exceed 1.0
            "environmental_stress_offset": -0.2,  # Would go below 0.0
        }
        result = apply_scenario(sub_indices, scenario)

        assert result["economic_stress"] == 1.0  # Clamped
        assert result["environmental_stress"] == 0.0  # Clamped

    def test_recompute_behavior_index(self):
        """Test behavior index recomputation with fixed weights."""
        sub_indices = {
            "economic_stress": 0.4,
            "environmental_stress": 0.3,
            "mobility_activity": 0.7,  # High activity = low disruption
            "digital_attention": 0.5,
            "public_health_stress": 0.4,
        }

        # Expected: (0.4 * 0.25) + (0.3 * 0.25) + ((1-0.7) * 0.20) +
        # (0.5 * 0.15) + (0.4 * 0.15)
        # = 0.1 + 0.075 + 0.06 + 0.075 + 0.06 = 0.37
        result = recompute_behavior_index_from_sub_indices(sub_indices)

        assert 0.36 <= result <= 0.38  # Allow small floating point differences

    def test_recompute_behavior_index_clipping(self):
        """Test that recomputed behavior index is clipped to [0.0, 1.0]."""
        # Extreme values
        sub_indices = {
            "economic_stress": 2.0,  # Would exceed 1.0 if not clipped
            "environmental_stress": -1.0,  # Would go below 0.0 if not clipped
            "mobility_activity": 0.5,
            "digital_attention": 0.5,
            "public_health_stress": 0.5,
        }

        result = recompute_behavior_index_from_sub_indices(sub_indices)
        assert 0.0 <= result <= 1.0


class TestCompareRegions:
    """Test multi-region comparison."""

    def test_compare_regions_single_region(self):
        """Test comparison with a single region."""
        result = compare_regions(
            region_ids=["us_dc"],
            historical_days=30,
            forecast_horizon_days=7,
            include_explanations=False,
        )

        assert "config" in result
        assert "results" in result
        assert "errors" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["region_id"] == "us_dc"
        assert "forecast" in result["results"][0]

    def test_compare_regions_multiple_regions(self):
        """Test comparison with multiple regions."""
        result = compare_regions(
            region_ids=["us_dc", "us_mn"],
            historical_days=30,
            forecast_horizon_days=7,
            include_explanations=False,
        )

        assert len(result["results"]) == 2
        region_ids = [r["region_id"] for r in result["results"]]
        assert "us_dc" in region_ids
        assert "us_mn" in region_ids

    def test_compare_regions_invalid_region(self):
        """Test that invalid regions are handled gracefully."""
        result = compare_regions(
            region_ids=["invalid_region_id"],
            historical_days=30,
            forecast_horizon_days=7,
            include_explanations=False,
        )

        assert len(result["results"]) == 0
        assert len(result["errors"]) == 1
        assert result["errors"][0]["region_id"] == "invalid_region_id"

    def test_compare_regions_mixed_valid_invalid(self):
        """Test comparison with mix of valid and invalid regions."""
        result = compare_regions(
            region_ids=["us_dc", "invalid_region", "us_mn"],
            historical_days=30,
            forecast_horizon_days=7,
            include_explanations=False,
        )

        assert len(result["results"]) == 2
        assert len(result["errors"]) == 1
        assert result["errors"][0]["region_id"] == "invalid_region"

    def test_compare_regions_with_explanations(self):
        """Test comparison with explanations enabled."""
        result = compare_regions(
            region_ids=["us_dc"],
            historical_days=30,
            forecast_horizon_days=7,
            include_explanations=True,
        )

        assert result["config"]["include_explanations"] is True
        # Explanations may or may not be present depending on data availability
        # Just verify the structure is correct

    def test_compare_regions_with_scenario(self):
        """Test comparison with scenario adjustments."""
        scenario = {
            "digital_attention_offset": 0.1,
        }

        result = compare_regions(
            region_ids=["us_dc"],
            historical_days=30,
            forecast_horizon_days=7,
            include_explanations=False,
            scenario=scenario,
        )

        assert result["config"]["scenario_applied"] is True
        assert len(result["results"]) == 1
        # Check that scenario metadata is present
        if result["results"][0].get("scenario_applied"):
            assert "scenario_description" in result["results"][0]

    def test_compare_regions_empty_list(self):
        """Test that empty region list raises ValueError."""
        with pytest.raises(ValueError, match="At least one region_id"):
            compare_regions(region_ids=[])
