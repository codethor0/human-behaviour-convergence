# Next-Generation Visualization & Data Expansion Implementation Plan

**Status:** In Progress
**Last Updated:** 2026-01-26
**Priority:** High Impact - User-Facing First

---

## Executive Summary

This document outlines the implementation plan for transforming the HBC platform into an immersive intelligence ecosystem with cinematic visualizations and comprehensive data ingestion.

**Current State:**
- Basic metric cards and line charts
- 14 data sources integrated
- Grafana dashboards for operational monitoring

**Target State:**
- Multi-dimensional, narrative-driven visualizations
- 30+ data sources covering all behavioral dimensions
- 4-tier dashboard hierarchy (Executive → Analyst → Researcher → Public)
- Real-time anomaly detection and automated insights

---

## Phase 1: Revolutionary Visualization (IN PROGRESS)

### Status: 3/6 Core Visualizations Complete

#### [OK] Completed

1. **3D Temporal Topology Map** (`TemporalTopologyMap.tsx`)
   - Three.js-based 3D landscape visualization
   - X-axis: Time, Y-axis: Behavior Index, Z-axis: Causal Density
   - Interactive rotation and drag controls
   - Color-coded confidence levels

2. **Predictive Horizon Clouds** (`PredictiveHorizonClouds.tsx`)
   - Probability density visualization with gradient opacity
   - Interactive assumption slider for scenario testing
   - Warning fronts for high-risk periods
   - Confidence intervals visually represented

3. **Behavioral Heat Cartography** (`BehavioralHeatCartography.tsx`)
   - Mapbox GL-based geo-temporal heatmaps
   - Time-lapse animation capabilities
   - Multi-region stress propagation visualization
   - Real-time data updates

####  In Progress / Pending

4. **Convergence Vortex** (`ConvergenceVortex.tsx`)
   - Status: Basic implementation exists, needs enhancement
   - Required: Real correlation data integration
   - Required: Pulse animations for real-time influence

5. **Anomaly Detection Theater** (`AnomalyDetectionTheater.tsx`)
   - Status: [OK] Just completed
   - Automated Z-score detection
   - Investigation thread generation
   - Spotlight effects for outliers

6. **Executive Narrative Streams** (`ExecutiveNarrativeStreams.tsx`)
   - Status: Pending
   - Auto-generated "Behavioral Weather Reports"
   - Red Team scenario simulations
   - Twin Region historical analog finder

---

## Phase 1B: Dashboard Hierarchy (PENDING)

### Tier 1: Command Center (Executive View)
**Status:** Components exist, needs integration

**Components Available:**
- [OK] `BehaviorIndexFuelGauge.tsx` - Live fuel gauge with trend velocity
- [OK] `CriticalAlertsTicker.tsx` - Top 5 active shocks
- [OK] `RegionalComparisonMatrix.tsx` - Grid view of all regions
- [OK] `WarningRadar.tsx` - 72-hour warning radar
- [OK] `ConfidenceThermometer.tsx` - Data quality indicator
- [OK] `InsightOfTheDay.tsx` - Auto-generated insights

**Action Required:**
- Create `/command-center` page integrating all 6 panels
- Implement cinematic 6-panel layout
- Add real-time WebSocket updates

### Tier 2: Operational Intelligence (Analyst View)
**Status:** Pending

**Required Features:**
- Drag-and-drop modular workspace
- Sub-index "Control Room" with oscilloscope displays
- Correlation Matrix Explorer (interactive heatmap)
- Data Source Health Monitor
- Event Timeline with annotations

**Action Required:**
- Create `/operational-intelligence` page
- Implement drag-and-drop grid system (react-grid-layout)
- Build correlation matrix component
- Integrate data source health API

### Tier 3: Deep Dive Laboratory (Researcher View)
**Status:** Pending

**Required Features:**
- Time-series decomposition trees
- Causal inference graphs (Bayesian networks)
- Raw data explorer with SQL-like query builder
- Model performance diagnostics
- Residual analysis visualizer

**Action Required:**
- Create `/deep-dive-laboratory` page
- Integrate statistical decomposition libraries
- Build query builder interface
- Add model diagnostics components

### Tier 4: Public/Stakeholder View
**Status:** Pending

**Required Features:**
- Story-mode scrolling interface
- "This Week in Behavioral Risk" infographic
- Regional "Vital Signs" cards (5-metric view)
- Historical context comparisons

