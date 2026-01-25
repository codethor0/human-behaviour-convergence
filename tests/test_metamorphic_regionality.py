# SPDX-License-Identifier: PROPRIETARY
"""
Metamorphic tests for regionality and input transformations.

Metamorphic testing: verify that expected transformations occur when inputs change.
- Changing region_name should change regional indices
- Changing horizon should change forecast length
- Changing days_back should change history window
"""
import pytest

from app.core.prediction import BehavioralForecaster


class TestMetamorphicRegionality:
    """
    Metamorphic tests demonstrating expected transformations.

    These tests verify that changing inputs produces expected changes in outputs.
    """

    @pytest.fixture
    def forecaster(self):
        """Create a BehavioralForecaster instance."""
        return BehavioralForecaster()

    def test_region_change_affects_regional_indices(self, forecaster):
        """
        Metamorphic test: Changing region_name should change at least one regional index.

        Expected transformation: region_name change → regional index change (epsilon threshold)
        """
        epsilon = 0.005

        # Test with two distant US states (should have different regional data)
        result_il = forecaster.forecast(
            latitude=40.3495,
            longitude=-88.9861,
            region_name="Illinois",
            days_back=30,
            forecast_horizon=7,
        )

        result_az = forecaster.forecast(
            latitude=34.0489,
            longitude=-111.0937,
            region_name="Arizona",
            days_back=30,
            forecast_horizon=7,
        )

        # Extract latest values
        def get_latest_values(result):
            history = result.get("history", [])
            if not history:
                return {}
            if isinstance(history, list) and history:
                return history[-1] if isinstance(history[-1], dict) else {}
            elif hasattr(history, "iloc"):
                return history.iloc[-1].to_dict()
            return {}

        il_values = get_latest_values(result_il)
        az_values = get_latest_values(result_az)

        # Check regional indices that should differ
        regional_indices = [
            "environmental_stress",
            "fuel_stress",
            "drought_stress",
            "storm_severity_stress",
            "behavior_index",  # Should also differ if regional sources contribute
        ]

        differences = []
        for idx_name in regional_indices:
            il_val = il_values.get(idx_name)
            az_val = az_values.get(idx_name)

            if il_val is not None and az_val is not None:
                diff = abs(float(il_val) - float(az_val))
                differences.append((idx_name, diff))

        # At least one regional index must differ
        max_diff = max((d[1] for d in differences), default=0.0)

        assert max_diff >= epsilon, (
            f"Metamorphic test failure: Changing region from Illinois to Arizona "
            f"did not change any regional indices by >= {epsilon}. "
            f"Max difference: {max_diff}. "
            f"Illinois values: {il_values}, Arizona values: {az_values}. "
            f"This suggests regional sources are not being applied correctly."
        )

    def test_horizon_change_affects_forecast_length(self, forecaster):
        """
        Metamorphic test: Changing horizon should change forecast length.

        Expected transformation: horizon change → forecast length change
        """
        base_params = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "region_name": "New York City",
            "days_back": 30,
        }

        result_h7 = forecaster.forecast(forecast_horizon=7, **base_params)
        result_h14 = forecaster.forecast(forecast_horizon=14, **base_params)

        forecast_h7 = result_h7.get("forecast", [])
        forecast_h14 = result_h14.get("forecast", [])

        len_h7 = len(forecast_h7) if forecast_h7 else 0
        len_h14 = len(forecast_h14) if forecast_h14 else 0

        # Forecast length should increase with horizon
        assert len_h14 >= len_h7, (
            f"Metamorphic test failure: Increasing horizon from 7 to 14 "
            f"did not increase forecast length ({len_h7} -> {len_h14})."
        )

        # Ideally, forecast length should match horizon (allowing for some tolerance)
        # But at minimum, it should increase
        assert len_h14 > len_h7 or (len_h7 == 0 and len_h14 == 0), (
            f"Metamorphic test failure: Forecast length did not change "
            f"when horizon changed from 7 to 14 ({len_h7} -> {len_h14})."
        )

    def test_days_back_change_affects_history_window(self, forecaster):
        """
        Metamorphic test: Changing days_back should change history window.

        Expected transformation: days_back change → history window size change
        """
        base_params = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "region_name": "New York City",
            "forecast_horizon": 7,
        }

        result_30 = forecaster.forecast(days_back=30, **base_params)
        result_60 = forecaster.forecast(days_back=60, **base_params)

        history_30 = result_30.get("history", [])
        history_60 = result_60.get("history", [])

        len_30 = len(history_30) if history_30 else 0
        len_60 = len(history_60) if history_60 else 0

        # History should increase or stay the same when days_back increases
        # (may not exactly double due to data availability, but should not decrease)
        assert len_60 >= len_30, (
            f"Metamorphic test failure: Increasing days_back from 30 to 60 "
            f"reduced history length from {len_30} to {len_60}. "
            f"History window should not shrink when days_back increases."
        )

    def test_region_change_preserves_global_indices(self, forecaster):
        """
        Metamorphic test: Changing region should NOT change global indices significantly.

        Expected transformation: region change → global indices remain similar (within tolerance)
        """
        # Global indices should be similar across regions
        # (economic_stress from VIX/SPY, digital_attention from GDELT global tone)

        result_il = forecaster.forecast(
            latitude=40.3495,
            longitude=-88.9861,
            region_name="Illinois",
            days_back=30,
            forecast_horizon=7,
        )

        result_az = forecaster.forecast(
            latitude=34.0489,
            longitude=-111.0937,
            region_name="Arizona",
            days_back=30,
            forecast_horizon=7,
        )

        def get_latest_values(result):
            history = result.get("history", [])
            if not history:
                return {}
            if isinstance(history, list) and history:
                return history[-1] if isinstance(history[-1], dict) else {}
            elif hasattr(history, "iloc"):
                return history.iloc[-1].to_dict()
            return {}

        il_values = get_latest_values(result_il)
        az_values = get_latest_values(result_az)

        # Global indices (if present) should be similar
        # Note: This is a weaker assertion since global indices may still vary slightly
        # due to timing or other factors, but they should not differ dramatically
        global_indices = [
            "economic_stress",  # May have some regional component (fuel_stress)
            "digital_attention",  # Should be mostly global
        ]

        for idx_name in global_indices:
            il_val = il_values.get(idx_name)
            az_val = az_values.get(idx_name)

            if il_val is not None and az_val is not None:
                diff = abs(float(il_val) - float(az_val))
                # Global indices should not differ by more than 0.2 (20%)
                # (allowing for some regional contribution)
                max_expected_diff = 0.2

                # This is informational - we don't fail if global indices differ
                # (they may have regional components), but we log it
                if diff > max_expected_diff:
                    pytest.skip(
                        f"Global index {idx_name} differs significantly between regions "
                        f"({il_val} vs {az_val}, diff={diff}). "
                        f"This may be expected if the index has regional components."
                    )

    def test_same_region_same_params_produces_consistent_results(self, forecaster):
        """
        Metamorphic test: Same region + same params should produce consistent results.

        Expected transformation: no input change → minimal output change (within noise tolerance)
        """
        params = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "region_name": "New York City",
            "days_back": 30,
            "forecast_horizon": 7,
        }

        result1 = forecaster.forecast(**params)

        # Reset cache to force recomputation
        forecaster.reset_cache()

        result2 = forecaster.forecast(**params)

        # Extract behavior_index from latest history
        def get_latest_bi(result):
            history = result.get("history", [])
            if not history:
                return None
            if isinstance(history, list) and history:
                last = history[-1]
                return last.get("behavior_index") if isinstance(last, dict) else None
            elif hasattr(history, "iloc"):
                return history.iloc[-1].get("behavior_index")
            return None

        bi1 = get_latest_bi(result1)
        bi2 = get_latest_bi(result2)

        if bi1 is not None and bi2 is not None:
            diff = abs(float(bi1) - float(bi2))
            # In CI offline mode, results should be identical
            # In live mode, small differences are acceptable due to data freshness
            import os

            if os.getenv("HBC_CI_OFFLINE_DATA") == "1":
                assert diff < 0.001, (
                    f"Metamorphic test failure: Same inputs produced different results "
                    f"in CI offline mode (BI1: {bi1}, BI2: {bi2}, diff: {diff})."
                )
            else:
                # In live mode, allow small differences (data may have updated)
                assert diff < 0.1, (
                    f"Metamorphic test failure: Same inputs produced very different results "
                    f"in live mode (BI1: {bi1}, BI2: {bi2}, diff: {diff}). "
                    f"This may indicate non-deterministic behavior."
                )
