# SPDX-License-Identifier: PROPRIETARY
"""Tests for NOAA Storm Events fetcher."""
import os
import pytest
import pandas as pd

from app.services.ingestion.noaa_storm_events import NOAAStormEventsFetcher


@pytest.fixture
def fetcher():
    """Create a NOAAStormEventsFetcher instance."""
    return NOAAStormEventsFetcher()


def test_storm_fetcher_initialization(fetcher):
    """Test that fetcher initializes correctly."""
    assert fetcher is not None
    assert fetcher.cache_duration_minutes == 4320


def test_storm_fetch_basic(fetcher):
    """Test basic fetch functionality."""
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        df, status = fetcher.fetch_storm_stress_indices(state="FL", days_back=30)
        assert status.ok
        assert not df.empty
        assert "storm_severity_stress" in df.columns
        assert "heatwave_stress" in df.columns
        assert "flood_risk_stress" in df.columns
        assert "timestamp" in df.columns
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)


def test_storm_regional_variance(fetcher):
    """Test that two distant regions produce different storm stress values."""
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        fl_data, fl_status = fetcher.fetch_storm_stress_indices(
            state="FL", days_back=30
        )
        az_data, az_status = fetcher.fetch_storm_stress_indices(
            state="AZ", days_back=30
        )

        assert fl_status.ok
        assert az_status.ok
        assert not fl_data.empty
        assert not az_data.empty

        # FL should have higher flood_risk, AZ should have higher heatwave_stress
        fl_flood_mean = fl_data["flood_risk_stress"].mean()
        az_flood_mean = az_data["flood_risk_stress"].mean()
        assert (
            fl_flood_mean > az_flood_mean
        ), f"FL flood ({fl_flood_mean:.6f}) should be > AZ flood ({az_flood_mean:.6f})"

        az_heatwave_mean = az_data["heatwave_stress"].mean()
        fl_heatwave_mean = fl_data["heatwave_stress"].mean()
        assert (
            az_heatwave_mean > fl_heatwave_mean
        ), f"AZ heatwave ({az_heatwave_mean:.6f}) should be > FL heatwave ({fl_heatwave_mean:.6f})"
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)


def test_storm_cache_key_includes_state(fetcher):
    """Test that cache key includes state parameter."""
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        fl_data, _ = fetcher.fetch_storm_stress_indices(state="FL", days_back=30)
        az_data, _ = fetcher.fetch_storm_stress_indices(state="AZ", days_back=30)

        # Verify they differ (proves cache key includes state)
        fl_mean = fl_data["storm_severity_stress"].mean()
        az_mean = az_data["storm_severity_stress"].mean()
        assert fl_mean != az_mean
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)


def test_storm_stress_indices_range(fetcher):
    """Test that all stress indices are in valid range [0, 1]."""
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        df, status = fetcher.fetch_storm_stress_indices(state="TX", days_back=30)
        assert status.ok
        assert not df.empty

        for col in ["storm_severity_stress", "heatwave_stress", "flood_risk_stress"]:
            assert (df[col] >= 0.0).all(), f"{col} should be >= 0"
            assert (df[col] <= 1.0).all(), f"{col} should be <= 1"
            assert pd.api.types.is_numeric_dtype(df[col]), f"{col} should be numeric"
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)
