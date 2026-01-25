# Enterprise Dataset Expansion + Regional Signal Hardening Plan

**Date**: 2026-01-22  
**Status**: Planning Phase  
**Goal**: Move the project toward **enterprise-grade open-source credibility**.  
**Objective**: Expand dataset portfolio to materially improve regional behavioral forecasting accuracy, variance, and explainability while maintaining zero-regression guarantees.

---

## SECTION 0 — Absolute Guardrails (Non-Negotiable)

- **NO** private, personal, or PII data.
- **NO** scraping behind auth walls unless explicitly licensed and documented.
- **NO** social media APIs requiring OAuth (Twitter/X, Meta, Instagram, TikTok).
- **NO** “black box” vendor feeds that cannot be reproduced independently.
- **ALL** datasets must be: **public or openly licensed**, **aggregated**, **regionally attributable** (or explicitly global).
- Every **REGIONAL** dataset must: **use geo inputs in fetch logic**, **include geo in cache keys**, **emit metrics with region labels**.
- Every dataset must have: **failure mode documentation**, **fallback behavior**, **observability hooks**.
- **Zero refactors.** Additive, surgical changes only.
- Every dataset addition requires: **evidence of regional variance**, **tests**, **documentation**, **metrics**.

---

## Executive Summary

This plan identifies **15 high-value datasets** across 7 categories to strengthen regional behavioral forecasting. The **Top 5 MVP datasets** are prioritized for immediate implementation, with detailed integration blueprints, regionality safety nets, and observability requirements.

**Success Criteria**:
- Two distant regions (e.g., Illinois vs Arizona) show measurable divergence in ≥3 independent sub-indices within 30 days
- Dashboards clearly distinguish global vs regional signals
- Forecasts are auditable back to source-level contributors
- Zero regressions in existing workflows

### Prompt Compliance Map (Enhanced Master Prompt)

| Prompt section | Plan location | Status |
|----------------|---------------|--------|
| **Section 0** — Absolute Guardrails | § Section 0 | ✅ |
| **Section 1** — Why we are adding datasets | Exec Summary, Success Criteria | ✅ |
| **Section 2** — Dataset categories (2.1–2.7) | § Section 1 (1.1–1.7) | ✅ |
| **Section 3** — Top 10–15 ranked + Top 5 MVP | § Section 2 | ✅ |
| **Section 4** — MVP integration blueprints (Top 5) | § Section 3 | ✅ |
| **Section 5** — Discrepancy & regionality safety net | § Section 4 | ✅ |
| **Section 6** — Dashboard & UX (GLOBAL/REGIONAL, contribution, source health) | § Section 5 | ✅ |
| **Section 7** — Documentation (DATA_SOURCES, etc.) | § Section 6 | ✅ |
| **Section 8** — Final output (catalog, Top 5, checklist, risk, impact, order) | § 1–2, 7–10 | ✅ |
| **Section 9** — Success criteria | Exec Summary, § Section 9 | ✅ |
| **Next Steps** — Agents, Explainability dashboard, open-source positioning | § Section 10.2 | ✅ |

---

## SECTION 1: Expanded Dataset Catalog (15 Items)

### 1.1 — ECONOMIC MICRO-SIGNALS (REGIONAL, HIGH VALUE)

#### Dataset 1: EIA Gasoline Prices by State
- **Dataset Name**: EIA Weekly Gasoline Prices by State
- **Behavioral Mechanism**: Local fuel costs drive transportation decisions, economic stress, and migration patterns
- **Geo Resolution**: State-level (50 states + DC)
- **Update Frequency**: Weekly (Monday releases)
- **Source & License**: Energy Information Administration (EIA) API v2, public domain
- **API Endpoint**: `https://api.eia.gov/v2/petroleum/pri/gnd/data/`
- **Raw Fields**: `price`, `state`, `week_ending`, `product` (regular, midgrade, premium, diesel)
- **Derived Features**:
  - `fuel_stress_index`: Normalized price deviation from national average (0-1)
  - `fuel_volatility`: Rolling 4-week coefficient of variation
  - `regional_fuel_burden`: Price × typical consumption proxy
- **Sub-Index Impact**: `economic_stress` (new child: `fuel_stress`)
- **Expected Regional Variance**: **HIGH** (state prices vary 20-40% from national average)
- **Observability Metrics**: `eia_fuel_price{state,product}`, `eia_fuel_stress_index{state}`, `data_source_status{source="eia_fuel",region}`
- **Failure Modes**:
  - API rate limits (1000 requests/day): Cache 24h, fallback to last known value
  - Missing state data: Use national average with `source_quality="fallback_national"`
  - API downtime: Return cached data with `source_quality="stale_cache"`
- **Ethical Review Notes**: ✅ Public aggregate data, no PII, state-level only

#### Dataset 2: FDIC Bank Branch Closures
- **Dataset Name**: FDIC Branch History & Closures
- **Behavioral Mechanism**: Financial service deserts correlate with economic stress, reduced access, and community decline
- **Geo Resolution**: State + County (can aggregate to state)
- **Update Frequency**: Quarterly (FDIC releases)
- **Source & License**: FDIC Institution Directory, public domain
- **API Endpoint**: `https://banks.data.fdic.gov/api/institutions`
- **Raw Fields**: `branch_count`, `closure_count`, `state`, `county`, `date`
- **Derived Features**:
  - `banking_access_index`: Branches per 10k population (inverse stress)
  - `branch_closure_rate`: Quarterly closures per existing branches
  - `financial_desert_score`: Normalized access deficit (0-1)
- **Sub-Index Impact**: `economic_stress` (new child: `financial_access_stress`)
- **Expected Regional Variance**: **MEDIUM-HIGH** (rural states show 2-3x closure rates)
- **Observability Metrics**: `fdic_branch_count{state,county}`, `fdic_closure_rate{state}`, `data_source_status{source="fdic_branches",region}`
- **Failure Modes**:
  - FDIC API changes: Version detection, fallback to CSV bulk download
  - Missing county data: Aggregate to state level
  - Historical gaps: Forward-fill with last known value
- **Ethical Review Notes**: ✅ Public institutional data, aggregated, no PII

#### Dataset 3: Eviction Lab Filings (State/City)
- **Dataset Name**: Eviction Lab Eviction Filings
- **Behavioral Mechanism**: Housing instability drives stress, migration, and community disruption
- **Geo Resolution**: State + City (limited geography: ~30 states, ~100 cities)
- **Update Frequency**: Monthly (with 1-2 month lag)
- **Source & License**: Eviction Lab (Princeton), CC BY 4.0
- **API Endpoint**: S3 bucket + CSV: `https://eviction-lab-data-downloads.s3.amazonaws.com/`
- **Raw Fields**: `eviction_filings`, `eviction_rate`, `state`, `city`, `month`
- **Derived Features**:
  - `eviction_stress_index`: Normalized filing rate (0-1)
  - `housing_instability_trend`: 3-month moving average change
  - `eviction_burden`: Filings per 1000 renter households
- **Sub-Index Impact**: `economic_stress` (new child: `housing_stress`)
- **Expected Regional Variance**: **VERY HIGH** (rates vary 10x: 0.5% to 5%+)
- **Observability Metrics**: `eviction_filings{state,city}`, `eviction_stress_index{region}`, `data_source_status{source="eviction_lab",region}`
- **Failure Modes**:
  - Limited geography: Mark regions as "not_available", use state-level proxy
  - S3 access issues: Retry with exponential backoff, fallback to cached data
  - Data lag: Document expected 1-2 month delay, use most recent available
- **Ethical Review Notes**: ✅ Aggregated public data, CC BY 4.0, no PII

