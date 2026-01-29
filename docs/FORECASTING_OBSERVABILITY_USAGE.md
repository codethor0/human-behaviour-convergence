# Forecasting Observability - Usage Guide

This guide explains how to use the forecasting observability features, including the model registry, metrics, and Grafana dashboards.

## Overview

The forecasting observability system provides:
- **Model Registry**: Standardized interface for forecasting models
- **Model Metrics**: Prometheus metrics for model performance tracking
- **Grafana Dashboards**: Visual monitoring of forecast quality and model performance

## Quick Start

### 1. Start the Stack

```bash
# Start all services (backend, Prometheus, Grafana)
docker compose up -d --build

# Or start backend only
uvicorn app.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Generate Forecasts

Forecasts automatically emit metrics when generated via the API:

```bash
# Generate a forecast (metrics are emitted automatically)
curl -X POST http://localhost:8000/api/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "region_name": "New York City",
    "days_back": 30,
    "forecast_horizon": 7
  }'
```

### 3. Verify Metrics

Check that metrics are being emitted:

```bash
# View all model metrics
curl http://localhost:8100/metrics | grep hbc_model_

# View specific metrics
curl http://localhost:8100/metrics | grep "hbc_model_mae"
curl http://localhost:8100/metrics | grep "hbc_forecast_compute_duration_seconds"
```

### 4. View Dashboards

1. Open Grafana: http://localhost:3001
2. Navigate to dashboards:
   - **Model Performance Hub** (`model-performance`) - Compare model performance metrics
   - **Forecast Quality and Drift** (`forecast-quality-drift`) - Monitor forecast quality and computation duration
   - **Baselines Dashboard** (`baselines`) - Compare baseline models (naive, seasonal naive)
   - **Classical Models** (`classical_models`) - Compare statistical models (exponential smoothing, ARIMA)

## Model Registry

### Available Models

The model registry provides access to multiple forecasting models:

#### Baseline Models
- **`naive`**: Returns last observed value
- **`seasonal_naive`**: Returns value from same period in previous season

#### Statistical Models
- **`exponential_smoothing`**: Holt-Winters exponential smoothing (requires statsmodels)
- **`arima`**: ARIMA model (requires statsmodels)

### Using the Model Registry

```python
from app.core.model_registry import get_registry

# Get the global registry
registry = get_registry()

# List available models
models = registry.list()
# ['naive', 'seasonal_naive', 'exponential_smoothing', 'arima']

# Get a specific model
model = registry.get("exponential_smoothing")

# Get default model (exponential_smoothing if available, else naive)
default_model = registry.get_default()

# Use a model to generate forecast
import pandas as pd
history = pd.Series([0.5, 0.6, 0.7, 0.65, 0.7],
                    index=pd.date_range("2025-01-01", periods=5, freq="D"))
result = model.forecast(history, horizon=7)
```

### API Endpoint

List available models via the API:

```bash
curl http://localhost:8000/api/forecasting/models
```

Response includes model name, description, type, and parameters.

## Prometheus Metrics

### Model Performance Metrics

All metrics are labeled with `region` and `model`:

- **`hbc_model_mae{region="...", model="..."}`**: Mean Absolute Error (gauge)
- **`hbc_model_rmse{region="...", model="..."}`**: Root Mean Squared Error (gauge)
- **`hbc_model_mape{region="...", model="..."}`**: Mean Absolute Percentage Error (gauge)
- **`hbc_interval_coverage{region="...", model="..."}`**: Prediction interval coverage % (gauge)
- **`hbc_backtest_last_run_timestamp_seconds{region="...", model="..."}`**: Last backtest timestamp (gauge)

### Forecast Metrics

- **`hbc_forecast_compute_duration_seconds{region="...", model="..."}`**: Computation duration histogram
- **`hbc_forecast_total{region="...", model="...", outcome="success|empty"}`**: Forecast outcome counter
- **`hbc_model_selected{region="...", model="..."}`**: Currently selected model (1 if selected, 0 otherwise)

### Querying Metrics

Example PromQL queries:

```promql
# Average MAE across all models for a region
avg(hbc_model_mae{region="New York City"})

# Model with lowest RMSE
topk(1, hbc_model_rmse{region="New York City"})

# Forecast success rate
sum(rate(hbc_forecast_total{outcome="success"}[5m])) /
sum(rate(hbc_forecast_total[5m]))

# P95 computation duration by model
histogram_quantile(0.95,
  rate(hbc_forecast_compute_duration_seconds_bucket[5m]))
