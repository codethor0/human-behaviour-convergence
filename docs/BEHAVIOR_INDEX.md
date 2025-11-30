# Behavior Index Documentation

**Date:** 2025-01-XX
**Version:** 2.0 (Interpretable Design)

**Maintainer:** Thor Thor (codethor@gmail.com)

---

## What Is the Behavior Index?

The **Behavior Index** is a composite measure (0.0 to 1.0) that quantifies the overall level of **behavioral disruption** or stress in a population at a given time. It aggregates multiple dimensions of human behavior signals from public data sources.

**Interpretation:**
- **Lower values (0.0-0.4):** Low disruption, normal behavioral patterns
- **Moderate values (0.4-0.6):** Moderate disruption or mixed signals
- **Higher values (0.6-1.0):** High disruption, significant behavioral stress or changes

---

## Geographic Coverage

The Behavior Index can be computed for any region with available data. Currently supported:

- **Global Cities:** New York City, London, Tokyo
- **US States:** All 50 US states plus District of Columbia (51 total)

See `docs/REGIONS.md` for the complete list of supported regions and how to use them via the API.

---

## What Is Being Forecast?

The Behavior Index forecasts **daily behavioral disruption/stress** per region, represented as a normalized value in [0, 1].

### Qualitative Interpretation

- **0.0-0.3: Stable, Low-Stress Human Behavior**
  - Normal economic conditions, comfortable weather, typical mobility patterns
  - Low information load, minimal health stress
  - People engage in routine activities, normal spending, regular travel

- **0.3-0.6: Mixed/Transition State**
  - Some stress indicators elevated, others normal
  - Partial disruption (e.g., economic uncertainty but good weather)
  - Behavioral patterns in flux, mixed signals

- **0.6-1.0: Elevated Disruption / Behavioral Stress**
  - Multiple stress dimensions elevated simultaneously
  - Economic volatility, extreme weather, reduced mobility, high information load
  - Significant behavioral changes: reduced travel, increased savings, altered routines

### Human Behavior Story by Sub-Index

**Economic Stress:** When markets are volatile (VIX spikes) or unemployment rises, people reduce spending, increase savings, and change consumption patterns. High economic stress correlates with reduced discretionary travel and altered lifestyle choices.

**Environmental Stress:** Extreme temperatures, storms, and wildfires directly impact human behavior through physical comfort and safety. Heat waves reduce outdoor activity, storms disrupt travel, and fires cause evacuations. These environmental stressors force behavioral adaptation.

**Mobility Activity:** During normal times, people move freely for work, recreation, and social activities. During crises (pandemics, disasters, economic shocks), mobility decreases as people stay home, reduce travel, and change daily routines. Mobility patterns are direct proxies for behavioral normalcy.

**Digital Attention:** When crises occur, people seek information (Wikipedia pageviews spike), media coverage intensifies (GDELT tone/events), and search interest increases. These digital attention indicators capture the "information environment" that influences human behavior and decision-making. High attention often precedes or accompanies behavioral disruption.

**Public Health Stress:** High disease incidence, excess mortality, and hospitalization rates correlate with behavioral changes: reduced mobility, increased remote work, mask-wearing, and social distancing. These indicators measure the health burden that drives behavioral adaptation.

---

## Behavior Index Formula

The Behavior Index is computed as a weighted combination of five sub-indices:

```
BEHAVIOR_INDEX =
  (ECONOMIC_STRESS × 0.25) +
  (ENVIRONMENTAL_STRESS × 0.25) +
  ((1 - MOBILITY_ACTIVITY) × 0.20) +
  (DIGITAL_ATTENTION × 0.15) +
  (PUBLIC_HEALTH_STRESS × 0.15)
```

**Note:** Mobility activity is inverted because lower activity often indicates disruption (stay-at-home behavior during crises).

---

## Weighting & Calibration

### Current Weights

The Behavior Index uses fixed weights that sum to 1.0:

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Economic Stress | 25% | Economic uncertainty directly affects spending, travel, and behavioral patterns |
| Environmental Stress | 25% | Weather extremes and environmental disasters cause immediate behavioral disruption |
| Mobility Activity | 20% | Movement patterns are direct proxies for behavioral normalcy |
| Digital Attention | 15% | Information-seeking and media intensity indicate awareness of disruption |
| Public Health Stress | 15% | Health concerns drive behavioral adaptation (social distancing, mask-wearing, etc.) |

### Economic Stress Sub-Index Composition

The **Economic Stress** sub-index (25% of overall index) combines multiple economic indicators with adaptive weights:

