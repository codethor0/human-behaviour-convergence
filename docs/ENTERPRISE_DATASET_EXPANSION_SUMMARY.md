# Enterprise Dataset Expansion - Executive Summary

**Date**: 2026-01-22
**Status**: Planning Complete, Ready for Implementation
**Full Plan**: See `docs/ENTERPRISE_DATASET_EXPANSION_PLAN.md`

---

## Quick Overview

This expansion adds **15 high-value datasets** across 7 categories to strengthen regional behavioral forecasting. The **Top 5 MVP datasets** are prioritized for immediate implementation.

**Goal**: Two distant regions (e.g., Illinois vs Arizona) show measurable divergence in ≥3 independent sub-indices within 30 days.

---

## Top 5 MVP Datasets (Selected for Immediate Implementation)

| # | Dataset | Category | ROI | Regionality | Complexity | Priority |
|---|---------|----------|-----|-------------|------------|----------|
| 1 | **EIA Gasoline Prices by State** | Economic | 9 | 10 | 4 | P0 |
| 2 | **U.S. Drought Monitor (State)** | Environmental | 8 | 10 | 5 | P0 |
| 3 | **NOAA Storm Events (State)** | Environmental | 9 | 10 | 6 | P0 |
| 4 | **Eviction Lab (State/City)** | Economic | 8 | 10 | 5 | P1 |
| 5 | **CDC WONDER Overdose (State)** | Health | 8 | 9 | 7 | P1 |

**Total Score Calculation**: ROI + Regionality - Complexity (higher is better)

---

## Expected Impact

### Current State
- Regional sub-indices: 5-6 REGIONAL sources
- Regional variance: Moderate

### After Top 5 MVP Implementation
- Regional sub-indices: **10-11 REGIONAL sources** (+5 new)
- Regional variance: **Significantly increased**
- New sub-indices:
  - `economic_stress`: +2 children (fuel_stress, housing_stress)
  - `environmental_stress`: +4 children (drought_stress, heatwave_stress, flood_risk_stress, storm_severity_stress)
  - `public_health_stress`: +1 child (substance_use_stress)

---

## Implementation Phases

### Phase 1: MVP 1 — EIA Gasoline Prices (Week 1)
- Connector: `app/services/ingestion/eia_fuel_prices.py`
- Sub-index: `economic_stress` → `fuel_stress`
- Expected variance: **HIGH** (state prices vary 20-40%)

### Phase 2: MVP 2 — Drought Monitor (Week 1-2)
- Connector: `app/services/ingestion/drought_monitor.py`
- Sub-index: `environmental_stress` → `drought_stress`
- Expected variance: **VERY HIGH** (DSCI ranges 0-500)

### Phase 3: MVP 3 — NOAA Storm Events (Week 2-3)
- Connector: `app/services/ingestion/noaa_storm_events.py`
- Sub-indices: `environmental_stress` → `heatwave_stress`, `flood_risk_stress`, `storm_severity_stress`
- Expected variance: **VERY HIGH** (coastal vs plains vs desert)

### Phase 4: MVP 4 — Eviction Lab (Week 3)
- Connector: `app/services/ingestion/eviction_lab.py`
- Sub-index: `economic_stress` → `housing_stress`
- Expected variance: **VERY HIGH** (rates vary 10x: 0.5% to 5%+)
- Note: Limited geography (~30 states)

### Phase 5: MVP 5 — CDC WONDER Overdose (Week 3-4)
- Connector: `app/services/ingestion/cdc_wonder_overdose.py`
- Sub-index: `public_health_stress` → `substance_use_stress`
- Expected variance: **HIGH** (rates vary 3-5x: 10-50 per 100k)
- Note: Provisional data (2-3 month lag)

### Phase 6: Safety Net & Validation (Week 4)
- Run full discrepancy investigation
- Verify variance_probe passes
- Verify Prometheus invariants
- Update documentation

---

## Regionality Safety Net

Every REGIONAL dataset must:
- [OK] Use geo inputs in fetch logic
- [OK] Include geo in cache keys
- [OK] Emit metrics with region labels
- [OK] Pass `variance_probe.py` (no alerts)
- [OK] Have regression tests (two distant regions produce different values)
- [OK] Be classified in `source_regionality_manifest.json`

---

## Risk & Ethics

**Risk Level**: **LOW** for all MVP datasets
- All are public/openly licensed
- All are aggregated (no PII)
- All are state-level or higher
- All have documented failure modes

**Ethics Review**: **PASSED** [OK]
- No private/paid APIs (except free-tier OpenStates, documented)
- No scraping behind auth walls
- No social media APIs
- Clear data licensing

---

## Success Criteria

[OK] Two distant regions show divergence in ≥3 independent sub-indices within 30 days
[OK] Dashboards clearly distinguish global vs regional signals
[OK] Forecasts are auditable back to source-level contributors
[OK] Zero regressions in existing workflows
[OK] All REGIONAL sources pass variance_probe

---

## Next Steps

1. **Review & Approve**: Review full plan (`ENTERPRISE_DATASET_EXPANSION_PLAN.md`)
2. **Start Phase 1**: Implement EIA Gasoline Prices (highest ROI, lowest complexity)
3. **Iterative Integration**: One MVP dataset at a time, validate before next
4. **Safety Net**: Run discrepancy investigation after each dataset
5. **Documentation**: Update docs as each dataset is integrated

---

## Full Documentation

- **Complete Plan**: `docs/ENTERPRISE_DATASET_EXPANSION_PLAN.md` (15 datasets, detailed blueprints)
- **Data Sources Catalog**: `docs/DATA_SOURCES.md` (updated with new datasets)
- **Global vs Regional**: `docs/GLOBAL_VS_REGIONAL_INDICES.md` (updated classifications)
- **Verification**: `docs/VERIFY_INTEGRITY.md` (regionality checks)

---

**Ready for implementation. Begin with MVP 1 (EIA Gasoline Prices).**
