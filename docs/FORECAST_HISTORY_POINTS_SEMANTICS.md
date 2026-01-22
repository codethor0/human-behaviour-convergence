# forecast_history_points Metric Semantics

## What It Represents

The `forecast_history_points` metric represents the **number of time-series data points in the historical window** used for forecasting, **not** the number of raw events or region-specific signals.

## Computation

```python
forecast_history_points_gauge.labels(region=region_id).set(len(history_records))
```

Where `history_records` is the result of:
1. Fetching data from multiple sources for `days_back` days (default: 30)
2. Harmonizing and merging time series on a daily frequency
3. Forward-filling missing values (e.g., weekends for market data)
4. Interpolating sparse data (e.g., weekly/monthly FRED indicators)

## Expected Behavior

### Constant Across Regions (By Design)

When all regions use the same `days_back` parameter (e.g., 30 days):

- **All regions will have the same `forecast_history_points` value** (typically ~78 points)
- This is **correct and expected** behavior
- The value represents the time-series window size, not region-specific data volume

### Why It's Constant

1. **Same time window**: All forecasts use `days_back=30` by default
2. **Daily frequency**: Data is resampled to daily frequency
3. **Interpolation**: Sparse data (weekly/monthly) is interpolated to daily
4. **Forward-filling**: Missing values are forward-filled to create continuous series

Result: ~78 daily data points for a 30-day window with interpolation.

## Common Misconception

**Myth**: "If `forecast_history_points` is the same for all regions, the system isn't region-aware."

**Reality**: 
- `forecast_history_points` measures **window size**, not **data content**
- The **values** within those points differ across regions (weather, political events, etc.)
- Region-specific variation is visible in `behavior_index` and region-specific sub-indices

## If You Need Region-Dependent Event Counts

If you want to track the number of **raw events or signals** per region (which would vary), you would need separate metrics:

```promql
# Example (not currently implemented):
signal_samples_total{source="weather", region="us_mn"}  # Number of weather data points
signal_samples_total{source="gdelt", region="us_mn"}     # Number of GDELT events
signal_freshness_seconds{source="weather", region="us_mn"}  # Data freshness
```

These would show:
- Different regions may have different numbers of weather stations
- Different regions may have different volumes of GDELT events
- Different regions may have different data freshness

## Dashboard Labeling

The Grafana dashboard panel for `forecast_history_points` should be labeled as:

**"History Window Size (points)"** or **"Time-Series Window Length"**

Not:
- ❌ "Events in Region"
- ❌ "Region-Specific Data Points"
- ❌ "Historical Events Count"

## Verification

To verify the metric is working correctly:

```bash
# All regions should have the same value when days_back is constant
curl -s http://localhost:8100/metrics | grep forecast_history_points

# Expected output (all regions = ~78):
# forecast_history_points{region="us_mn"} 78.0
# forecast_history_points{region="us_ca"} 78.0
# forecast_history_points{region="city_nyc"} 78.0
```

If you see different values, check:
1. Are different `days_back` parameters being used?
2. Is there a bug in the harmonization/interpolation logic?

## Summary

- **Metric**: `forecast_history_points{region="..."}`
- **Meaning**: Time-series window size (number of daily data points)
- **Expected**: Constant across regions when `days_back` is constant
- **Reason**: Window size, not data content
- **Region-specific variation**: Visible in `behavior_index` and sub-indices, not in window size
