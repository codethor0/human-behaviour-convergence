# SPDX-License-Identifier: PROPRIETARY
"""Metrics integrity tests - enforce no region=None labels and multi-region export."""
import re

import pytest
import requests


class TestMetricsIntegrity:
    """Test suite enforcing metrics integrity contracts."""

    @pytest.fixture
    def metrics_endpoint(self):
        """Get metrics endpoint URL."""
        import os
        base_url = os.getenv("HBC_BACKEND_URL", "http://localhost:8100")
        return f"{base_url}/metrics"

    def test_no_none_region_labels(self, metrics_endpoint):
        """
        Contract C2 regression: No metric should have region="None" or region=None label.

        This test prevents the bug where region=None labels collapse multiple regions
        into a single label in Grafana.
        """
        try:
            response = requests.get(metrics_endpoint, timeout=10)
            response.raise_for_status()
            metrics_text = response.text
        except requests.exceptions.RequestException:
            pytest.skip(f"Metrics endpoint not accessible: {metrics_endpoint}")

        # Search for region="None" or region=None patterns
        none_patterns = [
            r'region="None"',
            r"region='None'",
            r"region=None[,\s}]",
        ]

        violations = []
        for pattern in none_patterns:
            matches = re.findall(pattern, metrics_text)
            if matches:
                violations.extend(matches)

        assert len(violations) == 0, (
            f"Contract C2 violation: Found {len(violations)} metrics with region=None labels. "
            f"Patterns found: {set(violations)}. "
            f"This breaks Grafana region filtering. "
            f"Fix: Ensure region_id normalization in main.py lines 2145-2153 always produces a non-None value."
        )

    def test_multi_region_metrics_after_forecasts(self, metrics_endpoint):
        """
        Contract C5 regression: Metrics must be exported for multiple regions.

        After generating forecasts for multiple regions, verify that metrics
        exist for all of them (not just the most recent).
        """
        import os
        base_url = os.getenv("HBC_BACKEND_URL", "http://localhost:8100")
        prometheus_url = os.getenv("HBC_PROMETHEUS_URL", "http://localhost:9090")

        # Generate forecasts for 3 distinct regions
        test_regions = [
            {"region_id": "us_mn", "region_name": "Minnesota"},
            {"region_id": "us_ca", "region_name": "California"},
            {"region_id": "city_nyc", "region_name": "New York City"},
        ]

        for region in test_regions:
            try:
                payload = {
                    "region_id": region["region_id"],
                    "region_name": region["region_name"],
                    "days_back": 30,
                    "forecast_horizon": 7,
                }
                response = requests.post(
                    f"{base_url}/api/forecast",
                    json=payload,
                    timeout=120,
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                pytest.skip(f"Could not generate forecast for {region['region_id']}: {e}")

        # Wait a moment for metrics to be scraped
        import time
        time.sleep(2)

        # Query Prometheus for distinct regions
        try:
            query = 'count(count by(region)(behavior_index))'
            response = requests.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("data", {}).get("result"):
                region_count = int(float(data["data"]["result"][0]["value"][1]))
            else:
                region_count = 0
        except requests.exceptions.RequestException:
            pytest.skip("Prometheus not accessible")

        # Contract C5: Should have metrics for multiple regions
        assert region_count >= 3, (
            f"Contract C5 violation: Only {region_count} regions have metrics "
            f"after generating forecasts for 3 regions. "
            f"Expected at least 3. This indicates metrics are only exported for the most recent region."
        )

        # Also check parent and child sub-index metrics
        for metric in ["parent_subindex_value", "child_subindex_value"]:
            try:
                query = f'count(count by(region)({metric}))'
                response = requests.get(
                    f"{prometheus_url}/api/v1/query",
                    params={"query": query},
                    timeout=10,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("data", {}).get("result"):
                    subindex_region_count = int(
                        float(data["data"]["result"][0]["value"][1])
                    )
                else:
                    subindex_region_count = 0

                assert subindex_region_count >= 3, (
                    f"Contract C5 violation: {metric} only has metrics for {subindex_region_count} regions. "
                    f"Expected at least 3 after generating forecasts for 3 regions."
                )
            except requests.exceptions.RequestException:
                # Prometheus not accessible - skip this check
                pass
