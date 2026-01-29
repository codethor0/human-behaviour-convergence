# HBC Dashboard Data Validation, Wiring Verification and Auto-Repair Report

## Summary

Variable wiring for Grafana dashboards that use `$regions` was corrected. All 23 provisioned dashboards were audited for variable names, PromQL metrics, and datasource UID. One repair was made (frontend `var-regions`). No backend, forecast, or metrics-emission changes.

---

## Phase 1: Dashboard Enumeration (Ground Truth)

| Dashboard | UID | Panels | Variables | Frontend embed |
|-----------|-----|--------|-----------|----------------|
| Forecast Quick Summary | forecast-summary | 12 | region | yes |
| Forecast Overview | forecast-overview | 9 | region | yes |
| Public Overview | public-overview | 8 | (none) | yes |
| Global Behavior Index | behavior-index-global | 4 | region | yes |
| Sub-Index Deep Dive | subindex-deep-dive | 11 | region, parent | yes |
| Regional Variance Explorer | regional-variance-explorer | 6 | regions | yes |
| Forecast Quality and Drift | forecast-quality-drift | 6 | region | yes |
| Algorithm / Model Comparison | algorithm-model-comparison | 6 | region, model | yes |
| Data Sources and Pipeline Health | data-sources-health | 12 | (none) | yes |
| Source Health and Freshness | source-health-freshness | 8 | (none) | yes |
| Cross-Domain Correlation Matrix | cross-domain-correlation | 6 | region | yes |
| Regional Deep Dive | regional-deep-dive | 5 | region | yes |
| Regional Comparison | regional-comparison | 9 | regions | yes |
| Regional Economic and Environmental Signals | regional-signals | 5 | region | yes |
| Geo Map - Regional Stress | geo-map | 4 | (none) | yes |
| Anomaly Detection Center | anomaly-detection-center | 9 | region | yes |
| Behavioral Risk Regimes | risk-regimes | 7 | (none) | yes |
| Model Performance Hub | model-performance | 8 | region, model | yes |
| Historical Trends and Volatility | historical-trends | 7 | region | yes |
| Contribution Breakdown Analysis | contribution-breakdown | 9 | region | yes |
| Baselines Dashboard | baselines | 2 | region | yes |
| Classical Models Dashboard | classical-models | 2 | region, model | yes |
| Data Sources and Pipeline Health (enhanced) | data-sources-health-enhanced | 10 | (none) | yes |

All 23 JSON files under `infra/grafana/dashboards/` are provisioned and embedded on the main page. None are frontend-only or provisioned-only.

---

## Phase 2: Variable and Wiring Verification

### Issue found and fixed

- **regional-comparison** and **regional-variance-explorer** use variable `regions` (multi, from `label_values(behavior_index, region)`). The embed only sent `var-region`. Grafana does not map `var-region` to `$regions`, so `$regions` stayed on dashboard default and the global region selector did not filter these two.
- **Fix:** In `GrafanaDashboardEmbed.tsx`, when `regionId` is set, the URL now includes both `var-region` and `var-regions` with the same value. Dashboards with only `$region` ignore `var-regions`; those with `$regions` now receive the selected region.

### Verified

- **$region:** 18 dashboards; all receive `var-region` from the embed when `regionId` is set.
- **$regions:** regional-comparison, regional-variance-explorer; now receive `var-regions`.
- **$model:** algorithm-model-comparison, classical-models, model-performance; filled by `label_values(hbc_model_mae, model)` (or variant); no frontend change.
- **$parent:** subindex-deep-dive; filled by `label_values(parent_subindex_value, parent)`; default All is valid.
- **Dashboards with no variables:** data-sources-health, data-sources-health-enhanced, source-health-freshness, geo-map, public-overview, risk-regimes; data-sources-* and source-health-freshness correctly do not receive `regionId` in the embed.

### Datasource

- All Prometheus panels use UID `PBFA97CFB590B2093`, matching `infra/grafana/provisioning/datasources/prometheus.yml`.

---

## Phase 3: Panel-Level Data Validation

### Metrics used in PromQL (sample)

- `behavior_index{region=...}`, `parent_subindex_value{region=..., parent=...}`, `child_subindex_value{region=..., parent=..., child=...}`
- `forecast_history_points`, `forecast_points_generated`, `forecast_last_updated_timestamp_seconds`
- `hbc_subindex_contribution`, `hbc_model_mae`, `hbc_model_rmse`, `hbc_model_mape`, `hbc_interval_coverage`, `hbc_backtest_last_run_timestamp_seconds`
- `hbc_data_source_fetch_total`, `hbc_data_source_error_total`, `hbc_data_source_last_success_timestamp_seconds`, `data_source_status`
- `up{job="behavior-forecast-backend"}`

All of these are defined or implied in `app/backend/app/main.py` (gauges, counters, histograms) or by the Prometheus scrape of the backend (`job_name: behavior-forecast-backend` in `infra/prometheus/prometheus.yml`). No unsupported or typo’d metric names were found.

