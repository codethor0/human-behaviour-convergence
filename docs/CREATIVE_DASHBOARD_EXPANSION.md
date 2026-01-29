# HBC Creative Dashboard and Data-Source Expansion

Technical design and inventory for additive dashboard and data-source work. No prompt text or orchestration instructions are stored in the repo.

## Phase 0 – Baseline (current state)

### Grafana dashboards (27)

| UID | Title (approx) |
|-----|-----------------|
| executive-storyboard | Executive Storyboard |
| forecast-quality-drift | Forecast Quality Drift |
| anomaly-detection-center | Anomaly Detection Center |
| risk-regimes | Risk Regimes |
| regional-deep-dive | Regional Deep Dive |
| forecast-performance-storybook | Forecast Performance Storybook |
| regional-comparison-storyboard | Regional Comparison Storyboard |
| shock-recovery-timeline | Shock Recovery Timeline |
| source-health-freshness | Source Health Freshness |
| public-overview | Public Overview |
| model-performance | Model Performance |
| data-sources-health | Data Sources Health |
| forecast-overview | Forecast Overview |
| contribution-breakdown | Contribution Breakdown |
| subindex-deep-dive | Subindex Deep Dive |
| forecast-summary | Forecast Summary |
| regional-comparison | Regional Comparison |
| cross-domain-correlation | Cross Domain Correlation |
| geo-map | Geo Map |
| algorithm-model-comparison | Algorithm Model Comparison |
| regional-variance-explorer | Regional Variance Explorer |
| classical-models | Classical Models |
| baselines | Baselines |
| data-sources-health-enhanced | Data Sources Health Enhanced |
| regional-signals | Regional Signals |
| behavior-index-global | Behavior Index Global |
| historical-trends | Historical Trends |
| hbc-anomaly-atlas | Anomaly Atlas and Regime Shifts (new) |

### Key Prometheus metrics (existing)

- `behavior_index{region}` – main index
- `parent_subindex_value`, `child_subindex_value` – subindices
- `behavior_index_static_anomaly`, `behavior_index_static_upper_bound`, `behavior_index_static_lower_bound`
- `behavior_index_zscore`, `behavior_index_zscore_anomaly`
- `behavior_index_baseline`, `behavior_index_upper_band`, `behavior_index_lower_band`
- `behavior_index_residual_anomaly`, `behavior_index_seasonal_anomaly`
- `hbc_multivariate_md_score`, `hbc_multivariate_md_anomaly`
- Data quality / source health metrics as in data_sources_health dashboards

### New dashboards (additive only)

- **hbc-anomaly-atlas** – Anomaly Atlas and Regime Shifts: heatmap-style view of anomaly state, regime timeline for selected region, top current anomalies table. Uses existing behavior_index and anomaly metrics only; no new collectors.

### Candidate data sources (for future phases)

- Economic: FRED (already used), World Bank, DBnomics
- Social/mobility: Google Community Mobility, NYC Open Data
- Environmental: NOAA, EPA AirNow
- News/events: GDELT

Each future source to be gated by `HBC_ENABLE_<SOURCE>`, env-based credentials, timeouts, and graceful degradation.

## First slice implemented

- **Dashboard:** `hbc-anomaly-atlas` (Anomaly Atlas and Regime Shifts). File: `infra/grafana/dashboards/hbc_anomaly_atlas.json`.
- **Panels:** (1) Purpose text; (2) Behavior index and z-score time series for selected region; (3) Anomaly state over time (static, z-score, seasonal, residual, multivariate flags) for selected region; (4) Table of current anomaly state and behavior index per region (all regions).
- **Hub:** New card in "Additional Analytics Dashboards" (full-width), with `regionId={selectedRegion}` so the global region selector drives the dashboard variable.
- **Metrics used:** Existing only: `behavior_index`, `behavior_index_zscore`, `behavior_index_static_anomaly`, `behavior_index_zscore_anomaly`, `behavior_index_seasonal_anomaly`, `behavior_index_residual_anomaly`, `hbc_multivariate_md_anomaly`. No new collectors or Prometheus metrics.
- **Verification:** All 23 tests in `test_api_backend.py` and `test_forecasting_endpoints.py` pass. No existing dashboard UIDs or panels modified. No prompt text or emojis in repo.
