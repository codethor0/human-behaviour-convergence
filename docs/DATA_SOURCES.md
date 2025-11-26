# Data Sources Registry

This document catalogs all data sources used by the Human Behaviour Convergence forecasting platform, including current implementations and planned additions.

## Project Stewardship

Primary maintainer: **Thor Thor**
Email: [codethor@gmail.com](mailto:codethor@gmail.com)
LinkedIn: [https://www.linkedin.com/in/thor-thor0](https://www.linkedin.com/in/thor-thor0)

---

## Current Data Sources

### 1. Economic Indicators (Market Sentiment)

**Status:** Active and fully implemented

**Implementation:**
- **Connector:** `app/services/ingestion/finance.py` → `MarketSentimentFetcher`
- **API:** yfinance (Python library wrapping Yahoo Finance)
- **Data:** VIX (Volatility Index) and SPY (S&P 500 ETF)
- **Authentication:** None required (public data)
- **Rate Limits:** Subject to Yahoo Finance rate limits (informal, no documented limit)
- **Update Frequency:** Daily (market hours)
- **Data Granularity:** Daily closing prices
- **Output:** Normalized stress index (0.0-1.0) combining VIX and SPY signals

**Usage:**
```python
from app.services.ingestion import MarketSentimentFetcher
fetcher = MarketSentimentFetcher()
data = fetcher.fetch_stress_index(days_back=30)
```

**Notes:**
- Handles weekend market closures with forward-filling
- Caches responses for 5 minutes by default
- Returns empty DataFrame on API errors (graceful degradation)

---

### 2. Weather Patterns (Environmental Impact)

**Status:** Active and fully implemented

**Implementation:**
- **Connector:** `app/services/ingestion/weather.py` → `EnvironmentalImpactFetcher`
- **API:** Open-Meteo Archive API (https://archive-api.open-meteo.com)
- **Authentication:** None required (free public API)
- **Rate Limits:** No documented limits (generous free tier)
- **Update Frequency:** Historical data available, updates daily
- **Data Granularity:** Hourly data aggregated to daily averages
- **Output:** Normalized discomfort score (0.0-1.0) based on temperature deviation, precipitation, and wind speed

**Usage:**
```python
from app.services.ingestion import EnvironmentalImpactFetcher
fetcher = EnvironmentalImpactFetcher()
data = fetcher.fetch_regional_comfort(
    latitude=40.7128,
    longitude=-74.0060,
    days_back=30
)
```

**Notes:**
- Requires latitude/longitude coordinates
- Caches responses for 30 minutes by default
- Uses requests-cache for HTTP-level caching
- Returns empty DataFrame on API errors (graceful degradation)

---

## Placeholder Connectors (Stubbed, Require Configuration)

### 3. Search Trends

**Status:** Stubbed (requires API configuration)

**Implementation:**
- **Connector:** `app/services/ingestion/search_trends.py` → `SearchTrendsFetcher`
- **API:** Generic placeholder (configurable via environment variables)
- **Authentication:** API key required (set via `SEARCH_TRENDS_API_KEY`)
- **Configuration:**
  - `SEARCH_TRENDS_API_ENDPOINT`: API endpoint URL
  - `SEARCH_TRENDS_API_KEY`: API key for authentication
- **Behavior:** Returns empty DataFrame if environment variables are not set

**Planned Integration Options:**
- Google Trends API (if available and license-compliant)
- Alternative search trend aggregators with public APIs
- Custom search interest indices from public data

---

### 4. Public Health Indicators

**Status:** Stubbed (requires API configuration)

**Implementation:**
- **Connector:** `app/services/ingestion/public_health.py` → `PublicHealthFetcher`
- **API:** Generic placeholder (configurable via environment variables)
- **Authentication:** API key required (set via `PUBLIC_HEALTH_API_KEY`)
- **Configuration:**
  - `PUBLIC_HEALTH_API_ENDPOINT`: API endpoint URL
  - `PUBLIC_HEALTH_API_KEY`: API key for authentication
- **Behavior:** Returns empty DataFrame if environment variables are not set

**Planned Integration Options:**
- CDC (Centers for Disease Control and Prevention) public APIs
- WHO (World Health Organization) public data APIs
- ECDC (European Centre for Disease Prevention and Control) APIs
- Other regional public health data sources with appropriate licensing

**Notes:**
- Must use aggregated, anonymized data only (no individual records)
- Must comply with data privacy regulations (GDPR, HIPAA, etc.)
- Should prioritize sources with clear licensing terms

---

### 5. Mobility Patterns

**Status:** Stubbed (requires API configuration)

**Implementation:**
- **Connector:** `app/services/ingestion/mobility.py` → `MobilityFetcher`
- **API:** Generic placeholder (configurable via environment variables)
- **Authentication:** API key required (set via `MOBILITY_API_KEY`)
- **Configuration:**
  - `MOBILITY_API_ENDPOINT`: API endpoint URL
  - `MOBILITY_API_KEY`: API key for authentication
- **Behavior:** Returns empty DataFrame if environment variables are not set

**Planned Integration Options:**
- Apple Mobility Trends (if publicly accessible)
- Google Mobility Reports (if API available)
- OpenStreetMap activity indices
- Other aggregated mobility data sources with appropriate licensing

**Notes:**
- Must use aggregated, anonymized data only
- Should respect privacy and data protection regulations
- Prefer sources with clear terms of service and licensing

---

## Data Harmonization

All data sources are harmonized by `app/services/ingestion/processor.py` → `DataHarmonizer`, which:

1. **Aligns timestamps** across all sources to a common daily index
2. **Forward-fills** market data for weekends (market closures)
3. **Interpolates** missing values in continuous signals
4. **Computes behavioral index** using weighted combination:
   - Inverse stress (25%)
   - Comfort (25%)
   - Search attention (15%)
   - Inverse health burden (15%)
   - Mobility activity (10%)
   - Seasonality (10%)

---

## Adding New Data Sources

To add a new data source:

1. **Create connector class** in `app/services/ingestion/`:
   - Inherit common patterns from existing connectors
   - Implement `fetch_*` method returning DataFrame with `timestamp` column
   - Handle missing env vars gracefully (return empty DataFrame)
   - Add caching for API responses

2. **Register in `app/services/ingestion/__init__.py`**

3. **Update `BehavioralForecaster`** in `app/core/prediction.py`:
   - Add fetcher initialization
   - Call fetcher in `forecast()` method
   - Add source name to `sources` list if data is available

4. **Update `DataHarmonizer`** in `app/services/ingestion/processor.py`:
   - Add parameter to `harmonize()` method
   - Include in merge logic
   - Update `behavior_index` formula if needed

5. **Update API endpoints**:
   - Add to `/api/forecasting/data-sources` response
   - Update `/api/forecasting/status` if needed

6. **Document**:
   - Add entry to this file
   - Update README if significant
   - Add environment variable documentation

---

## Data Source Requirements

All data sources must:

- Use **public data only** (no proprietary or restricted datasets)
- Handle **missing configuration gracefully** (return empty DataFrame, don't crash)
- Implement **caching** to reduce API calls
- Return **normalized indices** (0.0-1.0 range) where applicable
- Include **timestamp column** for time-series alignment
- Log **warnings** when data is unavailable (don't fail silently)
- Comply with **licensing terms** and **rate limits**
- Respect **privacy regulations** (no individual-level data)

---

## Future Data Sources (Proposed)

### 6. Social Media Sentiment (Planned)
- **Source:** Public sentiment APIs or aggregated social media data
- **Status:** Research phase
- **Considerations:** Privacy, licensing, rate limits

### 7. Economic Indicators (Extended) (Planned)
- **Source:** Additional market indices, commodity prices, currency exchange rates
- **Status:** Research phase
- **Considerations:** Data availability, relevance to behavioral forecasting

### 8. News Headlines / Media Attention (Planned)
- **Source:** News API aggregators with public access
- **Status:** Research phase
- **Considerations:** Licensing, rate limits, content filtering

---

## License and Attribution

All data sources used in this project are:
- Publicly available
- Used in compliance with their respective terms of service
- Properly attributed in code comments and documentation

For specific licensing questions, refer to each data source's official documentation.

---

**Last Updated:** 2025-01-XX
**Maintainer:** Thor Thor (codethor@gmail.com)
