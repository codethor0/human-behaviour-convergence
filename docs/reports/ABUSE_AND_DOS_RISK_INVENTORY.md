# Abuse & DoS Risk Inventory (Code-Derived)

**Generated:** 2025-12-22
**Source:** Direct code analysis
**Iteration:** N+12 - Abuse & DoS Reality

## Endpoint Cost Classification

### HIGH COST Endpoints

#### 1. POST /api/forecast
**File:** `app/backend/app/main.py` (line 1017)

**Cost Justification:**
- Creates `BehavioralForecaster()` instance
- Fetches multiple data sources (market, FRED, weather, search, health, mobility, GDELT, OWID, USGS, political, crime, misinformation, social cohesion)
- Performs time-series forecasting (exponential smoothing)
- Computes behavior indices and sub-indices
- Generates explanations

**Abuse Vectors:**
- Request frequency: No rate limiting
- Parameter amplification: `days_back` up to 365, `forecast_horizon` up to 30
- External API calls: Multiple fetchers make external requests
- Memory: Creates DataFrames, performs computations

**Current Bounds:**
- `days_back`: 7-365 (validated)
- `forecast_horizon`: 1-30 (validated)
- Coordinates: -90 to 90, -180 to 180 (validated)

**Status:** BOUNDED (parameter ranges limited, but no rate limiting)

#### 2. POST /api/playground/compare
**File:** `app/backend/app/routers/playground.py` (line 91)

**Cost Justification:**
- Processes up to 10 regions (max_length=10)
- Each region triggers full forecast generation (same cost as /api/forecast)
- Amplification: 10x cost multiplier possible
- Post-processing: Scenario adjustments, recomputation

**Abuse Vectors:**
- Request frequency: No rate limiting
- Amplification: Up to 10 regions per request = 10x forecast cost
- Parameter ranges: Same as /api/forecast (365 days_back, 30 horizon)

**Current Bounds:**
- `regions`: 1-10 (max_length=10)
- `historical_days`: 7-365 (validated)
- `forecast_horizon_days`: 1-30 (validated)

**Status:** BOUNDED (region count limited, but amplification risk remains)

#### 3. GET /api/public/synthetic_score/{h3_res}/{date}
**File:** `app/backend/app/routers/public.py` (line 115)

**Cost Justification:**
- Fetches 3 data sources: WikiPageviewsSync, OSMChangesetsSync, FIRMSFiresSync
- Each connector makes external API calls
- Performs normalization and aggregation
- Returns potentially large dataset

**Abuse Vectors:**
- Request frequency: No rate limiting
- External API amplification: 3 external calls per request
- Response size: Unbounded (depends on data availability)

**Current Bounds:**
- `h3_res`: 5-9 (validated)
- `date`: YYYY-MM-DD format (validated)
- Wiki: `max_hours=1` (limits data fetch)
- OSM: `max_bytes=10 * 1024 * 1024` (10MB limit)

**Status:** BOUNDED (connector-level limits, but no rate limiting)

#### 4. GET /api/public/{source}/latest
**File:** `app/backend/app/routers/public.py` (line 58)

**Cost Justification:**
- Fetches external data (wiki, osm, firms)
- Makes HTTP requests to external APIs
- Processes and returns data

**Abuse Vectors:**
- Request frequency: No rate limiting
- External API calls: Direct amplification to external services
- Response size: Unbounded (depends on source)

**Current Bounds:**
- `source`: Literal["wiki", "osm", "firms"] (validated)
- `date`: YYYY-MM-DD format (validated)
- Wiki: `max_hours=1`
- OSM: `max_bytes=10 * 1024 * 1024`

**Status:** BOUNDED (connector-level limits, but no rate limiting)

#### 5. GET /api/visual/*
**File:** `app/backend/app/main.py` (lines 1814+)

**Cost Justification:**
- Creates `BehavioralForecaster()` instances
- Generates forecasts for multiple regions
- Processes visualization data
- May iterate over multiple states/regions

**Abuse Vectors:**
- Request frequency: No rate limiting
- Multiple forecast generations per request
- Memory: Creates multiple DataFrames

**Current Bounds:**
- Limited to key_states list (5 states) in heatmap
- Other visualizations may process more regions

**Status:** PARTIALLY BOUNDED (some limits, but not comprehensive)

### MEDIUM COST Endpoints

#### 6. GET /api/forecasts, GET /api/metrics
**File:** `app/backend/app/main.py` (lines 839, 859)

