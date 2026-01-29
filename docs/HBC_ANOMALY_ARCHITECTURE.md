# HBC Anomaly Detection Architecture

This document describes the layered anomaly detection system for the HBC behavioral forecasting platform. All anomalies are quantitatively defined, emitted as Prometheus metrics, and surfaced in Grafana.

## Data Flow

- Raw time-series: backend computes behavior_index and subindices per region.
- Metrics: emitted to Prometheus (behavior_index, parent_subindex_value, etc.).
- Layer 1 (univariate): backend maintains rolling window per region; computes static bounds and z-score; emits behavior_index_static_* and behavior_index_zscore*.
- Grafana: Anomaly Detection Center and related dashboards query Prometheus and display time-series, bands, and anomaly flags.

## Metric Catalog (Anomaly-Relevant)

| Metric | Labels | Role |
|--------|--------|------|
| behavior_index | region | Primary signal; anomaly detection input |
| parent_subindex_value | region, parent | Driver attribution |
| behavior_index_static_upper_bound | region | Upper bound (percentile-based) |
| behavior_index_static_lower_bound | region | Lower bound (percentile-based) |
| behavior_index_static_anomaly | region | 1 if value outside bounds else 0 |
| behavior_index_zscore | region | Rolling z-score |
| behavior_index_zscore_anomaly | region | 1 if \|zscore\| > k else 0 |
| behavior_index_baseline | region | EWMA baseline |
| behavior_index_upper_band | region | baseline + k*std |
| behavior_index_lower_band | region | baseline - k*std |
| behavior_index_residual | region | value - baseline |
| behavior_index_residual_zscore | region | z-score of residual |
| behavior_index_seasonal_anomaly | region | 1 if outside band else 0 |
| behavior_index_residual_anomaly | region | 1 if \|residual_z\| > k else 0 |
| hbc_multivariate_md_score | region | Squared Mahalanobis-style (diagonal) distance |
| hbc_multivariate_md_anomaly | region | 1 if md_score > threshold else 0 |

## Layer 1: Univariate Anomalies

### Static Bounds (Backend-Emitted)

- **Formula**: For each region, a rolling window of the last N behavior_index values is kept. Lower bound = percentile_low (default 5th), upper bound = percentile_high (default 95th).
- **Emitted metrics**: behavior_index_static_upper_bound{region}, behavior_index_static_lower_bound{region}, behavior_index_static_anomaly{region}.
- **Threshold**: static_anomaly = 1 if value < lower_bound or value > upper_bound; else 0.

### Z-Score

- **Formula**: z_t = (x_t - mean_window) / std_window. If std_window == 0, z_t = 0.
- **Emitted metrics**: behavior_index_zscore{region}, behavior_index_zscore_anomaly{region}.
- **Threshold**: zscore_anomaly = 1 if |z_t| > k (default k = 2.5); else 0.

### Implementation

- **Module**: `app/services/anomaly/univariate.py` (UnivariateAnomalyTracker).
- **Window**: 500 observations per region (configurable).
- **Invocation**: On each behavior_index update in the metrics pipeline, the tracker is updated and the five new gauges are set.

## Layer 2: Dynamic Statistical (Seasonal Bands + Residual)

### Baseline and Bands

- **Formula**: EWMA baseline: baseline_t = alpha * value_t + (1 - alpha) * baseline_{t-1}. Rolling std of values; upper_band = baseline + k_band * std, lower_band = baseline - k_band * std.
- **Emitted metrics**: behavior_index_baseline{region}, behavior_index_upper_band{region}, behavior_index_lower_band{region}, behavior_index_seasonal_anomaly{region}.
- **Threshold**: seasonal_anomaly = 1 if value < lower_band or value > upper_band; else 0.

### Residual Z-Score

