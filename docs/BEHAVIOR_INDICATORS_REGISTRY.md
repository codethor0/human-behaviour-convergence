# Behavioral Indicators Registry

**Date:** 2025-01-XX
**Version:** 2.0

**Maintainer:** Thor Thor (codethor@gmail.com)

---

## Overview

This registry catalogs all behavioral indicators used or planned for the Human Behaviour Convergence forecasting platform. Each indicator represents a measurable proxy for human behavioral patterns, organized by dimension.

**Geographic Coverage:** Economic and environmental indicators are parameterized by region (latitude/longitude) and support all configured regions, including global cities and US states. See `docs/REGIONS.md` for supported regions.

**Status Legend:**
- **ACTIVE** - Implemented in code and actively used in Behavior Index computation
- **PLANNED** - Has clear target API/schema, design complete, implementation pending
- **IDEA** - Interesting concept, requires research/licensing review before implementation

---

## Dimension 1: Economic Stress & Uncertainty

**Purpose:** Measures economic uncertainty, market volatility, and consumer sentiment as proxies for behavioral stress and disruption.

| Indicator Name | What Human Behavior It Proxies | Example Metrics / Units | Candidate Public Data Source(s) | Status |
|----------------|-------------------------------|-------------------------|--------------------------------|--------|
| **Market Volatility (VIX)** | Investor fear, economic uncertainty, risk aversion behavior | VIX index (0-100+), normalized to [0,1] | CBOE VIX via yfinance | ACTIVE |
| **Market Returns (SPY)** | Economic confidence, wealth effects on spending behavior | Daily returns (%), normalized inverse | S&P 500 ETF via yfinance | ACTIVE |
| **Consumer Sentiment** | Consumer confidence, spending intentions, economic outlook | Index (0-100+), normalized | University of Michigan Consumer Sentiment (FRED: UMCSENT) | ACTIVE |
| **Unemployment Rate** | Labor market stress, job insecurity, reduced spending | Percentage (0-100%), normalized | FRED API (UNRATE) | ACTIVE |
| **Initial Jobless Claims** | Weekly labor market disruption, economic shock signals | Weekly claims count, normalized | FRED API (ICSA) | ACTIVE |
| **Credit Spreads** | Financial stress, credit market tightness | Basis points, normalized | FRED API (BAMLC0A0CM) | IDEA |
| **GDP Growth Rate** | Economic expansion/contraction, overall economic health | Quarterly percentage change | FRED API (GDPC1) | IDEA |

**Human Behavior Story:** Economic stress indicators capture how financial uncertainty and market volatility affect human behavior. High volatility (VIX spikes) and market declines correlate with reduced consumer spending, increased savings, and behavioral changes like reduced travel and discretionary purchases. Unemployment and jobless claims directly measure economic disruption that affects mobility, spending, and overall behavioral patterns.

---

## Dimension 2: Environmental & Climate Stress

**Purpose:** Measures weather-related discomfort, extreme environmental conditions, and climate stress that affect human behavior and mobility patterns.

| Indicator Name | What Human Behavior It Proxies | Example Metrics / Units | Candidate Public Data Source(s) | Status |
|----------------|-------------------------------|-------------------------|--------------------------------|--------|
| **Temperature Deviation** | Thermal comfort, outdoor activity levels, energy consumption | Degrees Celsius deviation from 20C ideal, normalized | Open-Meteo Archive API | ACTIVE |
| **Precipitation** | Outdoor activity disruption, flood risk, travel delays | Daily mm, normalized | Open-Meteo Archive API | ACTIVE |
| **Wind Speed** | Outdoor activity comfort, storm intensity | m/s, normalized | Open-Meteo Archive API | ACTIVE |
| **Heat Wave Indicators** | Extreme heat stress, health risks, reduced outdoor activity | Days above threshold (e.g., 35C), normalized | Open-Meteo (derived from temperature) | PLANNED |
| **Active Fire Events** | Evacuation behavior, air quality impacts, regional disruption | Fire count per region, normalized | NASA FIRMS API (connector exists) | PLANNED |
| **Earthquake Intensity** | Environmental hazard, regional disruption, safety concerns | Daily intensity score (magnitude-weighted), normalized | USGS Earthquake API | ACTIVE |
| **Air Quality Index** | Health-related behavior changes, outdoor activity reduction | AQI (0-500), normalized | EPA AirNow API, OpenAQ | IDEA |
| **Drought Indicators** | Agricultural stress, water restrictions, regional economic impact | Drought severity index | NOAA Climate Data | IDEA |

