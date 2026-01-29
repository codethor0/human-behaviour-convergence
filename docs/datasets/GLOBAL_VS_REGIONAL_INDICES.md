# Global vs Region-Specific Index Map

This document clarifies which behavior indices are global/national (expected to be identical across regions) versus region-specific (must vary across regions).

## Global/National Indices

These indices use global or national-level data sources and **are expected to be identical** across regions:

### economic_stress
- **Source**: VIX/SPY (global market data via yfinance) + FRED indicators (national) + **EIA fuel prices (state-level)** [OK]
- **Scope**: Mixed (global/national components + regional fuel_stress)
- **Expected Behavior**: **MUST vary** across regions (fuel_stress component is state-specific)
- **Reason**: While market volatility is global, fuel prices vary by state (20-40% deviation from national average)
- **Children**: `fuel_stress` (REGIONAL, MVP1) [OK]

### mobility_activity
- **Source**: TSA passenger throughput (national US data)
- **Scope**: National (US regions only)
- **Expected Behavior**: Same value for all US regions
- **Reason**: TSA data is aggregated at the national level

### digital_attention
- **Source**: GDELT global tone aggregate
- **Scope**: Global
- **Expected Behavior**: Same value for all regions (unless region filter is applied)
- **Reason**: Global event tone is not region-specific

### public_health_stress
- **Source**: Public health API (may fallback to OWID global data)
- **Scope**: Varies by source configuration
- **Expected Behavior**: May be constant if using global fallback, or vary if region-specific data is available
- **Note**: Currently may appear constant if region-specific health data is not configured

## Region-Specific Indices

These indices use region-specific data sources and **MUST differ** across regions:

### environmental_stress
- **Source**: Weather data (Open-Meteo) using lat/lon coordinates
- **Scope**: Region-specific
- **Expected Behavior**: **MUST vary** across regions
- **Reason**: Weather conditions differ by location

### political_stress
- **Source**: GDELT legislative/enforcement events with region filter
- **Scope**: Region-specific
- **Expected Behavior**: Should vary across regions
- **Reason**: Political activity differs by state/region

### crime_stress
- **Source**: Region-specific crime data
- **Scope**: Region-specific
- **Expected Behavior**: Should vary across regions
- **Reason**: Crime rates differ by location

### misinformation_stress
- **Source**: Region-specific misinformation signals
- **Scope**: Region-specific
- **Expected Behavior**: Should vary across regions
- **Reason**: Information environment differs by region

### social_cohesion_stress
- **Source**: Region-specific social cohesion indicators
- **Scope**: Region-specific
- **Expected Behavior**: Should vary across regions
- **Reason**: Social dynamics differ by region

## Planned New Indices (Enterprise Expansion)

The following are **planned** per `docs/ENTERPRISE_DATASET_EXPANSION_PLAN.md`. Once implemented, they will be **REGIONAL** and must vary:

| Index | Source | Sub-Index Parent |
|-------|--------|------------------|
| `fuel_stress` | EIA gasoline by state | economic_stress | [OK] **Implemented (MVP1)** |
| `drought_stress` | U.S. Drought Monitor (state) | environmental_stress |
| `eviction_stress` / `housing_cost_burden` | Eviction Lab (state/city) | economic_stress |
| `overdose_stress` / `substance_use_stress` | CDC WONDER (state) | public_health_stress |
| `storm_event_*` (e.g. `heatwave_stress`, `flood_risk_stress`) | NOAA Storm Events (state) | environmental_stress |

All must use geo in fetch and cache keys, emit region-labeled metrics, and pass variance_probe.

## Behavior Index

### behavior_index
- **Composition**: Weighted combination of all sub-indices
- **Scope**: Region-specific (even if some components are global)
- **Expected Behavior**: **MUST vary** across regions
- **Reason**: Even if some components (economic_stress, mobility_activity) are global, region-specific components (environmental_stress, political_stress, etc.) ensure the final behavior_index varies

## Metrics Semantics

### forecast_history_points
- **Meaning**: Number of time-series data points in the historical window
- **Computation**: `len(history_records)` after interpolation/forward-filling
- **Expected Behavior**: Constant across regions when `days_back` parameter is constant
- **Reason**: This is the **window size**, not the number of raw events. With `days_back=30` and interpolation, this typically results in ~78 points for all regions.
- **Note**: This is **NOT** a count of region-specific events. If you need region-dependent event counts, use separate metrics like `signal_samples_total{source,region}`.

### forecast_points_generated
- **Meaning**: Number of forecast points generated
- **Computation**: `len(forecast_records)` based on `forecast_horizon` parameter
- **Expected Behavior**: Constant across regions when `forecast_horizon` parameter is constant
- **Reason**: This is the forecast window size, not region-specific data volume.

## Dashboard Interpretation

When viewing Grafana dashboards:

1. **If you see identical values across regions**:
   - Check which index you're viewing
   - Global indices (economic_stress, mobility_activity) are **expected** to be identical
   - Region-specific indices (environmental_stress, political_stress) **should** differ

2. **If behavior_index appears identical**:
   - This is a bug - behavior_index should always vary due to region-specific components
   - Check if region-specific data sources are failing and falling back to global defaults

3. **If forecast_history_points is identical**:
   - This is **correct** - it represents the time-series window length, not event counts
   - All regions use the same `days_back` parameter, so window size is constant

## Data Source Configuration

To ensure region-specific indices vary:

1. **Weather data**: Automatically uses lat/lon - should work out of the box
2. **Political/crime/misinformation/social_cohesion**: May require region-specific data sources to be configured
3. **Public health**: May require API key or region-specific health data source

If a region-specific index appears constant, check:
- Data source configuration (API keys, endpoints)
- Source registry status (`/api/forecasting/data-sources`)
- Fallback behavior (may be using global defaults)
