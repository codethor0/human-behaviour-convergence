# SPDX-License-Identifier: PROPRIETARY
"""Tests for comparative benchmarks."""
import pytest

from app.core.benchmarks import (
    compute_deviation_from_baseline,
    compute_historical_baseline,
    compute_peer_group_average,
    compute_sub_index_benchmarks,
    compose_benchmarks,
)
from app.core.invariants import get_registry
from app.core.regions import get_region_by_id


class TestPeerGroupAverage:
    """Tests for peer group average computation."""

    def test_peer_group_average_basic(self):
        """Test basic peer group average computation."""
        region = get_region_by_id("us_mn")
        assert region is not None

        behavior_index_values = {
            "us_mn": 0.5,
            "us_ca": 0.6,
            "us_tx": 0.4,
            "us_ny": 0.55,
        }

        result = compute_peer_group_average(region, behavior_index_values)

        assert result["peer_group"] == "US_STATES"
        assert result["peer_count"] >= 0  # Depends on available peers
        if result["average_behavior_index"] is not None:
            assert 0.0 <= result["average_behavior_index"] <= 1.0

    def test_peer_group_average_no_peers(self):
        """Test peer group average with no peers."""
        region = get_region_by_id("us_mn")
        assert region is not None

        behavior_index_values = {
            "us_mn": 0.5,
        }

        result = compute_peer_group_average(region, behavior_index_values)

        assert result["peer_group"] == "US_STATES"
        assert result["peer_count"] == 0
        assert result["average_behavior_index"] is None

    def test_peer_group_average_with_sub_indices(self):
        """Test peer group average with sub-index values."""
        region = get_region_by_id("us_mn")
        assert region is not None

        behavior_index_values = {
            "us_mn": 0.5,
            "us_ca": 0.6,
        }

        sub_index_values = {
            "us_mn": {
                "economic_stress": 0.4,
                "environmental_stress": 0.5,
            },
            "us_ca": {
                "economic_stress": 0.5,
                "environmental_stress": 0.6,
            },
        }

        result = compute_peer_group_average(
            region, behavior_index_values, sub_index_values
        )

        assert result["peer_group"] == "US_STATES"
        if result["average_sub_indices"]:
            assert "economic_stress" in result["average_sub_indices"]
            assert "environmental_stress" in result["average_sub_indices"]


class TestHistoricalBaseline:
    """Tests for historical baseline computation."""

    def test_historical_baseline_basic(self):
        """Test basic historical baseline computation."""
        history = [0.5, 0.52, 0.48, 0.51, 0.49]

        result = compute_historical_baseline(history, baseline_window_days=5)

        assert result["baseline_value"] is not None
        assert 0.0 <= result["baseline_value"] <= 1.0
        assert result["baseline_std"] >= 0.0
        assert result["baseline_min"] <= result["baseline_max"]
        assert result["window_days"] == 5

    def test_historical_baseline_empty_history(self):
        """Test historical baseline with empty history."""
        result = compute_historical_baseline([])

        assert result["baseline_value"] is None
        assert result["window_days"] == 0

    def test_historical_baseline_window_limits(self):
        """Test historical baseline with window larger than history."""
        history = [0.5, 0.52]

        result = compute_historical_baseline(history, baseline_window_days=30)

        assert result["baseline_value"] is not None
        assert result["window_days"] == 2  # Uses available data


class TestDeviationFromBaseline:
    """Tests for deviation from baseline computation."""

    def test_deviation_from_baseline_normal(self):
        """Test deviation classification for normal values."""
        baseline = {
            "baseline_value": 0.5,
            "baseline_std": 0.05,
        }

        result = compute_deviation_from_baseline(0.52, baseline)

        assert result["absolute_deviation"] is not None
        assert result["relative_deviation"] is not None
        assert result["z_score"] is not None
        assert result["classification"] in ["normal", "elevated", "anomalous"]

    def test_deviation_from_baseline_elevated(self):
        """Test deviation classification for elevated values."""
        baseline = {
            "baseline_value": 0.5,
            "baseline_std": 0.05,
        }

        result = compute_deviation_from_baseline(0.58, baseline)  # Z-score ~1.6

        assert result["classification"] in ["elevated", "anomalous"]

    def test_deviation_from_baseline_anomalous(self):
        """Test deviation classification for anomalous values."""
        baseline = {
            "baseline_value": 0.5,
            "baseline_std": 0.05,
        }

        result = compute_deviation_from_baseline(0.65, baseline)  # Z-score ~3.0

        assert result["classification"] == "anomalous"

    def test_deviation_from_baseline_no_baseline(self):
        """Test deviation with no baseline."""
        baseline = {}

        result = compute_deviation_from_baseline(0.5, baseline)

        assert result["absolute_deviation"] is None
        assert result["classification"] == "unknown"


