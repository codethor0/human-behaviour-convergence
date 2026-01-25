# High-Value Public Datasets for Regional Variance Expansion

This document lists research-backed public datasets that will increase regional variance and enhance dashboard value. All datasets are:
- Public/aggregated
- Vary meaningfully by state/region
- Have stable update cadence
- Explainable to users
- Fit existing ingestion + metrics + Grafana pattern

## Environmental and Climate Shocks (Very High Variance)

### A) U.S. Drought Monitor (State-Level Severity/Area Coverage)
**Source**: U.S. Drought Monitor (USDM) via USDA/NIDIS
- **Update Frequency**: Weekly (Thursday releases)
- **Regional Variance**: Extremely high — drought severity varies dramatically by state
- **Integration**: `drought_stress` child of `environmental_stress`
- **API**: Public JSON/CSV feeds, no key required
- **Priority**: **MVP2** (highest impact for environmental variance)

### B) NOAA Storm Events Database (State/County Event Counts, Fatalities, Damages)
**Source**: NOAA NCEI Storm Events Database
- **Update Frequency**: Monthly (with near-real-time updates for major events)
- **Regional Variance**: Very high — storm type and impact vary heavily by geography
- **Integration**: `storm_severity_stress` child of `environmental_stress`
- **API**: Public CSV/JSON, no key required
- **Priority**: **MVP3** (high impact, clean event-rate signal)

### C) NOAA/NWS Alerts (Deepen Existing Implementation)
**Source**: National Weather Service API
- **Update Frequency**: Real-time
- **Regional Variance**: High — alert density varies by state/region
- **Integration**: Enhance existing `weather_alerts` source; derive severity-weighted alert density
- **API**: Public, no key required
- **Priority**: Enhancement to existing source

## Economic Micro-Signals (High Variance)

### D) State Unemployment / Labor Market Series (BLS LAUS)
**Source**: Bureau of Labor Statistics Local Area Unemployment Statistics (LAUS)
- **Update Frequency**: Monthly
- **Regional Variance**: High — unemployment rates vary significantly by state
- **Integration**: `unemployment_stress` child of `economic_stress`
- **API**: BLS Public Data API v2, no key required (rate limits apply)
- **Priority**: **MVP4** (quick win, widely understood)

### E) Census Population Estimates / Migration
**Source**: U.S. Census Bureau API
- **Update Frequency**: Annual (with quarterly estimates)
- **Regional Variance**: Moderate — helps normalize per-capita signals
- **Integration**: Demographic context for forecasts (not a direct stress index)
- **API**: Census API, no key required
- **Priority**: Lower (supporting data, not primary signal)

### F) Housing Pressure Proxies
**Source**: Eviction Lab (if keeping "public + aggregated only")
- **Update Frequency**: Varies
- **Regional Variance**: High
- **Integration**: `eviction_stress` / `housing_cost_burden` child of `economic_stress`
- **API**: Public aggregated data
- **Priority**: Planned (already in expansion plan)
- **Note**: Keep strictly aggregated, document usage/coverage clearly

## Public Health Pressure (High Variance, Careful Semantics)

### G) CDC WONDER (Aggregated Mortality/Overdose via API)
**Source**: CDC WONDER (Wide-ranging Online Data for Epidemiologic Research)
- **Update Frequency**: Quarterly/Annual
- **Regional Variance**: High — overdose/mortality rates vary by state
- **Integration**: `overdose_stress` / `substance_use_stress` child of `public_health_stress`
- **API**: CDC WONDER API, public, rate-limited
- **Priority**: High (but requires careful documentation of data-use constraints)
- **Note**: Build polite rate limiting and caching

### H) WHO Disease Surveillance
**Source**: WHO Global Health Observatory
- **Update Frequency**: Weekly/Monthly
- **Regional Variance**: Country-level (may be subnational for specific countries)
- **Integration**: Global/national signal enhancement
- **API**: WHO API, public
- **Priority**: Lower (global signal, less regional variance)

## Public Safety and Civic Stress (High Variance)

### I) FEMA Disaster Declarations + Assistance Summaries (State-Level)
**Source**: OpenFEMA API
- **Update Frequency**: Real-time (as declarations occur)
- **Regional Variance**: High — event-like public signal
- **Integration**: Enhance existing `emergency_management` source
- **API**: OpenFEMA API, public, no key required
- **Priority**: Enhancement to existing source

### J) USGS Earthquakes (Regional but "Bursty")
**Source**: USGS Earthquake API
- **Update Frequency**: Real-time
- **Regional Variance**: Moderate (regional but bursty)
- **Integration**: Shock-type signal for `environmental_stress`
- **API**: USGS API, public, no key required
- **Priority**: Lower (bursty nature may not provide stable variance)

## Information Pressure (Regionalizable)

### K) GDELT "By State" Media Pressure
**Source**: GDELT Project
- **Update Frequency**: Daily
- **Regional Variance**: Moderate (if properly filtered by state)
- **Integration**: Enhance existing `gdelt_events` source
- **API**: GDELT API, public
- **Priority**: Enhancement (verify cache keys and query parameters in variance probe)

## Infrastructure/System Strain (Regional)

### L) EIA Grid / Load / Balancing Authority Metrics
**Source**: EIA API v2
- **Update Frequency**: Daily/Weekly
- **Regional Variance**: High (regional grid stress)
- **Integration**: Expand existing EIA hooks using EIA API v2 conventions
- **API**: EIA API v2, public, no key required
- **Priority**: Enhancement to existing EIA source

## Implementation Priority

1. **MVP2**: U.S. Drought Monitor (highest environmental variance impact)
2. **MVP3**: NOAA Storm Events (high variance, clean event signal)
3. **MVP4**: BLS LAUS Unemployment (quick win, economic variance)
4. **Enhancements**: NWS Alerts, FEMA, GDELT by-state, EIA grid metrics
5. **Future**: CDC WONDER (requires careful handling), Census (supporting data)

## Selection Criteria Summary

All recommended datasets meet:
- ✅ Public/aggregated (no PII)
- ✅ Meaningful regional variance
- ✅ Stable update cadence
- ✅ Explainable to users
- ✅ Fits existing ingestion pattern
- ✅ Ethical use (aggregated, documented)
