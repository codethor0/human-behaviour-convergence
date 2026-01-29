# Data Expansion Audit & Dashboard Enhancement Plan

## Current Data Sources (23 sources)

### Economic & Cost-of-Living
- [OK] FRED Economic Data (GDP, unemployment, CPI, consumer sentiment)
- [OK] EIA Fuel Prices by State
- [OK] EIA Energy Data (prices, demand)
- [OK] Consumer Spending (FRED - retail sales, personal consumption)
- [OK] Employment Sector Data (BLS)
- [OK] Market Sentiment (volatility indices)

### Environmental & Climate
- [OK] Weather Patterns (temperature, precipitation)
- [OK] OpenAQ Air Quality
- [OK] Air Quality (PurpleAir + EPA AirNow)
- [OK] U.S. Drought Monitor
- [OK] NOAA Storm Events
- [OK] Weather Alerts (NWS)

### Public Health
- [OK] Public Health Indicators (aggregated statistics)
- [OK] OWID Health Data

### Social & Civic Stress
- [OK] Legislative Activity (GDELT + OpenStates)
- [OK] Emergency Management (OpenFEMA)
- [OK] GDELT Events
- [OK] GDELT Enforcement Events

### Information & Attention
- [OK] Search Trends (Wikipedia Pageviews)
- [OK] Cyber Risk (CISA KEV)

### Mobility
- [OK] Mobility Patterns (TSA passenger throughput)

### Demographic
- [OK] Demographic Data (US Census Bureau)

## Gap Analysis

### High-Priority Missing Data Sources

#### Economic & Cost-of-Living
1. **Housing Stress** (Rent, Evictions)
   - Source: Zillow Rent Index API (public)
   - Eviction Lab (public dataset)
   - Impact: Housing affordability stress index
   - Regional variance: High (city-level differences)

2. **Inflation Sub-Components**
   - Source: FRED API (expands existing)
   - Food inflation, energy inflation, shelter inflation
   - Impact: Granular economic stress breakdown
   - Regional variance: Medium (national with regional proxies)

3. **Wage Growth Indicators**
   - Source: BLS Wage Data (public)
   - Real wage growth, wage by sector
   - Impact: Economic stress adjustment
   - Regional variance: Medium (state-level)

#### Environmental & Climate
4. **Heatwave Severity**
   - Source: NOAA Climate Data (expands storm events)
   - Heat index, consecutive hot days
   - Impact: Environmental stress enhancement
   - Regional variance: High (geographic differences)

5. **Flood Risk Indicators**
   - Source: USGS Water Services (public)
   - River gauge levels, flood warnings
   - Impact: Environmental stress, disaster risk
   - Regional variance: High (watershed-based)

6. **Wildfire Activity**
   - Source: NASA FIRMS (already in connectors/)
   - Active fire counts, fire intensity
   - Impact: Environmental stress, emergency indicators
   - Regional variance: High (geographic)

#### Public Health
7. **Hospital Strain Indicators**
   - Source: HHS Protect Public Data Hub (public)
   - Bed occupancy, ICU capacity
   - Impact: Public health stress
   - Regional variance: High (hospital-level aggregation)

8. **Overdose Trends**
   - Source: CDC Wonder (public, aggregated)
   - Drug overdose mortality rates
   - Impact: Public health stress, social indicators
   - Regional variance: Medium (state-level)

9. **Disease Surveillance**
   - Source: CDC FluView, NNDSS (public)
   - Influenza-like illness, reportable diseases
   - Impact: Public health stress
   - Regional variance: High (state/regional)

#### Social & Civic Stress
10. **Crime Volatility**
    - Source: FBI UCR (public, aggregated)
    - Crime rate trends, violent crime indicators
    - Impact: Social stress, safety indicators
    - Regional variance: High (city-level)

11. **Legislative Churn**
    - Source: OpenStates API (expands existing)
    - Bill introduction rates, legislative activity
    - Impact: Political stress refinement
    - Regional variance: High (state-level)

#### Information & Attention
12. **Media Volume Spikes**
    - Source: GDELT (expands existing)
    - News volume, coverage intensity
    - Impact: Digital attention, narrative instability
    - Regional variance: Medium (national with regional proxies)

13. **Search Volatility**
    - Source: Google Trends API (public, aggregated)
    - Search interest volatility, trending topics
    - Impact: Digital attention refinement
    - Regional variance: Medium (state-level)

## Dashboard Enhancement Plan

### Executive Overview Dashboard (NEW/ENHANCE)

**Current State**: `forecast_summary.json` has basic stats
**Enhancement Plan**:
- Add risk tier visualization (current + trend)
- Add key driver cards (top 3 contributing sub-indices)
- Add recent shock timeline (last 30 days)
- Add forecast confidence indicator
- Add data freshness summary

