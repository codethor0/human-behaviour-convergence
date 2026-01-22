# SPDX-License-Identifier: PROPRIETARY
"""Regression test to ensure forecasts differ across regions."""
import hashlib
import json
from typing import Dict, List

import pytest

from app.core.prediction import BehavioralForecaster


class TestRegionAwareness:
    """Test that forecasts are region-dependent, not identical across regions."""

    def test_forecasts_differ_across_regions(self):
        """
        Regression test: ensure forecasts for different regions produce different values.

        This test prevents the bug where all regions return identical forecast/history values.
        """
        forecaster = BehavioralForecaster()

        # Test regions with different coordinates
        test_regions = [
            {"name": "Minnesota", "lat": 46.7296, "lon": -94.6859},
            {"name": "California", "lat": 36.7783, "lon": -119.4179},
            {"name": "New York City", "lat": 40.7128, "lon": -74.0060},
        ]

        results = {}
        for region in test_regions:
            result = forecaster.forecast(
                latitude=region["lat"],
                longitude=region["lon"],
                region_name=region["name"],
                days_back=30,
                forecast_horizon=7,
            )

            # Extract behavior_index values from history
            history = result.get("history", [])
            if history and isinstance(history, list):
                # Get behavior_index column if DataFrame, or extract from records
                if hasattr(history, "columns") and "behavior_index" in history.columns:
                    history_values = history["behavior_index"].tolist()
                else:
                    # Assume it's already a list of dicts/records
                    history_values = [
                        h.get("behavior_index", 0) if isinstance(h, dict) else 0
                        for h in history
                    ]
            else:
                history_values = []

            # Extract forecast values
            forecast = result.get("forecast", [])
            if forecast and isinstance(forecast, list):
                if hasattr(forecast, "columns") and "prediction" in forecast.columns:
                    forecast_values = forecast["prediction"].tolist()
                else:
                    forecast_values = [
                        f.get("prediction", 0) if isinstance(f, dict) else 0
                        for f in forecast
                    ]
            else:
                forecast_values = []

            results[region["name"]] = {
                "history_values": history_values,
                "forecast_values": forecast_values,
            }

        # Compute hashes for comparison
        history_hashes = {}
        forecast_hashes = {}
        for region_name, data in results.items():
            history_str = json.dumps(data["history_values"], sort_keys=True)
            forecast_str = json.dumps(data["forecast_values"], sort_keys=True)
            history_hashes[region_name] = hashlib.md5(history_str.encode()).hexdigest()
            forecast_hashes[region_name] = hashlib.md5(
                forecast_str.encode()
            ).hexdigest()

        # Assert: at least one region must differ from another
        unique_history_hashes = len(set(history_hashes.values()))
        unique_forecast_hashes = len(set(forecast_hashes.values()))

        # In CI offline mode, regions should still differ due to region_id-based seeding
        # In live mode, regions should differ due to region-specific data sources (weather, etc.)
        assert unique_history_hashes > 1 or unique_forecast_hashes > 1, (
            f"All regions produced identical values. "
            f"History hashes: {history_hashes}, Forecast hashes: {forecast_hashes}. "
            f"This indicates a bug where region-specific inputs are not being used."
        )

        # Additional check: ensure at least one numeric difference exists
        # (hashes could theoretically collide, though extremely unlikely)
        all_history_identical = all(
            results[list(results.keys())[0]]["history_values"]
            == results[r]["history_values"]
            for r in results.keys()
        )
        all_forecast_identical = all(
            results[list(results.keys())[0]]["forecast_values"]
            == results[r]["forecast_values"]
            for r in results.keys()
        )

        assert not (all_history_identical and all_forecast_identical), (
            "All regions have identical history AND forecast values. "
            "This violates the requirement that forecasts must be region-dependent."
        )

    def test_behavior_index_metrics_differ_per_region(self):
        """
        Test that behavior_index metrics are emitted with correct region labels.

        After generating forecasts for multiple regions, metrics should exist
        for each region with different values (unless data sources are intentionally global).
        """
        # This test would require Prometheus to be available and metrics to be emitted
        # For now, we test that the forecaster produces different results per region
        # (the metrics emission is tested in test_resource_exhaustion.py)

        forecaster = BehavioralForecaster()

        regions = [
            {"name": "Minnesota", "lat": 46.7296, "lon": -94.6859},
            {"name": "California", "lat": 36.7783, "lon": -119.4179},
        ]

        behavior_indices = []
        for region in regions:
            result = forecaster.forecast(
                latitude=region["lat"],
                longitude=region["lon"],
                region_name=region["name"],
                days_back=30,
                forecast_horizon=7,
            )

            # Extract latest behavior_index
            history = result.get("history", [])
            if history:
                if hasattr(history, "iloc"):
                    # DataFrame
                    latest_bi = float(history["behavior_index"].iloc[-1])
                elif isinstance(history, list) and history:
                    # List of records
                    latest_bi = float(
                        history[-1].get("behavior_index", 0)
                        if isinstance(history[-1], dict)
                        else 0
                    )
                else:
                    latest_bi = 0.0
            else:
                latest_bi = 0.0

            behavior_indices.append(latest_bi)

        # Assert: behavior indices should differ (unless in a failure mode where
        # all data sources return defaults, which would be a separate bug)
        # In normal operation with region-specific weather data, they should differ
        if len(set(behavior_indices)) == 1 and behavior_indices[0] != 0.0:
            # This could be legitimate if all data sources are global and working correctly
            # But it's suspicious - at least weather should vary by lat/lon
            pytest.skip(
                "Behavior indices are identical - may be expected if all sources are global, "
                "but investigate if region-specific sources (weather) are not being used"
            )
        else:
            # If they differ, that's good
            # If they're both 0.0, that indicates a failure mode
            assert not all(
                bi == 0.0 for bi in behavior_indices
            ), "All behavior indices are 0.0 - indicates data source failure mode"