**Human Behavior Story:** Environmental stress directly impacts human behavior through physical comfort and safety. Extreme temperatures reduce outdoor activity and increase energy consumption. Heat waves correlate with increased mortality, reduced mobility, and behavioral changes. Wildfires cause evacuations and regional disruption. Precipitation extremes affect travel patterns and outdoor activities.

---

## Dimension 3: Mobility & Physical Activity

**Purpose:** Measures population movement patterns, transit usage, and physical activity as indicators of behavioral normalcy and disruption.

| Indicator Name | What Human Behavior It Proxies | Example Metrics / Units | Candidate Public Data Source(s) | Status |
|----------------|-------------------------------|-------------------------|--------------------------------|--------|
| **OSM Changeset Activity** | Geographic data editing activity, proxy for local engagement | Changeset count per H3-9 cell, normalized | OpenStreetMap Planet (connector exists) | PLANNED |
| **Apple Mobility Trends** | Relative mobility vs baseline (driving, transit, walking) | Percentage change vs baseline, normalized | Apple Mobility Reports (archived 2020-2022) | PLANNED |
| **Google Mobility Reports** | Retail/recreation, grocery/pharmacy, parks, transit, workplace | Percentage change vs baseline | Google Mobility Reports (archived, discontinued) | PLANNED |
| **Public Transit Ridership** | Urban mobility patterns, economic activity proxy | Daily/weekly ridership counts, normalized | City open data portals (varies by city) | IDEA |
| **Traffic Volume** | Road usage, economic activity, mobility patterns | Vehicle counts, normalized | City/state DOT APIs | IDEA |
| **Pedestrian Activity** | Urban activity levels, safety perceptions | Pedestrian count sensors | City open data portals | IDEA |

**Human Behavior Story:** Mobility patterns are direct proxies for behavioral normalcy. During crises (pandemics, natural disasters, economic shocks), mobility typically decreases as people stay home, reduce travel, and change daily routines. Increased mobility often indicates recovery and return to normal patterns. Transit usage reflects urban economic activity and social engagement.

---

## Dimension 4: Digital Attention & Media Intensity

**Purpose:** Measures digital attention spikes, information load, and media intensity as proxies for behavioral disruption and crisis awareness.

| Indicator Name | What Human Behavior It Proxies | Example Metrics / Units | Candidate Public Data Source(s) | Status |
|----------------|-------------------------------|-------------------------|--------------------------------|--------|
| **Wikipedia Pageviews** | Public interest in topics, information-seeking behavior | Hourly/daily pageview counts, normalized | Wikimedia Pageviews API (connector exists) | PLANNED |
| **GDELT Media Tone** | Global media sentiment, crisis intensity, event coverage | Tone score (-100 to +100), normalized | GDELT Project API | ACTIVE |
| **GDELT Event Counts** | Global event intensity, conflict/disaster coverage | Daily event counts by type, normalized | GDELT Project API | ACTIVE |
| **Google Trends** | Search interest in topics, information demand | Relative search volume (0-100), normalized | Google Trends API (limited access) | IDEA |
| **News Volume** | Media coverage intensity, information overload | Article count per topic/time, normalized | News API aggregators | IDEA |
| **Social Media Sentiment** | Public sentiment, crisis awareness (aggregate only) | Sentiment score, normalized | Public sentiment APIs (if available) | IDEA |

**Human Behavior Story:** Digital attention spikes often precede or accompany behavioral disruption. During crises, people seek information (Wikipedia pageviews increase), media coverage intensifies (GDELT tone/events), and search interest spikes. These indicators capture the "information environment" that influences human behavior and decision-making.

---

## Dimension 5: Public Health & Stress

**Purpose:** Measures aggregate public health indicators that affect behavioral patterns (coarse aggregates only, no individual data).

