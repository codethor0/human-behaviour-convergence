# HBC State Discrepancy Investigation - Summary

## Status: Framework Ready [OK]

**Date**: 2026-01-22
**Evidence Directory**: `/tmp/hbc_discrepancy_proof_20260122_122847/`

## Investigation Framework Deployed

A comprehensive investigation framework has been created to systematically prove whether forecasts/metrics truly differ by region. All scripts are ready to execute once the stack is running.

## Quick Start

```bash
# 1. Start stack
docker compose up -d

# 2. Wait for readiness
curl http://localhost:8100/health

# 3. Run full investigation
bash scripts/run_full_discrepancy_investigation.sh
```

## Scripts Created

1. **`scripts/discrepancy_harness.py`** - Forecast variance analysis (hash-based)
2. **`scripts/source_regionality_audit.py`** - Source classification and audit
3. **`scripts/cache_key_audit.py`** - Cache key pattern analysis
4. **`scripts/run_full_discrepancy_investigation.sh`** - Master orchestration

## Preliminary Findings (Code Analysis)

### Cache Keys: [OK] CORRECT
- **13 REGIONAL sources** correctly include geo parameters in cache keys
- **Forecast cache** correctly includes lat/lon/region_name
- **1 potential issue**: USGS earthquakes (may be intentional - global data)

### Source Classifications
- **GLOBAL**: economic_indicators, fred_economic, eia_energy, gdelt_tone
- **NATIONAL**: mobility_patterns (TSA - national aggregate)
- **REGIONAL**: weather, openaq, nws_alerts, search_trends, political, crime, misinformation, social_cohesion, gdelt_legislative, gdelt_enforcement, openfema, openstates
- **POTENTIALLY_GLOBAL**: public_health (OWID fallback), usgs_earthquakes (needs verification)

## Expected Outcomes

### Scenario A: Variance Exists (Most Likely)
- Forecasts show unique hashes for most regions
- Metrics show distinct region labels
- **Action**: Improve UX clarity (labels, variance panels)

### Scenario B: State Collapse (P0 Bug)
- >=80% regions share identical hashes
- Metrics show region="None"
- **Action**: Apply root cause fixes

## Evidence Will Be Saved To

`/tmp/hbc_discrepancy_proof_<TIMESTAMP>/`

Key files:
- `forecast_variance_matrix.csv` - Hash comparison
- `source_regionality_manifest.json` - Source classifications
- `cache_key_audit.json` - Cache key analysis
- `variance_probe_report.txt` - Per-source variance
- `p0_*.txt` - P0 issue flags (if any)

## Documentation

- **Framework Guide**: `docs/DISCREPANCY_INVESTIGATION_FRAMEWORK.md`
- **Deep Report**: `/tmp/HBC_STATE_DISCREPANCY_DEEP_REPORT.md`

## Next Action

**Start the stack and run the investigation to get definitive proof.**