### 1.2 — ENVIRONMENTAL & CLIMATE SHOCKS (REGIONAL, HIGH VARIANCE)

#### Dataset 4: U.S. Drought Monitor (State)
- **Dataset Name**: U.S. Drought Monitor State-Level DSCI
- **Behavioral Mechanism**: Drought severity affects agriculture, water stress, and economic activity
- **Geo Resolution**: State-level (50 states)
- **Update Frequency**: Weekly (Thursday releases)
- **Source & License**: National Drought Mitigation Center (NDMC), public domain
- **API Endpoint**: `https://droughtmonitor.unl.edu/DmData/DataTables.aspx` (CSV export)
- **Raw Fields**: `DSCI` (Drought Severity and Coverage Index, 0-500), `state`, `week_ending`
- **Derived Features**:
  - `drought_stress_index`: Normalized DSCI (0-1, where 1 = extreme drought)
  - `drought_persistence`: Weeks in current severity category
  - `drought_shock`: Week-over-week DSCI change (shock detection)
- **Sub-Index Impact**: `environmental_stress` (new child: `drought_stress`)
- **Expected Regional Variance**: **VERY HIGH** (DSCI ranges 0-500, states vary dramatically)
- **Observability Metrics**: `drought_dsci{state}`, `drought_stress_index{state}`, `data_source_status{source="drought_monitor",region}`
- **Failure Modes**:
  - CSV format changes: Robust parsing with fallback regex
  - Missing state data: Use national average with `source_quality="fallback_national"`
  - Weekly lag: Document expected Thursday release, cache until next week
- **Ethical Review Notes**: ✅ Public climate data, aggregated, no PII

#### Dataset 5: NOAA Storm Events (State/County)
- **Dataset Name**: NOAA Storm Events Database
- **Behavioral Mechanism**: Severe weather events (hail, flood, heat wave, tornado) create immediate stress and recovery lag
- **Geo Resolution**: State + County (can aggregate to state)
- **Update Frequency**: Monthly (with 1-2 month lag for final data)
- **Source & License**: NOAA National Centers for Environmental Information, public domain
- **API Endpoint**: Bulk CSV download: `https://www.ncei.noaa.gov/stormevents/ftp.jsp`
- **Raw Fields**: `event_type`, `begin_date`, `end_date`, `state`, `county`, `damage_property`, `injuries`, `deaths`
- **Derived Features**:
  - `storm_event_frequency`: Events per month by type
  - `storm_severity_index`: Weighted sum (deaths × 10 + injuries × 1 + property_damage_log)
  - `heatwave_stress`: Heat wave days per month (normalized)
  - `flood_risk_stress`: Flood events per month (normalized)
- **Sub-Index Impact**: `environmental_stress` (new children: `heatwave_stress`, `flood_risk_stress`, `storm_severity_stress`)
- **Expected Regional Variance**: **VERY HIGH** (coastal states: hurricanes; plains: tornadoes; desert: heat waves)
- **Observability Metrics**: `noaa_storm_events{state,event_type}`, `storm_severity_index{state}`, `data_source_status{source="noaa_storms",region}`
- **Failure Modes**:
  - Large CSV files (100MB+): Stream parsing, chunk processing, cache intermediate results
  - Data lag: Use provisional data, document final data delay
  - Missing county: Aggregate to state level
- **Ethical Review Notes**: ✅ Public weather/climate data, aggregated, no PII

#### Dataset 6: NASA FIRMS Wildfire Data (State)
- **Dataset Name**: NASA FIRMS Active Fire Data
- **Behavioral Mechanism**: Wildfire exposure (acreage, smoke) affects air quality, evacuation stress, and economic disruption
- **Geo Resolution**: State-level (aggregate from lat/lon points)
- **Update Frequency**: Daily (near real-time)
- **Source & License**: NASA FIRMS, public domain
- **API Endpoint**: `https://firms.modaps.eosdis.nasa.gov/api/country/`
- **Raw Fields**: `latitude`, `longitude`, `acq_date`, `acq_time`, `brightness`, `confidence`, `state` (derived)
- **Derived Features**:
  - `wildfire_acreage_proxy`: Fire pixel count × estimated acreage per pixel
  - `smoke_exposure_index`: Normalized fire density near population centers
  - `wildfire_stress_index`: Combined acreage + smoke exposure (0-1)
- **Sub-Index Impact**: `environmental_stress` (new child: `wildfire_stress`)
- **Expected Regional Variance**: **VERY HIGH** (CA, OR, WA: high; NE, IA: near-zero)
- **Observability Metrics**: `firms_fire_count{state}`, `wildfire_stress_index{state}`, `data_source_status{source="firms_wildfire",region}`
- **Failure Modes**:
  - API rate limits: Cache 6h, batch requests
  - Missing state mapping: Use lat/lon → state lookup table
  - Seasonal gaps: Document fire seasonality, use 0 during off-season
- **Ethical Review Notes**: ✅ Public satellite data, aggregated, no PII

### 1.3 — PUBLIC SAFETY & CIVIC STRESS (REGIONAL)

#### Dataset 7: NIBRS Crime Incident Density (State)
- **Dataset Name**: FBI NIBRS State-Level Aggregates
- **Behavioral Mechanism**: Crime rates correlate with community stress, safety perception, and social cohesion
- **Geo Resolution**: State-level (aggregated from agency-level NIBRS)
- **Update Frequency**: Quarterly (with 3-6 month lag)
- **Source & License**: FBI Crime Data Explorer (CDE), public domain
- **API Endpoint**: `https://api.usa.gov/crime/fbi/cde/`
- **Raw Fields**: `offense_type`, `state`, `year`, `quarter`, `incident_count`, `victim_count`
- **Derived Features**:
  - `crime_incident_rate`: Incidents per 100k population
  - `violent_crime_stress`: Violent crime rate (normalized 0-1)
  - `property_crime_stress`: Property crime rate (normalized 0-1)
- **Sub-Index Impact**: `crime_stress` (enhance existing with NIBRS data)
- **Expected Regional Variance**: **HIGH** (rates vary 2-3x across states)
- **Observability Metrics**: `nibrs_crime_rate{state,offense_type}`, `crime_stress_index{state}`, `data_source_status{source="nibrs",region}`
- **Failure Modes**:
  - Data lag: Use most recent available, document expected delay
  - Missing states: Use national average with `source_quality="fallback_national"`
  - API changes: Version detection, fallback to CSV bulk download
- **Ethical Review Notes**: ✅ Public aggregated crime statistics, no PII, state-level only

#### Dataset 8: OpenStates Legislative Churn (State)
- **Dataset Name**: OpenStates Bill Introduction & Passage Rates
- **Behavioral Mechanism**: High legislative activity (bills, votes) indicates political stress and policy volatility
- **Geo Resolution**: State-level (50 states)
- **Update Frequency**: Daily (real-time via OpenStates API)
- **Source & License**: OpenStates API, CC BY 4.0 (with attribution)
- **API Endpoint**: `https://v3.openstates.org/bills/` (requires API key, free tier available)
- **Raw Fields**: `bill_count`, `vote_count`, `state`, `session`, `date`
- **Derived Features**:
  - `legislative_activity_index`: Bills introduced per month (normalized)
  - `legislative_churn_rate`: Bills passed / bills introduced (volatility proxy)
  - `political_volatility_stress`: Combined activity + churn (0-1)