**Action Required:**
- Create `/public-view` page
- Design infographic-style components
- Implement story-mode scrolling
- Add comparison tool

---

## Phase 2: Comprehensive Data Expansion

### Current Data Sources (14)

1. Economic Indicators (Market Sentiment)
2. FRED Economic Data
3. Weather Patterns
4. OpenAQ Air Quality
5. EIA Energy Data
6. Search Trends (Wikipedia Pageviews)
7. Public Health
8. Mobility Patterns (TSA)
9. Emergency Management (OpenFEMA)
10. Legislative Activity (GDELT + OpenStates)
11. GDELT Events
12. GDELT Enforcement
13. Weather Alerts (NWS)
14. Cyber Risk (CISA KEV)

### Phase 2A: Alternative Economic Signals (PENDING)

**Priority:** High (High-frequency signals)

**Data Sources to Add:**
- [ ] **Satellite Economic Activity**
  - VIIRS Night Lights intensity by region
  - Parking lot occupancy (satellite imagery)
  - Port/shipping container traffic
  - Implementation: NASA VIIRS API, commercial satellite APIs

- [ ] **Digital Economy Proxies**
  - App download trends (AppTweak/App Annie)
  - Job posting velocity (Indeed/LinkedIn APIs)
  - Restaurant reservation trends (OpenTable)
  - Freight movement (AIS shipping + truck GPS)
  - Implementation: Public APIs where available, scraping where necessary

**Estimated Effort:** 2-3 weeks per source

### Phase 2B: Environmental & Infrastructure IoT (PENDING)

**Priority:** Medium (Real-time indicators)

**Data Sources to Add:**
- [ ] **IoT Sensor Networks**
  - Smart grid stress indicators (power consumption)
  - Water quality monitoring (EPA real-time feeds)
  - Traffic sensor density/flow (DOT open data)
  - Air quality sensors (PurpleAir, EPA AirNow) - Partially implemented

- [ ] **Climate Extremes**
  - Soil moisture deficits (agricultural stress)
  - River gauge levels (flood precursors)
  - Wildfire smoke dispersion (HRRR smoke data)

**Estimated Effort:** 1-2 weeks per source

### Phase 2C: Social & Cultural Pulse (PENDING)

**Priority:** High (Behavioral indicators)

**Data Sources to Add:**
- [ ] **Digital Exhaust**
  - Reddit API sentiment by subreddit/region
  - Meetup.com event creation/cancellation rates
  - Google Reviews sentiment velocity
  - Wikipedia edit velocity on crisis pages

- [ ] **Cultural Indicators**
  - Eventbrite ticket sales trends
  - Movie theater attendance (where public)
  - Religious service attendance (Google mobility)
  - Dating app activity trends

**Estimated Effort:** 1-2 weeks per source

### Phase 2D: Institutional & Governance (PENDING)

**Priority:** Medium (Micro-signals)

**Data Sources to Add:**
- [ ] **Legal/Political Micro-Signals**
  - Court case filing rates
  - FOIA request volumes
  - Procurement contract awards
  - 311 call volumes

- [ ] **Financial System Health**
  - ATM cash withdrawal patterns
  - Bank branch closure announcements
  - Credit union membership growth
  - Payday lending search trends

**Estimated Effort:** 2-3 weeks per source

### Phase 2E: Health & Biological (PENDING)

**Priority:** Medium (Beyond COVID)

**Data Sources to Add:**
- [ ] **Syndromic Surveillance**
  - Influenza-like illness (ILI) emergency visits
  - Overdose incident reports (EMS data)
  - Poison control call volumes
  - Veterinary diagnostic data

- [ ] **Environmental Health**
  - Pollen counts
  - UV index extremes
  - Noise pollution levels

**Estimated Effort:** 1-2 weeks per source

### Phase 2F: Cyber & Information Ecosystem (PENDING)

**Priority:** Low (Specialized)

**Data Sources to Add:**
- [ ] **Dark Web Monitoring**
  - Data breach announcements
  - Ransomware attack frequency (public trackers)

- [ ] **Information Velocity**
  - Telegram channel growth
  - Discord server activity trends
  - Nextdoor post sentiment
  - Craigslist "missed connections" volume

**Estimated Effort:** 2-3 weeks per source

