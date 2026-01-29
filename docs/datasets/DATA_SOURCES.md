# Data Sources Documentation

## Overview
This document describes all data sources integrated into the human-behaviour-convergence project. All sources are publicly available and comply with strict ethical and privacy standards.

## Ethical Standards
All data sources must:
- [OK] Be publicly available (no private/paid APIs)
- [OK] Comply with privacy regulations (GDPR, CCPA)
- [OK] Not collect or store PII
- [OK] Follow k-anonymity (minimum 15 individuals per aggregation)
- [OK] Use geo-precision ≤ H3-9 (≈ 0.1 km²)
- [OK] Have clear data licensing

## Data Source Categories

### Health Data Sources

#### WHO Disease Surveillance
- **Source**: World Health Organization (WHO) Global Health Observatory (GHO)
- **API Endpoint**: `https://ghoapi.azureedge.net/api/`
- **Category**: Health
- **Requires Key**: No
- **Data Provided**: Global disease outbreak indicators, mortality data, epidemiological signals
- **Update Frequency**: Daily
- **Connector**: `connectors/who_disease.py`
- **Status**: [OK] Active
- **Notes**: GHO OData API will be deprecated end of 2025, replaced with new OData implementation

#### OWID Health Data
- **Source**: Our World in Data (OWID)
- **Category**: Health
- **Requires Key**: No
- **Data Provided**: Aggregated health statistics, vaccination rates, mortality data
- **Connector**: `app/services/ingestion/health_owid.py`
- **Status**: [OK] Active

### Economic Data Sources

#### FRED Economic Data
- **Source**: Federal Reserve Economic Data (FRED)
- **Category**: Economic
- **Requires Key**: No (public data)
- **Data Provided**: GDP growth, unemployment rate, consumer sentiment, CPI inflation, jobless claims
- **Connector**: `app/services/ingestion/economic_fred.py`
- **Status**: [OK] Active

#### Market Sentiment
- **Source**: Public financial market data
- **Category**: Economic
- **Requires Key**: No
- **Data Provided**: Volatility index (VIX), market indices (SPY), financial market signals
- **Connector**: `app/services/ingestion/finance.py`
- **Status**: [OK] Active

#### EIA Energy Data
- **Source**: Energy Information Administration (EIA)
- **Category**: Economic
- **Requires Key**: No (public data)
- **Data Provided**: Energy prices (gasoline, natural gas, crude oil), electricity demand, grid stress indicators
- **Connector**: `app/services/ingestion/eia_energy.py`
- **Status**: [OK] Active

#### EIA Fuel Prices by State
- **Source**: Energy Information Administration (EIA) API v2
- **Category**: Economic
- **Requires Key**: No (public data)
- **Data Provided**: State-level gasoline prices, fuel stress index (normalized price deviation from national average)
- **Update Frequency**: Weekly (Monday releases)
- **Geo Resolution**: State-level (50 states + DC)
- **Connector**: `app/services/ingestion/eia_fuel_prices.py`
- **Status**: [OK] Active (MVP1)
- **Sub-Index Impact**: `economic_stress` → child `fuel_stress` (weight: 15%)
- **Failure Modes**:
  - API rate limits: Cache 24h, fallback to last known value
  - Missing state data: Use national average with `source_quality="fallback_national"`
  - API downtime: Return cached data with `source_quality="stale_cache"`
- **Notes**: State prices vary 20-40% from national average, providing high regional variance

### Environmental Data Sources

#### Weather Patterns
- **Source**: Open-Meteo API
- **Category**: Environmental
- **Requires Key**: No
- **Data Provided**: Temperature, precipitation, wind speed, environmental discomfort scores
- **Connector**: `app/services/ingestion/weather.py`
- **Status**: [OK] Active

#### Air Quality
- **Source**: OpenAQ
- **Category**: Environmental
- **Requires Key**: No
- **Data Provided**: PM2.5, PM10, AQI measurements from global monitoring network
- **Connector**: `app/services/ingestion/openaq_air_quality.py`
- **Status**: [OK] Active

#### Weather Alerts
- **Source**: National Weather Service (NWS)
- **Category**: Environmental
- **Requires Key**: No
- **Data Provided**: Active weather alerts (warnings, watches, advisories)
- **Connector**: `app/services/ingestion/nws_alerts.py`
- **Status**: [OK] Active

#### USGS Earthquakes
- **Source**: US Geological Survey (USGS)
- **Category**: Environmental
- **Requires Key**: No
- **Data Provided**: Earthquake data, seismic activity indicators
- **Connector**: `app/services/ingestion/usgs_earthquakes.py`
- **Status**: [OK] Active

### Digital Attention Sources

#### Search Trends
- **Source**: Wikimedia Pageviews API
- **Category**: Digital
- **Requires Key**: No
- **Data Provided**: Wikipedia pageview data as proxy for digital attention and search interest
- **Connector**: `app/services/ingestion/search_trends.py`
- **Status**: [OK] Active

#### GDELT Events
- **Source**: Global Database of Events, Language, and Tone (GDELT)
- **Category**: Digital
- **Requires Key**: No
- **Data Provided**: Global event and crisis signals, news event data
- **Connector**: `app/services/ingestion/gdelt_events.py`
- **Status**: [OK] Active

#### Cyber Risk
- **Source**: CISA Known Exploited Vulnerabilities (KEV)
- **Category**: Digital
- **Requires Key**: No
- **Data Provided**: Known exploited vulnerabilities, cybersecurity threat indicators
- **Connector**: `app/services/ingestion/cisa_kev.py`
- **Status**: [OK] Active

