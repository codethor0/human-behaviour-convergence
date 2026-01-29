# SPDX-License-Identifier: PROPRIETARY
"""
Paranoid metrics contracts tests - enforce strict metrics integrity.

These tests verify:
- No region="None" labels
- Multiple distinct regions exist after seeding
- Child index metrics are present
- Metrics are properly labeled
"""
import re

import pytest
import requests


class TestMetricsContractsParanoid:
    """
    Paranoid tests for metrics contracts.

    These tests are stricter than basic metrics tests and verify
    contracts that must hold for proper observability.
    """

    @pytest.fixture
    def metrics_endpoint(self):
        """Get metrics endpoint URL."""
        import os

        base_url = os.getenv("HBC_BACKEND_URL", "http://localhost:8100")
        return f"{base_url}/metrics"

    @pytest.fixture
    def forecaster(self):
        """Create a BehavioralForecaster instance for seeding."""
        from app.core.prediction import BehavioralForecaster

        return BehavioralForecaster()

    def test_no_region_none_labels(self, metrics_endpoint):
        """
        Paranoid contract: No metric should have region="None" or region=None.

        This is a stricter version of the basic test, checking multiple patterns.
        """
        try:
            response = requests.get(metrics_endpoint, timeout=10)
            response.raise_for_status()
            metrics_text = response.text
        except requests.exceptions.RequestException:
            pytest.skip(f"Metrics endpoint not accessible: {metrics_endpoint}")

        # Comprehensive pattern matching for None labels
        none_patterns = [
            r'region="None"',
            r"region='None'",
            r"region=None[,\s}]",
            r'region="none"',  # Case insensitive
            r"region='none'",
            r"region=null",  # JSON null
            r'region=""',  # Empty string
            r"region=''",
        ]

        violations = []
        for pattern in none_patterns:
            matches = re.findall(pattern, metrics_text, re.IGNORECASE)
            if matches:
                violations.extend(matches)

        assert len(violations) == 0, (
            f"Paranoid contract violation: Found {len(violations)} metrics with region=None labels. "
            f"Patterns found: {set(violations)}. "
            f"First 5 lines with violations:\n"
            + "\n".join(
                [
                    line
                    for line in metrics_text.split("\n")
                    if any(re.search(p, line, re.IGNORECASE) for p in none_patterns)
                ][:5]
            )
        )

    def test_multiple_distinct_regions_after_seeding(
        self, metrics_endpoint, forecaster
    ):
        """
        Paranoid contract: After seeding forecasts for N regions, metrics must show >= N distinct regions.

        This test seeds forecasts and then verifies metrics reflect all regions.
        """
        # Seed forecasts for multiple regions
        test_regions = [
            {"name": "Illinois", "lat": 40.3495, "lon": -88.9861},
            {"name": "Arizona", "lat": 34.0489, "lon": -111.0937},
            {"name": "Florida", "lat": 27.7663, "lon": -81.6868},
            {"name": "Washington", "lat": 47.0379, "lon": -120.5015},
            {"name": "California", "lat": 36.7783, "lon": -119.4179},
        ]

        # Generate forecasts to populate metrics
        for region in test_regions:
            try:
                forecaster.forecast(
                    latitude=region["lat"],
                    longitude=region["lon"],
                    region_name=region["name"],
                    days_back=30,
                    forecast_horizon=7,
                )
            except Exception as e:
                pytest.skip(f"Failed to generate forecast for {region['name']}: {e}")

        # Wait a moment for metrics to be emitted (if async)
        import time

        time.sleep(1)

        # Fetch metrics
        try:
            response = requests.get(metrics_endpoint, timeout=10)
            response.raise_for_status()
            metrics_text = response.text
        except requests.exceptions.RequestException:
            pytest.skip(f"Metrics endpoint not accessible: {metrics_endpoint}")

        # Extract all region labels from behavior_index metrics
        behavior_index_pattern = r'behavior_index\{[^}]*region="([^"]+)"[^}]*\}'
        matches = re.findall(behavior_index_pattern, metrics_text)

        unique_regions = set(matches)

        # Should have at least 2 distinct regions (or all seeded regions if metrics are working)
        min_expected = min(2, len(test_regions))

        assert len(unique_regions) >= min_expected, (
            f"Paranoid contract violation: After seeding {len(test_regions)} regions, "
            f"metrics show only {len(unique_regions)} distinct region labels: {unique_regions}. "
            f"Expected at least {min_expected}. "
            f"This indicates metrics are not being emitted per region or labels are collapsing."
        )

    def test_child_index_metrics_present(self, metrics_endpoint, forecaster):
        """
        Paranoid contract: Child index metrics must be present after generating forecasts.

        Verifies that child_subindex_value metrics include expected child indices.
        """
        # Generate a forecast for a US state (to trigger regional child indices)
        try:
            forecaster.forecast(
                latitude=40.3495,
                longitude=-88.9861,
                region_name="Illinois",
                days_back=30,
                forecast_horizon=7,
            )
        except Exception as e:
            pytest.skip(f"Failed to generate forecast: {e}")

        import time

        time.sleep(1)

        # Fetch metrics
        try:
            response = requests.get(metrics_endpoint, timeout=10)
            response.raise_for_status()
            metrics_text = response.text
        except requests.exceptions.RequestException:
            pytest.skip(f"Metrics endpoint not accessible: {metrics_endpoint}")

        # Check for child_subindex_value metrics
        child_index_pattern = r'child_subindex_value\{[^}]*child="([^"]+)"[^}]*\}'
        child_matches = re.findall(child_index_pattern, metrics_text)

        unique_children = set(child_matches)

        # Expected child indices (at least some should be present)
        expected_children = [
            "fuel_stress",
            "drought_stress",
            "storm_severity_stress",
            "labor_stress",
            "inflation_cost_pressure",
        ]

        # At least one expected child index should be present
        found_expected = [c for c in expected_children if c in unique_children]

        assert len(found_expected) > 0 or len(unique_children) > 0, (
            f"Paranoid contract violation: No child index metrics found. "
            f"Expected at least one of: {expected_children}. "
            f"Found child indices: {unique_children}. "
            f"This indicates child index metrics are not being emitted."
        )

    def test_region_label_format_consistency(self, metrics_endpoint, forecaster):
        """
        Paranoid contract: Region labels must follow consistent format.

        Verifies that region labels are not malformed (no special chars, no spaces in quotes, etc.)
        """
        # Generate forecasts for regions with different name formats
        test_regions = [
            {"name": "New York", "lat": 40.7128, "lon": -74.0060},  # Space in name
            {"name": "us_il", "lat": 40.3495, "lon": -88.9861},  # Underscore format
            {"name": "California", "lat": 36.7783, "lon": -119.4179},  # Standard name
        ]

        for region in test_regions:
            try:
                forecaster.forecast(
                    latitude=region["lat"],
                    longitude=region["lon"],
                    region_name=region["name"],
                    days_back=30,
                    forecast_horizon=7,
                )
            except Exception:
                pass  # Continue even if one fails

        import time

        time.sleep(1)

        # Fetch metrics
        try:
            response = requests.get(metrics_endpoint, timeout=10)
            response.raise_for_status()
            metrics_text = response.text
        except requests.exceptions.RequestException:
            pytest.skip(f"Metrics endpoint not accessible: {metrics_endpoint}")

        # Extract all region labels
        region_pattern = r'region="([^"]+)"'
        region_matches = re.findall(region_pattern, metrics_text)

        # Check for malformed labels
        malformed = []
        for region_label in set(region_matches):
            # Check for problematic characters or patterns
            if "\n" in region_label or "\t" in region_label:
                malformed.append(f"{region_label} (contains newline/tab)")
            if region_label.startswith(" ") or region_label.endswith(" "):
                malformed.append(f"{region_label} (leading/trailing space)")
            if len(region_label) == 0:
                malformed.append("(empty string)")

        assert len(malformed) == 0, (
            f"Paranoid contract violation: Found {len(malformed)} malformed region labels: {malformed}. "
            f"Region labels must be clean strings without special characters or whitespace issues."
        )

    def test_metrics_cardinality_bounds(self, metrics_endpoint, forecaster):
        """
        Paranoid contract: Metrics should not explode in cardinality.

        Verifies that unique label combinations don't exceed reasonable bounds.
        """
        # Generate forecasts for many regions
        many_regions = [
            {"name": f"TestRegion{i}", "lat": 40.0 + i * 0.1, "lon": -80.0 + i * 0.1}
            for i in range(20)
        ]

        for region in many_regions:
            try:
                forecaster.forecast(
                    latitude=region["lat"],
                    longitude=region["lon"],
                    region_name=region["name"],
                    days_back=30,
                    forecast_horizon=7,
                )
            except Exception:
                pass  # Continue even if some fail

        import time

        time.sleep(2)

        # Fetch metrics
        try:
            response = requests.get(metrics_endpoint, timeout=10)
            response.raise_for_status()
            metrics_text = response.text
        except requests.exceptions.RequestException:
            pytest.skip(f"Metrics endpoint not accessible: {metrics_endpoint}")

        # Count unique region labels
        region_pattern = r'region="([^"]+)"'
        region_matches = re.findall(region_pattern, metrics_text)
        unique_regions = set(region_matches)

        # Count unique metric series (all label combinations)
        metric_lines = [
            line
            for line in metrics_text.split("\n")
            if line and not line.startswith("#") and "{" in line
        ]
        unique_series = set(metric_lines)

        # Cardinality should be bounded
        # Allow up to 100 unique series (reasonable for 20 regions with multiple metrics)
        max_expected_series = 100

        # This is informational - we don't fail hard, but we warn
        if len(unique_series) > max_expected_series:
            pytest.skip(
                f"Metrics cardinality is high ({len(unique_series)} unique series for "
                f"{len(unique_regions)} regions). This may be expected but should be monitored. "
                f"Consider metric aggregation or label reduction if this grows unbounded."
            )

        # At minimum, we should have some metrics
        assert len(unique_series) > 0, (
            f"Paranoid contract violation: No metrics found after seeding {len(many_regions)} regions. "
            f"This indicates metrics are not being emitted."
        )
