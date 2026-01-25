# HBC State Discrepancy Investigation Framework

## Overview

This document describes the comprehensive investigation framework created to systematically prove whether forecasts/metrics truly differ by region, and to identify and fix any root causes if "identical states" is a real bug.

## Investigation Scripts

### 1. `scripts/discrepancy_harness.py`
**Purpose**: Compute deterministic hashes of forecasts to detect region collapse.

**What it does**:
- Loads regions catalog from API
- Generates forecasts for 20+ diverse regions (12 US states + DC + 6 global cities)
- Computes SHA256 hashes of:
  - History series
  - Forecast series  
  - Subindices
- Outputs variance matrix CSV
- Flags P0 if >=80% regions share identical hashes

**Outputs**:
- `forecast_<region_id>.json` - Individual forecast responses
- `forecast_variance_matrix.csv` - Hash comparison matrix
- `discrepancy_harness.log` - Analysis log
- `p0_collapse_detected.txt` - P0 flag if collapse detected

**Usage**:
```bash
export PROOF_DIR=/tmp/hbc_discrepancy_proof_<TIMESTAMP>
python3 scripts/discrepancy_harness.py
```

### 2. `scripts/source_regionality_audit.py`
**Purpose**: Classify and audit each data source for regionality.

**What it does**:
- Classifies sources as GLOBAL, NATIONAL, REGIONAL, or POTENTIALLY_GLOBAL
- Verifies geo inputs are actually used
- Verifies cache keys include region parameters for REGIONAL sources
- Documents expected variance behavior

**Outputs**:
- `source_regionality_manifest.json` - Complete source classification

**Usage**:
```bash
export PROOF_DIR=/tmp/hbc_discrepancy_proof_<TIMESTAMP>
python3 scripts/source_regionality_audit.py
```

### 3. `scripts/cache_key_audit.py`
**Purpose**: Analyze source code for cache key patterns and flag issues.

**What it does**:
- Scans ingestion files for cache key construction
- Identifies REGIONAL sources that don't include geo parameters
- Flags potential "identical states" bugs

**Outputs**:
- `cache_key_audit.json` - Detailed cache key analysis
- `cache_key_issues.json` - Flagged issues (if any)

**Usage**:
```bash
export PROOF_DIR=/tmp/hbc_discrepancy_proof_<TIMESTAMP>
python3 scripts/cache_key_audit.py
```

### 4. `scripts/variance_probe.py` (existing)
**Purpose**: Compute per-source variance scores across regions.

**What it does**:
- Analyzes forecast data for each source/index
- Computes variance statistics (unique count, std dev, range)
- Flags REGIONAL sources with near-zero variance

**Outputs**:
- `variance_probe_report.csv` - Per-source variance metrics
- `variance_probe_report.txt` - Human-readable report

**Usage**:
```bash
python3 scripts/variance_probe.py \
    --forecasts-dir "$PROOF_DIR" \
    --output-csv "$PROOF_DIR/variance_probe_report.csv" \
    --output-report "$PROOF_DIR/variance_probe_report.txt"
```

### 5. `scripts/run_full_discrepancy_investigation.sh`
**Purpose**: Master orchestration script for complete investigation.

**What it does**:
- Executes all investigation phases in sequence
- Captures baseline (git, versions, stack health)
- Runs forecast variance analysis
- Validates metrics truth layer
- Performs source regionality audit
- Generates comprehensive evidence bundle

**Usage**:
```bash
# Ensure stack is running
docker compose up -d

# Wait for readiness, then run:
bash scripts/run_full_discrepancy_investigation.sh
```

## Cache Key Analysis Results

### ✅ Correct Regional Sources (Include Geo Params)
- **Weather**: `{latitude:.4f},{longitude:.4f},{days_back}`
- **OpenAQ**: `openaq_{latitude}_{longitude}_{radius_km}_{days_back}`
- **NWS Alerts**: `nws_alerts_{latitude}_{longitude}_{days_back}`
- **Search Trends**: `search_trends_{region_name or query}_{days_back}`
- **Public Health**: `{region_code or 'default'},{days_back}`
- **Political**: `political_{state_name}_{days_back}`
- **Crime**: `crime_{region_name}_{days_back}`
- **Misinformation**: `misinformation_{region_name}_{days_back}`
- **Social Cohesion**: `social_cohesion_{region_name}_{days_back}`
- **GDELT Legislative**: `gdelt_legislative_{region_name or 'global'}_{days_back}`
- **GDELT Enforcement**: `gdelt_enforcement_{region_name or 'global'}_{days_back}`
- **OpenFEMA**: `openfema_{region_name or 'national'}_{days_back}`
- **OpenStates**: `openstates_{region_name or 'default'}_{days_back}`

### ✅ Correct Global/National Sources (Expected Constant)
- **FRED Economic**: `{series_id}_{days_back}` (national data)
- **EIA Energy**: `{series_id}_{days_back}` (national data)
- **CISA KEV**: `cisa_kev_{days_back}` (global vulnerability catalog)
- **GDELT Tone**: `gdelt_tone_{days_back}` (global average tone - intentional)
- **Mobility (TSA)**: `mobility_tsa_{region_key}_{days_back}` (national, but cache includes region_key for future expansion)

### ⚠️ Potential Issues Found

1. **USGS Earthquakes**: `usgs_earthquakes_{days_back}_{min_magnitude}`
   - **Issue**: No geo parameters in cache key
   - **Analysis**: USGS API supports geographic filtering, but current implementation fetches global data
   - **Status**: May be intentional (global environmental hazard indicator)
   - **Action**: Verify if earthquakes should be region-filtered or remain global

