# Human Behavior Indicator Taxonomy

**Date:** 2025-01-XX
**Status:** Design Document

**Maintainer:** Thor Thor (codethor@gmail.com)

---

## Overview

This document defines the taxonomy of human behavior indicators organized into dimensions. Each dimension represents a distinct aspect of human behavioral patterns that can be measured using public data sources.

---

## Dimension 1: Economic Stress / Sentiment

**Purpose:** Measures economic uncertainty and market sentiment as proxies for behavioral stress.

### Indicators

| Indicator | Data Source | Access Method | Status | Refresh | Notes |
|-----------|-------------|---------------|--------|---------|-------|
| **Market Volatility** | CBOE VIX via yfinance | Python library, no auth | Implemented | Daily | Normalized with SPY for stress index |
| **Market Returns** | SPY (S&P 500 ETF) via yfinance | Python library, no auth | Implemented | Daily | Inverse correlation with stress |
| **Consumer Sentiment** | University of Michigan Consumer Sentiment Index via FRED | FRED API (free, no auth) | Planned | Monthly | Historical data available |
| **Unemployment Rate** | FRED API | FRED API (free, no auth) | Planned | Monthly | U.S. national rate |
| **Initial Jobless Claims** | FRED API | FRED API (free, no auth) | Planned | Weekly | Higher frequency signal |

**Sub-index Direction:** ECONOMIC_STRESS ↑ when volatility ↑, unemployment ↑, sentiment ↓

**Normalization:** Min-max scaling to [0.0, 1.0] with higher values = higher stress

---

## Dimension 2: Environmental Stress

**Purpose:** Measures weather-related discomfort and extreme environmental conditions.

### Indicators

| Indicator | Data Source | Access Method | Status | Refresh | Notes |
|-----------|-------------|---------------|--------|---------|-------|
| **Temperature Deviation** | Open-Meteo Archive API | HTTP API, no auth | Implemented | Daily | Deviation from 20C ideal |
| **Precipitation** | Open-Meteo Archive API | HTTP API, no auth | Implemented | Daily | Daily totals |
| **Wind Speed** | Open-Meteo Archive API | HTTP API, no auth | Implemented | Daily | Daily averages |
| **Heat Wave Indicators** | Open-Meteo (derived) | Computed from temperature | Planned | Daily | Days above threshold |
| **Active Fire Events** | NASA FIRMS | HTTP API, MAP_KEY required | Connector exists | Daily | Via connectors/firms_fires.py |

**Sub-index Direction:** ENVIRONMENTAL_STRESS ↑ during extreme heat/cold, storms, fires

**Normalization:** Weighted combination normalized to [0.0, 1.0]

---

## Dimension 3: Mobility / Activity Patterns

**Purpose:** Measures population movement and activity as indicators of behavioral normalcy.

### Indicators

| Indicator | Data Source | Access Method | Status | Refresh | Notes |
|-----------|-------------|---------------|--------|---------|-------|
| **OSM Changeset Activity** | OpenStreetMap Planet | HTTP download, no auth | Connector exists | Daily | Via connectors/osm_changesets.py |
| **Apple Mobility Trends** | Apple (archived) | CSV download (historical) | Planned | N/A | Historical only (2020-2022) |
| **Google Mobility Reports** | Google (archived) | CSV download (historical) | Planned | N/A | Historical only, discontinued |
| **Public Transit Ridership** | City open data portals | Varies by city | Planned | Daily/Weekly | Requires per-city integration |

**Sub-index Direction:** MOBILITY_ACTIVITY ↑ when people are more mobile/active vs baseline

**Normalization:** Z-score or percentile relative to historical baseline, then min-max to [0.0, 1.0]

---

## Dimension 4: Digital Attention / Media Intensity

**Purpose:** Measures digital attention spikes and media intensity as proxies for behavioral disruption.

### Indicators