**When all indicators available:**
- Market Volatility (VIX/SPY): 40%
- Consumer Sentiment (FRED): 30%
- Unemployment Rate (FRED): 20%
- Initial Jobless Claims (FRED): 10%

**When FRED data unavailable:**
- Market Volatility (VIX/SPY): 100% (falls back to market-only)

**Adaptive Weighting:**
- If only market + consumer sentiment: Market 60%, Consumer 40%
- If only market + unemployment: Market 70%, Unemployment 30%
- If only market + jobless claims: Market 80%, Jobless 20%
- Weights normalize to sum to 1.0 based on available data

**Rationale:**
- Market volatility (VIX/SPY) provides daily, high-frequency signals
- Consumer sentiment captures forward-looking expectations
- Unemployment and jobless claims measure labor market stress
- Combining these provides a more robust economic stress measure than any single indicator

### Calibration Notes

**Normalization:**
- All sub-indices are normalized to [0.0, 1.0] range
- Higher values = more stress/disruption (except mobility_activity, where higher = more activity)
- Missing data defaults to 0.5 (neutral midpoint) to avoid bias

**Temporal Alignment:**
- Market data: Daily
- FRED indicators: Monthly (consumer sentiment, unemployment) or weekly (jobless claims)
- Weather data: Daily
- Other indicators: Varies by source

**Forward-Filling:**
- FRED monthly/weekly data is forward-filled up to 90 days to align with daily market/weather data
- This ensures all indicators contribute to daily behavior index computation

### Future Calibration

As more indicators are integrated, weights may be adjusted based on:
- Empirical correlation with behavioral outcomes
- Data quality and reliability
- Temporal resolution and update frequency
- Regional availability

**See `docs/BEHAVIOR_INDICATORS_REGISTRY.md` for complete indicator taxonomy.**

---

## Sub-Indices Explained

### 1. Economic Stress (Weight: 25%)

**What it measures:** Economic uncertainty and market volatility as proxies for behavioral stress.

**Sources:**
- CBOE VIX (Volatility Index) via yfinance
- S&P 500 ETF (SPY) returns via yfinance

**Computation:**
- Normalized combination of VIX (higher = more stress) and SPY (lower = more stress)
- Range: [0.0, 1.0] where 1.0 = maximum economic stress

**Interpretation:**
- **0.0-0.3:** Low economic stress, stable markets
- **0.3-0.6:** Moderate economic uncertainty
- **0.6-1.0:** High economic stress, volatile markets

**Example:** During a market crash, VIX spikes and SPY falls, resulting in high economic_stress (close to 1.0).

---

### 2. Environmental Stress (Weight: 25%)

**What it measures:** Weather-related discomfort and extreme environmental conditions.

**Sources:**
- Temperature deviation from ideal (20C)
- Precipitation levels
- Wind speed
- Active fire events (NASA FIRMS)

**Computation:**
- Weighted combination normalized to [0.0, 1.0]
- Higher values = more environmental discomfort/stress

**Interpretation:**
- **0.0-0.3:** Comfortable weather conditions
- **0.3-0.6:** Moderate discomfort (e.g., hot/cold days, light precipitation)
- **0.6-1.0:** Extreme conditions (heat waves, storms, heavy precipitation, fires)

**Example:** During a heat wave with temperatures 15C above normal and high precipitation, environmental_stress approaches 1.0.

---

### 3. Mobility Activity (Weight: 20%, inverted)

**What it measures:** Population movement and activity patterns as indicators of behavioral normalcy.

**Sources:**
- OpenStreetMap changeset activity
- Historical mobility datasets (Apple, Google - archived)

**Computation:**
- Normalized activity index to [0.0, 1.0] where 1.0 = maximum activity
- **Inverted in formula:** (1 - mobility_activity) because lower activity often indicates disruption

**Interpretation:**
- **High mobility (0.7-1.0):** Normal activity patterns
- **Moderate mobility (0.4-0.7):** Reduced activity
- **Low mobility (0.0-0.4):** Significant activity reduction (e.g., lockdowns, severe weather)

**Example:** During a lockdown, mobility_activity drops to 0.2, so (1 - 0.2) = 0.8 contributes to behavior_index, indicating disruption.

---

### 4. Digital Attention (Weight: 15%)

**What it measures:** Digital attention spikes and media intensity as proxies for behavioral disruption.

**Sources:**
- Wikipedia pageviews (aggregated)
- GDELT media tone scores (planned)
- Google Trends (planned, limited availability)

**Computation:**
- Normalized attention index to [0.0, 1.0] where 1.0 = maximum attention
- Detects spikes relative to baseline