2. **GDELT Events**: `gdelt_events_{days_back}_{event_type}`
   - **Issue**: No region parameter
   - **Analysis**: May be intentional for global event counts
   - **Status**: Needs verification

## Source Classifications

### GLOBAL (Expected Constant)
- `economic_indicators` - Market sentiment (VIX/SPY)
- `fred_economic` - National economic data
- `eia_energy` - National energy data
- `gdelt_tone` - Global average tone

### NATIONAL (Expected Constant for US States)
- `mobility_patterns` - TSA passenger throughput (national aggregate)

### REGIONAL (Must Vary)
- `weather_patterns` - By lat/lon ✅
- `openaq_air_quality` - By lat/lon ✅
- `nws_alerts` - By lat/lon ✅
- `search_trends` - By region_name ✅
- `political_stress` - By state_name ✅
- `crime_stress` - By region_name ✅
- `misinformation_stress` - By region_name ✅
- `social_cohesion_stress` - By region_name ✅
- `gdelt_legislative` - By region_name ✅
- `gdelt_enforcement` - By region_name ✅
- `openfema` - By region_name ✅
- `openstates_legislative` - By region_name ✅

### POTENTIALLY_GLOBAL (May Fallback)
- `public_health` - OWID fallback if API not configured
- `usgs_earthquakes` - Global if not region-filtered (needs verification)

## Investigation Execution

### Prerequisites
1. Stack must be running: `docker compose up -d`
2. Wait for backend readiness: `curl http://localhost:8100/health`
3. Ensure forecasts have been generated for multiple regions

### Execution Steps

1. **Start Investigation**:
   ```bash
   bash scripts/run_full_discrepancy_investigation.sh
   ```

2. **Review Evidence**:
   - Check `forecast_variance_matrix.csv` for hash uniqueness
   - Review `source_regionality_manifest.json` for classifications
   - Check `cache_key_audit.json` for cache key patterns
   - Review `variance_probe_report.txt` for per-source variance

3. **Decision Point**:
   - **If P0 detected**: Review `p0_*.txt` files and proceed to fixes
   - **If variance exists**: Issue is likely UI/dashboard perception, improve UX

## Expected Outcomes

### Scenario A: Variance Exists (Most Likely)
- Forecasts show unique hashes for most regions
- Metrics show distinct region labels
- Regional sources show variance
- **Conclusion**: Computation is correct
- **Action**: Improve UX clarity (labels, variance panels, warm-up indicators)

### Scenario B: State Collapse (P0 Bug)
- >=80% regions share identical hashes
- Metrics show region="None" or single region
- Regional sources show zero variance
- **Conclusion**: Backend regionality bug
- **Action**: Fix root cause (cache keys, region resolution, fallback behavior)

## Root Cause Fix Playbook

If P0 is detected, investigate in this order:

### H1: Region Resolution Failure
**Symptoms**: `region="None"` in metrics, cache keys missing region
**Fix**: Ensure region_id is deterministically resolved
**Files**: `app/core/prediction.py`, region resolution logic

### H2: Cache Key Regionality Bug
**Symptoms**: REGIONAL source cache key missing region parameter
**Fix**: Add region_id/lat/lon/name to cache key
**Files**: Individual ingestion fetchers

### H3: Silent Fallback to Global
**Symptoms**: Errors caught and constant vector returned without marking
**Fix**: Make fallback explicit with metrics and logs
**Files**: Error handling in fetchers

### H4: Too Many Global Sources
**Symptoms**: Most indices are global/national, overall variance is small
**Fix**: Add more regional data sources
**Files**: New source integrations

### H5: Grafana/Dashboard Misinterpretation
**Symptoms**: Panels show only global indices, regional indices not visible
**Fix**: Add explicit labels, variance panels, warm-up indicators
**Files**: Grafana dashboard JSON, UI components

## Evidence Bundle Structure

```
/tmp/hbc_discrepancy_proof_<TIMESTAMP>/
├── commit.txt                          # Git commit SHA
├── git_status.txt                      # Working tree status
├── python_version.txt                  # Python version
├── docker_version.txt                  # Docker version
├── backend_health.json                 # Backend health check
├── frontend_routes_http.txt            # Frontend route status
├── regions.json                        # Regions catalog
├── forecast_<region_id>.json           # Individual forecasts (20+ files)
├── forecast_variance_matrix.csv        # Hash comparison matrix
├── discrepancy_harness.log             # Variance analysis log
├── metrics.txt                         # Backend /metrics dump
├── metrics_region_counts.txt           # Region label distribution
├── prom_region_values.json             # Prometheus label values
├── source_regionality_manifest.json    # Source classification
├── cache_key_audit.json                # Cache key analysis
├── cache_key_issues.json               # Flagged cache key issues
├── variance_probe_report.csv           # Per-source variance metrics
├── variance_probe_report.txt          # Human-readable variance report
├── p0_collapse_detected.txt            # P0 flag (if collapse detected)
└── p0_region_none.txt                  # P0 flag (if region=None found)
```

## Next Steps

1. **Start Stack**: `docker compose up -d`
2. **Run Investigation**: `bash scripts/run_full_discrepancy_investigation.sh`
3. **Review Evidence**: Analyze proof directory contents
4. **Apply Fixes**: If P0 detected, apply surgical fixes with tests
5. **Verify**: Re-run investigation to confirm fixes

## Files Ready

All investigation scripts are ready and can be executed once the stack is running. The framework will systematically prove whether "identical states" is a real bug or expected behavior, and provide evidence for any fixes needed.