- **Formula**: residual = value - baseline. Rolling mean and std of residuals; residual_zscore = (residual - mean_residual) / std_residual.
- **Emitted metrics**: behavior_index_residual{region}, behavior_index_residual_zscore{region}, behavior_index_residual_anomaly{region}.
- **Threshold**: residual_anomaly = 1 if |residual_zscore| > k_residual (default 2.5); else 0.

### Implementation

- **Module**: `app/services/anomaly/seasonal.py` (SeasonalResidualTracker).
- **Parameters**: window_size=500, ewma_alpha=0.1, band_k=2.0, residual_k=2.5.
- **Invocation**: Same pipeline as Layer 1; seasonal tracker updated after univariate.

## Layer 3: Multivariate (Mahalanobis-Style)

### Formula

- **Feature vector**: [behavior_index, economic_stress, environmental_stress, ...] (behavior_index plus parent subindices).
- **Diagonal covariance**: D^2 = sum_i ((x_i - mu_i) / sigma_i)^2. Mean and std per dimension from rolling window.
- **Emitted metrics**: hbc_multivariate_md_score{region}, hbc_multivariate_md_anomaly{region}.
- **Threshold**: md_anomaly = 1 if md_score > threshold (default 15.0); else 0.

### Implementation

- **Module**: `app/services/anomaly/multivariate.py` (MultivariateTracker).
- **Parameters**: window_size=500, md_threshold=15.0.
- **Invocation**: Same pipeline; multivariate tracker updated after seasonal; feature vector built from latest behavior_index and latest subindices per region.

## Dashboards

- **Anomaly Detection Center** (uid: anomaly-detection-center): Primary hub. Includes:
  - Behavior Index with Anomaly Bands (PromQL-based bands).
  - Anomaly Score by Region (Z-Score) (PromQL).
  - Behavior Index vs Emitted Static Bands (Backend): uses backend-emitted static bounds and z-score.
  - Behavior Index vs Seasonal Band (Layer 2): baseline and upper/lower bands.
  - Residual Shock Radar (Layer 2): residual z-score with threshold lines.
  - Multivariate Anomaly Score (Layer 3): MD score time series and anomaly flag.
  - Current anomaly flags (row): per-layer stat panels for $region (static, z-score, seasonal, residual, multivariate).
- **Risk Regimes** (uid: risk-regimes): overlay panel "Regions in Anomaly (Backend Layer 1)" – count of regions with static anomaly; link to Anomaly Center.
- **Regional Deep Dive** (uid: regional-deep-dive): overlay panel "Anomaly status ($region)" – max across all five layer flags; link to Anomaly Center.
- **Forecast Quality and Drift** (uid: forecast-quality-drift): overlay panel "Anomaly status ($region)" – max across five layer flags; link to Anomaly Center.
- **Regional Variance**, **Model Performance**: Secondary; further anomaly overlays can be added without changing existing panels.

## Tuning

- **Window size**: Larger window = smoother bounds and z-score; slower to react. Default 500.
- **Percentiles**: 5th/95th give narrow band; 1st/99th wider.
- **Z-score k**: 2.0 = more sensitive; 3.0 = fewer flags. Default 2.5.

## Validation / Testing

- **Unit tests**: `tests/test_anomaly.py` – UnivariateAnomalyTracker (static bounds, z-score), SeasonalResidualTracker (baseline, bands, residual z-score), MultivariateTracker (md_score, md_anomaly). Run: `PYTHONPATH=. pytest tests/test_anomaly.py -v` (or via project Makefile/CI).
- **Integration**: Anomaly trackers are invoked from the metrics pipeline in `app/backend/app/main.py` on each behavior_index emission; Prometheus scrapes the new gauges; Grafana panels query Prometheus.
- **Tuning**: Window size and thresholds are configurable per layer; see Tuning section and module defaults.

## Non-Breaking Guarantees

- No existing API or Grafana UID is changed.
- New metrics and panels are additive only.
- Existing panels continue to use PromQL-only bands where applicable.