- **Sub-Index Impact**: `political_stress` (enhance existing OpenStates integration)
- **Expected Regional Variance**: **MEDIUM** (varies by state legislative calendar, 2-3x range)
- **Observability Metrics**: `openstates_bills{state}`, `legislative_churn_rate{state}`, `data_source_status{source="openstates_legislative",region}`
- **Failure Modes**:
  - API key required: Document free tier, fallback to cached data if key missing
  - Rate limits: Cache 1h, batch requests
  - Missing states: Use national average with `source_quality="fallback_national"`
- **Ethical Review Notes**: ✅ Public legislative data, CC BY 4.0, aggregated, no PII

### 1.4 — HEALTH SYSTEM PRESSURE (REGIONAL / NATIONAL MIX)

#### Dataset 9: HHS Hospital Bed Occupancy (State)
- **Dataset Name**: HHS Protect Hospital Capacity Data
- **Behavioral Mechanism**: Hospital strain indicates health system pressure, affects care access and community stress
- **Geo Resolution**: State-level (aggregated from facility-level)
- **Update Frequency**: Daily (near real-time)
- **Source & License**: HHS Protect Public Data Hub, public domain
- **API Endpoint**: `https://healthdata.gov/api/3/action/package_show?id=`
- **Raw Fields**: `inpatient_beds_used`, `inpatient_beds_total`, `state`, `date`
- **Derived Features**:
  - `hospital_occupancy_rate`: Used / total beds (0-1)
  - `hospital_strain_index`: Normalized occupancy above 80% threshold (0-1)
  - `health_system_pressure`: Combined occupancy + strain (0-1)
- **Sub-Index Impact**: `public_health_stress` (new child: `health_system_strain`)
- **Expected Regional Variance**: **MEDIUM-HIGH** (occupancy varies 50-95% across states)
- **Observability Metrics**: `hhs_hospital_occupancy{state}`, `hospital_strain_index{state}`, `data_source_status{source="hhs_hospital",region}`
- **Failure Modes**:
  - API changes: Version detection, fallback to CSV export
  - Missing states: Use national average with `source_quality="fallback_national"`
  - Data gaps: Forward-fill with last known value (max 7 days)
- **Ethical Review Notes**: ✅ Public health system data, aggregated, no PII, facility-level aggregated to state

#### Dataset 10: CDC WONDER Overdose Data (State)
- **Dataset Name**: CDC WONDER Provisional Drug Overdose Deaths
- **Behavioral Mechanism**: Overdose rates indicate substance use stress, mental health pressure, and community crisis
- **Geo Resolution**: State-level (50 states + DC)
- **Update Frequency**: Monthly (with 2-3 month lag for provisional data)
- **Source & License**: CDC WONDER, public domain
- **API Endpoint**: `https://wonder.cdc.gov/controller/datarequest/` (XML API)
- **Raw Fields**: `deaths`, `state`, `month`, `drug_type` (all drugs, opioids, stimulants)
- **Derived Features**:
  - `overdose_rate`: Deaths per 100k population (normalized)
  - `overdose_stress_index`: Normalized rate (0-1)
  - `substance_use_trend`: 3-month moving average change
- **Sub-Index Impact**: `public_health_stress` (new child: `substance_use_stress`)
- **Expected Regional Variance**: **HIGH** (rates vary 3-5x: 10-50 per 100k)
- **Observability Metrics**: `cdc_overdose_rate{state,drug_type}`, `overdose_stress_index{state}`, `data_source_status{source="cdc_wonder",region}`
- **Failure Modes**:
  - XML API complexity: Robust XML parsing, fallback to CSV export if available
  - Data lag: Document expected 2-3 month delay, use most recent available
  - Missing states: Use national average with `source_quality="fallback_national"`
- **Ethical Review Notes**: ✅ Public health statistics, aggregated, no PII, state-level only

### 1.5 — INFORMATION & MEDIA PRESSURE (REGIONALIZED WHERE POSSIBLE)

#### Dataset 11: GDELT Event Intensity by State (Enhanced)
- **Dataset Name**: GDELT Event Counts by State (Enhanced Regional Filtering)
- **Behavioral Mechanism**: Event density (protests, violence, disasters) by state indicates regional information pressure
- **Geo Resolution**: State-level (filter GDELT events by state)
- **Update Frequency**: Daily (real-time)
- **Source & License**: GDELT Project, CC BY 4.0
- **API Endpoint**: `https://api.gdeltproject.org/api/v2/doc/doc` (existing integration)
- **Raw Fields**: `event_count`, `state` (from location fields), `event_type`, `date`
- **Derived Features**:
  - `gdelt_event_density`: Events per day per state (normalized)
  - `gdelt_event_intensity_stress`: Combined density + severity (0-1)
  - `regional_media_pressure`: State-specific event volume (0-1)
- **Sub-Index Impact**: `digital_attention` (enhance existing with state-level filtering)
- **Expected Regional Variance**: **MEDIUM** (varies by state size and event frequency, 2-3x range)
- **Observability Metrics**: `gdelt_events_by_state{state,event_type}`, `regional_media_pressure{state}`, `data_source_status{source="gdelt_regional",region}`
- **Failure Modes**:
  - GDELT API rate limits: Cache 1h, batch requests
  - State filtering accuracy: Use location name matching + lat/lon bounding boxes
  - Missing states: Use national average with `source_quality="fallback_national"`
- **Ethical Review Notes**: ✅ Public event data, aggregated, no PII, state-level only

### 1.6 — INFRASTRUCTURE & SYSTEM STRAIN

#### Dataset 12: EIA Electricity Price Volatility by ISO/RTO
- **Dataset Name**: EIA Electricity Wholesale Prices by Regional Grid
- **Behavioral Mechanism**: Electricity price volatility indicates grid stress, affects economic activity and household stress
- **Geo Resolution**: ISO/RTO region (e.g., CAISO, ERCOT, PJM) → map to states
- **Update Frequency**: Daily (real-time)
- **Source & License**: EIA API v2, public domain
- **API Endpoint**: `https://api.eia.gov/v2/electricity/rto/`
- **Raw Fields**: `price`, `iso_region`, `date`, `hour` (can aggregate to daily)
- **Derived Features**:
  - `electricity_price_volatility`: Rolling 7-day coefficient of variation
  - `grid_stress_index`: Normalized price spikes above baseline (0-1)
  - `energy_cost_stress`: Combined volatility + absolute price (0-1)
- **Sub-Index Impact**: `economic_stress` (new child: `energy_cost_stress`)
- **Expected Regional Variance**: **HIGH** (ISO regions vary dramatically: CA vs TX vs NE)
- **Observability Metrics**: `eia_electricity_price{iso_region}`, `grid_stress_index{region}`, `data_source_status{source="eia_electricity",region}`
- **Failure Modes**:
  - ISO region → state mapping: Use lookup table, handle multi-state ISOs
  - API rate limits: Cache 6h, batch requests
  - Missing regions: Use national average with `source_quality="fallback_national"`
- **Ethical Review Notes**: ✅ Public energy data, aggregated, no PII

#### Dataset 13: Power Outage Reports (State)
- **Dataset Name**: DOE Power Outage Incident Reports
- **Behavioral Mechanism**: Power outages indicate infrastructure strain, affect daily life and economic activity
- **Geo Resolution**: State-level (aggregated from utility-level)
- **Update Frequency**: Daily (near real-time)
- **Source & License**: DOE EIA, public domain
- **API Endpoint**: `https://www.eia.gov/electricity/gridmonitor/dashboard/electric_overview/` (scrape or API if available)
- **Raw Fields**: `outage_customers`, `outage_duration_hours`, `state`, `date`
- **Derived Features**:
  - `outage_frequency`: Outages per month (normalized)
  - `outage_severity_index`: Customer-hours lost (normalized 0-1)
  - `infrastructure_strain_stress`: Combined frequency + severity (0-1)