**New Panels Needed**:
1. Risk Tier Evolution (time-series showing tier changes)
2. Top Contributors (bar chart of sub-index contributions)
3. Shock Timeline (annotated timeline of significant events)
4. Forecast Confidence Gauge (stat panel)
5. Data Freshness Summary (multi-stat panel)

### Sub-Index Deep Dive (ENHANCE)

**Current State**: `subindex_deep_dive.json` has basic time-series
**Enhancement Plan**:
- Add heatmap across regions
- Add radar/spider chart for behavioral fingerprint
- Add delta views (week-over-week, month-over-month)
- Add acceleration indicators (rate of change)

**New Panels Needed**:
1. Regional Heatmap (heatmap panel showing sub-index values across regions)
2. Behavioral Fingerprint (radar chart - requires custom visualization)
3. Week-over-Week Change (time-series with offset)
4. Month-over-Month Change (time-series with offset)
5. Acceleration Indicator (second derivative visualization)

### Contribution Analysis (ENHANCE)

**Current State**: `contribution_breakdown.json` exists
**Enhancement Plan**:
- Add waterfall chart (how components build to total)
- Add historical contribution drift
- Add sensitivity analysis (variance-based)

**New Panels Needed**:
1. Waterfall Chart (current contributions breakdown)
2. Contribution Over Time (stacked area showing how contributions change)
3. Sensitivity Analysis (variance of contributions)

### Forecast & Uncertainty (ENHANCE)

**Current State**: `forecast_overview.json`, `forecast_quality_drift.json`
**Enhancement Plan**:
- Add confidence bands visualization
- Add historical vs forecast overlay
- Add horizon comparison (7-day vs 14-day vs 30-day)
- Add model behavior visualization

**New Panels Needed**:
1. Forecast with Confidence Bands (time-series with shaded areas)
2. Historical vs Forecast Overlay (comparison view)
3. Multi-Horizon Comparison (side-by-side forecasts)
4. Model Performance Over Time (which model performs best when)

### Intelligence Layer (NEW)

**Current State**: `anomaly_detection_center.json` exists
**Enhancement Plan**:
- Add shock timelines with event markers
- Add convergence graphs (network visualization)
- Add correlation matrices
- Add risk tier evolution

**New Panels Needed**:
1. Shock Timeline (annotated time-series with event markers)
2. Correlation Matrix (heatmap of sub-index correlations)
3. Risk Tier Evolution (time-series showing tier changes)
4. Convergence Network (requires custom visualization)

### Data Source Health & Provenance (ENHANCE)

**Current State**: `data_sources_health.json`, `source_health_freshness.json`
**Enhancement Plan**:
- Add source contribution visualization
- Add missing-data indicators
- Add reliability signals
- Add freshness heatmap

**New Panels Needed**:
1. Source Contribution Chart (pie/bar showing which sources contribute most)
2. Missing Data Indicators (table showing data gaps)
3. Reliability Score (gauge per source)
4. Freshness Heatmap (time since last update per source)

## Implementation Priority

### Sprint 1 (High Priority - Core Enhancements)
1. Executive Overview enhancements
2. Sub-Index Deep Dive enhancements (heatmap, deltas)
3. Forecast confidence bands
4. Contribution waterfall chart

### Sprint 2 (Medium Priority - Intelligence)
1. Shock timeline visualization
2. Correlation matrix
3. Data source contribution chart
4. Missing data indicators

### Sprint 3 (Lower Priority - Advanced Visualizations)
1. Behavioral fingerprint (radar chart)
2. Convergence network graph
3. Sensitivity analysis panels
4. Multi-horizon comparison

## Metrics Coverage Analysis

### Currently Visualized Metrics
- [OK] behavior_index (all dashboards)
- [OK] parent_subindex_value (sub-index dashboards)
- [OK] child_subindex_value (some dashboards)
- [OK] forecast metrics (forecast dashboards)
- [OK] model performance metrics (model dashboards)
- [OK] data source health metrics (health dashboards)

### Missing Visualizations
- [FAIL] Contribution breakdown over time
- [FAIL] Confidence intervals on forecasts
- [FAIL] Regional heatmaps
- [FAIL] Correlation matrices
- [FAIL] Shock event timelines
- [FAIL] Data source contribution analysis
- [FAIL] Missing data gap visualization
- [FAIL] Acceleration indicators (rate of change of rate of change)

## Next Steps

1. Enhance existing dashboards with new panels
2. Create new specialized dashboards
3. Add visualizations for new data sources
4. Implement advanced visualizations (radar, network graphs)
5. Verify all panels render correctly
6. Ensure data integrity
