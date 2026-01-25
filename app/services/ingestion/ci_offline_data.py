# SPDX-License-Identifier: PROPRIETARY
"""CI offline data mode for deterministic behavior in CI environments.

When HBC_CI_OFFLINE_DATA=1 is set, data fetchers will return synthetic deterministic
data instead of making real external API calls. This ensures:
- Docker Gates GATE G has metrics to verify
- CI runs are deterministic and don't depend on external API availability
- Tests can run without network access

This mode is ONLY active when the environment variable is explicitly set.
Normal local/production runs are unaffected.
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np


def is_ci_offline_mode() -> bool:
    """Check if CI offline data mode is enabled."""
    return os.getenv("HBC_CI_OFFLINE_DATA", "0") == "1"


def generate_synthetic_time_series(
    days: int = 90,
    base_value: float = 0.5,
    volatility: float = 0.1,
    trend: float = 0.0,
    seed: Optional[int] = None,
) -> pd.DataFrame:
    """
    Generate a deterministic synthetic time series for CI testing.

    Args:
        days: Number of days of data
        base_value: Base value (0.0-1.0)
        volatility: Random variation amplitude
        trend: Linear trend per day
        seed: Random seed for reproducibility

    Returns:
        DataFrame with columns: timestamp, value
    """
    if seed is not None:
        np.random.seed(seed)

    end_date = datetime.now()
    dates = [end_date - timedelta(days=i) for i in range(days, 0, -1)]

    # Generate synthetic values with trend and noise
    values = []
    for i, date in enumerate(dates):
        # Base value + trend + random noise
        value = base_value + (trend * i) + np.random.normal(0, volatility)
        # Clip to valid range
        value = max(0.0, min(1.0, value))
        values.append(value)

    return pd.DataFrame(
        {
            "timestamp": dates,
            "value": values,
        }
    )


def get_ci_mobility_data(region_id: str) -> pd.DataFrame:
    """Get synthetic mobility data for CI mode."""
    # Use region_id hash as seed for deterministic but varied data per region
    seed = abs(hash(region_id)) % 10000
    return generate_synthetic_time_series(
        days=90,
        base_value=0.6,
        volatility=0.08,
        trend=0.001,
        seed=seed,
    )


def get_ci_search_trends_data(region_id: str) -> pd.DataFrame:
    """Get synthetic search trends data for CI mode."""
    seed = abs(hash(region_id + "_search")) % 10000
    return generate_synthetic_time_series(
        days=90,
        base_value=0.4,
        volatility=0.12,
        trend=-0.0005,
        seed=seed,
    )


def get_ci_public_health_data(region_id: str) -> pd.DataFrame:
    """Get synthetic public health data for CI mode."""
    seed = abs(hash(region_id + "_health")) % 10000
    return generate_synthetic_time_series(
        days=90,
        base_value=0.3,
        volatility=0.05,
        trend=0.0002,
        seed=seed,
    )


def get_ci_economic_data(region_id: str) -> pd.DataFrame:
    """Get synthetic economic stress data for CI mode."""
    seed = abs(hash(region_id + "_econ")) % 10000
    return generate_synthetic_time_series(
        days=90,
        base_value=0.45,
        volatility=0.09,
        trend=0.0003,
        seed=seed,
    )


def get_ci_market_sentiment_data() -> Dict[str, Any]:
    """Get synthetic market sentiment data for CI mode."""
    return {
        "market_stress": 0.35,
        "timestamp": datetime.now().isoformat(),
        "source": "ci_synthetic",
    }


def get_ci_event_data(region_id: str) -> pd.DataFrame:
    """Get synthetic event data (GDELT-style) for CI mode."""
    seed = abs(hash(region_id + "_events")) % 10000
    return generate_synthetic_time_series(
        days=90,
        base_value=0.25,
        volatility=0.15,
        trend=0.0,
        seed=seed,
    )


def get_ci_weather_data(region_id: str) -> pd.DataFrame:
    """Get synthetic weather stress data for CI mode."""
    seed = abs(hash(region_id + "_weather")) % 10000
    return generate_synthetic_time_series(
        days=30,
        base_value=0.15,
        volatility=0.08,
        trend=0.0,
        seed=seed,
    )


def get_ci_air_quality_data() -> pd.DataFrame:
    """Generate synthetic OpenAQ air quality data for CI."""
    dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
    np.random.seed(42)  # Deterministic for CI
    pm25 = np.random.uniform(5.0, 35.0, len(dates))  # PM2.5 in µg/m³
    pm10 = np.random.uniform(10.0, 50.0, len(dates))  # PM10 in µg/m³
    # Simple AQI calculation (US EPA scale)
    aqi = np.where(
        pm25 <= 12, 50,
        np.where(pm25 <= 35.4, 100, np.where(pm25 <= 55.4, 150, 200))
    )
    return pd.DataFrame({
        "timestamp": dates,
        "pm25": pm25,
        "pm10": pm10,
        "aqi": aqi,
    })


def get_ci_energy_data(series_id: str) -> pd.DataFrame:
    """Get synthetic EIA energy data for CI mode."""
    # Use series_id hash as seed for deterministic but varied data per series
    seed = abs(hash(series_id)) % 10000
    return generate_synthetic_time_series(
        days=90,
        base_value=0.5,
        volatility=0.1,
        trend=0.0,
        seed=seed,
    )


def get_ci_fuel_prices_data(state_code: str) -> pd.DataFrame:
    """Get synthetic EIA fuel prices data for CI mode (state-specific)."""
    import numpy as np
    # Use state_code hash as seed for deterministic but varied data per state
    seed = abs(hash(f"eia_fuel_{state_code}")) % 10000
    np.random.seed(seed)

    end_date = datetime.now()
    dates = [end_date - timedelta(days=i) for i in range(90, 0, -1)]

    # Synthetic prices: base varies by state (simulating regional variance)
    base_price = 3.0 + (hash(state_code) % 100) / 100.0  # $3.00-$4.00 range
    prices = [base_price + np.random.normal(0, 0.1) for _ in dates]

    # Compute national average (simulated)
    national_avg = 3.50

    # Compute stress index: deviation from national average, normalized
    stress_indices = []
    for price in prices:
        deviation = (price - national_avg) / national_avg  # -0.2 to +0.2 range
        # Normalize to 0-1: sigmoid-like transformation
        stress = 0.5 + (deviation * 2.5)  # Scale deviation
        stress = max(0.0, min(1.0, stress))  # Clip to [0, 1]
        stress_indices.append(stress)

    return pd.DataFrame({
        "timestamp": dates,
        "fuel_price": prices,
        "fuel_stress_index": stress_indices,
    })


def get_ci_drought_monitor_data(state_code: str, days_back: int = 90) -> pd.DataFrame:
    """Get synthetic drought monitor data for CI mode (state-specific)."""
    import numpy as np
    # Use state_code hash as seed for deterministic but varied data per state
    seed = abs(hash(f"drought_{state_code}")) % 10000
    np.random.seed(seed)

    end_date = datetime.now()
    dates = [end_date - timedelta(days=i) for i in range(days_back, 0, -1)]

    # Synthetic DSCI: base varies by state (simulating regional variance)
    # CA typically high (300-450), FL typically low (0-150), IL moderate (50-200)
    state_dsci_baselines = {
        "CA": 350, "TX": 150, "FL": 50, "AZ": 300, "NM": 250,
        "NV": 280, "UT": 200, "CO": 180, "WY": 150, "MT": 120,
        "IL": 80, "IA": 60, "NY": 40, "MA": 30, "WA": 100,
    }
    baseline_dsci = state_dsci_baselines.get(state_code, 100)

    # Generate DSCI values with variation
    dsci_values = []
    for i, date in enumerate(dates):
        # Add weekly variation (drought changes slowly)
        week_num = i // 7
        variation = np.random.normal(0, 30)  # Moderate variation
        dsci = baseline_dsci + variation
        dsci = max(0, min(500, dsci))  # Clip to valid DSCI range
        dsci_values.append(dsci)

    # Normalize DSCI (0-500) to drought_stress_index (0-1)
    stress_indices = [dsci / 500.0 for dsci in dsci_values]

    return pd.DataFrame({
        "timestamp": dates,
        "dsci": dsci_values,
        "drought_stress_index": stress_indices,
    })


def get_ci_storm_events_data(state_code: str, days_back: int = 90) -> pd.DataFrame:
    """Get synthetic NOAA storm events data for CI mode (state-specific)."""
    import numpy as np
    # Use state_code hash as seed for deterministic but varied data per state
    seed = abs(hash(f"noaa_storms_{state_code}")) % 10000
    np.random.seed(seed)

    end_date = datetime.now()
    dates = [end_date - timedelta(days=i) for i in range(days_back, 0, -1)]

    # State-specific patterns (FL: hurricanes/floods, AZ: heat waves, TX: mixed)
    state_patterns = {
        "FL": {"storm_severity": 0.6, "heatwave": 0.4, "flood": 0.7},
        "AZ": {"storm_severity": 0.2, "heatwave": 0.9, "flood": 0.1},
        "TX": {"storm_severity": 0.5, "heatwave": 0.7, "flood": 0.3},
        "CA": {"storm_severity": 0.3, "heatwave": 0.5, "flood": 0.4},
        "IL": {"storm_severity": 0.4, "heatwave": 0.3, "flood": 0.5},
        "NY": {"storm_severity": 0.3, "heatwave": 0.2, "flood": 0.4},
    }
    pattern = state_patterns.get(state_code, {"storm_severity": 0.3, "heatwave": 0.3, "flood": 0.3})

    # Generate values with variation
    storm_severity_values = []
    heatwave_values = []
    flood_values = []

    for i, date in enumerate(dates):
        # Monthly variation
        month_variation = np.random.normal(0, 0.1)

        base_severity = pattern["storm_severity"] + month_variation
        storm_severity_values.append(max(0.0, min(1.0, base_severity)))

        base_heatwave = pattern["heatwave"] + month_variation
        heatwave_values.append(max(0.0, min(1.0, base_heatwave)))

        base_flood = pattern["flood"] + month_variation
        flood_values.append(max(0.0, min(1.0, base_flood)))

    return pd.DataFrame({
        "timestamp": dates,
        "storm_severity_stress": storm_severity_values,
        "heatwave_stress": heatwave_values,
        "flood_risk_stress": flood_values,
    })


def get_ci_data_source_status() -> List[Dict[str, Any]]:
    """
    Get synthetic data source status for CI mode.

    Returns a list of all expected data sources with 'healthy' status.
    This ensures data_source_status metrics are populated in CI.
    """
    sources = [
        "mobility",
        "search_trends",
        "public_health",
        "economic_fred",
        "market_sentiment",
        "gdelt_events",
        "owid_health",
        "weather",
        "usgs_earthquakes",
        "openfema",
        "political",
        "crime_safety",
    ]

    return [
        {
            "source": source,
            "status": "healthy",
            "last_update": datetime.now().isoformat(),
            "ci_mode": True,
        }
        for source in sources
    ]