- **Sub-Index Impact**: `environmental_stress` (new child: `infrastructure_strain_stress`)
- **Expected Regional Variance**: **MEDIUM** (varies by state infrastructure quality, weather)
- **Observability Metrics**: `power_outage_customers{state}`, `outage_severity_index{state}`, `data_source_status{source="power_outages",region}`
- **Failure Modes**:
  - Scraping required: Robust HTML parsing, fallback to cached data
  - Missing states: Use national average with `source_quality="fallback_national"`
  - Data gaps: Forward-fill with 0 (assume no outages if missing)
- **Ethical Review Notes**: ✅ Public infrastructure data, aggregated, no PII

### 1.7 — SOCIAL & COMMUNITY SIGNALS

#### Dataset 14: Civic Participation Proxies (State)
- **Dataset Name**: Voter Turnout & Civic Engagement Indicators
- **Behavioral Mechanism**: Low civic participation indicates social disengagement and community stress
- **Geo Resolution**: State-level (50 states)
- **Update Frequency**: Annual (election years) + quarterly (other indicators)
- **Source & License**: Various (US Census, state election offices), public domain
- **API Endpoint**: Multiple sources (Census API, state APIs)
- **Raw Fields**: `voter_turnout_rate`, `state`, `election_year`, `civic_engagement_score`
- **Derived Features**:
  - `civic_participation_index`: Normalized voter turnout (0-1, inverse stress)
  - `social_engagement_stress`: 1 - participation_index (stress proxy)
  - `community_cohesion_proxy`: Combined participation + engagement (0-1)
- **Sub-Index Impact**: `social_cohesion_stress` (enhance existing)
- **Expected Regional Variance**: **MEDIUM** (turnout varies 50-80% across states)
- **Observability Metrics**: `voter_turnout{state}`, `civic_participation_index{state}`, `data_source_status{source="civic_participation",region}`
- **Failure Modes**:
  - Multiple sources: Aggregate with fallback priority
  - Annual data: Use last known value until next election
  - Missing states: Use national average with `source_quality="fallback_national"`
- **Ethical Review Notes**: ✅ Public election data, aggregated, no PII

#### Dataset 15: Community Survey Indices (State)
- **Dataset Name**: State-Level Community Survey Aggregates (where available)
- **Behavioral Mechanism**: Survey-based trust, safety, and satisfaction indicators measure community cohesion
- **Geo Resolution**: State-level (limited availability)
- **Update Frequency**: Annual or biennial (varies by source)
- **Source & License**: Various (Gallup, Pew, state surveys), check licensing
- **API Endpoint**: Varies by source (may require manual data entry or CSV import)
- **Raw Fields**: `trust_index`, `safety_perception`, `satisfaction_score`, `state`, `year`
- **Derived Features**:
  - `community_trust_index`: Normalized trust score (0-1, inverse stress)
  - `social_cohesion_stress`: 1 - trust_index (stress proxy)
- **Sub-Index Impact**: `social_cohesion_stress` (enhance existing)
- **Expected Regional Variance**: **MEDIUM** (varies by state, 2-3x range)
- **Observability Metrics**: `community_trust_index{state}`, `social_cohesion_stress{state}`, `data_source_status{source="community_survey",region}`
- **Failure Modes**:
  - Limited availability: Mark as "optional", use only where available
  - Licensing issues: Verify CC/public domain, skip if unclear
  - Data gaps: Use national average with `source_quality="fallback_national"`
- **Ethical Review Notes**: ⚠️ Verify licensing per source, ensure aggregated, no PII

---

## SECTION 2: Dataset Ranking & Top 5 MVP Selection

### Ranking Criteria

| Dataset | ROI (1-10) | Regionality (1-10) | Complexity (1-10) | Forecast Impact | Risk | **Total Score** |
|---------|------------|-------------------|-------------------|-----------------|------|----------------|
| **1. EIA Gasoline by State** | 9 | 10 | 4 | High (economic micro-signal) | Low | **23** |
| **2. U.S. Drought Monitor** | 8 | 10 | 5 | High (environmental shock) | Low | **23** |
| **3. NOAA Storm Events** | 9 | 10 | 6 | Very High (multi-event types) | Medium | **25** |
| **4. Eviction Lab** | 8 | 10 | 5 | High (housing stress) | Low | **23** |
| **5. CDC WONDER Overdose** | 8 | 9 | 7 | High (health pressure) | Low | **24** |
| 6. HHS Hospital Occupancy | 7 | 8 | 6 | Medium-High | Low | **21** |
| 7. NASA FIRMS Wildfire | 7 | 10 | 5 | Medium-High | Low | **22** |
| 8. FDIC Bank Closures | 6 | 8 | 6 | Medium | Low | **20** |
| 9. EIA Electricity Volatility | 7 | 9 | 7 | Medium-High | Medium | **23** |
| 10. NIBRS Crime | 6 | 9 | 7 | Medium (enhance existing) | Low | **22** |
| 11. OpenStates Legislative | 5 | 7 | 4 | Medium (enhance existing) | Low | **16** |
| 12. GDELT Regional | 5 | 7 | 4 | Medium (enhance existing) | Low | **16** |
| 13. Power Outages | 6 | 7 | 8 | Medium | Medium | **21** |
| 14. Civic Participation | 5 | 6 | 7 | Low-Medium | Low | **18** |
| 15. Community Surveys | 4 | 6 | 8 | Low-Medium | Medium | **18** |

**Note**: Lower complexity score = easier to implement. Total Score = ROI + Regionality - Complexity (higher is better).

### Top 5 MVP Datasets (Selected for Immediate Implementation)

1. **EIA Gasoline Prices by State** (Score: 23)
   - **Priority**: P0 (highest ROI + regionality, low complexity)
   - **Rationale**: Direct economic micro-signal, high state-level variance, well-documented API

2. **U.S. Drought Monitor (State)** (Score: 23)
   - **Priority**: P0 (high regionality, environmental shock)
   - **Rationale**: Strong environmental signal, very high variance, weekly updates

3. **NOAA Storm Events (State)** (Score: 25)
   - **Priority**: P0 (highest total score, multi-event types)
   - **Rationale**: Multiple sub-indices (heatwave, flood, storm severity), very high variance

4. **Eviction Lab (State/City)** (Score: 23)
   - **Priority**: P1 (high value, limited geography)
   - **Rationale**: Strong housing stress signal, very high variance, but limited to ~30 states

5. **CDC WONDER Overdose Data (State)** (Score: 24)
   - **Priority**: P1 (high health pressure signal)
   - **Rationale**: Important health system pressure indicator, high variance, but XML API complexity

---

## SECTION 3: MVP Dataset Integration Blueprints (Top 5)

### MVP 1: EIA Gasoline Prices by State

#### 1) Connector Name
- **File**: `app/services/ingestion/eia_fuel_prices.py`
- **Class**: `EIAFuelPricesFetcher`

#### 2) Fetch Strategy
- **Method**: Polling (weekly, Monday releases)
- **Schedule**: Daily check, cache 24h
- **API**: EIA API v2 (`/v2/petroleum/pri/gnd/data/`)

#### 3) Geo Mapping Strategy
- **Input**: `state` (2-letter code) or `region_name` → map to state
- **Cache Key**: `eia_fuel_{state}_{product}_{days_back}`
- **Region Label**: Use `state` for Prometheus metrics