**Cost Justification:**
- Reads CSV files from disk
- Cached (5-minute TTL) but cache can be evicted
- Processes up to 10000 rows

**Abuse Vectors:**
- Request frequency: No rate limiting
- Cache eviction: Can force cache misses
- Disk I/O: Repeated file reads

**Current Bounds:**
- `limit`: 1-10000 (validated)
- Cache: MAX_CACHE_SIZE=100 entries (default)

**Status:** BOUNDED (limit enforced, cache provides some protection)

#### 7. GET /api/live/summary
**File:** `app/backend/app/routers/live.py` (line 24)

**Cost Justification:**
- Reads from in-memory snapshots
- Processes multiple regions
- May trigger refresh if data stale

**Abuse Vectors:**
- Request frequency: No rate limiting
- Memory: Reads from in-memory data structures

**Current Bounds:**
- `time_window_minutes`: 1-1440 (validated)
- Regions: Optional list (no explicit limit)

**Status:** BOUNDED (time window limited, but region list unbounded)

#### 8. POST /api/live/refresh
**File:** `app/backend/app/routers/live.py` (line 72)

**Cost Justification:**
- Triggers refresh of live monitoring data
- May refresh all regions or specific regions
- Calls `refresh_all_regions()` or `refresh_region()` for each

**Abuse Vectors:**
- Request frequency: No rate limiting
- Can trigger expensive refresh operations
- Amplification: Can refresh multiple regions

**Current Bounds:**
- Regions: Optional list (no explicit limit)
- Background thread handles refresh (bounded by refresh interval)

**Status:** PARTIALLY BOUNDED (background thread provides some protection)

### LOW COST Endpoints

#### 9. GET /health
**File:** `app/backend/app/main.py` (line 158)

**Cost:** Minimal (simple return)

**Status:** LOW COST

#### 10. GET /api/status, GET /api/cache/status
**File:** `app/backend/app/main.py` (lines 879, 885)

**Cost:** Minimal (simple returns, cache status read)

**Status:** LOW COST

#### 11. GET /api/forecasting/data-sources, /regions, /models, /status, /history
**File:** `app/backend/app/routers/forecasting.py`

**Cost:** Low (metadata endpoints, database queries are lightweight)

**Status:** LOW COST

## Abuse Vectors Summary

### 1. Request Frequency
**Status:** UNBOUNDED

**Impact:** HIGH
- No rate limiting on any endpoint
- Can flood HIGH COST endpoints
- Can exhaust external API quotas
- Can exhaust server resources

**Mitigation:** DEFERRED
- Planned: API Gateway rate limiting (production)
- Current: None

### 2. Payload Size
**Status:** PARTIALLY BOUNDED

**Bounded:**
- `/api/playground/compare`: `regions` max_length=10
- `/api/forecasts`, `/api/metrics`: `limit` max=10000
- Connector limits: Wiki (1 hour), OSM (10MB)

**Unbounded:**
- POST request body size (no explicit limit)
- Response size (depends on data)

**Mitigation:** DEFERRED
- Planned: Request size limits at API Gateway (production)
- Current: Connector-level limits only

### 3. Parameter Range Amplification
**Status:** BOUNDED

**Bounded Parameters:**
- `days_back`: 7-365
- `forecast_horizon`: 1-30
- `regions`: 1-10
- `h3_res`: 5-9
- `limit`: 1-10000
- `time_window_minutes`: 1-1440

**Impact:** MEDIUM (ranges are reasonable but maximums can be expensive)

**Mitigation:** ACCEPTED (ranges are intentional, documented)

### 4. External API Amplification
**Status:** PARTIALLY BOUNDED

**Protection:**
- Connector timeouts: 30-60 seconds
- Connector size limits: Wiki (1 hour), OSM (10MB)
- No direct user control over external URLs (SSRF protected)

**Risk:**
- No rate limiting on connector calls
- Can exhaust external API quotas
- Can trigger external service rate limits

**Mitigation:** DEFERRED
- Planned: Per-connector rate limiting (production)
- Current: Timeout and size limits only

### 5. Background Thread Amplification
**Status:** BOUNDED

**Protection:**
- Single background thread (daemon)
- Refresh interval bounded by `refresh_interval_minutes`
- Thread-safe operations

**Risk:** LOW (single thread, bounded operations)

**Mitigation:** ACCEPTED (current design is safe)

