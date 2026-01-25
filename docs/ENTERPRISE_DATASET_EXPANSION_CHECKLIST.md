# Enterprise Dataset Expansion - Implementation Checklist

**Use this checklist when implementing each MVP dataset.**

---

## Pre-Implementation Checklist (Per Dataset)

### 1. Research & Planning
- [ ] Review dataset API documentation
- [ ] Verify public/openly licensed status
- [ ] Check data availability (geography, time range)
- [ ] Identify failure modes and fallback strategies
- [ ] Document expected regional variance

### 2. Connector Implementation
- [ ] Create fetcher class in `app/services/ingestion/<dataset_name>.py`
- [ ] Implement `fetch_*` method with geo parameters (state/lat/lon)
- [ ] Add CI offline mode support (`is_ci_offline_mode()`)
- [ ] Implement error handling and fallback behavior
- [ ] Add logging with `structlog`

### 3. Cache Key Design
- [ ] Include geo parameter in cache key (e.g., `{state}`, `{lat}_{lon}`)
- [ ] Verify cache key uniqueness per region
- [ ] Test cache hit/miss behavior

### 4. Feature Engineering
- [ ] Normalize raw data to 0-1 stress index
- [ ] Compute derived features (trends, volatility, etc.)
- [ ] Return DataFrame with standardized columns

### 5. Forecast Pipeline Integration
- [ ] Add fetcher to `BehavioralForecaster.__init__`
- [ ] Call fetcher in `forecast()` method with geo parameters
- [ ] Integrate into sub-index calculation (add as child to parent index)
- [ ] Set appropriate weight (0.10-0.20 typical)
- [ ] Update harmonization logic

### 6. Prometheus Metrics
- [ ] Emit `{dataset}_stress_index{state="..."}` metric
- [ ] Emit `data_source_status{source="<dataset>",region="..."}` metric
- [ ] Emit raw data metrics if useful (e.g., `{dataset}_price{state="..."}`)
- [ ] Verify metrics have region labels (no `region="None"`)

### 7. Source Registry
- [ ] Add `SourceDefinition` to `app/services/ingestion/source_registry.py`
- [ ] Set `class` = "REGIONAL" (or GLOBAL/NATIONAL if appropriate)
- [ ] Set `requires_key` and `can_run_without_key` flags
- [ ] Add description with failure modes

### 8. Tests
- [ ] Create `tests/test_<dataset_name>.py`
- [ ] Test regional variance (two distant regions produce different values)
- [ ] Test cache key includes geo parameter
- [ ] Test CI offline mode returns deterministic data
- [ ] Test error handling and fallback behavior
- [ ] Test Prometheus metrics have region labels

### 9. Variance Probe Integration
- [ ] Add dataset to `scripts/variance_probe.py` classification
- [ ] Classify as REGIONAL (or GLOBAL/NATIONAL)
- [ ] Run variance probe and verify no alerts

### 10. Source Regionality Manifest
- [ ] Add entry to `/tmp/source_regionality_manifest.json` (or proof-dir equivalent)
- [ ] Set `class`, `geo_inputs_used`, `cache_key_fields`, `expected_variance`, `failure_mode`

### 11. Grafana Panels
- [ ] Add panel(s) to appropriate dashboard(s)
- [ ] Tag panel as **REGIONAL** (or GLOBAL/NATIONAL)
- [ ] Add data lag/limitation notes if applicable (e.g., "Provisional data, 2-3 month lag")
- [ ] Add "Limited Geography" warning if applicable

### 12. Documentation
- [ ] Add entry to `docs/DATA_SOURCES.md` (API details, failure modes, observability)
- [ ] Update `docs/GLOBAL_VS_REGIONAL_INDICES.md` (add new sub-index classification)
- [ ] Update `docs/NEW_DATA_SOURCES_PLAN.md` (mark as implemented)
- [ ] Add to `docs/ENTERPRISE_DATASET_EXPANSION_PLAN.md` (mark as complete)

### 13. Validation
- [ ] Run discrepancy investigation (`scripts/run_full_discrepancy_investigation.sh`)
- [ ] Verify variance_probe passes (no alerts for REGIONAL classification)
- [ ] Verify Prometheus invariants (no `region="None"`, multi-region series exist)
- [ ] Verify regression tests pass
- [ ] Generate evidence bundle

---

## MVP 1: EIA Gasoline Prices by State

**File**: `app/services/ingestion/eia_fuel_prices.py`  
**Class**: `EIAFuelPricesFetcher`  
**Sub-Index**: `economic_stress` → `fuel_stress`  
**Expected Variance**: HIGH (state prices vary 20-40%)

### Implementation Steps
- [ ] Create connector file
- [ ] Implement EIA API v2 fetch (`/v2/petroleum/pri/gnd/data/`)
- [ ] Add state parameter to fetch method
- [ ] Cache key: `eia_fuel_{state}_{product}_{days_back}`
- [ ] Feature: `fuel_stress_index` = normalized price deviation from national average
- [ ] Integrate into `economic_stress` (weight: 0.15)
- [ ] Add Prometheus metrics
- [ ] Add Grafana panel ("Fuel Stress by State")
- [ ] Add tests (regional variance, cache key, CI offline)
- [ ] Update source_registry
- [ ] Update variance_probe
- [ ] Update documentation

---

## MVP 2: U.S. Drought Monitor (State)

**File**: `app/services/ingestion/drought_monitor.py`  
**Class**: `DroughtMonitorFetcher`  
**Sub-Index**: `environmental_stress` → `drought_stress`  
**Expected Variance**: VERY HIGH (DSCI ranges 0-500)