### Mobility Sources

#### Mobility Patterns
- **Source**: TSA Passenger Throughput
- **Category**: Mobility
- **Requires Key**: No
- **Data Provided**: Daily passenger throughput data as mobility indicator
- **Connector**: `app/services/ingestion/mobility.py`
- **Status**: [OK] Active

### Government/Social Sources

#### Emergency Management
- **Source**: OpenFEMA
- **Category**: Government
- **Requires Key**: No
- **Data Provided**: Disaster declarations, emergency events, FEMA program activity
- **Connector**: `app/services/ingestion/openfema_emergency_management.py`
- **Status**: [OK] Active

#### Legislative Activity
- **Source**: GDELT (no-key) + OpenStates (optional enhancement)
- **Category**: Government
- **Requires Key**: No (OpenStates optional)
- **Data Provided**: Legislative/governance events, political activity signals
- **Connector**: `app/services/ingestion/openstates_legislative.py`
- **Status**: [OK] Active

#### Political Stress
- **Source**: GDELT + OpenStates
- **Category**: Social/Political
- **Requires Key**: No (OpenStates optional)
- **Data Provided**: Political stress indicators, legislative volatility
- **Connector**: `app/services/ingestion/political.py`
- **Status**: [OK] Active

#### Crime & Public Safety
- **Source**: Public crime data APIs
- **Category**: Social
- **Requires Key**: No
- **Data Provided**: Crime statistics, public safety indicators
- **Connector**: `app/services/ingestion/crime.py`
- **Status**: [OK] Active

#### Misinformation Stress
- **Source**: GDELT + news analysis
- **Category**: Social
- **Requires Key**: No
- **Data Provided**: Misinformation intensity, narrative fragmentation signals
- **Connector**: `app/services/ingestion/misinformation.py`
- **Status**: [OK] Active

#### Social Cohesion
- **Source**: GDELT + aggregated social signals
- **Category**: Social
- **Requires Key**: No
- **Data Provided**: Social cohesion indicators, community anxiety proxies
- **Connector**: `app/services/ingestion/social_cohesion.py`
- **Status**: [OK] Active

### Public Data Connectors

#### Wikipedia Pageviews
- **Source**: Wikimedia Pageviews API
- **Category**: Digital
- **Requires Key**: No
- **Data Provided**: Hourly pageview data for Wikipedia articles
- **Connector**: `connectors/wiki_pageviews.py`
- **Status**: [OK] Active

#### OSM Changesets
- **Source**: OpenStreetMap Changesets API
- **Category**: Digital
- **Requires Key**: No
- **Data Provided**: OpenStreetMap edit activity, geographic changes
- **Connector**: `connectors/osm_changesets.py`
- **Status**: [OK] Active

#### FIRMS Fires
- **Source**: NASA FIRMS (Fire Information for Resource Management System)
- **Category**: Environmental
- **Requires Key**: Optional (MAP_KEY for enhanced access)
- **Data Provided**: Active fire detection data, fire counts, brightness measurements
- **Connector**: `connectors/firms_fires.py`
- **Status**: [OK] Active

## Data Source Registry

All data sources are registered in `app/services/ingestion/source_registry.py`. The registry provides:
- Source metadata (name, category, description)
- Configuration requirements (API keys, environment variables)
- Health status tracking
- Graceful degradation when sources are unavailable

## Adding New Data Sources

To add a new data source:

1. **Create Connector/Fetcher**:
   - For simple public data: Create in `connectors/` following `AbstractSync` pattern
   - For complex ingestion: Create in `app/services/ingestion/` following fetcher pattern

2. **Register Source**: Add to `app/services/ingestion/source_registry.py` in `initialize_registry()`

3. **Add CI Offline Support**: Add synthetic data generation in `app/services/ingestion/ci_offline_data.py`

4. **Add Tests**: Create tests in `tests/test_connectors.py` or `tests/test_ingestion/`

5. **Update Documentation**: Add entry to this file

6. **Integrate into Pipeline**: Update `app/core/prediction.py` if needed for forecasting

## Privacy and Ethics Compliance

All data sources are validated for:
- [OK] No PII collection
- [OK] K-anonymity (minimum 15 individuals)
- [OK] Geo-precision limits (H3-9 or coarser)
- [OK] Public data only
- [OK] Ethical data practices

See `connectors/base.py` for the `ethical_check` decorator that enforces these standards.

## Enterprise Dataset Expansion (Planned)

See **`docs/ENTERPRISE_DATASET_EXPANSION_PLAN.md`** for the full plan. **Top 5 MVP** sources to be added:

| Source | Category | Geo | Status |
|--------|----------|-----|--------|
| EIA Gasoline by State | Economic | State | Planned |
| U.S. Drought Monitor (State) | Environmental | State | Planned |
| NOAA Storm Events (State) | Environmental | State/County | Planned |
| Eviction Lab (State/City) | Economic | State/City | Planned |
| CDC WONDER Overdose (State) | Health | State | Planned |

Each will be documented here upon implementation, with API details, failure modes, and observability.

## Future Enhancements

Potential new sources (under evaluation):
- NOAA Climate Data (enhanced weather/climate indicators)
- City-specific transit APIs (where publicly available)
- Additional public health surveillance systems
- FDIC branch history, NIBRS state-level, NHSN hospital occupancy (per Enterprise Plan)

## Support

For questions about data sources, see:
- Source registry: `/api/sources/status` endpoint
- Documentation: This file and `docs/NEW_DATA_SOURCES_PLAN.md`
- Code: `app/services/ingestion/` and `connectors/`