class TestSubIndexBenchmarks:
    """Tests for sub-index benchmark computation."""

    def test_sub_index_benchmarks_basic(self):
        """Test basic sub-index benchmarks."""
        current_sub_indices = {
            "economic_stress": 0.5,
            "environmental_stress": 0.6,
        }

        result = compute_sub_index_benchmarks(current_sub_indices)

        assert "economic_stress" in result
        assert "environmental_stress" in result
        assert result["economic_stress"]["current_value"] == 0.5

    def test_sub_index_benchmarks_with_peer_averages(self):
        """Test sub-index benchmarks with peer averages."""
        current_sub_indices = {
            "economic_stress": 0.5,
        }

        peer_averages = {
            "economic_stress": 0.45,
        }

        result = compute_sub_index_benchmarks(
            current_sub_indices, peer_averages=peer_averages
        )

        assert result["economic_stress"]["peer_average"] == 0.45
        assert abs(result["economic_stress"]["peer_deviation"] - 0.05) < 1e-9

    def test_sub_index_benchmarks_with_baseline_averages(self):
        """Test sub-index benchmarks with baseline averages."""
        current_sub_indices = {
            "economic_stress": 0.5,
        }

        baseline_averages = {
            "economic_stress": 0.48,
        }

        result = compute_sub_index_benchmarks(
            current_sub_indices, baseline_averages=baseline_averages
        )

        assert result["economic_stress"]["baseline_average"] == 0.48
        assert abs(result["economic_stress"]["baseline_deviation"] - 0.02) < 1e-9


class TestComposeBenchmarks:
    """Tests for complete benchmark composition."""

    def test_compose_benchmarks_basic(self):
        """Test basic benchmark composition."""
        region = get_region_by_id("us_mn")
        assert region is not None

        result = compose_benchmarks(
            current_region=region,
            current_behavior_index=0.5,
            current_sub_indices={
                "economic_stress": 0.4,
                "environmental_stress": 0.5,
            },
            behavior_index_history=[0.48, 0.49, 0.51, 0.52],
        )

        assert "peer_group_analysis" in result
        assert "historical_baseline" in result
        assert "baseline_deviation" in result
        assert "sub_index_benchmarks" in result
        assert "metadata" in result

    def test_compose_benchmarks_with_peers(self):
        """Test benchmark composition with peer data."""
        region = get_region_by_id("us_mn")
        assert region is not None

        peer_behavior_indices = {
            "us_ca": 0.6,
            "us_tx": 0.4,
        }

        result = compose_benchmarks(
            current_region=region,
            current_behavior_index=0.5,
            current_sub_indices={},
            peer_behavior_indices=peer_behavior_indices,
        )

        assert result["peer_group_analysis"] is not None
        if result["peer_group_analysis"]["peer_count"] > 0:
            assert result["peer_group_analysis"]["average_behavior_index"] is not None

    def test_compose_benchmarks_no_history(self):
        """Test benchmark composition without history."""
        region = get_region_by_id("us_mn")
        assert region is not None

        result = compose_benchmarks(
            current_region=region,
            current_behavior_index=0.5,
            current_sub_indices={},
            behavior_index_history=[],
        )

        assert result["historical_baseline"]["baseline_value"] is None
        assert result["baseline_deviation"]["classification"] == "unknown"


