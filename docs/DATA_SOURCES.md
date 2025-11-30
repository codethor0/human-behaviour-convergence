# Data Sources Registry

This document catalogs all data sources used by the Human Behaviour Convergence forecasting platform, including current implementations and planned additions.

## Project Stewardship

Primary maintainer: **Thor Thor**
Email: [codethor@gmail.com](mailto:codethor@gmail.com)
LinkedIn: [https://www.linkedin.com/in/thor-thor0](https://www.linkedin.com/in/thor-thor0)

---

## Geographic Coverage

Environmental and economic signals are available for all configured regions, including:
- Global cities (New York City, London, Tokyo)
- All 50 US states plus District of Columbia

See `docs/REGIONS.md` for the complete list of supported regions.

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

## Planned Data Sources (High Priority)

### 6. FRED Economic Indicators

**Status:** Implemented (requires API key configuration)

**Implementation:**
- **Connector:** `app/services/ingestion/economic_fred.py` → `FREDEconomicFetcher`
- **API:** FRED (Federal Reserve Economic Data) API
- **Base URL:** https://api.stlouisfed.org/fred/
- **Authentication:** API key required (free registration at https://fred.stlouisfed.org/docs/api/api_key.html)
- **Rate Limits:** 120 requests per 120 seconds
- **Update Frequency:** Varies by series (daily, weekly, monthly)

**Available Indicators:**
- **Consumer Sentiment** (UMCSENT): University of Michigan Consumer Sentiment Index (monthly)
- **Unemployment Rate** (UNRATE): U.S. national unemployment rate (monthly)
- **Initial Jobless Claims** (ICSA): Weekly initial jobless claims (weekly)

**Configuration:**
- Set `FRED_API_KEY` environment variable with your FRED API key

**Usage:**
```python
from app.services.ingestion.economic_fred import FREDEconomicFetcher

fetcher = FREDEconomicFetcher()
consumer_sentiment = fetcher.fetch_consumer_sentiment(days_back=90)
unemployment = fetcher.fetch_unemployment_rate(days_back=90)
jobless_claims = fetcher.fetch_jobless_claims(days_back=30)
```

**Output Schema:**
- All methods return DataFrame with columns: `['timestamp', '<indicator_name>']`
- Values normalized to [0.0, 1.0] where 1.0 = maximum stress/uncertainty
- Returns empty DataFrame if API key not set or on error

**Notes:**
- Handles missing values gracefully (FRED uses "." for missing data)
- Caches responses for 60 minutes by default
- Returns empty DataFrame on API errors (graceful degradation)

---

### 7. Wikipedia Pageviews (Digital Attention)

**Status:** Connector exists, integration pending

**Implementation:**
- **Connector:** `connectors/wiki_pageviews.py` → `WikiPageviewsSync`
- **Source:** Wikimedia pageviews dumps (https://dumps.wikimedia.org/other/pageviews/)
- **Authentication:** None required
- **Update Frequency:** Daily (hourly dumps available)
- **Data Granularity:** Hourly pageview counts by project (language)

**Usage:**
```python
from connectors.wiki_pageviews import WikiPageviewsSync

connector = WikiPageviewsSync(date="2025-01-15", max_hours=24)
df = connector.pull()  # Returns: ['project', 'hour', 'views']
```

**Integration Notes:**
- Currently used by `/api/public/wiki/latest` endpoint
- Needs adapter to convert to forecasting pipeline format
- Should aggregate by day and normalize to attention index

---

### 8. GDELT Media Tone (Digital Attention)

**Status:** Planned

**Implementation:**
- **Connector:** To be implemented in `app/services/ingestion/digital_gdelt.py`
- **API:** GDELT Project API (https://api.gdeltproject.org/api/v2/)
- **Authentication:** None required for basic queries
- **Rate Limits:** Generous free tier
- **Update Frequency:** Daily

**Planned Indicators:**
- **Media Tone Score:** Average tone of global media coverage (-100 to +100, normalized)
- **Event Counts:** Daily event counts by type (conflict, disaster, etc.)

**Configuration:**
- No API key required for basic access
- May require API key for advanced features

**Output Schema:**
- DataFrame with columns: `['timestamp', 'tone_score', 'event_count']`
- Values normalized to [0.0, 1.0] where 1.0 = maximum attention/stress

---

### 9. Our World in Data (Public Health)

**Status:** Planned

**Implementation:**
- **Connector:** To be implemented in `app/services/ingestion/health_owid.py`
- **Source:** OWID datasets (https://github.com/owid/owid-datasets)
- **Format:** CSV files with country-level aggregates
- **Authentication:** None required
- **Update Frequency:** Daily

**Planned Indicators:**
- **Infectious Disease Incidence:** Cases per 100k population
- **Excess Mortality:** Percentage above baseline
- **Vaccination Rates:** Percentage vaccinated
- **Hospitalization Rates:** Hospitalizations per 100k

**Output Schema:**
- DataFrame with columns: `['timestamp', 'location', '<indicator_name>']`
- Values normalized to [0.0, 1.0] where 1.0 = maximum health stress

**Privacy:** Uses only coarse aggregates (country-level, no individual data)

---

### 10. GDELT Events (Global Event Signals)

**Status:** Active and fully implemented

**Implementation:**
- **Connector:** `app/services/ingestion/gdelt_events.py` → `GDELTEventsFetcher`
- **API:** GDELT Project API (https://api.gdeltproject.org/api/v2/)
- **Authentication:** None required (public API)
- **Rate Limits:** Generous free tier (no documented strict limits)
- **Update Frequency:** Daily (real-time monitoring)
- **Data Granularity:** Daily aggregated tone scores and event counts
- **Output:** Normalized tone score (0.0-1.0) and event count indices

**Usage:**
```python
from app.services.ingestion import GDELTEventsFetcher
fetcher = GDELTEventsFetcher()
tone_data = fetcher.fetch_event_tone(days_back=30)
event_data = fetcher.fetch_event_count(days_back=30)
```

**Notes:**
- Provides global media tone and event volume signals
- Integrated into digital_attention sub-index
- Returns empty DataFrame on API errors (graceful degradation)
- Caches responses for 60 minutes by default
- Appears in forecast explanations as "GDELT Tone" component when available
- **Live Monitoring:** Participates in live monitoring event detection (digital_attention_spike flag)

---

### 11. Our World in Data (Public Health Indicators)

**Status:** Active and fully implemented

**Implementation:**
- **Connector:** `app/services/ingestion/health_owid.py` → `OWIDHealthFetcher`
- **Source:** OWID datasets (https://github.com/owid/owid-datasets)
- **Format:** CSV files with country-level aggregates
- **Authentication:** None required
- **Update Frequency:** Daily
- **Data Granularity:** Country-level daily aggregates
- **Output:** Normalized health stress index (0.0-1.0)

**Usage:**
```python
from app.services.ingestion import OWIDHealthFetcher
fetcher = OWIDHealthFetcher()
health_data = fetcher.fetch_health_stress_index(country="United States", days_back=90)
excess_mortality = fetcher.fetch_excess_mortality(country="United States", days_back=90)
```

**Notes:**
- Provides excess mortality and health stress indicators
- Integrated into public_health_stress sub-index
- Uses only coarse aggregates (country-level, no individual data)
- Returns empty DataFrame on API errors (graceful degradation)
- Caches responses for 24 hours by default
- Appears in forecast explanations as "OWID Health Stress" component when available
- **Live Monitoring:** Participates in live monitoring event detection (health_stress_elevated flag)

---

### 12. USGS Earthquake Feed (Environmental Hazards)

**Status:** Active and fully implemented

**Implementation:**
- **Connector:** `app/services/ingestion/usgs_earthquakes.py` → `USGSEarthquakeFetcher`
- **API:** USGS Earthquake API (https://earthquake.usgs.gov/fdsnws/event/1/)
- **Authentication:** None required (public API)
- **Rate Limits:** No documented limits
- **Update Frequency:** Real-time
- **Data Granularity:** Daily aggregated intensity scores
- **Output:** Normalized earthquake intensity index (0.0-1.0)

**Usage:**
```python
from app.services.ingestion import USGSEarthquakeFetcher
fetcher = USGSEarthquakeFetcher()
earthquake_data = fetcher.fetch_earthquake_intensity(days_back=30, min_magnitude=4.0)
```

**Notes:**
- Provides global earthquake intensity signals
- Integrated into environmental_stress sub-index
- Aggregates earthquakes by date with magnitude-weighted intensity
- Returns empty DataFrame on API errors (graceful degradation)
- Caches responses for 60 minutes by default
- Appears in forecast explanations as "Earthquake Intensity" component when available
- **Live Monitoring:** Participates in live monitoring event detection (environmental_shock flag)

---

## Future Data Sources (Research Phase)

### 13. Social Media Sentiment (Idea)
- **Source:** Public sentiment APIs or aggregated social media data
- **Status:** Research phase
- **Considerations:** Privacy, licensing, rate limits, data quality

### 14. Additional Economic Indicators (Idea)
- **Source:** Additional market indices, commodity prices, currency exchange rates
- **Status:** Research phase
- **Considerations:** Data availability, relevance to behavioral forecasting

### 15. News Headlines / Media Attention (Idea)
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
