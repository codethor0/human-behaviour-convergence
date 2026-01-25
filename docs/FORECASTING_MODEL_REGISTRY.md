# Forecasting Model Registry

Technical documentation of forecasting models implemented in HBC.

## Model Families

### A) Baselines

#### Naive (Last Value)
- **Implementation**: Returns last observed value for all forecast steps
- **Use Case**: Baseline comparison, minimal history scenarios
- **Parameters**: None
- **Output**: Single value repeated for horizon

#### Seasonal Naive
- **Implementation**: Returns value from same period in previous season
- **Use Case**: Baseline with seasonality awareness
- **Parameters**: `seasonal_period` (default: 7 for weekly)
- **Output**: Seasonal pattern repeated

### B) Classical Statistical

#### Exponential Smoothing (Holt-Winters)
- **Implementation**: statsmodels.tsa.holtwinters.ExponentialSmoothing
- **Parameters**:
  - `trend`: "add" (additive trend)
  - `seasonal`: "add" (additive seasonality) if series >= 30 days, else None
  - `seasonal_periods`: min(7, len(series) // 4) for weekly seasonality
- **Use Case**: Primary forecasting model for behavior_index
- **Output**: Point forecast + standard error for intervals
- **Status**: IMPLEMENTED

#### ARIMA/SARIMA
- **Implementation**: Not yet implemented
- **Parameters**: (p, d, q) for ARIMA, (p, d, q)(P, D, Q, s) for SARIMA
- **Use Case**: Alternative to exponential smoothing for non-seasonal or complex patterns
- **Status**: NOT IMPLEMENTED (stub with TODO)

### C) ML Tabular Time-Series (Optional)

#### XGBoost/LightGBM
- **Implementation**: Not implemented
- **Status**: STUB (requires feature engineering pipeline)
- **Note**: Only implement if dependencies already present

### D) Deep Learning (Optional)

#### N-BEATS, TFT, DeepAR
- **Implementation**: Not implemented
- **Status**: NOT PLANNED (requires significant dependencies)
- **Note**: Keep out unless deliberately adopting forecasting library

## Model Output Contract

Every model run must emit:

- `model_name`: String identifier (e.g., "exponential_smoothing", "naive")
- `horizon`: Number of forecast steps
- `history_points`: Number of historical data points used
- `forecast_points`: Number of forecast points generated
- `created_at`: ISO timestamp
- `region_id`: Region identifier (never None)
- `prediction`: Array of forecast values
- `lower_bound`: Array of lower interval bounds (if intervals supported)
- `upper_bound`: Array of upper interval bounds (if intervals supported)
- `std_error`: Standard error estimate (if available)

## Evaluation Metrics

### Point Forecast Metrics

- **MAE** (Mean Absolute Error): Average absolute difference between forecast and actual
- **RMSE** (Root Mean Squared Error): Square root of mean squared error
- **MAPE** (Mean Absolute Percentage Error): Average percentage error
- **sMAPE** (Symmetric MAPE): Symmetric version of MAPE

### Interval Metrics

- **Coverage %**: Percentage of actuals falling within prediction intervals
- **Average Interval Width**: Mean width of prediction intervals
- **Pinball Loss**: For quantile forecasts (if quantiles supported)

## Backtesting

Rolling-origin evaluation:

- Split history into train/test windows
- For each window:
  - Train model on training data
  - Generate forecast for test period
  - Compute evaluation metrics
- Aggregate metrics across all windows

## Prometheus Metrics

Model observability metrics:

- `hbc_model_mae{region="...", model="..."}` - Mean Absolute Error
- `hbc_model_rmse{region="...", model="..."}` - Root Mean Squared Error
- `hbc_model_mape{region="...", model="..."}` - Mean Absolute Percentage Error
- `hbc_interval_coverage{region="...", model="..."}` - Interval coverage percentage
- `hbc_backtest_last_run_timestamp_seconds{region="...", model="..."}` - Last backtest run time

## Model Selection

Current selection logic:

- If statsmodels available: Use Exponential Smoothing
- If statsmodels not available: Fallback to simple moving average
- Model selection based on series length:
  - >= 30 days: Seasonal exponential smoothing
  - < 30 days: Trend-only exponential smoothing

## Future Enhancements

1. Model comparison framework (run multiple models, select best)
2. Automatic model selection based on AIC/BIC
3. Ensemble forecasting (weighted combination of models)
4. Online learning (update models as new data arrives)