### 6. Cache Growth
**Status:** BOUNDED

**Protection:**
- MAX_CACHE_SIZE=100 entries (default, configurable)
- TTL-based expiration (5 minutes default)
- LRU eviction when limit reached
- Thread-safe cache operations

**Risk:** LOW (cache size bounded)

**Mitigation:** ACCEPTED (current design is safe)

### 7. Memory Pressure
**Status:** PARTIALLY BOUNDED

**Protection:**
- CSV read limits: 10000 rows max
- Connector limits: OSM (10MB), Wiki (1 hour)
- DataFrame operations bounded by input size

**Risk:**
- Multiple concurrent HIGH COST requests can exhaust memory
- No per-request memory limits
- No request concurrency limits

**Mitigation:** DEFERRED
- Planned: Request concurrency limits at API Gateway (production)
- Current: Per-endpoint limits only

### 8. Disk I/O Pressure
**Status:** BOUNDED

**Protection:**
- CSV reads cached (5-minute TTL)
- Cache limits prevent excessive disk reads
- File access whitelisted (path traversal protected)

**Risk:** LOW (caching provides protection)

**Mitigation:** ACCEPTED (current design is safe)

## Required Actions

### HIGH PRIORITY (Security Risk)

1. **Rate Limiting** - DEFERRED TO PRODUCTION
   - **Impact:** HIGH (DoS vulnerability)
   - **Mitigation:** API Gateway rate limiting (e.g., AWS API Gateway, Cloudflare)
   - **Trigger:** Production deployment
   - **Planned Control:** API Gateway (named infrastructure)

2. **Request Concurrency Limits** - DEFERRED TO PRODUCTION
   - **Impact:** HIGH (Memory exhaustion)
   - **Mitigation:** API Gateway concurrency limits
   - **Trigger:** Production deployment
   - **Planned Control:** API Gateway (named infrastructure)

### MEDIUM PRIORITY (Operational Risk)

3. **Request Size Limits** - DEFERRED TO PRODUCTION
   - **Impact:** MEDIUM (Memory exhaustion)
   - **Mitigation:** API Gateway request size limits (e.g., 1MB)
   - **Trigger:** Production deployment
   - **Planned Control:** API Gateway (named infrastructure)

4. **Per-Endpoint Rate Limits** - DEFERRED TO PRODUCTION
   - **Impact:** MEDIUM (Resource exhaustion)
   - **Mitigation:** Per-endpoint rate limits at API Gateway
   - **Trigger:** Production deployment
   - **Planned Control:** API Gateway (named infrastructure)

### ACCEPTED (Current Design)

5. **Parameter Range Bounds** - ACCEPTED
   - All parameters have validated ranges
   - Maximums are intentional and documented

6. **Cache Limits** - ACCEPTED
   - Cache size bounded (MAX_CACHE_SIZE)
   - TTL-based expiration
   - LRU eviction

7. **Connector Limits** - ACCEPTED
   - Timeout limits (30-60s)
   - Size limits (10MB for OSM, 1 hour for Wiki)
   - SSRF protection (validated URL construction)

## Risk Summary

| Risk | Impact | Current State | Mitigation |
|------|--------|---------------|------------|
| Request frequency (no rate limiting) | HIGH | UNBOUNDED | DEFERRED (API Gateway) |
| Request concurrency | HIGH | UNBOUNDED | DEFERRED (API Gateway) |
| Payload size | MEDIUM | PARTIALLY BOUNDED | DEFERRED (API Gateway) |
| Parameter amplification | MEDIUM | BOUNDED | ACCEPTED |
| External API amplification | MEDIUM | PARTIALLY BOUNDED | DEFERRED (API Gateway) |
| Cache growth | LOW | BOUNDED | ACCEPTED |
| Memory pressure | MEDIUM | PARTIALLY BOUNDED | DEFERRED (API Gateway) |
| Disk I/O | LOW | BOUNDED | ACCEPTED |

## Production Readiness

**Current State:** Development/Research Ready

**Production Requirements:**
- API Gateway with rate limiting (e.g., AWS API Gateway, Cloudflare)
- Request concurrency limits
- Request size limits
- Per-endpoint rate limits
- Monitoring and alerting for abuse patterns

**Deferred Risks Documented:**
- All deferred risks include expected impact
- All deferred risks include trigger conditions (production deployment)
- All deferred risks include planned mitigation (API Gateway)