#### 4) Schema (Raw → Normalized)
```python
# Raw API Response
{
    "response": {
        "data": [
            {
                "period": "2026-01-15",
                "price": 3.45,
                "state": "CA",
                "product": "regular"
            }
        ]
    }
}

# Normalized DataFrame
columns = ["timestamp", "fuel_stress_index", "fuel_price", "product"]
```

#### 5) Cache Key Design
```python
cache_key = f"eia_fuel_{state}_{product}_{days_back}"
# Must include state for regional caching
```

#### 6) Feature Engineering Steps
```python
# 1. Fetch raw prices by state/product
# 2. Compute national average
# 3. Calculate deviation: (state_price - national_avg) / national_avg
# 4. Normalize to 0-1: fuel_stress_index = sigmoid(deviation * 2)
# 5. Aggregate products (regular, midgrade, premium) → weighted average
```

#### 7) Forecast Pipeline Integration
- **Sub-Index**: `economic_stress` → new child `fuel_stress`
- **Weight**: 0.15 (moderate weight, economic micro-signal)
- **Harmonization**: Merge with existing economic_stress components

#### 8) Prometheus Metrics
```python
# Emit:
eia_fuel_price{state="CA",product="regular"} 3.45
eia_fuel_stress_index{state="CA"} 0.65
data_source_status{source="eia_fuel",region="us_ca"} 1
```

#### 9) Grafana Panels to Add
- **Panel**: "Fuel Stress by State" (heatmap or bar chart)
- **Panel**: "Fuel Price Deviation from National Average" (time series)
- **Label**: Tag as **REGIONAL** (must vary by state)

#### 10) Tests Required
```python
# tests/test_eia_fuel_prices.py
def test_eia_fuel_regional_variance():
    """Assert Illinois vs Arizona produce different fuel_stress_index values."""
    il_data = fetcher.fetch_fuel_stress(state="IL", days_back=30)
    az_data = fetcher.fetch_fuel_stress(state="AZ", days_back=30)
    assert il_data["fuel_stress_index"].mean() != az_data["fuel_stress_index"].mean()

def test_eia_fuel_cache_key_includes_state():
    """Assert cache key includes state parameter."""
    # Verify cache_key contains state

def test_eia_fuel_ci_offline_mode():
    """Test CI offline mode returns deterministic data."""
    # Verify synthetic data for testing
```

#### 11) Expected Regional Variance Proof
- **Test**: Generate forecasts for CA, TX, NY, FL, IL, AZ
- **Assert**: `fuel_stress_index` values differ (std dev > 0.1)
- **Variance Probe**: Must pass (no alerts for REGIONAL classification)

---

### MVP 2: U.S. Drought Monitor (State)

#### 1) Connector Name
- **File**: `app/services/ingestion/drought_monitor.py`
- **Class**: `DroughtMonitorFetcher`

#### 2) Fetch Strategy
- **Method**: Polling (weekly, Thursday releases)
- **Schedule**: Daily check, cache 7 days (weekly data)
- **API**: NDMC CSV export (`/DmData/DataTables.aspx`)

#### 3) Geo Mapping Strategy
- **Input**: `state` (full name or 2-letter code)
- **Cache Key**: `drought_monitor_{state}_{days_back}`
- **Region Label**: Use `state` for Prometheus metrics

#### 4) Schema (Raw → Normalized)
```python
# Raw CSV
State,Week_Ending,DSCI
California,2026-01-18,450
Texas,2026-01-18,120

# Normalized DataFrame
columns = ["timestamp", "drought_stress_index", "dsci"]
```

#### 5) Cache Key Design
```python
cache_key = f"drought_monitor_{state}_{days_back}"
# Must include state for regional caching
```

#### 6) Feature Engineering Steps
```python
# 1. Fetch DSCI (0-500) by state/week
# 2. Normalize to 0-1: drought_stress_index = DSCI / 500
# 3. Compute persistence: weeks in current severity category
# 4. Compute shock: week-over-week DSCI change
```

#### 7) Forecast Pipeline Integration
- **Sub-Index**: `environmental_stress` → new child `drought_stress`
- **Weight**: 0.20 (significant environmental signal)
- **Harmonization**: Merge with weather, air quality, NWS alerts

#### 8) Prometheus Metrics
```python
# Emit:
drought_dsci{state="CA"} 450
drought_stress_index{state="CA"} 0.90
data_source_status{source="drought_monitor",region="us_ca"} 1
```

#### 9) Grafana Panels to Add
- **Panel**: "Drought Stress by State" (heatmap, color by DSCI)
- **Panel**: "Drought Persistence" (weeks in current category)
- **Label**: Tag as **REGIONAL** (must vary by state)

#### 10) Tests Required
```python
# tests/test_drought_monitor.py
def test_drought_regional_variance():
    """Assert California vs Texas produce different drought_stress_index values."""
    ca_data = fetcher.fetch_drought_stress(state="CA", days_back=90)
    tx_data = fetcher.fetch_drought_stress(state="TX", days_back=90)
    assert ca_data["drought_stress_index"].mean() != tx_data["drought_stress_index"].mean()
```

#### 11) Expected Regional Variance Proof
- **Test**: Generate forecasts for CA (high drought), TX (variable), FL (low)
- **Assert**: `drought_stress_index` values differ dramatically (std dev > 0.3)
- **Variance Probe**: Must pass (no alerts for REGIONAL classification)

---

### MVP 3: NOAA Storm Events (State)

#### 1) Connector Name
- **File**: `app/services/ingestion/noaa_storm_events.py`
- **Class**: `NOAAStormEventsFetcher`

#### 2) Fetch Strategy
- **Method**: Bulk CSV download (monthly)
- **Schedule**: Weekly check, cache 30 days
- **API**: NOAA NCEI bulk CSV (`/stormevents/ftp.jsp`)

#### 3) Geo Mapping Strategy
- **Input**: `state` (full name) + optional `county`
- **Cache Key**: `noaa_storms_{state}_{event_type}_{days_back}`
- **Region Label**: Use `state` for Prometheus metrics

#### 4) Schema (Raw → Normalized)
```python
# Raw CSV columns
EVENT_TYPE, BEGIN_DATE, STATE, COUNTY, DEATHS_DIRECT, INJURIES_DIRECT, DAMAGE_PROPERTY

# Normalized DataFrame
columns = ["timestamp", "heatwave_stress", "flood_risk_stress", "storm_severity_stress", "event_type"]
```

#### 5) Cache Key Design
```python
cache_key = f"noaa_storms_{state}_{event_type}_{days_back}"
# Must include state for regional caching
```

#### 6) Feature Engineering Steps
```python
# 1. Filter events by type: heat wave, flood, tornado, hail, etc.
# 2. Aggregate by month/state: event_count, total_deaths, total_injuries, total_damage
# 3. Compute heatwave_stress: heat_wave_days / days_in_month (normalized)
# 4. Compute flood_risk_stress: flood_events / days_in_month (normalized)
# 5. Compute storm_severity_stress: weighted sum (deaths×10 + injuries×1 + log(damage)) (normalized)
```

#### 7) Forecast Pipeline Integration
- **Sub-Index**: `environmental_stress` → new children:
  - `heatwave_stress` (weight: 0.10)
  - `flood_risk_stress` (weight: 0.10)
  - `storm_severity_stress` (weight: 0.15)
- **Harmonization**: Merge with weather, drought, NWS alerts

#### 8) Prometheus Metrics
```python
# Emit:
noaa_storm_events{state="FL",event_type="hurricane"} 3
heatwave_stress_index{state="AZ"} 0.85
flood_risk_stress_index{state="LA"} 0.60
storm_severity_stress_index{state="TX"} 0.45
data_source_status{source="noaa_storms",region="us_fl"} 1
```

