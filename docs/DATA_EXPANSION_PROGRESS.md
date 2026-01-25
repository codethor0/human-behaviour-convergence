# Data Expansion Progress - Phase 2

## Overview

Tracking progress on comprehensive data expansion initiative to integrate 15+ new public data sources.

## Completed Sources

### ✅ Air Quality (TICKET-011)
**Status**: Complete  
**File**: `app/services/ingestion/air_quality.py`  
**Sources**: PurpleAir API + EPA AirNow API  
**Features**:
- Combines data from both PurpleAir (community sensors) and EPA AirNow (official)
- Calculates AQI from PM2.5 concentrations
- Normalizes to `air_quality_stress_index` (0-1 scale)
- CI offline mode
- Caching (5-minute TTL)
- Error handling with fallback data
- API keys optional (can run without keys)

**Integration**:
- ✅ Registered in `source_registry.py`
- ✅ Integrated into `processor.py`
- ⏳ Prometheus metrics (to be added)
- ⏳ Dashboard visualization (to be added)

## In Progress

None currently.

## Pending High-Priority Sources

### TICKET-012: Water Quality Monitoring (EPA)
**Priority**: HIGH  
**Status**: Pending  
**Source**: EPA Water Quality Portal API  
**Estimated Effort**: 1 week

### TICKET-013: Traffic Sensor Data (DOT)
**Priority**: HIGH  
**Status**: Pending  
**Source**: DOT open data portals (varies by state)  
**Estimated Effort**: 1 week

### TICKET-014: River Gauge Levels (USGS)
**Priority**: HIGH  
**Status**: Pending  
**Source**: USGS Water Services API  
**Estimated Effort**: 1 week

## Pending Medium-Priority Sources

### TICKET-018: Reddit Sentiment Integration
**Priority**: MEDIUM  
**Status**: Pending  
**Source**: Reddit API  
**Estimated Effort**: 1 week

### TICKET-019: Job Posting Velocity
**Priority**: MEDIUM  
**Status**: Pending  
**Source**: Indeed/LinkedIn APIs  
**Estimated Effort**: 1 week

### TICKET-020: 311 Call Volumes
**Priority**: MEDIUM  
**Status**: Pending  
**Source**: City open data portals  
**Estimated Effort**: 1 week

## Implementation Pattern

Each new data source follows this pattern:

1. **Create Fetcher Class** (`app/services/ingestion/<source>.py`):
   - `__init__` method with API key handling
   - `fetch_<source>` method returning DataFrame
   - CI offline mode (`_get_ci_offline_data`)
   - Caching mechanism
   - Error handling with fallback
   - Stress index normalization (0-1 scale)

2. **Register in Source Registry** (`app/services/ingestion/source_registry.py`):
   - Create `SourceDefinition` object
   - Specify `id`, `display_name`, `category`
   - Set `requires_key`, `required_env_vars`, `can_run_without_key`
   - Add description

3. **Integrate into Processor** (`app/services/ingestion/processor.py`):
   - Add parameter to `harmonize` method
   - Handle empty DataFrame case
   - Normalize timestamps and set index
   - Add to `dataframes` and `names` lists
   - Reindex to common date range
   - Extract stress index value
   - Add to merged DataFrame

4. **Add Prometheus Metrics** (Future):
   - Expose metrics in `app/backend/app/main.py`
   - Update dashboards to visualize new data

## Success Metrics

- **Target**: 15+ new public APIs integrated
- **Current**: 1/15 complete (6.7%)
- **Next Sprint**: 3 more high-priority sources (Water Quality, Traffic, River Gauges)

## Notes

- All sources follow consistent patterns for maintainability
- CI offline mode ensures tests pass without API keys
- Caching reduces API rate limit issues
- Fallback data ensures graceful degradation
- Stress index normalization ensures consistency across sources