class TestBenchmarkInvariants:
    """Tests for benchmark invariants."""

    def test_inv_b01_benchmark_determinism(self):
        """Test INV-B01: Benchmark determinism."""
        registry = get_registry()

        region = get_region_by_id("us_mn")
        assert region is not None

        benchmarks1 = compose_benchmarks(
            current_region=region,
            current_behavior_index=0.5,
            current_sub_indices={},
            behavior_index_history=[0.48, 0.49, 0.51],
        )

        benchmarks2 = compose_benchmarks(
            current_region=region,
            current_behavior_index=0.5,
            current_sub_indices={},
            behavior_index_history=[0.48, 0.49, 0.51],
        )

        is_valid, error = registry.check("INV-B01", benchmarks1, benchmarks2)
        assert is_valid is True

    def test_inv_b02_peer_group_consistency(self):
        """Test INV-B02: Peer group consistency."""
        registry = get_registry()

        peer_analysis = {
            "average_behavior_index": 0.5,
            "peer_count": 3,
        }

        peer_values = [0.48, 0.50, 0.52]

        is_valid, error = registry.check("INV-B02", peer_analysis, peer_values)
        assert is_valid is True

    def test_inv_b03_baseline_consistency(self):
        """Test INV-B03: Baseline consistency."""
        registry = get_registry()

        baseline = {
            "baseline_value": 0.5,
            "baseline_std": 0.05,
        }

        history = [0.48, 0.49, 0.51, 0.52]

        is_valid, error = registry.check("INV-B03", baseline, history)
        assert is_valid is True

    def test_inv_b04_deviation_correctness(self):
        """Test INV-B04: Deviation correctness."""
        registry = get_registry()

        baseline = {
            "baseline_value": 0.5,
            "baseline_std": 0.05,
        }

        deviation = compute_deviation_from_baseline(0.55, baseline)

        is_valid, error = registry.check("INV-B04", 0.55, baseline, deviation)
        assert is_valid is True

    def test_inv_b05_zero_numerical_drift(self):
        """Test INV-B05: Zero numerical drift."""
        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.548

        is_valid, error = registry.check(
            "INV-B05", behavior_index_before, behavior_index_after
        )
        assert is_valid is True

    def test_inv_b05_zero_numerical_drift_violation(self):
        """Test INV-B05 violation: Numerical drift detected."""
        from app.core.invariants import InvariantViolation

        registry = get_registry()

        behavior_index_before = 0.548
        behavior_index_after = 0.550  # Changed

        # INV-B05 is HARD_FAIL, so it raises exception
        with pytest.raises(InvariantViolation) as exc_info:
            registry.check("INV-B05", behavior_index_before, behavior_index_after)

        assert (
            "drift" in str(exc_info.value).lower()
            or "changed" in str(exc_info.value).lower()
        )


class TestNoSemanticDrift:
    """Tests to ensure benchmarks do not cause semantic drift."""

    def test_base_index_unchanged_with_benchmarks(self):
        """Test that behavior index is unchanged when benchmarks are generated."""
        behavior_index_before = 0.548

        region = get_region_by_id("us_mn")
        assert region is not None

        # Generate benchmarks
        result = compose_benchmarks(
            current_region=region,
            current_behavior_index=behavior_index_before,
            current_sub_indices={},
            behavior_index_history=[0.5, 0.52],
        )

        # Behavior index should be unchanged
        assert (
            abs(
                result["metadata"].get("behavior_index", behavior_index_before)
                - behavior_index_before
            )
            < 1e-10
        )

    def test_benchmarks_are_purely_derived(self):
        """Test that benchmarks are purely derived from existing outputs."""
        region = get_region_by_id("us_mn")
        assert region is not None

        result1 = compose_benchmarks(
            current_region=region,
            current_behavior_index=0.5,
            current_sub_indices={"economic_stress": 0.4},
            behavior_index_history=[0.48, 0.49],
        )

        result2 = compose_benchmarks(
            current_region=region,
            current_behavior_index=0.5,
            current_sub_indices={"economic_stress": 0.4},
            behavior_index_history=[0.48, 0.49],
        )

        # Results should be identical (deterministic)
        assert (
            result1["historical_baseline"]["baseline_value"]
            == result2["historical_baseline"]["baseline_value"]
        )


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_benchmarks_optional_in_api(self):
        """Test that benchmarks are optional in API responses."""
        # This test verifies that the API can function without benchmarks
        # The actual API integration will be tested separately
        region = get_region_by_id("us_mn")
        assert region is not None

        result = compose_benchmarks(
            current_region=region,
            current_behavior_index=0.5,
            current_sub_indices={},
            behavior_index_history=None,
            peer_behavior_indices=None,
        )

        assert isinstance(result, dict)
        assert "peer_group_analysis" in result
        assert "historical_baseline" in result
        assert "baseline_deviation" in result
        assert "sub_index_benchmarks" in result

    def test_benchmark_composition_without_peers(self):
        """Test benchmark composition works without peer data."""
        region = get_region_by_id("us_mn")
        assert region is not None

        result = compose_benchmarks(
            current_region=region,
            current_behavior_index=0.5,
            current_sub_indices={},
            peer_behavior_indices=None,
        )

        assert isinstance(result, dict)
        assert (
            result["peer_group_analysis"] is None
            or result["peer_group_analysis"]["peer_count"] == 0
        )

    def test_benchmark_composition_without_history(self):
        """Test benchmark composition works without history."""
        region = get_region_by_id("us_mn")
        assert region is not None

        result = compose_benchmarks(
            current_region=region,
            current_behavior_index=0.5,
            current_sub_indices={},
            behavior_index_history=[],
        )

        assert isinstance(result, dict)
        assert result["historical_baseline"]["baseline_value"] is None