| Indicator Name | What Human Behavior It Proxies | Example Metrics / Units | Candidate Public Data Source(s) | Status |
|----------------|-------------------------------|-------------------------|--------------------------------|--------|
| **Infectious Disease Incidence** | Health stress, behavioral restrictions, risk perception | Cases per 100k population, normalized | Our World in Data (OWID), CDC Data API | PLANNED |
| **Excess Mortality** | Overall health burden, pandemic/disaster impact | Percentage above baseline, normalized | OWID, CDC, WHO | ACTIVE |
| **Vaccination Rates** | Public health response, risk mitigation behavior | Percentage vaccinated, normalized | OWID | PLANNED |
| **Hospitalization Rates** | Healthcare system stress, severe illness burden | Hospitalizations per 100k, normalized | OWID, CDC | PLANNED |
| **OWID Health Stress Index** | Composite health burden indicator | Normalized index (0-1), combines excess mortality | OWID | ACTIVE |
| **Mental Health Indicators** | Psychological stress, behavioral health burden | Survey-based indices (if available) | National health surveys (aggregate) | IDEA |
| **Life Expectancy Changes** | Long-term health trends, population health stress | Years, normalized change | OWID, WHO | IDEA |

**Human Behavior Story:** Public health indicators directly measure the health burden affecting populations. High disease incidence, excess mortality, and hospitalization rates correlate with behavioral changes: reduced mobility, increased remote work, mask-wearing, and social distancing. These indicators capture the health stress that drives behavioral adaptation.

---

## Dimension 6: Conflict / Social Unrest / Governance (Optional)

**Purpose:** Measures conflict intensity, social unrest, and governance stability as proxies for behavioral disruption.

| Indicator Name | What Human Behavior It Proxies | Example Metrics / Units | Candidate Public Data Source(s) | Status |
|----------------|-------------------------------|-------------------------|--------------------------------|--------|
| **Protest/Event Counts** | Social unrest, political instability, civil disruption | Daily event counts, normalized | GDELT Project API | IDEA |
| **Conflict Intensity** | Armed conflict, violence, regional instability | Conflict events per region, normalized | GDELT Project API, UCDP | IDEA |
| **Regime Stability** | Political stability, governance quality | Stability index (if available) | Various governance indices | IDEA |
| **Refugee/Displacement** | Forced migration, humanitarian crisis | Displacement counts, normalized | UNHCR, IDMC | IDEA |

**Human Behavior Story:** Conflict and social unrest cause significant behavioral disruption: forced migration, reduced economic activity, increased stress, and changed mobility patterns. These indicators capture extreme forms of behavioral disruption beyond economic or environmental stress.

---

## Summary by Status

### ACTIVE (11+ indicators)
- Market Volatility (VIX)
- Market Returns (SPY)
- Consumer Sentiment (FRED) - if FRED_API_KEY set
- Unemployment Rate (FRED) - if FRED_API_KEY set
- Initial Jobless Claims (FRED) - if FRED_API_KEY set
- Temperature Deviation
- Precipitation
- Wind Speed
- GDELT Media Tone
- GDELT Event Counts
- Earthquake Intensity (USGS)
- Excess Mortality (OWID)
- OWID Health Stress Index

### PLANNED (8+ indicators)
- Heat Wave Indicators (derived)
- Active Fire Events (FIRMS)
- OSM Changeset Activity
- Wikipedia Pageviews
- Infectious Disease Incidence (OWID)
- Vaccination Rates (OWID)
- Hospitalization Rates (OWID)

### IDEA (10+ indicators)
- Credit Spreads
- GDP Growth Rate
- Air Quality Index
- Drought Indicators
- Public Transit Ridership
- Traffic Volume
- Google Trends
- News Volume
- Mental Health Indicators
- Conflict/Protest indicators

---

## Integration Priority

**High Priority (Next Implementation):**
1. Integrate existing connectors (Wiki Pageviews, OSM Changesets) into forecasting pipeline
2. Heat wave computation from weather data
3. FIRMS fire integration
4. Additional OWID health indicators (vaccination, hospitalization)

**Medium Priority:**
5. Heat wave computation from weather data
6. FIRMS fire integration
7. GDELT event counts

**Low Priority (Research Phase):**
8. City-specific transit data
9. Air quality indicators
10. Conflict/social unrest indicators

---

**Maintainer:** Thor Thor (codethor@gmail.com)