**Interpretation:**
- **0.0-0.4:** Normal attention levels
- **0.4-0.7:** Elevated attention (e.g., news events)
- **0.7-1.0:** Very high attention spikes (e.g., major crises, breaking news)

**Example:** During a major event, Wikipedia pageviews for related topics spike, resulting in high digital_attention.

---

### 5. Public Health Stress (Weight: 15%)

**What it measures:** Public health indicators that affect behavioral patterns.

**Sources:**
- CDC aggregate health indicators (planned)
- WHO public health data (planned)
- Our World in Data aggregates (planned)

**Computation:**
- Normalized health stress index to [0.0, 1.0] where 1.0 = maximum health stress
- Uses only coarse aggregates (national/regional, no individual data)

**Interpretation:**
- **0.0-0.3:** Low health stress
- **0.3-0.6:** Moderate health concerns
- **0.6-1.0:** High health stress (e.g., outbreaks, high hospitalization rates)

**Example:** During a health crisis, aggregate indicators show elevated case counts, resulting in high public_health_stress.

---

## Example Interpretation

### Scenario: Moderate Disruption

**Sub-indices:**
- Economic stress: 0.45 (moderate market volatility)
- Environmental stress: 0.35 (mild weather discomfort)
- Mobility activity: 0.60 (slightly reduced activity)
- Digital attention: 0.50 (normal attention levels)
- Public health stress: 0.40 (low-moderate health concerns)

**Calculation:**
```
BEHAVIOR_INDEX =
  (0.45 × 0.25) +           # Economic: 0.1125
  (0.35 × 0.25) +           # Environmental: 0.0875
  ((1 - 0.60) × 0.20) +     # Mobility (inverted): 0.0800
  (0.50 × 0.15) +           # Digital: 0.0750
  (0.40 × 0.15)             # Health: 0.0600
  = 0.415
```

**Interpretation:** Behavior Index of **0.415** indicates moderate disruption. The primary driver is economic stress (45%), with some environmental and mobility factors contributing.

### Scenario: High Disruption

**Sub-indices:**
- Economic stress: 0.75 (market crash)
- Environmental stress: 0.60 (heat wave)
- Mobility activity: 0.25 (lockdown)
- Digital attention: 0.80 (major news event)
- Public health stress: 0.70 (health crisis)

**Calculation:**
```
BEHAVIOR_INDEX =
  (0.75 × 0.25) +           # Economic: 0.1875
  (0.60 × 0.25) +           # Environmental: 0.1500
  ((1 - 0.25) × 0.20) +     # Mobility (inverted): 0.1500
  (0.80 × 0.15) +           # Digital: 0.1200
  (0.70 × 0.15)             # Health: 0.1050
  = 0.7125
```

**Interpretation:** Behavior Index of **0.71** indicates high disruption across multiple dimensions. All factors are elevated, with economic stress and mobility reduction being the largest contributors.

---

## Data Availability and Defaults

### Currently Active Sources

- **Economic Stress:** Market data (VIX/SPY) via yfinance - **Active**
- **Environmental Stress:** Weather data via Open-Meteo - **Active**

### Stubbed Sources (Default to 0.5)

When data sources are not configured or unavailable, sub-indices default to 0.5 (neutral midpoint):

- **Mobility Activity:** Defaults to 0.5 if no mobility data available
- **Digital Attention:** Defaults to 0.5 if no search/attention data available
- **Public Health Stress:** Defaults to 0.5 if no health data available

This ensures the Behavior Index can still be computed when only partial data is available, but the interpretation should note which dimensions are using defaults.

---

## Limitations and Considerations

1. **Geographic Scope:** Market data is global, while weather and mobility are regional. The index reflects a mix of global and regional signals.

2. **Temporal Granularity:** All sub-indices are daily aggregates. Intra-day variations are not captured.

3. **Causality:** The index measures correlation and patterns, not causation. High index values indicate disruption but do not explain why.

4. **Baseline Comparison:** The index is relative, not absolute. Interpretation benefits from comparing to historical values or regional baselines.

5. **Missing Data:** When sources are unavailable, defaults to neutral (0.5) may mask actual conditions.

---

## Live Monitoring

The system includes a live monitoring capability (`/live` route) that provides near real-time tracking of behavior index values across regions. Live monitoring maintains a rolling window of recent snapshots and automatically detects major events that could impact human behavior scores.

### Live Monitoring Features

- **Near real-time snapshots:** Behavior index and sub-indices updated periodically (default: every 30 minutes)
- **Event detection:** Automatic flagging of major events:
  - Digital attention spikes (sudden increases in digital_attention)
  - Health stress elevation (public_health_stress above threshold)
  - Environmental shocks (environmental_stress above threshold)
  - Economic volatility (economic_stress above threshold)
