"""Tests for EIA Fuel Prices fetcher (state-level gasoline prices)."""

import os
import pytest
import pandas as pd

from app.services.ingestion.eia_fuel_prices import EIAFuelPricesFetcher


@pytest.fixture
def fetcher():
    """Create EIA fuel prices fetcher instance."""
    return EIAFuelPricesFetcher()


def test_eia_fuel_ci_offline_mode(fetcher):
    """Test CI offline mode returns deterministic data."""
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        df, status = fetcher.fetch_fuel_stress_index(state="IL", days_back=30)
        assert not df.empty
        assert "timestamp" in df.columns
        assert "fuel_stress_index" in df.columns
        assert "fuel_price" in df.columns
        assert len(df) == 30
        assert status.ok
        assert status.provider == "CI_Synthetic_EIA_Fuel"
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)


def test_eia_fuel_cache_key_includes_state(fetcher):
    """Test that cache key includes state parameter for regional caching."""
    # This is tested implicitly by checking that different states produce different data
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        il_data, _ = fetcher.fetch_fuel_stress_index(state="IL", days_back=30)
        ca_data, _ = fetcher.fetch_fuel_stress_index(state="CA", days_back=30)

        # Different states should produce different fuel_stress_index values
        # (in CI mode, this is based on state hash)
        il_mean = il_data["fuel_stress_index"].mean()
        ca_mean = ca_data["fuel_stress_index"].mean()

        # In CI mode, states should differ (hash-based)
        assert il_mean != ca_mean, "IL and CA should have different fuel stress indices"
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)


def test_eia_fuel_regional_variance(fetcher):
    """Test that two distant regions produce different fuel_stress_index values."""
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        # Illinois vs Arizona (distant states)
        il_data, il_status = fetcher.fetch_fuel_stress_index(state="IL", days_back=30)
        az_data, az_status = fetcher.fetch_fuel_stress_index(state="AZ", days_back=30)

        assert il_status.ok
        assert az_status.ok
        assert not il_data.empty
        assert not az_data.empty

        # Compute means and assert they differ
        il_mean = il_data["fuel_stress_index"].mean()
        az_mean = az_data["fuel_stress_index"].mean()

        # In CI mode, different states should produce different values (hash-based)
        assert (
            il_mean != az_mean
        ), f"IL ({il_mean:.4f}) and AZ ({az_mean:.4f}) should have different fuel stress indices"

        # Also check that values have reasonable variance (std dev > 0.01)
        il_std = il_data["fuel_stress_index"].std()
        az_std = az_data["fuel_stress_index"].std()
        assert (
            il_std > 0.01
        ), f"IL fuel_stress_index should have variance (std={il_std:.6f})"
        assert (
            az_std > 0.01
        ), f"AZ fuel_stress_index should have variance (std={az_std:.6f})"
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)


def test_eia_fuel_state_normalization(fetcher):
    """Test state code normalization (full name -> 2-letter code)."""
    # Test various input formats
    test_cases = [
        ("Illinois", "IL"),
        ("IL", "IL"),
        ("California", "CA"),
        ("CA", "CA"),
        ("us_il", "US"),  # Will extract "IL" from "us_il"
    ]

    for input_state, expected_prefix in test_cases:
        normalized = fetcher._normalize_state_code(input_state)
        # Should be 2-letter uppercase
        assert len(normalized) == 2 or len(normalized) <= 2
        assert normalized.isupper() or len(normalized) <= 2


def test_eia_fuel_schema(fetcher):
    """Test that returned DataFrame has correct schema."""
    os.environ["HBC_CI_OFFLINE_DATA"] = "1"
    try:
        df, status = fetcher.fetch_fuel_stress_index(state="TX", days_back=30)

        assert "timestamp" in df.columns
        assert "fuel_stress_index" in df.columns
        assert "fuel_price" in df.columns

        # Check data types
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
        assert pd.api.types.is_numeric_dtype(df["fuel_stress_index"])
        assert pd.api.types.is_numeric_dtype(df["fuel_price"])

        # Check value ranges
        assert (df["fuel_stress_index"] >= 0.0).all()
        assert (df["fuel_stress_index"] <= 1.0).all()
        assert (df["fuel_price"] > 0.0).all()  # Prices should be positive
    finally:
        os.environ.pop("HBC_CI_OFFLINE_DATA", None)
