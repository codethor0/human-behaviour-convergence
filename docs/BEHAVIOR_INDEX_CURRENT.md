# Current Behavior Index Analysis

**Date:** 2025-01-XX
**Analysis:** Phase 0 - Current State Understanding

---

## Current BEHAVIOR_INDEX Definition

### What It Measures

The current `behavior_index` represents a **composite measure of behavioral normalcy/activity** that aggregates multiple stress and activity signals into a single normalized score.

**Range:** [0.0, 1.0]
- **Higher values (closer to 1.0):** Lower stress, higher comfort, more normal activity patterns
- **Lower values (closer to 0.0):** Higher stress, lower comfort, reduced activity patterns

### Current Formula

Located in `app/services/ingestion/processor.py` (lines 313-320):

```
behavior_index =
  (inverse_stress * 0.25) +
  (comfort * 0.25) +
  (attention_score * 0.15) +
  (inverse_health_burden * 0.15) +
  (mobility_activity * 0.10) +
  (seasonality * 0.10)
```

Where:

1. **inverse_stress** = 1 - stress_index
   - Source: Market data (VIX volatility index, SPY S&P 500 ETF)
   - Higher VIX = higher market stress = lower inverse_stress
   - Higher SPY = lower market stress = higher inverse_stress
   - Weight: 25%

2. **comfort** = 1 - discomfort_score
   - Source: Weather data (temperature deviation from 20C, precipitation, wind speed)
   - Calculated via Open-Meteo API
   - Weight: 25%

3. **attention_score** = search_interest_score
   - Source: Search trends (currently stubbed, defaults to 0.5)
   - Weight: 15%

4. **inverse_health_burden** = 1 - health_risk_index
   - Source: Public health indicators (currently stubbed, defaults to 0.5)
   - Weight: 15%

5. **mobility_activity** = mobility_index
   - Source: Mobility/activity patterns (currently stubbed, defaults to 0.5)
   - Weight: 10%

6. **seasonality** = day_of_year / 365.0
   - Simple cyclical pattern based on calendar day
   - Weight: 10%

### Normalization

All component signals are normalized to [0.0, 1.0] range:
- Market stress: Normalized VIX and inverse SPY
- Weather discomfort: Normalized temperature deviation, precipitation, wind
- Missing signals: Default to 0.5 (neutral midpoint)

### Aggregation

- **Time aggregation:** Daily (aligned to common date range)
- **Missing data handling:**
  - Forward-fill market data for weekends (2 days)
  - Linear interpolation for other signals
  - Default to 0.5 if entire signal missing

---

## Current Implementation Status

### Implemented Sources

1. **Market Sentiment (yfinance)**
   - Status: Fully implemented and active
   - Provides: stress_index (normalized VIX/SPY combination)
   - Caching: 5 minutes

2. **Weather/Environmental (Open-Meteo)**
   - Status: Fully implemented and active
   - Provides: discomfort_score (temperature, precipitation, wind)
   - Caching: 30 minutes

### Stubbed Sources (Return Empty DataFrames)

3. **Search Trends**
   - Status: Stubbed, requires `SEARCH_TRENDS_API_ENDPOINT` and `SEARCH_TRENDS_API_KEY`
   - Current behavior: Returns empty DataFrame, defaults to 0.5 in formula

4. **Public Health**
   - Status: Stubbed, requires `PUBLIC_HEALTH_API_ENDPOINT` and `PUBLIC_HEALTH_API_KEY`
   - Current behavior: Returns empty DataFrame, defaults to 0.5 in formula

5. **Mobility**
   - Status: Stubbed, requires `MOBILITY_API_ENDPOINT` and `MOBILITY_API_KEY`
   - Current behavior: Returns empty DataFrame, defaults to 0.5 in formula

---

## Interpretation

### What a Value Means

Given the current formula, a `behavior_index` of approximately **0.6** (as seen in screenshots) suggests:

- **Economic stress:** Moderate (assuming inverse_stress ≈ 0.6, stress_index ≈ 0.4)
- **Weather comfort:** Moderate (assuming comfort ≈ 0.6, discomfort ≈ 0.4)
- **Attention/search:** Neutral (default 0.5)
- **Health burden:** Neutral (default 0.5)
- **Mobility:** Neutral (default 0.5)
- **Seasonality:** Depends on day of year

**Interpretation:** The index is slightly above neutral (0.5), indicating moderately favorable conditions for normal behavioral patterns, but not exceptional. The actual signal strength is limited because only market and weather data are active, while other dimensions default to neutral.

---

## Gaps and Limitations

### Missing Dimensions

1. **Consumer Sentiment:** No direct measure of consumer confidence or sentiment (only market volatility)
2. **Employment Indicators:** No unemployment or jobless claims data
3. **Digital Attention:** Search trends stubbed, no Wikipedia pageviews or media tone
4. **Public Health:** Health indicators stubbed, no real health stress signals
5. **Mobility Patterns:** Mobility data stubbed, no real activity measures

### Conceptual Gaps

1. **Interpretability:** The index combines stress (inverse) and activity signals, but the meaning of the composite is not immediately clear to users
2. **Sub-index Visibility:** Users cannot see which dimensions are driving the index value
3. **Baseline Comparison:** No clear baseline or historical comparison for "normal" behavior
4. **Regional Granularity:** Limited regional variation (mostly weather is regional, market is global)

---

## Next Steps

1. **Redesign index** to be more interpretable with explicit sub-indices
2. **Add credible public data sources** for missing dimensions
3. **Improve documentation** so users understand what the index represents
4. **Add visualization** of sub-index contributions in the frontend

---

**Maintainer:** Thor Thor (codethor@gmail.com)