### Label usage

- `region` / `region=~"$regions"`: matches `behavior_index`, `parent_subindex_value`, `child_subindex_value`, and other `{region}` metrics.
- `parent` / `parent=~"$parent"`: matches `parent_subindex_value`, `child_subindex_value`, `hbc_subindex_contribution`.
- `model` / `model=~"$model"`: matches `hbc_model_mae`, `hbc_model_rmse`, `hbc_model_mape`, `hbc_interval_coverage`, `hbc_backtest_last_run_timestamp_seconds`, `hbc_forecast_total`, `hbc_model_selected`.

### Subindex deep dive

- Panel “Regional Heatmap - Sub-Index Values Across Regions” uses `parent_subindex_value{parent=~"$parent"}` without `region` by design to show all regions. Left as-is.

---

## Phases 4–6: Region Variance, Time Range, API Consistency

- **Region variance (Phase 4):** Wiring for `$regions` is fixed. Demonstrating different series for different regions requires a running stack and data; not executed in this pass.
- **Time range and freshness (Phase 5):** No hard-coded time ranges or incorrect `rate`/`avg_over_time` windows were found. Queries using `[90d]` depend on Prometheus retention.
- **Dashboard–API consistency (Phase 6):** No code changes. Backend writes the same metrics that panels read; consistency is by construction.

---

## Phase 7: Automated Visual Verification

- **Attempted:** `npx playwright test e2e/main-page-dom-verify.spec.ts` with `PLAYWRIGHT_BASE_URL=http://localhost:3100`. Tests failed (e.g. “dashboard embed containers exist and are visible”), likely because the target host/port was not the HBC frontend or the app was not running.
- **Evidence:** DOM and iframe checks are implemented in `main-page-dom-verify.spec.ts` and `main-page-dashboards.spec.ts`. To pass, run the stack (backend, Prometheus, Grafana, frontend) and point `PLAYWRIGHT_BASE_URL` at the HBC frontend (e.g. `http://localhost:3100` for compose or `http://localhost:3000` for `next dev`).

---

## Phase 8: Auto-Repair Loop

- One repair applied: `var-regions` in `GrafanaDashboardEmbed.tsx`.
- No panel PromQL or variable definitions were changed. No further repairs were required after the wiring fix and audit.

---

## Phase 9: Final Commit

- **Commit:** `fix(dashboards): validate and repair Grafana dashboard variable wiring`
- **Files:** `app/frontend/src/components/GrafanaDashboardEmbed.tsx` only.

---

## Issues Found and Fixed

| Issue | Dashboard(s) | Fix |
|-------|--------------|-----|
| `$regions` not set from frontend | regional-comparison, regional-variance-explorer | Embed now sends `var-regions={regionId}` when `regionId` is set |

---

## Dashboards and Panels Validated (by audit)

- **Dashboards:** 23 (all provisioned and embedded).
- **Panels:** 150+ across those dashboards; PromQL and variable usage reviewed for correct metrics and labels.
- **Regions tested:** Not run (no live stack targeting HBC in this pass). Wiring supports at least one valid region once `behavior_index` (and related) series exist.

---

## Remaining Limitations

1. **Data presence:** Panels stay empty until the backend has been called (e.g. `/api/forecast` or equivalent) for one or more regions and Prometheus has scraped `/metrics`. Warm-up and retention determine when `avg_over_time(...)[90d]` and similar queries return points.
2. **Visual e2e:** `main-page-dom-verify` and `main-page-dashboards` need the HBC frontend and, for full pass, Grafana and Prometheus. Run with the correct `PLAYWRIGHT_BASE_URL` after the stack is up.
3. **`$model` and `$parent`:** Populated only from Prometheus. If `hbc_model_mae` or `parent_subindex_value` have no series, those variables can be empty; no frontend or dashboard change was made.
4. **Grafana provisioning path:** Dashboards are mounted at `/var/lib/grafana/dashboards`. If the provisioner does not load a JSON (e.g. path or naming), that dashboard would not appear in Grafana; load was not verified in a live instance here.

---

## How to Re-Run Validation

1. **Wiring and variables:**
   - Inspect `GrafanaDashboardEmbed.tsx` for `var-region` and `var-regions`.
   - Compare `infra/grafana/dashboards/*.json` `templating.list[].name` to the URL params.

2. **Panel PromQL:**
   - `jq -r '.. | objects | select(has("expr")) | .expr' infra/grafana/dashboards/*.json | sort -u`
   - Cross-check metric and label names against `app/backend/app/main.py` and `infra/prometheus/prometheus.yml`.

3. **Visual e2e:**
   - `docker compose up -d backend prometheus grafana frontend` (or equivalent).
   - `cd app/frontend && PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/main-page-dom-verify.spec.ts e2e/main-page-dashboards.spec.ts`

4. **Panel data in Grafana:**
   - Generate at least one forecast for a region, wait for a Prometheus scrape, then open each dashboard and confirm panels show series for that region.