```

## Grafana Dashboards

### Model Performance Hub

**UID**: `model-performance`

**Panels**:
- MAE by Model (timeseries)
- RMSE by Model (timeseries)
- MAPE by Model (timeseries)
- Interval Coverage by Model (timeseries)
- Model Selection Count (table)
- Performance Comparison (table)

**Variables**:
- `region`: Filter by region
- `model`: Filter by model (supports "All")

### Forecast Quality and Drift

**UID**: `forecast-quality-drift`

**Panels**:
- Computation Duration by Model (P50/P95)
- Success Rate
- Output Stability (Delta)
- History Points Trend
- Forecast Points Generated
- Interval Coverage by Model
- Last Backtest Run by Model
- Forecast Outcomes by Model

**Variables**:
- `region`: Filter by region
- `model`: Filter by model (supports "All")

### Baselines Dashboard

**UID**: `baselines`

**Panels**:
- Naive vs Seasonal Naive Performance
- Top 10 Regions by MAE (baseline models)

### Classical Models Dashboard

**UID**: `classical_models`

**Panels**:
- MAE Comparison (exponential smoothing vs ARIMA)
- Performance Metrics by Model

## Verification Steps

### 1. Verify Metrics Emission

```bash
# After generating forecasts, check metrics endpoint
curl http://localhost:8100/metrics | grep -E "hbc_model_|hbc_forecast"

# Should see metrics like:
# hbc_model_mae{region="New York City",model="exponential_smoothing"} 0.123
# hbc_forecast_total{region="New York City",model="exponential_smoothing",outcome="success"} 1.0
```

### 2. Verify Dashboards Load

1. Open Grafana: http://localhost:3001
2. Navigate to Dashboards
3. Search for "Model Performance" or "Forecast Quality"
4. Verify panels render with data (may show "No data" if no forecasts generated yet)

### 3. Verify Model Registry

```python
from app.core.model_registry import get_registry

registry = get_registry()
assert "naive" in registry.list()
assert "seasonal_naive" in registry.list()
# exponential_smoothing and arima depend on statsmodels availability
```

### 4. Run Tests

```bash
# Run model registry tests
pytest tests/test_model_registry.py -v

# Run model metrics tests
pytest tests/test_model_metrics.py -v

# Run Grafana dashboard tests
pytest tests/test_grafana_dashboards.py -v

# Run all forecasting tests
pytest tests/test_forecasting_endpoints.py -v
```

## Troubleshooting

### Metrics Not Appearing

1. **Check Prometheus is running**: `curl http://localhost:9090/-/healthy`
2. **Check backend metrics endpoint**: `curl http://localhost:8100/metrics`
3. **Verify forecasts are being generated**: Check backend logs
4. **Check Prometheus is scraping**: Verify in Prometheus UI under Status > Targets

### Dashboards Show "No Data"

1. **Generate forecasts first**: Metrics only appear after forecasts are generated
2. **Check time range**: Ensure dashboard time range includes forecast generation time
3. **Verify region/model filters**: Check that selected region/model have data
4. **Check Prometheus queries**: Use Grafana's "Explore" to test PromQL queries directly

### Model Registry Empty

1. **Check dependencies**: `exponential_smoothing` and `arima` require statsmodels
2. **Verify imports**: Check that `app/core/model_registry.py` imports successfully
3. **Check logs**: Look for import errors in application logs

## CI/CD Integration

### Running Tests in CI

The test suite includes:
- Model registry functionality tests
- Model metrics emission tests
- Grafana dashboard JSON validation tests
- API endpoint integration tests

All tests should pass in CI:

```bash
pytest tests/test_model_registry.py tests/test_model_metrics.py tests/test_grafana_dashboards.py
```

### Metrics in CI

Metrics gracefully degrade if Prometheus is unavailable:
- No errors are raised
- Metrics emission is skipped silently
- Application continues to function normally

## References

- **Model Registry**: `docs/FORECASTING_MODEL_REGISTRY.md`
- **Model Evaluation**: `app/core/model_evaluation.py`
- **Model Metrics**: `app/core/model_metrics.py`
- **Implementation Plan**: `docs/FORECASTING_OBSERVABILITY_PLAN.md`
- **E2E Verification**: `scripts/e2e_verification_loop.sh`

## Next Steps

1. **Model Comparison**: Implement automatic model selection based on performance
2. **Ensemble Forecasting**: Combine multiple models for improved accuracy
3. **Alerting**: Set up alerts for model performance degradation
4. **A/B Testing**: Compare model performance across different regions