#### 9) Grafana Panels to Add
- **Panel**: "Storm Events by State/Type" (stacked bar chart)
- **Panel**: "Heatwave Stress by State" (heatmap)
- **Panel**: "Flood Risk by State" (heatmap)
- **Label**: Tag as **REGIONAL** (must vary by state)

#### 10) Tests Required
```python
# tests/test_noaa_storm_events.py
def test_noaa_storms_regional_variance():
    """Assert Florida vs Arizona produce different storm stress values."""
    fl_data = fetcher.fetch_storm_stress(state="FL", days_back=90)
    az_data = fetcher.fetch_storm_stress(state="AZ", days_back=90)
    # FL should have higher flood_risk, AZ should have higher heatwave_stress
    assert fl_data["flood_risk_stress"].mean() > az_data["flood_risk_stress"].mean()
    assert az_data["heatwave_stress"].mean() > fl_data["heatwave_stress"].mean()
```

#### 11) Expected Regional Variance Proof
- **Test**: Generate forecasts for FL (hurricanes), AZ (heat waves), TX (tornadoes)
- **Assert**: Event types and stress indices differ dramatically
- **Variance Probe**: Must pass (no alerts for REGIONAL classification)

---

### MVP 4: Eviction Lab (State/City)

#### 1) Connector Name
- **File**: `app/services/ingestion/eviction_lab.py`
- **Class**: `EvictionLabFetcher`

#### 2) Fetch Strategy
- **Method**: S3 CSV download (monthly)
- **Schedule**: Weekly check, cache 30 days
- **API**: Eviction Lab S3 bucket (`eviction-lab-data-downloads.s3.amazonaws.com`)

#### 3) Geo Mapping Strategy
- **Input**: `state` (full name) + optional `city`
- **Cache Key**: `eviction_lab_{state}_{city or 'state'}_{days_back}`
- **Region Label**: Use `state` or `city` for Prometheus metrics

#### 4) Schema (Raw → Normalized)
```python
# Raw CSV columns
GEOID, name, year, month, filings, eviction-rate

# Normalized DataFrame
columns = ["timestamp", "eviction_stress_index", "eviction_rate", "filings"]
```

#### 5) Cache Key Design
```python
cache_key = f"eviction_lab_{state}_{city or 'state'}_{days_back}"
# Must include state/city for regional caching
```

#### 6) Feature Engineering Steps
```python
# 1. Fetch eviction filings and rates by state/city/month
# 2. Normalize eviction_rate to 0-1: eviction_stress_index = min(eviction_rate / 0.05, 1.0)
# 3. Compute trend: 3-month moving average change
# 4. Compute burden: filings per 1000 renter households
```

#### 7) Forecast Pipeline Integration
- **Sub-Index**: `economic_stress` → new child `housing_stress`
- **Weight**: 0.20 (significant economic/housing signal)
- **Harmonization**: Merge with economic_stress components

#### 8) Prometheus Metrics
```python
# Emit:
eviction_filings{state="CA",city="Los Angeles"} 1250
eviction_stress_index{state="CA"} 0.75
data_source_status{source="eviction_lab",region="us_ca"} 1
```

#### 9) Grafana Panels to Add
- **Panel**: "Eviction Stress by State" (bar chart, sorted by stress)
- **Panel**: "Eviction Trend" (time series, state comparison)
- **Label**: Tag as **REGIONAL** (must vary by state/city)
- **Note**: Display "Limited Geography" warning for states not covered

#### 10) Tests Required
```python
# tests/test_eviction_lab.py
def test_eviction_regional_variance():
    """Assert high-eviction state vs low-eviction state produce different values."""
    # Use states known to have data (e.g., CA, TX, NY)
    ca_data = fetcher.fetch_eviction_stress(state="CA", days_back=90)
    wy_data = fetcher.fetch_eviction_stress(state="WY", days_back=90)
    # If WY not available, use fallback; if CA available, assert difference
    if not ca_data.empty and not wy_data.empty:
        assert ca_data["eviction_stress_index"].mean() != wy_data["eviction_stress_index"].mean()
```

#### 11) Expected Regional Variance Proof
- **Test**: Generate forecasts for CA (high eviction), TX (medium), WY (low or not available)
- **Assert**: `eviction_stress_index` values differ (std dev > 0.2) where data available
- **Variance Probe**: Must pass (no alerts for REGIONAL classification, handle "not_available" gracefully)

---

### MVP 5: CDC WONDER Overdose Data (State)

#### 1) Connector Name
- **File**: `app/services/ingestion/cdc_wonder_overdose.py`
- **Class**: `CDCWonderOverdoseFetcher`

#### 2) Fetch Strategy
- **Method**: XML API (monthly)
- **Schedule**: Weekly check, cache 30 days
- **API**: CDC WONDER XML API (`/controller/datarequest/`)

#### 3) Geo Mapping Strategy
- **Input**: `state` (full name or FIPS code)
- **Cache Key**: `cdc_wonder_overdose_{state}_{drug_type}_{days_back}`
- **Region Label**: Use `state` for Prometheus metrics

#### 4) Schema (Raw → Normalized)
```python
# Raw XML Response
<data>
    <row>
        <state>California</state>
        <month>2026-01</month>
        <deaths>450</deaths>
        <drug_type>All Drugs</drug_type>
    </row>
</data>

# Normalized DataFrame
columns = ["timestamp", "overdose_stress_index", "overdose_rate", "deaths", "drug_type"]
```

#### 5) Cache Key Design
```python
cache_key = f"cdc_wonder_overdose_{state}_{drug_type}_{days_back}"
# Must include state for regional caching
```

#### 6) Feature Engineering Steps
```python
# 1. Fetch overdose deaths by state/month/drug_type
# 2. Compute rate: deaths / population × 100000
# 3. Normalize to 0-1: overdose_stress_index = min(rate / 50, 1.0)
# 4. Compute trend: 3-month moving average change
```

#### 7) Forecast Pipeline Integration
- **Sub-Index**: `public_health_stress` → new child `substance_use_stress`
- **Weight**: 0.15 (significant health pressure signal)
- **Harmonization**: Merge with public_health_stress components

#### 8) Prometheus Metrics
```python
# Emit:
cdc_overdose_rate{state="CA",drug_type="All Drugs"} 12.5
overdose_stress_index{state="CA"} 0.25
data_source_status{source="cdc_wonder",region="us_ca"} 1
```

#### 9) Grafana Panels to Add
- **Panel**: "Overdose Stress by State" (bar chart, sorted by stress)
- **Panel**: "Overdose Trend" (time series, state comparison)
- **Label**: Tag as **REGIONAL** (must vary by state)
- **Note**: Display "Provisional Data" warning (2-3 month lag)

#### 10) Tests Required
```python
# tests/test_cdc_wonder_overdose.py
def test_cdc_overdose_regional_variance():
    """Assert high-overdose state vs low-overdose state produce different values."""
    wv_data = fetcher.fetch_overdose_stress(state="WV", days_back=90)
    hi_data = fetcher.fetch_overdose_stress(state="HI", days_back=90)
    assert wv_data["overdose_stress_index"].mean() != hi_data["overdose_stress_index"].mean()
```

#### 11) Expected Regional Variance Proof
- **Test**: Generate forecasts for WV (high overdose), HI (low), CA (medium)
- **Assert**: `overdose_stress_index` values differ (std dev > 0.2)
- **Variance Probe**: Must pass (no alerts for REGIONAL classification)

---

## SECTION 4: Regionality Safety Net Integration

### 4.1 — Variance Probe Integration

For each MVP dataset, add to `scripts/variance_probe.py`:

