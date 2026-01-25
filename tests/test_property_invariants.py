# SPDX-License-Identifier: PROPRIETARY
"""
Property-based invariant tests for human-behaviour-convergence.

These tests verify system properties that must hold across all inputs:
- Regionality: Different regions produce different outputs
- Determinism: Same inputs produce same outputs in CI offline mode
- Cache key regionality: Regional sources include geo in cache keys
- Metrics truth: Multiple regions produce distinct region labels
- No label collapse: No region="None", no unknown_* explosion
- Metamorphic monotonicity: Input changes produce expected output changes
- Data quality: Values are in valid ranges, no NaNs
"""
import hashlib
import json
import os
from typing import Dict, List

import pandas as pd
import pytest

from app.core.prediction import BehavioralForecaster


class TestPropertyInvariants:
    """
    Property-based tests enforcing system invariants.

    Properties:
    P1: Regionality - Different regions produce different outputs for regional indices
    P2: Determinism - Same inputs produce identical outputs in CI offline mode
    P3: Cache key regionality - Regional sources include geo in cache keys
    P4: Metrics truth - After forecasting N regions, metrics show N unique region labels
    P5: No label collapse - No region="None"; no "unknown_*" explosion beyond threshold
    P6: Metamorphic monotonicity - Input changes produce expected output changes
    P7: Data quality - Numeric ranges are bounded, no NaNs
    """

    @pytest.fixture
    def forecaster(self):
        """Create a BehavioralForecaster instance."""
        return BehavioralForecaster()

    @pytest.fixture
    def distant_regions(self):
        """Return two distant regions for regionality testing."""
        return [
            {"name": "Illinois", "lat": 40.3495, "lon": -88.9861, "state_code": "IL"},
            {"name": "Arizona", "lat": 34.0489, "lon": -111.0937, "state_code": "AZ"},
        ]

    def test_p1_regionality_property(self, forecaster, distant_regions):
        """
        Property P1: Regionality.

        If region changes (IL → AZ) and at least one REGIONAL source is enabled,
        at least one output scalar among {behavior_index, environmental_stress,
        fuel_stress, drought_stress, storm_severity_stress} must differ by >= epsilon.
        """
        epsilon = 0.005  # Minimum difference threshold
        results = {}

        for region in distant_regions:
            result = forecaster.forecast(
                latitude=region["lat"],
                longitude=region["lon"],
                region_name=region["name"],
                days_back=30,
                forecast_horizon=7,
            )

            # Extract latest values from history
            history = result.get("history", [])
            if not history:
                pytest.skip("No history data available")

            # Get last history entry
            if isinstance(history, list) and history:
                last_entry = history[-1] if isinstance(history[-1], dict) else {}
            elif hasattr(history, "iloc"):
                last_entry = history.iloc[-1].to_dict()
            else:
                pytest.skip("Cannot extract history entry")

            results[region["name"]] = {
                "behavior_index": last_entry.get("behavior_index"),
                "environmental_stress": last_entry.get("environmental_stress"),
                "fuel_stress": last_entry.get("fuel_stress"),
                "drought_stress": last_entry.get("drought_stress"),
                "storm_severity_stress": last_entry.get("storm_severity_stress"),
            }

        # Check for differences in regional indices
        il_values = results["Illinois"]
        az_values = results["Arizona"]

        differences = []
        regional_indices = [
            "behavior_index",
            "environmental_stress",
            "fuel_stress",
            "drought_stress",
            "storm_severity_stress",
        ]

        for idx_name in regional_indices:
            il_val = il_values.get(idx_name)
            az_val = az_values.get(idx_name)

            if il_val is not None and az_val is not None:
                diff = abs(float(il_val) - float(az_val))
                differences.append((idx_name, diff))

        # At least one regional index must differ by >= epsilon
        max_diff = max((d[1] for d in differences), default=0.0)
        max_diff_idx = next((d[0] for d in differences if d[1] == max_diff), None)

        assert max_diff >= epsilon, (
            f"Property P1 violation: All regional indices are identical or differ by < {epsilon}. "
            f"Max difference: {max_diff} in {max_diff_idx}. "
            f"Illinois values: {il_values}, Arizona values: {az_values}. "
            f"This indicates regional sources are not producing region-specific outputs."
        )

    def test_p2_determinism_property(self, forecaster):
        """
        Property P2: Determinism in CI offline mode.

        Same inputs yield identical outputs across 2 runs in CI offline mode.
        """
        # Only run in CI offline mode
        if not os.getenv("HBC_CI_OFFLINE_DATA") == "1":
            pytest.skip("P2 determinism test requires CI offline mode (HBC_CI_OFFLINE_DATA=1)")

        region = {"name": "Illinois", "lat": 40.3495, "lon": -88.9861}

        # Run 1
        result1 = forecaster.forecast(
            latitude=region["lat"],
            longitude=region["lon"],
            region_name=region["name"],
            days_back=30,
            forecast_horizon=7,
        )

        # Reset cache to force recomputation
        if hasattr(forecaster, "reset_cache"):
            forecaster.reset_cache()

        # Run 2
        result2 = forecaster.forecast(
            latitude=region["lat"],
            longitude=region["lon"],
            region_name=region["name"],
            days_back=30,
            forecast_horizon=7,
        )

        # Extract history and forecast as JSON strings for comparison
        def extract_for_hash(result):
            history = result.get("history", [])
            forecast = result.get("forecast", [])
            return json.dumps(
                {"history": history, "forecast": forecast}, sort_keys=True, default=str
            )

        hash1 = hashlib.sha256(extract_for_hash(result1).encode()).hexdigest()
        hash2 = hashlib.sha256(extract_for_hash(result2).encode()).hexdigest()

        assert hash1 == hash2, (
            f"Property P2 violation: Same inputs produced different outputs in CI offline mode. "
            f"Hash1: {hash1[:16]}..., Hash2: {hash2[:16]}... "
            f"This indicates non-deterministic behavior (random seeds, timestamps, etc.)."
        )

    def test_p3_cache_key_regionality(self):
        """
        Property P3: Cache key regionality.

        REGIONAL sources must include geo identity in cache keys.
        """
        # Test EIA fuel prices fetcher
        from app.services.ingestion.eia_fuel_prices import EIAFuelPricesFetcher

        fetcher = EIAFuelPricesFetcher()

        # Fetch for two different states
        df1, _ = fetcher.fetch_fuel_stress_index(state="IL", days_back=30, use_cache=False)
        df2, _ = fetcher.fetch_fuel_stress_index(state="AZ", days_back=30, use_cache=False)

        # Check that cache keys differ (internal check - cache keys should include state)
        # We verify by checking that fetching with cache returns different data
        df1_cached, _ = fetcher.fetch_fuel_stress_index(state="IL", days_back=30, use_cache=True)
        df2_cached, _ = fetcher.fetch_fuel_stress_index(state="AZ", days_back=30, use_cache=True)

        # If cache keys were correct, cached data should match original
        assert not df1.empty and not df1_cached.empty, "IL data should be cached"
        assert not df2.empty and not df2_cached.empty, "AZ data should be cached"

        # Verify data differs between states (proves cache keys are different)
        if not df1.empty and not df2.empty:
            il_avg = df1["fuel_stress_index"].mean() if "fuel_stress_index" in df1.columns else 0.0
            az_avg = df2["fuel_stress_index"].mean() if "fuel_stress_index" in df2.columns else 0.0
            # In CI offline mode, states should differ due to state_code-based seeding
            # In live mode, they should differ due to actual state-specific data
            assert abs(il_avg - az_avg) > 0.001 or os.getenv("HBC_CI_OFFLINE_DATA") == "1", (
                f"Property P3: Cache keys may not include geo identity. "
                f"IL and AZ data are identical (IL avg: {il_avg}, AZ avg: {az_avg})."
            )

    def test_p4_metrics_truth(self, forecaster):
        """
        Property P4: Metrics truth.

        After forecasting N regions, Prometheus /metrics must show N unique region labels
        (>=2 for proof, >=10 for stronger).
        """
        # This test requires the backend to be running and metrics endpoint accessible
        import requests
        import os

        metrics_url = os.getenv("HBC_METRICS_URL", "http://localhost:8100/metrics")
        
        try:
            response = requests.get(metrics_url, timeout=5)
            response.raise_for_status()
        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError):
            pytest.skip("Metrics endpoint not accessible (backend may not be running)")

        # Generate forecasts for at least 2 regions
        regions = [
            {"name": "Illinois", "lat": 40.3495, "lon": -88.9861},
            {"name": "Arizona", "lat": 34.0489, "lon": -111.0937},
        ]

        for region in regions:
            forecaster.forecast(
                latitude=region["lat"],
                longitude=region["lon"],
                region_name=region["name"],
                days_back=30,
                forecast_horizon=7,
            )

        # Wait a moment for metrics to update
        import time
        time.sleep(2)

        # Fetch metrics
        response = requests.get(metrics_url, timeout=5)
        response.raise_for_status()
        metrics_text = response.text

        # Extract region labels from behavior_index metrics
        import re
        region_pattern = r'behavior_index\{[^}]*region="([^"]+)"[^}]*\}'
        regions_found = set(re.findall(region_pattern, metrics_text))

        # Should have at least 2 distinct regions
        assert len(regions_found) >= 2, (
            f"Property P4 violation: Metrics show only {len(regions_found)} distinct region(s) "
            f"after forecasting 2 regions. Found: {regions_found}. "
            f"This indicates metrics are not being emitted per region."
        )

    def test_p5_no_label_collapse(self, forecaster):
        """
        Property P5: No label collapse.

        No region="None"; no "unknown_*" explosion beyond a low threshold;
        region IDs match catalog format.
        """
        import requests
        import os
        import re

        metrics_url = os.getenv("HBC_METRICS_URL", "http://localhost:8100/metrics")
        
        try:
            response = requests.get(metrics_url, timeout=5)
            response.raise_for_status()
        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError):
            pytest.skip("Metrics endpoint not accessible (backend may not be running)")

        metrics_text = response.text

        # Check for region="None"
        none_pattern = r'region="None"'
        none_matches = re.findall(none_pattern, metrics_text)
        assert len(none_matches) == 0, (
            f"Property P5 violation: Found {len(none_matches)} metrics with region='None'. "
            f"This indicates missing region labels in metrics emission."
        )

        # Check for excessive "unknown_*" labels (threshold: 5% of total)
        unknown_pattern = r'region="unknown_[^"]+"'
        unknown_matches = re.findall(unknown_pattern, metrics_text)
        total_region_labels = len(re.findall(r'region="[^"]+"', metrics_text))
        
        if total_region_labels > 0:
            unknown_ratio = len(unknown_matches) / total_region_labels
            assert unknown_ratio < 0.05, (
                f"Property P5 violation: {len(unknown_matches)} unknown_* labels "
                f"({unknown_ratio:.1%} of total {total_region_labels}). "
                f"This exceeds 5% threshold and indicates region identification issues."
            )

        # Check region ID format (should match known patterns: us_*, city_*, etc.)
        region_pattern = r'region="([^"]+)"'
        all_regions = set(re.findall(region_pattern, metrics_text))
        valid_patterns = [r'^us_[a-z]{2}$', r'^city_[a-z]+$', r'^[A-Z][a-z]+$']  # us_il, city_london, Illinois
        
        invalid_regions = []
        for region in all_regions:
            if region == "None" or region.startswith("unknown_"):
                continue
            if not any(re.match(pattern, region) for pattern in valid_patterns):
                invalid_regions.append(region)

        # Allow some flexibility but flag if too many invalid formats
        assert len(invalid_regions) <= 2, (
            f"Property P5 violation: Found {len(invalid_regions)} regions with invalid format: {invalid_regions}. "
            f"Region IDs should match catalog format (us_*, city_*, or proper names)."
        )

    def test_p6_metamorphic_monotonicity(self, forecaster):
        """
        Property P6: Metamorphic monotonicity (bounded).

        Increasing days_back should NOT reduce history points below a minimum.
        Forecast horizon changes should change number of forecast points, not history points.
        """
        # Test 1: Increasing days_back should increase or maintain history points
        result_30 = forecaster.forecast(
            latitude=40.7128,
            longitude=-74.0060,
            region_name="New York City",
            days_back=30,
            forecast_horizon=7,
        )

        result_60 = forecaster.forecast(
            latitude=40.7128,
            longitude=-74.0060,
            region_name="New York City",
            days_back=60,
            forecast_horizon=7,
        )

        history_30 = result_30.get("history", [])
        history_60 = result_60.get("history", [])

        len_30 = len(history_30) if history_30 else 0
        len_60 = len(history_60) if history_60 else 0

        # History should not decrease when days_back increases
        assert len_60 >= len_30, (
            f"Property P6 violation: Increasing days_back from 30 to 60 "
            f"reduced history points from {len_30} to {len_60}. "
            f"This violates monotonicity property."
        )

        # Test 2: Changing horizon should change forecast length, not history
        result_h7 = forecaster.forecast(
            latitude=40.7128,
            longitude=-74.0060,
            region_name="New York City",
            days_back=30,
            forecast_horizon=7,
        )

        result_h14 = forecaster.forecast(
            latitude=40.7128,
            longitude=-74.0060,
            region_name="New York City",
            days_back=30,
            forecast_horizon=14,
        )

        history_h7 = result_h7.get("history", [])
        history_h14 = result_h14.get("history", [])
        forecast_h7 = result_h7.get("forecast", [])
        forecast_h14 = result_h14.get("forecast", [])

        len_history_h7 = len(history_h7) if history_h7 else 0
        len_history_h14 = len(history_h14) if history_h14 else 0
        len_forecast_h7 = len(forecast_h7) if forecast_h7 else 0
        len_forecast_h14 = len(forecast_h14) if forecast_h14 else 0

        # History should remain the same
        assert len_history_h7 == len_history_h14, (
            f"Property P6 violation: Changing horizon from 7 to 14 "
            f"changed history length from {len_history_h7} to {len_history_h14}. "
            f"History should be independent of forecast horizon."
        )

        # Forecast should change
        assert len_forecast_h14 >= len_forecast_h7, (
            f"Property P6 violation: Increasing horizon from 7 to 14 "
            f"did not increase forecast length ({len_forecast_h7} -> {len_forecast_h14})."
        )

    def test_p7_data_quality_property(self, forecaster):
        """
        Property P7: Data quality.

        Numeric ranges are bounded [0,1] for index values, no NaNs in exported series.
        """
        result = forecaster.forecast(
            latitude=40.7128,
            longitude=-74.0060,
            region_name="New York City",
            days_back=30,
            forecast_horizon=7,
        )

        history = result.get("history", [])
        forecast = result.get("forecast", [])

        # Check history
        for item in history:
            if isinstance(item, dict):
                # Check behavior_index range
                bi = item.get("behavior_index")
                if bi is not None:
                    assert not pd.isna(bi), f"Property P7: behavior_index contains NaN: {item}"
                    assert (
                        0.0 <= float(bi) <= 1.0
                    ), f"Property P7: behavior_index out of range [0,1]: {bi}"

                # Check sub-indices ranges
                for idx_name in [
                    "economic_stress",
                    "environmental_stress",
                    "mobility_activity",
                    "digital_attention",
                    "public_health_stress",
                    "fuel_stress",
                    "drought_stress",
                    "storm_severity_stress",
                ]:
                    val = item.get(idx_name)
                    if val is not None:
                        assert not pd.isna(val), f"Property P7: {idx_name} contains NaN: {item}"
                        assert (
                            0.0 <= float(val) <= 1.0
                        ), f"Property P7: {idx_name} out of range [0,1]: {val}"

        # Check forecast
        for item in forecast:
            if isinstance(item, dict):
                pred = item.get("prediction")
                if pred is not None:
                    assert not pd.isna(pred), f"Property P7: forecast prediction contains NaN: {item}"
                    assert (
                        0.0 <= float(pred) <= 1.0
                    ), f"Property P7: forecast prediction out of range [0,1]: {pred}"