### Implementation Steps
- [ ] Create connector file
- [ ] Implement CSV fetch from NDMC (`/DmData/DataTables.aspx`)
- [ ] Add state parameter to fetch method
- [ ] Cache key: `drought_monitor_{state}_{days_back}`
- [ ] Feature: `drought_stress_index` = DSCI / 500 (normalized)
- [ ] Integrate into `environmental_stress` (weight: 0.20)
- [ ] Add Prometheus metrics
- [ ] Add Grafana panel ("Drought Stress by State")
- [ ] Add tests (regional variance, cache key, CI offline)
- [ ] Update source_registry
- [ ] Update variance_probe
- [ ] Update documentation

---

## MVP 3: NOAA Storm Events (State)

**File**: `app/services/ingestion/noaa_storm_events.py`  
**Class**: `NOAAStormEventsFetcher`  
**Sub-Indices**: `environmental_stress` → `heatwave_stress`, `flood_risk_stress`, `storm_severity_stress`  
**Expected Variance**: VERY HIGH (coastal vs plains vs desert)

### Implementation Steps
- [ ] Create connector file
- [ ] Implement bulk CSV download (`/pub/data/swdi/stormevents/csvfiles/`)
- [ ] Add state parameter to fetch method
- [ ] Cache key: `noaa_storms_{state}_{event_type}_{days_back}`
- [ ] Features:
  - [ ] `heatwave_stress` = heat_wave_days / days_in_month
  - [ ] `flood_risk_stress` = flood_events / days_in_month
  - [ ] `storm_severity_stress` = weighted sum (deaths×10 + injuries×1 + log(damage))
- [ ] Integrate into `environmental_stress` (weights: 0.10, 0.10, 0.15)
- [ ] Add Prometheus metrics
- [ ] Add Grafana panels ("Heatwave Stress", "Flood Risk", "Storm Severity")
- [ ] Add tests (regional variance, cache key, CI offline)
- [ ] Update source_registry
- [ ] Update variance_probe
- [ ] Update documentation

---

## MVP 4: Eviction Lab (State/City)

**File**: `app/services/ingestion/eviction_lab.py`  
**Class**: `EvictionLabFetcher`  
**Sub-Index**: `economic_stress` → `housing_stress`  
**Expected Variance**: VERY HIGH (rates vary 10x: 0.5% to 5%+)  
**Note**: Limited geography (~30 states)

### Implementation Steps
- [ ] Create connector file
- [ ] Implement S3 CSV download (`eviction-lab-data-downloads.s3.amazonaws.com`)
- [ ] Add state/city parameters to fetch method
- [ ] Cache key: `eviction_lab_{state}_{city or 'state'}_{days_back}`
- [ ] Feature: `eviction_stress_index` = normalized eviction_rate
- [ ] Integrate into `economic_stress` (weight: 0.20)
- [ ] Add Prometheus metrics
- [ ] Add Grafana panel ("Eviction Stress by State") with "Limited Geography" note
- [ ] Add tests (regional variance, cache key, CI offline, handle missing states)
- [ ] Update source_registry
- [ ] Update variance_probe
- [ ] Update documentation

---

## MVP 5: CDC WONDER Overdose (State)

**File**: `app/services/ingestion/cdc_wonder_overdose.py`  
**Class**: `CDCWonderOverdoseFetcher`  
**Sub-Index**: `public_health_stress` → `substance_use_stress`  
**Expected Variance**: HIGH (rates vary 3-5x: 10-50 per 100k)  
**Note**: Provisional data (2-3 month lag)

### Implementation Steps
- [ ] Create connector file
- [ ] Implement XML API fetch (`/controller/datarequest/`)
- [ ] Add state parameter to fetch method
- [ ] Cache key: `cdc_wonder_overdose_{state}_{drug_type}_{days_back}`
- [ ] Feature: `overdose_stress_index` = normalized overdose_rate
- [ ] Integrate into `public_health_stress` (weight: 0.15)
- [ ] Add Prometheus metrics
- [ ] Add Grafana panel ("Overdose Stress by State") with "Provisional Data" note
- [ ] Add tests (regional variance, cache key, CI offline)
- [ ] Update source_registry
- [ ] Update variance_probe
- [ ] Update documentation

---

## Post-Implementation Validation (All MVP Datasets)

### Discrepancy Investigation
- [ ] Run `scripts/run_full_discrepancy_investigation.sh`
- [ ] Verify forecast variance (≥70% regions with unique hashes)
- [ ] Verify metrics region labels (no `region="None"`, >10 distinct regions)
- [ ] Review evidence bundle

### Variance Probe
- [ ] Run `scripts/variance_probe.py` with new datasets
- [ ] Verify no alerts for REGIONAL classifications
- [ ] Verify GLOBAL/NATIONAL sources remain constant

### Prometheus Invariants
- [ ] Check no `region="None"` labels
- [ ] Check multi-region series exist for new metrics
- [ ] Check `data_source_status{source,region}` metrics

### Regression Tests
- [ ] All existing tests pass
- [ ] New regional variance tests pass
- [ ] CI offline mode tests pass

### Documentation
- [ ] All documentation files updated
- [ ] Source regionality manifest updated
- [ ] Grafana panels tagged correctly

---

## Success Criteria (Final Check)

✅ Two distant regions (Illinois vs Arizona) show divergence in ≥3 independent sub-indices within 30 days  
✅ Dashboards clearly distinguish global vs regional signals  
✅ Forecasts are auditable back to source-level contributors  
✅ Zero regressions in existing workflows  
✅ All REGIONAL sources pass variance_probe  
✅ All Prometheus invariants pass

---

**Use this checklist for each MVP dataset implementation. Check off items as you complete them.**