```python
# In classify_source()
regional_sources = [
    # ... existing ...
    "fuel_stress",           # EIA Gasoline
    "drought_stress",        # Drought Monitor
    "heatwave_stress",       # NOAA Storms
    "flood_risk_stress",     # NOAA Storms
    "storm_severity_stress", # NOAA Storms
    "housing_stress",        # Eviction Lab
    "substance_use_stress",  # CDC WONDER
]
```

### 4.2 — Source Regionality Manifest

Update `/tmp/source_regionality_manifest.json` (or proof-dir equivalent):

```json
{
  "sources": [
    {
      "source_id": "eia_fuel_prices",
      "class": "REGIONAL",
      "geo_inputs_used": ["state"],
      "cache_key_fields": ["state", "product", "days_back"],
      "expected_variance": true,
      "failure_mode": "fallback_to_national",
      "notes": "State-level fuel prices vary 20-40% from national average"
    },
    // ... repeat for each MVP dataset
  ]
}
```

### 4.3 — Regression Tests

For each MVP dataset, add to `tests/test_regionality.py`:

```python
def test_eia_fuel_regional_variance():
    """Assert two distant regions produce different fuel_stress_index values."""
    il_data = eia_fetcher.fetch_fuel_stress(state="IL", days_back=30)
    az_data = eia_fetcher.fetch_fuel_stress(state="AZ", days_back=30)
    assert il_data["fuel_stress_index"].mean() != az_data["fuel_stress_index"].mean()
    assert il_data["fuel_stress_index"].std() > 0.05  # Minimum variance threshold
```

### 4.4 — Prometheus Invariant Checks

Add to `scripts/discrepancy_harness.py` or create `scripts/prometheus_invariants.py`:

```python
def check_prometheus_invariants():
    """Check Prometheus metrics for regionality invariants."""
    metrics = fetch_prometheus_metrics()
    
    # Check 1: No region="None"
    assert not any('region="None"' in m for m in metrics), "Found region=None labels"
    
    # Check 2: Multi-region series exist
    behavior_index_regions = extract_regions(metrics, "behavior_index")
    assert len(behavior_index_regions) > 10, f"Only {len(behavior_index_regions)} regions for behavior_index"
    
    # Check 3: New REGIONAL sources have region labels
    for source in ["eia_fuel", "drought_monitor", "noaa_storms", "eviction_lab", "cdc_wonder"]:
        source_regions = extract_regions(metrics, f"{source}_stress_index")
        assert len(source_regions) > 5, f"{source} has insufficient regional coverage"
```

---

## SECTION 5: Dashboard & UX Requirements

### 5.1 — Visual Indicators

For every new dataset:
- **GLOBAL vs REGIONAL tags**: Add explicit labels in Grafana panels
- **Contribution breakdown**: Show how each source affects Behavior Index (auditable back to source-level)
- **Time-range sensitivity**: Explain data lag, “as of” dates (e.g., “Provisional data, 2–3 month lag”)
- **Source health**: Visualize `data_source_status{source,region}` in a dedicated “Source health” panel

**No silent behavior.** Everything must be explainable.

### 5.2 — Grafana Dashboard Updates

Add panels to existing dashboards:

1. **"Regional Variance Summary" Panel** (new dashboard or add to existing):
   - For each REGIONAL sub-index: min/max/avg across all regions
   - Color-code by variance level (high/medium/low)

2. **"Source Health by Region" Panel**:
   - Grid showing `data_source_status{source,region}` (green/yellow/red)
   - Filter by source or region

3. **"New Dataset Contributions" Panel**:
   - Show contribution of Top 5 MVP datasets to Behavior Index
   - Time series of contribution over time

4. **Forecast Explainability dashboard** (see Section 10.2, Option C):
   - Contributor breakdown: each sub-index → behavior_index delta
   - Source-level attribution: which dataset drove the change
   - Time-range sensitivity and “as of” dates

### 5.3 — Documentation Updates

Update `docs/GLOBAL_VS_REGIONAL_INDICES.md`:

```markdown
## New Regional Indices (Enterprise Expansion)

### fuel_stress (economic_stress child)
- **Source**: EIA Gasoline Prices by State
- **Scope**: REGIONAL (must vary by state)
- **Expected Behavior**: **MUST vary** (state prices vary 20-40%)

### drought_stress (environmental_stress child)
- **Source**: U.S. Drought Monitor State DSCI
- **Scope**: REGIONAL (must vary by state)
- **Expected Behavior**: **MUST vary** (DSCI ranges 0-500, high variance)

// ... repeat for each MVP dataset
```

---

## SECTION 6: Documentation Requirements

### 6.1 — Update `docs/DATA_SOURCES.md`

Add entries for each MVP dataset following existing format:
- Source & License
- API Endpoint
- Category
- Requires Key
- Data Provided
- Update Frequency
- Connector
- Status
- Notes (including failure modes, data lag, limited geography)

### 6.2 — Update `docs/NEW_DATA_SOURCES_PLAN.md`

Add section:
```markdown
## Enterprise Dataset Expansion (Top 5 MVP)

See **`docs/ENTERPRISE_DATASET_EXPANSION_PLAN.md`** for the full Enterprise Dataset Expansion + Regional Signal Hardening plan.

**Top 5 MVP datasets** for immediate implementation:

1. **EIA Gasoline by State** — Economic micro-signal; high regional variance.
2. **U.S. Drought Monitor (State)** — Environmental; DSCI by state.
3. **NOAA Storm Events (State)** — Severe weather by state/county; bulk CSV.
4. **Eviction Lab (State/City)** — Housing stress; S3/CSV; limited geography.
5. **CDC WONDER Overdose (State)** — Health pressure; XML API; provisional.

Each must: use geo in fetch + cache key, emit region-labeled metrics, pass `variance_probe`, have regression tests and docs.
```

### 6.3 — Update `docs/VERIFY_INTEGRITY.md`

Add section:
```markdown
## Dataset Expansion & Regionality Checks

When adding new data sources per `docs/ENTERPRISE_DATASET_EXPANSION_PLAN.md`:

1. **variance_probe**: Add each new REGIONAL source to `scripts/variance_probe.py` classification; run probe and ensure no alerts (REGIONAL sources must show variance).
2. **source_regionality_manifest**: Update `/tmp/source_regionality_manifest.json` (or proof-dir equivalent) with `source_id`, `class`, `geo_inputs_used`, `cache_key_fields`, `expected_variance`, `failure_mode`.
3. **Regression tests**: For each REGIONAL source, add a test that two distant regions (e.g. Illinois vs Arizona) produce different values for that source.
4. **Prometheus invariants**: No `region="None"`; multi-region series for `behavior_index` and key sub-indices; `data_source_status{source,region}` where applicable.

See Section 5 of the Enterprise Plan for the full safety net.
```

---

## SECTION 7: Implementation Order & Task Checklist

### Phase 1: MVP 1 — EIA Gasoline Prices (Week 1)
- [ ] Create `app/services/ingestion/eia_fuel_prices.py`
- [ ] Implement fetch with state parameter
- [ ] Add cache key with state
- [ ] Feature engineering (fuel_stress_index)
- [ ] Integrate into forecast pipeline (economic_stress child)
- [ ] Add Prometheus metrics
- [ ] Add Grafana panels
- [ ] Add tests (regional variance, cache key, CI offline)
- [ ] Update source_registry
- [ ] Update variance_probe classification
- [ ] Update documentation