### Phase 2G: Mobility & Physical Patterns (PENDING)

**Priority:** Medium (Granular indicators)

**Data Sources to Add:**
- [ ] **Micro-Mobility**
  - Bike-share usage (Lyft, Lime public data)
  - Scooter deployment density
  - Toll booth transaction volumes

- [ ] **Commercial Activity**
  - UPS/FedEx delivery volume indices
  - Garbage collection weight trends
  - Construction permit applications

**Estimated Effort:** 1-2 weeks per source

---

## Phase 3: Technical Infrastructure

### 3.1 Visualization Stack (PARTIALLY COMPLETE)

**Status:**
- [OK] D3.js installed and used (ConvergenceVortex)
- [OK] Three.js installed and used (TemporalTopologyMap)
- [OK] Apache ECharts installed and used (PredictiveHorizonClouds)
- [OK] Mapbox GL installed and used (BehavioralHeatCartography)
- [WARN] WebSocket connections - Pending (needs backend support)

**Action Required:**
- Implement WebSocket server in backend
- Add real-time data streaming for live visualizations
- Optimize rendering performance for large datasets

### 3.2 Data Ingestion Pipeline (PENDING)

**Current Architecture:**
- Source registry pattern (`source_registry.py`)
- Individual fetcher classes per source
- SQLite-backed storage (optional)

**Required Enhancements:**
- [ ] Apache Kafka for stream queuing
- [ ] Automated schema detection for new APIs
- [ ] Failsafe caching with staleness indicators
- [ ] Rate-limiting management
- [ ] Data quality scoring

**Estimated Effort:** 3-4 weeks

### 3.3 Quality Assurance Features (PENDING)

**Required for Every Visualization:**
- [ ] Confidence intervals visually represented
- [ ] Data freshness timestamps
- [ ] "Explain this" button linking to methodology
- [ ] Mobile-responsive breakpoints
- [ ] Focus Mode (dim non-critical elements during crisis)

**Action Required:**
- Create reusable QA component wrapper
- Add methodology documentation system
- Implement responsive design patterns

---

## Implementation Priorities

### Immediate (Week 1-2)
1. [OK] Complete core visualizations (3/6 done)
2. [OK] Anomaly Detection Theater (just completed)
3.  Executive Narrative Streams
4.  Tier 1 Command Center integration

### Short-term (Week 3-4)
1. Tier 2 Operational Intelligence
2. WebSocket real-time updates
3. High-priority data sources (Reddit, Meetup, Job postings)

### Medium-term (Month 2)
1. Tier 3 Deep Dive Laboratory
2. Tier 4 Public View
3. Data Vacuum architecture (Kafka)
4. Additional data sources (10-15 new sources)

### Long-term (Month 3+)
1. Remaining data sources (complete Phase 2)
2. Advanced analytics (Bayesian networks, causal inference)
3. Mobile optimization
4. Performance optimization

---

## Success Metrics

### User Engagement
- **Target:** 300% increase in engagement time
- **Measurement:** Analytics dashboard session duration

### Time-to-Insight
- **Target:** Under 30 seconds to find root cause of index spike
- **Measurement:** User testing with timed tasks

### Data Coverage
- **Target:** 95% of public data sources for target regions ingested
- **Measurement:** Source registry coverage report

### Dashboard Health
- **Target:** Zero "dead" dashboards (all update minimum daily)
- **Measurement:** Automated dashboard health checks

---

## Technical Debt & Constraints

### Known Limitations
1. Mapbox requires API token (environment variable)
2. Some data sources require API keys (documented in registry)
3. WebSocket infrastructure not yet implemented
4. Mobile responsiveness needs testing

### Creative Constraints
- Maximum 3 colors per dashboard (use intensity/opacity)
- All charts must answer "So what?" (include action/impact)
- Focus Mode required for crisis periods

---

## Next Steps

1. **Complete Executive Narrative Streams component**
2. **Integrate Tier 1 Command Center page**
3. **Begin high-priority data source integrations** (Reddit, Meetup)
4. **Set up WebSocket infrastructure**
5. **Create QA component wrapper**

---

## Related Documents

- `/docs/DATASET_EXPANSION_RECOMMENDATIONS.md`
- `/docs/NEW_DATA_SOURCES_IMPLEMENTATION.md`
- `/app/frontend/src/components/README.md` (to be created)
