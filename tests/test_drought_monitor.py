# SPDX-License-Identifier: PROPRIETARY
"""Tests for U.S. Drought Monitor fetcher."""
import os
import pytest
import pandas as pd

from app.services.ingestion.drought_monitor import DroughtMonitorFetcher


@pytest.fixture
def fetcher():
    """Create a DroughtMonitorFetcher instance."""
    return DroughtMonitorFetcher()


def test_drought_fetcher_initialization(fetcher):
    """Test that fetcher initializes correctly."""
    assert fetcher is not None
    assert fetcher.cache_duration_minutes == 1440


def test_drought_fetch_basic(fetcher):
    """Test basic fetch functionality."""
    # Enable CI offline mode
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        df, status = fetcher.fetch_drought_stress_index(state="IL", days_back=30)
        assert status.ok
        assert not df.empty
        assert "drought_stress_index" in df.columns
        assert "dsci" in df.columns
        assert "timestamp" in df.columns
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)


def test_drought_regional_variance(fetcher):
    """Test that two distant regions produce different drought_stress_index values."""
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        il_data, il_status = fetcher.fetch_drought_stress_index(
            state="IL", days_back=30
        )
        az_data, az_status = fetcher.fetch_drought_stress_index(
            state="AZ", days_back=30
        )

        assert il_status.ok
        assert az_status.ok
        assert not il_data.empty
        assert not az_data.empty

        # Different states should produce different drought_stress_index values
        il_mean = il_data["drought_stress_index"].mean()
        az_mean = az_data["drought_stress_index"].mean()

        # AZ should have higher drought stress than IL (AZ is more arid)
        assert (
            az_mean > il_mean
        ), f"AZ mean ({az_mean:.6f}) should be > IL mean ({il_mean:.6f})"

        # Both should have some variance
        il_std = il_data["drought_stress_index"].std()
        az_std = az_data["drought_stress_index"].std()
        assert (
            il_std > 0.01
        ), f"IL drought_stress_index should have variance (std={il_std:.6f})"
        assert (
            az_std > 0.01
        ), f"AZ drought_stress_index should have variance (std={az_std:.6f})"
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)


def test_drought_cache_key_includes_state(fetcher):
    """Test that cache key includes state parameter."""
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        # Fetch for IL
        il_data, _ = fetcher.fetch_drought_stress_index(state="IL", days_back=30)
        # Fetch for AZ (should be different due to state-specific seed)
        az_data, _ = fetcher.fetch_drought_stress_index(state="AZ", days_back=30)

        # Verify they differ (proves cache key includes state)
        il_mean = il_data["drought_stress_index"].mean()
        az_mean = az_data["drought_stress_index"].mean()
        assert il_mean != az_mean
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)


def test_drought_stress_index_range(fetcher):
    """Test that drought_stress_index values are in valid range [0, 1]."""
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        df, status = fetcher.fetch_drought_stress_index(state="TX", days_back=30)
        assert status.ok
        assert not df.empty

        assert (df["drought_stress_index"] >= 0.0).all()
        assert (df["drought_stress_index"] <= 1.0).all()
        assert pd.api.types.is_numeric_dtype(df["drought_stress_index"])
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)