### Phase 2: MVP 2 — Drought Monitor (Week 1-2)
- [ ] Create `app/services/ingestion/drought_monitor.py`
- [ ] Implement CSV fetch with state parameter
- [ ] Add cache key with state
- [ ] Feature engineering (drought_stress_index)
- [ ] Integrate into forecast pipeline (environmental_stress child)
- [ ] Add Prometheus metrics
- [ ] Add Grafana panels
- [ ] Add tests
- [ ] Update source_registry
- [ ] Update variance_probe classification
- [ ] Update documentation

### Phase 3: MVP 3 — NOAA Storm Events (Week 2-3)
- [ ] Create `app/services/ingestion/noaa_storm_events.py`
- [ ] Implement bulk CSV download + parsing
- [ ] Add cache key with state
- [ ] Feature engineering (heatwave_stress, flood_risk_stress, storm_severity_stress)
- [ ] Integrate into forecast pipeline (environmental_stress children)
- [ ] Add Prometheus metrics
- [ ] Add Grafana panels
- [ ] Add tests
- [ ] Update source_registry
- [ ] Update variance_probe classification
- [ ] Update documentation

### Phase 4: MVP 4 — Eviction Lab (Week 3)
- [ ] Create `app/services/ingestion/eviction_lab.py`
- [ ] Implement S3 CSV download
- [ ] Add cache key with state/city
- [ ] Feature engineering (eviction_stress_index)
- [ ] Integrate into forecast pipeline (economic_stress child)
- [ ] Add Prometheus metrics
- [ ] Add Grafana panels (with "Limited Geography" note)
- [ ] Add tests (handle missing states gracefully)
- [ ] Update source_registry
- [ ] Update variance_probe classification
- [ ] Update documentation

### Phase 5: MVP 5 — CDC WONDER Overdose (Week 3-4)
- [ ] Create `app/services/ingestion/cdc_wonder_overdose.py`
- [ ] Implement XML API fetch
- [ ] Add cache key with state
- [ ] Feature engineering (overdose_stress_index)
- [ ] Integrate into forecast pipeline (public_health_stress child)
- [ ] Add Prometheus metrics
- [ ] Add Grafana panels (with "Provisional Data" note)
- [ ] Add tests
- [ ] Update source_registry
- [ ] Update variance_probe classification
- [ ] Update documentation

### Phase 6: Safety Net & Validation (Week 4)
- [ ] Run full discrepancy investigation with new datasets
- [ ] Verify variance_probe passes for all MVP datasets
- [ ] Verify Prometheus invariants (no region="None", multi-region series)
- [ ] Verify regression tests pass
- [ ] Update source_regionality_manifest
- [ ] Generate evidence bundle

---

## SECTION 8: Risk & Ethics Review Summary

### Risk Assessment

| Dataset | Risk Level | Mitigation |
|---------|-----------|------------|
| EIA Gasoline | **Low** | Public API, well-documented, state-level only |
| Drought Monitor | **Low** | Public CSV, state-level only, no PII |
| NOAA Storms | **Low** | Public bulk data, state/county aggregated, no PII |
| Eviction Lab | **Low** | CC BY 4.0, aggregated, limited geography (documented) |
| CDC WONDER | **Low** | Public health statistics, state-level only, no PII |

### Ethics Review

All MVP datasets pass ethical standards:
- ✅ Public or openly licensed
- ✅ Aggregated (no PII)
- ✅ State-level or higher (no individual-level data)
- ✅ Clear data licensing
- ✅ No scraping behind auth walls
- ✅ No social media APIs
- ✅ No private/paid APIs (except free-tier OpenStates, documented)

### Failure Mode Handling

Each dataset has documented failure modes:
- **API rate limits**: Caching + fallback to last known value
- **Data lag**: Documented expected delays (e.g., CDC WONDER 2-3 months)
- **Limited geography**: Mark regions as "not_available", use state-level proxy
- **API changes**: Version detection, fallback to CSV/bulk download
- **Missing data**: Forward-fill with last known value (max 7-30 days depending on update frequency)

---

## SECTION 9: Expected Impact on Forecast Variance

### Current State
- **Regional variance**: Moderate (some indices are global/national)
- **Regional sub-indices**: 5-6 REGIONAL sources
- **Variance probe**: Passes, but some REGIONAL sources show limited variance

### After Top 5 MVP Implementation
- **Regional variance**: **Significantly increased**
- **Regional sub-indices**: 10-11 REGIONAL sources (5 new + existing)
- **Expected improvement**:
  - `economic_stress`: +2 REGIONAL children (fuel_stress, housing_stress)
  - `environmental_stress`: +4 REGIONAL children (drought_stress, heatwave_stress, flood_risk_stress, storm_severity_stress)
  - `public_health_stress`: +1 REGIONAL child (substance_use_stress)
- **Variance probe**: All REGIONAL sources must show variance (no alerts)

### Success Metrics
- **Two distant regions** (Illinois vs Arizona) show divergence in ≥3 independent sub-indices within 30 days ✅
- **Dashboards** clearly distinguish global vs regional signals ✅
- **Forecasts** are auditable back to source-level contributors ✅

---

## SECTION 10: Next Steps

### 10.1 — Immediate Implementation Order

1. **Review & Approve**: Review this plan, approve Top 5 MVP selection
2. **Phase 1 Implementation**: Start with EIA Gasoline Prices (highest ROI, lowest complexity)
3. **Iterative Integration**: Implement one MVP dataset at a time, validate before moving to next
4. **Safety Net Validation**: After each dataset, run discrepancy investigation + variance probe
5. **Documentation**: Update docs as each dataset is integrated
6. **Future Expansion**: After Top 5 MVP, consider remaining 10 datasets based on ROI/complexity

### 10.2 — Enhanced Options (Choose Your Path)

| Option | Description | Concrete next actions |
|--------|-------------|------------------------|
| **A. Real datasets + rankings** | Fill plan with researched datasets and scores | ✅ **Done** — 15 datasets, Top 5 MVP, ROI/regionality/complexity rankings in Section 2 |
| **B. Cursor agents** | Split work into Research, Ingestion, Integrity agents | Define agent prompts: **Research** (dataset discovery, API verification), **Ingestion** (connector + pipeline per blueprint), **Integrity** (variance_probe, regression tests, Prometheus invariants). Use this plan as shared context. |
| **C. Forecast Explainability dashboard** | Show exactly why a region’s score moved | Design Grafana dashboard: **contributor breakdown** (each sub-index → behavior_index delta), **source-level attribution** (which dataset drove the change), **time-range sensitivity** (as-of dates, lags). Wire to existing `explanations` / sub_indices APIs. |
| **D. Open-source positioning** | Credible analytics platform (docs, README, governance) | Update **README**: “Enterprise-grade behavioral forecasting,” link to DATA_SOURCES, ENTERPRISE_DATASET_EXPANSION_PLAN, VERIFY_INTEGRITY. Add **CONTRIBUTING**: dataset proposal template, guardrails, variance proof. Consider **governance**: maintainers, dataset approval checklist. |

**Recommendation:** Start with **Option A** (already done) → **Phase 1 (EIA Gasoline)** implementation → then **Option C** (Forecast Explainability dashboard) to make new signals interpretable. Option B (agents) and D (positioning) can run in parallel or follow.

---

## Conclusion

This Enterprise Dataset Expansion Plan provides a comprehensive roadmap for adding 15 high-value datasets, with detailed blueprints for the Top 5 MVP datasets. Each dataset is designed to:

- ✅ Increase regional variance
- ✅ Maintain zero-regression guarantees
- ✅ Integrate with existing regionality safety net
- ✅ Provide clear observability and documentation
- ✅ Pass ethical and privacy standards

**Ready for implementation. Begin with MVP 1 (EIA Gasoline Prices).**