- **Historical window:** View recent snapshots within a configurable time window
- **Background refresh:** Automatic background updates without blocking API requests

### Live Monitoring API

- **GET /api/live/summary:** Get live data summary for specified regions
  - Query parameters: `regions` (optional list), `time_window_minutes` (default: 60)
  - Returns: Latest snapshots and recent history for each region
- **POST /api/live/refresh:** Manually trigger a refresh of live data
  - Query parameters: `regions` (optional list, refreshes all if omitted)

### Event Detection Logic

Event detection uses rule-based heuristics on sub-index values:
- **Digital attention spike:** Detected when digital_attention increases by 0.15 or more compared to the previous snapshot
- **Health stress elevated:** Detected when public_health_stress >= 0.7
- **Environmental shock:** Detected when environmental_stress >= 0.8
- **Economic volatility:** Detected when economic_stress >= 0.75

Event flags are stored with each snapshot and displayed in the live monitoring UI.

### Live Snapshots vs Forecasts

Live snapshots use the same Behavior Index math and weights as standard forecasts. The difference is:
- **Forecasts:** Generated on-demand for specific time horizons (e.g., 7 days ahead)
- **Live snapshots:** Maintained continuously, showing current state and recent history

Both use the same underlying data sources and computation logic.

## Live Playground

The system includes an interactive playground (`/playground` route) for exploring forecasts across multiple regions and testing "what-if" scenarios. The playground uses the same Behavior Index math and weights as the standard forecast endpoint. Optional scenario adjustments are applied as post-processing transformations for exploration purposes only and do not affect the underlying forecasting model.

### Playground Features

- **Multi-region comparison:** Compare forecasts for multiple regions side-by-side
- **Configurable parameters:** Adjust historical days and forecast horizon
- **Optional scenario adjustments:** Explore "what-if" scenarios with post-processing offsets to sub-indices
- **Explanations:** View structured explanations for each region's forecast

### Scenario Adjustments

Scenario adjustments are pure post-processing transformations that:
- Apply offsets to sub-indices (clamped to [0.0, 1.0])
- Recompute the Behavior Index using the same fixed weights
- Are clearly labeled as hypothetical and experimental
- Do not modify the underlying forecasting model or data sources

## Interpretability and Explanations

The Behavior Index includes an optional explanation layer that provides human-readable interpretations of forecast values.

### Explanation Schema

Forecast API responses may include an optional `explanations` field with the following structure:

```json
{
  "explanations": {
    "summary": "High-level explanation string",
    "subindices": {
      "economic_stress": {
        "level": "moderate",
        "reason": "Market volatility is slightly elevated but unemployment remains stable.",
        "components": [
          {
            "id": "market_volatility",
            "label": "Market Volatility",
            "direction": "up",
            "importance": "high",
            "explanation": "Volatility index is above its 6-month average."
          }
        ]
      },
      ...
    }
  }
}
```

### Level Thresholds

Sub-index levels are classified using fixed thresholds:

- **Low:** 0.0 - 0.33 (normal/stable conditions)
- **Moderate:** 0.34 - 0.66 (mixed signals, partial disruption)
- **High:** 0.67 - 1.0 (elevated stress/disruption)

These thresholds apply to all sub-indices and the overall Behavior Index.

### Component-Level Details

When component-level data is available (e.g., from GDELT, OWID, USGS), explanations include:

- **Direction:** "up" (elevated), "down" (reduced), or "neutral" (near baseline)
- **Importance:** "high", "medium", or "low" (based on component weight and deviation from baseline)
- **Explanation:** Human-readable description of the component's contribution

### Component Integration

New data sources (GDELT, OWID, USGS) appear in component explanations:

- **GDELT Events:** Shows up in `digital_attention` components when available
- **OWID Health:** Shows up in `public_health_stress` components when available
- **USGS Earthquakes:** Shows up in `environmental_stress` components when available

### Usage

The explanation field is optional and backward-compatible. Clients that do not consume it will continue to work normally. The explanation generation is deterministic and based solely on numeric values and thresholds - no external AI services are used.

---

## Future Enhancements

1. **Regional Baselines:** Compute region-specific baselines for more accurate interpretation
2. **Historical Comparison:** Add "vs. last week/month" comparisons
3. **Dimension Decomposition:** Visualize which dimensions are driving changes
4. **Confidence Intervals:** Account for data quality and missing sources in uncertainty estimates

---

**Maintainer:** Thor Thor (codethor@gmail.com)
