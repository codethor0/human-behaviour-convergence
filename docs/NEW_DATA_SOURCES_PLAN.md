# New Data Sources Integration Plan

## Overview
This document outlines the plan for integrating new publicly available data sources into the human-behaviour-convergence project to enhance forecasting capabilities while maintaining strict ethical and privacy standards.

## Ethical Guidelines
All new data sources must:
- Be publicly available (no private/paid APIs requiring user data)
- Comply with privacy regulations (GDPR, CCPA)
- Not collect or store personally identifiable information (PII)
- Follow k-anonymity principles (minimum 15 individuals per aggregation)
- Use geo-precision ≤ H3-9 (≈ 0.1 km²)
- Have clear data licensing and usage terms

## Approved Data Sources

### 1. WHO Disease Surveillance Data ✅
**Source**: World Health Organization (WHO) public APIs
**Category**: Health
**Availability**: Public, no API key required
**Data**: Global disease outbreak data, epidemiological indicators
**Integration**: New connector in `connectors/who_disease.py`
**Status**: Ready to implement

### 2. NOAA Climate Data ✅
**Source**: National Oceanic and Atmospheric Administration (NOAA) Climate Data API
**Category**: Environmental
**Availability**: Public, no API key required
**Data**: Historical climate data, temperature anomalies, precipitation patterns
**Integration**: Enhance existing `app/services/ingestion/weather.py`
**Status**: Ready to implement

### 3. Google Trends (Limited) ⚠️
**Source**: Google Trends (via pytrends library)
**Category**: Digital Attention
**Availability**: Public but rate-limited
**Data**: Search interest trends (normalized 0-100 scale)
**Integration**: Enhance existing `app/services/ingestion/search_trends.py`
**Status**: Requires careful rate limiting

### 4. Public Transit Data (City-Specific) ⚠️
**Source**: City-specific transit APIs (e.g., NYC MTA, London TfL)
**Category**: Mobility
**Availability**: Varies by city, some require API keys
**Data**: Transit ridership, delays, service disruptions
**Integration**: New connector with city-specific adapters
**Status**: Requires research per city

## Excluded Sources (Ethical/Privacy Concerns)

### ❌ Social Media Data
- **Twitter/X**: Requires API keys, rate limits, privacy concerns
- **Instagram**: Private data, requires authentication
- **Facebook**: Private data, requires authentication
- **Reason**: Not truly public, requires user authentication, privacy risks

### ❌ Personal Health Data
- **Fitbit**: Private health data, requires user authentication
- **Apple HealthKit**: Private health data, requires device access
- **Reason**: Personal health information (PHI), HIPAA concerns

### ❌ Smartphone Sensor Data
- **Location data**: Privacy concerns, requires device access
- **Voice/Speech data**: Privacy concerns, requires device access
- **Reason**: Personal data, requires device-level access

## Implementation Phases

### Phase 1: WHO Disease Surveillance (Priority: High)
**Timeline**: 1-2 days
**Files to Create**:
- `connectors/who_disease.py` - WHO data connector
- Update `connectors/__init__.py` to export new connector

**Files to Modify**:
- `app/services/ingestion/public_health.py` - Integrate WHO data
- `app/services/ingestion/source_registry.py` - Register new source

### Phase 2: NOAA Climate Data Enhancement (Priority: Medium)
**Timeline**: 1 day
**Files to Modify**:
- `app/services/ingestion/weather.py` - Add NOAA climate indicators
- `app/services/ingestion/source_registry.py` - Update weather source description

### Phase 3: Google Trends Enhancement (Priority: Low)
**Timeline**: 1 day
**Files to Modify**:
- `app/services/ingestion/search_trends.py` - Add Google Trends support
- Add rate limiting and caching

### Phase 4: Documentation (Priority: High)
**Timeline**: 1 day
**Files to Create/Update**:
- `docs/DATA_SOURCES.md` - Comprehensive data source documentation
- `README.md` - Update with new sources
- API documentation for new endpoints

## Testing Requirements

For each new data source:
1. Unit tests in `tests/test_connectors.py` or `tests/test_ingestion/`
2. Integration tests with CI offline mode
3. Data quality checks (schema, types, ranges)
4. Privacy compliance checks (PII detection, k-anonymity)
5. Error handling tests (API failures, rate limits)

## Monitoring and Observability

Each new data source should:
- Log fetch attempts and results
- Report source status in `/api/sources/status`
- Include health checks in source registry
- Support graceful degradation when unavailable

## Enterprise Dataset Expansion (Top 5 MVP)

See **`docs/ENTERPRISE_DATASET_EXPANSION_PLAN.md`** for the full Enterprise Dataset Expansion + Regional Signal Hardening plan.

**Top 5 MVP datasets** for immediate implementation:

1. **EIA Gasoline by State** — Economic micro-signal; high regional variance.
2. **U.S. Drought Monitor (State)** — Environmental; DSCI by state.
3. **NOAA Storm Events (State)** — Severe weather by state/county; bulk CSV.
4. **Eviction Lab (State/City)** — Housing stress; S3/CSV; limited geography.
5. **CDC WONDER Overdose (State)** — Health pressure; XML API; provisional.

Each must: use geo in fetch + cache key, emit region-labeled metrics, pass `variance_probe`, have regression tests and docs.

## Next Steps

1. ✅ Create this planning document
2. Implement WHO Disease Surveillance connector
3. Enhance NOAA climate data integration
4. Update source registry
5. Add tests
6. Update documentation
7. Implement Top 5 MVP per `ENTERPRISE_DATASET_EXPANSION_PLAN.md`