| Indicator | Data Source | Access Method | Status | Refresh | Notes |
|-----------|-------------|---------------|--------|---------|-------|
| **Wikipedia Pageviews** | Wikimedia dumps | HTTP download, no auth | Connector exists | Daily | Via connectors/wiki_pageviews.py |
| **GDELT Media Tone** | GDELT Project | HTTP API, no auth | Planned | Daily | Global media sentiment/tone scores |
| **Google Trends** | Google Trends API | Limited alpha access | Planned | Daily | Requires API key, limited availability |

**Sub-index Direction:** DIGITAL_ATTENTION ↑ when attention on "crisis" topics spikes

**Normalization:** Normalize pageview/tone metrics, detect spikes relative to baseline

---

## Dimension 5: Public Health Stress

**Purpose:** Measures public health indicators that affect behavioral patterns (aggregate only, no individual data).

### Indicators

| Indicator | Data Source | Access Method | Status | Refresh | Notes |
|-----------|-------------|---------------|--------|---------|-------|
| **CDC Aggregate Indicators** | CDC Data API | HTTP API, no auth | Planned | Weekly | Coarse aggregates only |
| **WHO Health Indicators** | WHO APIs | HTTP API, varies | Planned | Weekly | Aggregate statistics |
| **Our World in Data** | OWID API/CSV | HTTP download, no auth | Planned | Daily | Aggregated public health metrics |

**Sub-index Direction:** PUBLIC_HEALTH_STRESS ↑ when health indicators worsen (cases, hospitalizations)

**Normalization:** Min-max scaling, higher values = higher health stress

**Privacy:** Must use only coarse aggregates (national/regional, ≥24h temporal bins, no individual data)

---

## Integration Status Summary

### Implemented (Active)

- Market volatility/stress (VIX/SPY) via yfinance
- Weather/environmental data (Open-Meteo)
- OSM changesets (connector exists, not integrated into forecasting)
- Wikipedia pageviews (connector exists, not integrated into forecasting)
- FIRMS fires (connector exists, not integrated into forecasting)

### Stubbed (Placeholder Structure)

- Search trends (generic connector, requires API configuration)
- Public health (generic connector, requires API configuration)
- Mobility (generic connector, requires API configuration)

### Planned (Not Yet Implemented)

- FRED API integration (consumer sentiment, unemployment, jobless claims)
- GDELT media tone indicators
- Apple/Google mobility historical data
- Our World in Data health aggregates
- Heat wave computation from weather data

---

## Access Methods Reference

### FRED API

**URL:** https://api.stlouisfed.org/fred/
**Authentication:** API key (free registration at https://fred.stlouisfed.org/docs/api/api_key.html)
**Rate Limits:** 120 requests per 120 seconds
**Examples:**
- Consumer Sentiment: Series ID `UMCSENT`
- Unemployment Rate: Series ID `UNRATE`
- Initial Jobless Claims: Series ID `ICSA`

### GDELT Project

**URL:** https://api.gdeltproject.org/api/v2/
**Authentication:** None required for basic queries
**Rate Limits:** Generous free tier
**Data:** Global media mentions, tone scores, event data

### Our World in Data (OWID)

**URL:** https://github.com/owid/owid-datasets (CSV) or direct API endpoints
**Authentication:** None required
**Format:** CSV files with country-level aggregates
**Data:** COVID-19, vaccination rates, excess mortality, etc.

---

## Data Quality Requirements

All indicators must:

1. **Be publicly available** (no proprietary or restricted datasets)
2. **Handle missing data gracefully** (return empty DataFrame, don't crash)
3. **Implement caching** (reduce API calls, respect rate limits)
4. **Return normalized indices** (0.0-1.0 range where applicable)
5. **Include timestamp column** (for time-series alignment)
6. **Log warnings** when data unavailable (don't fail silently)
7. **Comply with licensing terms** and rate limits
8. **Respect privacy regulations** (no individual-level data, coarse aggregates only)

---

## Next Steps

1. Implement FRED API connector for economic indicators
2. Integrate existing connectors (OSM, Wiki, FIRMS) into forecasting pipeline
3. Add GDELT connector for media tone
4. Create behavior index computation module with sub-indices
5. Update harmonizer to compute sub-indices separately

---

**Maintainer:** Thor Thor (codethor@gmail.com)
