# Example Results

This folder contains example outputs from the convergence forecasting pipeline.

## Files

- `ground_truth.csv` — Ground truth behavioral states (aggregate, coarse-grained)
- `forecasts.csv` — Point forecasts for each time step
- `intervals.csv` — 95% prediction intervals
- `metrics.csv` — Error metrics (MAE, RMSE, CRPS, coverage)

## Format

All CSV files follow this structure:

### ground_truth.csv
```csv
timestamp,location_id,state,count
2025-01-01,grid_001,active,12500
2025-01-01,grid_002,active,8300
...
```

### forecasts.csv
```csv
timestamp,location_id,forecast_mean,forecast_median
2025-01-01,grid_001,12450,12400
2025-01-01,grid_002,8250,8200
...
```

### intervals.csv
```csv
timestamp,location_id,lower_95,upper_95
2025-01-01,grid_001,10200,14700
2025-01-01,grid_002,6900,9600
...
```

### metrics.csv
```csv
metric,value
mae,450.2
rmse,612.5
crps,0.082
coverage_95,0.948
...
```

## Notes

- All data is synthetic and for demonstration purposes only.
- Real-world results would be aggregated to ≥5 km spatial and ≥24 h temporal resolution to preserve privacy.
