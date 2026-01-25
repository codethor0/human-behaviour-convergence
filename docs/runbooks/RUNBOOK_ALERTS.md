# Alert Response Runbook

**Purpose:** Guide for operators responding to behavioral alerts in Grafana

**Last Updated:** 2026-01-19

---

## Overview

This runbook tells operators what to do when behavioral alerts fire in Grafana.

**Assumptions:**
- Docker stack is running (backend, frontend, prometheus, grafana)
- GATE A and GATE G are normally GREEN
- Alerts are defined in `infra/grafana/provisioning/alerting/rules.yml`

**Quick Access:**
- Alerts List: http://localhost:3001/alerting/list (local dev)
- Operator Console: http://localhost:3100/ops

---

## 1. High Behavior Index Alert

**Alert Name:** `High Behavior Index`
**Condition:** `behavior_index > 0.8` for any region for ≥ 5 minutes
**Severity:** Warning

### 1.1. What This Alert Means

**Questions this alert answers:**
- "Which regions are currently experiencing very high behavioral stress?"
- "Is this a spike or a sustained condition?"

**Interpretation:**
- Behavior index > 0.8 indicates **critical behavioral stress** in a region
- This can signal:
  - Public health emergency
  - Economic crisis
  - Environmental disaster
  - Political instability
  - Combination of multiple stressors

**Context:**
- Normal range: 0.0 - 0.4 (Stable)
- Elevated: 0.4 - 0.7
- **Critical: ≥ 0.7** (This alert fires at > 0.8)

---

### 1.2. Immediate Triage Steps

**Step 1: Identify the Region(s)**

From the alert notification:
- Note the `region` label (e.g., `us_mn`, `city_nyc`)
- Note the current `behavior_index` value

**Step 2: Open Risk Regimes Dashboard**

1. Go to `/ops` → Click **"Behavioral Risk Regimes"**
2. Check:
   - **Critical regions table:** Is this region listed?
   - **Top 10 by index panel:** Where does this region rank?
   - **30-day regime history heatmap:** Has this region been critical before, or is this new?

**Step 3: Assess Trajectory**

1. From `/ops`, open **"Historical Trends & Volatility"** dashboard
2. Select the region from the dropdown
3. Check:
   - **7-day derivative:** Is the index trending up (worsening) or down (improving)?
   - **7-day volatility:** Is this a stable elevated state or a volatile spike?
   - **Current vs 7-day average:** Is this significantly different from recent history?

**Step 4: Identify Root Causes**

1. From `/ops`, open **"Sub-Index Deep Dive"** dashboard
2. Select the region
3. Check:
   - **Parent sub-indices panel:** Which categories are elevated?
     - Economic stress?
     - Public health stress?
     - Environmental stress?
     - Political stress?
     - Crime stress?
     - Misinformation stress?
     - Social cohesion stress?
   - **Child sub-indices:** Drill down to specific stressors

**Step 5: Cross-Check with Other Regions**

1. From `/ops`, open **"Regional Comparison"** dashboard
2. Multi-select nearby or similar regions
3. Check:
   - Is this affecting multiple regions? (Systemic event)
   - Or is it localized to this region? (Regional event)

---

### 1.3. Technical Pipeline Sanity Check

Before trusting alert data, confirm the pipeline is healthy:

```bash
cd /Users/thor/Projects/human-behaviour-convergence
./ops/verify_gate_grafana.sh
```

**Confirm:**
- [1] Backend /metrics → OK
- [2] Prometheus targets → backend target is up
- [4.1] Global Behavior Index dashboard queries → non-empty
- [4.5] Risk Regimes dashboard queries → non-empty (or documented "0 regions" case)

**If any check fails:** See `docs/RUNBOOK_DASHBOARDS.md` Section 2: Pipeline Failures

---

### 1.4. Documentation & Communication

**Document:**
- Region(s) affected
- Current behavior index value
- Primary drivers (which parent sub-indices are elevated)
- Trajectory (improving vs. worsening)
- Duration (how long has it been above 0.8?)

**Communication Template:**

```
ALERT: High Behavior Index - [Region Name]

Region: [region_id] ([region_name])
Current Index: [value]
Threshold: 0.8
Duration: [minutes/hours]

Primary Drivers:
- [Parent Index 1]: [value]
- [Parent Index 2]: [value]

Trajectory: [Improving/Stable/Worsening]
Volatility: [Low/Moderate/High]

Context: [Brief description of what's driving this]

Dashboards:
- Risk Regimes: http://localhost:3001/d/risk-regimes
- Trends: http://localhost:3001/d/historical-trends?var-region=[region_id]
- Deep Dive: http://localhost:3001/d/subindex-deep-dive?var-region=[region_id]

Action: [Continue monitoring / Investigate further / Escalate]
```

---

### 1.5. Escalation Guidelines

**Escalate when:**
- Behavior index > 0.9 (extreme stress)
- Multiple regions simultaneously > 0.8 (systemic crisis)
- Index has been > 0.8 for > 60 minutes and is trending up
- Volatility is also high (≥ 0.1) indicating instability

**Escalation Package:**
- Screenshots of Risk Regimes dashboard (Critical regions table)
- Screenshots of Trends dashboard (7-day derivative, volatility)
- Screenshots of Deep Dive dashboard (parent sub-indices)
- Communication template (above) filled out
- Output of `./ops/verify_gate_grafana.sh` (to prove pipeline is healthy)

---

## 2. Behavior Index Spike Alert

**Alert Name:** `Behavior Index Spike`
**Condition:** `abs(behavior_index - behavior_index offset 7d) > 0.3` for ≥ 5 minutes
**Severity:** Warning

### 2.1. What This Alert Means

**Questions this alert answers:**
- "Which regions have changed dramatically vs. 7 days ago?"
- "Is the system entering a new regime or reacting to a transient event?"

**Interpretation:**
- A change of > 0.3 over 7 days is **significant**
- This can indicate:
  - Rapid onset event (natural disaster, major policy change)
  - Sudden improvement after crisis resolution
  - Data anomaly or pipeline issue

**Context:**
- Change of 0.1-0.2: Normal fluctuation
- Change of 0.3-0.5: Significant shift
- Change of > 0.5: Major event or data issue

---

### 2.2. Immediate Triage Steps

**Step 1: Identify the Region and Direction**

From the alert:
- Note the `region` label
- Note the current `behavior_index` value
- Calculate the change:
  - If current > 7-day-ago: **Worsening** (stress increasing)
  - If current < 7-day-ago: **Improving** (stress decreasing)

**Step 2: Check Historical Context**

1. From `/ops`, open **"Historical Trends & Volatility"** dashboard
2. Select the region
3. Check:
   - **Current vs 7-day trend panel:** Visual confirmation of the spike
   - **7-day derivative:** Positive (increasing) or negative (decreasing)?
   - **7-day volatility:** High volatility suggests rapid changes

**Step 3: Compare to 30-Day Trend**

Still in Historical Trends dashboard:
- Check **Current vs 30-day trend panel**
- Is the 30-day trend also showing this change?
  - If YES: Sustained shift, not a one-day spike
  - If NO: Short-term spike, may revert

**Step 4: Check Risk Regime Transition**

1. From `/ops`, open **"Behavioral Risk Regimes"** dashboard
2. Check **30-day regime history heatmap**
3. Look for regime transitions:
   - Stable → Elevated (minor concern)
   - Elevated → Unstable or Critical (major concern)
   - Critical → Elevated or Stable (improvement, but verify it's real)

**Step 5: Identify What Changed**

1. From `/ops`, open **"Sub-Index Deep Dive"** dashboard
2. Select the region
3. Compare current values to 7-day history
4. Identify:
   - Which parent sub-indices spiked?
   - Are there new child indices that weren't elevated 7 days ago?

---

### 2.3. Technical Pipeline Sanity Check

Before trusting spike data:

```bash
cd /Users/thor/Projects/human-behaviour-convergence
./ops/verify_gate_grafana.sh
```

**Confirm:**
- [4.3] Historical Trends queries → non-empty
  - 7-day average
  - 7-day derivative
  - 7-day volatility
- [4.5] Risk Regimes queries → non-empty

**Special Check for Data Gaps:**

```bash
# Check if metrics are being continuously exported
curl -sS http://localhost:8100/metrics | grep "behavior_index{region=\"us_mn\"}" | head -3
```

If you see recent timestamps, data is fresh. If timestamps are old (> 1 hour), pipeline may be stale.

---

### 2.4. Distinguishing Real Events from Anomalies

**Real Event Indicators:**
- Multiple regions showing similar spikes
- Spike correlates with known real-world events (news, weather, policy changes)
- Sub-indices show logical patterns (e.g., environmental stress spikes during hurricane)
- Volatility is moderate (data is consistent)

**Data Anomaly Indicators:**
- Only one region spikes, all others stable
- No corresponding real-world event
- Sub-indices show illogical patterns (all maxed out simultaneously)
- Volatility is extreme (> 0.2, suggesting noisy data)
- Recent changes to data pipeline or forecasting code

**If suspected anomaly:**
1. Generate a fresh forecast:
   ```bash
   curl -X POST http://localhost:8100/api/forecast \
     -H "Content-Type: application/json" \
     -d '{
       "region_id": "us_mn",
       "region_name": "Minnesota (US)",
       "days_back": 30,
       "forecast_horizon": 7
     }'
   ```
2. Wait 30s for Prometheus scrape
3. Refresh Grafana dashboards
4. If spike persists, treat as real event

---

### 2.5. Documentation & Communication

**Document:**
- Region(s) affected
- Current behavior index value
- 7-day-ago behavior index value
- Change magnitude and direction
- Duration of spike
- Root cause hypothesis

**Communication Template:**

```
ALERT: Behavior Index Spike - [Region Name]

Region: [region_id] ([region_name])
Current Index: [current_value]
7-Day-Ago Index: [7d_value]
Change: [+/- delta]
Direction: [Worsening/Improving]

Duration: [minutes/hours since spike detected]

Trajectory Analysis:
- 7-day derivative: [positive/negative]
- 7-day volatility: [value] ([low/moderate/high])
- 30-day trend: [consistent with spike / contradicts spike]

Primary Drivers:
- [Sub-index that changed most]
- [Sub-index that changed second-most]

Hypothesis: [Real event / Data anomaly / Under investigation]

Dashboards:
- Trends: http://localhost:3001/d/historical-trends?var-region=[region_id]
- Risk Regimes: http://localhost:3001/d/risk-regimes
- Deep Dive: http://localhost:3001/d/subindex-deep-dive?var-region=[region_id]

Action: [Continue monitoring / Investigate further / Escalate / Dismiss as anomaly]
```

---

### 2.6. Escalation Guidelines

**Escalate when:**
- Spike magnitude > 0.5 (extremely large change)
- Spike is worsening AND behavior index now > 0.7
- Multiple regions showing simultaneous spikes
- Spike correlates with known crisis event
- Spike has persisted for > 30 minutes and shows no signs of reverting

**Do NOT escalate if:**
- Spike is improving (current < 7-day-ago) AND current index is still < 0.5
- Only one region affected, all others stable, and no real-world event correlates
- Volatility is extremely high (> 0.2), suggesting data noise

---

## 3. General Alert Response Workflow

For any alert that fires:

### Step 1: Acknowledge & Triage (0-5 minutes)
1. Open `/ops` Operator Console
2. Identify which alert fired and which region(s)
3. Open the relevant dashboard (Risk Regimes or Trends)
4. Assess severity and trajectory

### Step 2: Technical Validation (5-10 minutes)
1. Run `./ops/verify_gate_grafana.sh`
2. Confirm pipeline is healthy
3. If RED, follow `docs/RUNBOOK_DASHBOARDS.md`

### Step 3: Root Cause Analysis (10-20 minutes)
1. Use Sub-Index Deep Dive to identify drivers
2. Check Regional Comparison for systemic vs. localized
3. Check Historical Trends for context

### Step 4: Document & Communicate (20-30 minutes)
1. Fill out communication template
2. Capture screenshots of key dashboards
3. Notify appropriate channels

### Step 5: Ongoing Monitoring
1. Set a reminder to re-check in 30-60 minutes
2. If alert resolves:
   - Document resolution
   - Note any actions taken
3. If alert persists or worsens:
   - Follow escalation guidelines

---

## 4. When Alerts Fire But Dashboards Look Empty

**Symptom:** Alert notification received, but Grafana dashboards show "No data"

**Possible Causes:**
1. Pipeline failure (Prometheus not scraping)
2. Time range mismatch (alert is for current data, dashboard showing last 7 days)
3. Region variable not set correctly

**Resolution Steps:**

1. Run both gate scripts:
   ```bash
   ./ops/verify_gate_a.sh
   ./ops/verify_gate_grafana.sh
   ```

2. If **GATE A is RED:**
   - Fix app-level issues first (backend down, CORS broken)
   - Alerts may be stale or incorrect until GATE A is GREEN

3. If **GATE G is RED:**
   - Follow `docs/RUNBOOK_DASHBOARDS.md` Section 2: Pipeline Failures
   - Do not trust alert data until GATE G is GREEN

4. If **both gates are GREEN:**
   - Check Grafana time range (top-right picker)
     - For High Index alerts: Use "Last 6 hours" or "Last 24 hours"
     - For Spike alerts: Use "Last 7 days" or "Last 30 days"
   - Check region variable in dashboard
     - Click the region dropdown, select the alerted region
   - Refresh the dashboard manually (circular arrow icon)

5. If dashboards still empty after gates GREEN + time range + region correct:
   - Generate a fresh forecast for that region (see Section 2.4)
   - Wait 30s for Prometheus scrape
   - Refresh dashboard
   - If still empty, escalate to engineering with full gate outputs

---

## 5. Common False Positives

### 5.1. Alert Fires During Forecast Generation

**Scenario:** Alert fires exactly when you manually generate a forecast

**Cause:** Forecast generation temporarily updates metrics, which can cross thresholds

**Resolution:** Wait 5 minutes. If alert clears on its own, it was transient. If it persists, treat as real.

---

### 5.2. Alert Fires After Backend Restart

**Scenario:** Alert fires immediately after `docker compose restart backend`

**Cause:** Metrics are re-exported with new values after restart

**Resolution:**
1. Check if behavior index values are consistent with pre-restart
2. If values jumped unexpectedly, investigate forecasting code changes
3. If values are consistent, alert is real

---

### 5.3. Alert Fires for Historical Data

**Scenario:** Alert shows "firing" but the timestamp is > 1 hour old

**Cause:** Grafana alert evaluation lag or Prometheus scrape gaps

**Resolution:**
1. Check Prometheus targets: http://localhost:9090/targets
2. Confirm "Last Scrape" is recent (< 30s)
3. If scrape is stale, restart Prometheus: `docker compose restart prometheus`
4. If scrape is fresh, check alert evaluation interval in `rules.yml`

---

## 6. Escalation Contacts

**Primary:** [TBD - Fill in your team's Slack channel, PagerDuty, email list]

**Secondary:** [TBD - Engineering on-call]

**Escalation SLA:**
- High Behavior Index (> 0.8): Notify within 30 minutes if persists
- Behavior Index Spike (> 0.3 change): Notify within 60 minutes if persists and worsens
- Critical Regime (multiple regions): Notify immediately

---

## 7. Post-Incident Review

After an alert is resolved:

1. **Document:**
   - Alert start time and end time
   - Regions affected
   - Peak behavior index value
   - Root cause (if identified)
   - Actions taken (if any)

2. **Review:**
   - Was the alert actionable?
   - Did the runbook help?
   - Were thresholds appropriate?
   - Did we escalate correctly?

3. **Improve:**
   - Update runbook with lessons learned
   - Adjust alert thresholds if needed (via `rules.yml`)
   - Add new panels to dashboards if gaps identified

---

## Quick Reference

| Alert | Threshold | Dashboard to Check First |
|-------|-----------|--------------------------|
| High Behavior Index | > 0.8 | Risk Regimes |
| Behavior Index Spike | Δ > 0.3 (7d) | Historical Trends |

**Gate Scripts:**
- `./ops/verify_gate_a.sh` - Core app health
- `./ops/verify_gate_grafana.sh` - Metrics pipeline health

**Dashboards:**
- Risk Regimes: http://localhost:3001/d/risk-regimes
- Historical Trends: http://localhost:3001/d/historical-trends
- Sub-Index Deep Dive: http://localhost:3001/d/subindex-deep-dive
- Regional Comparison: http://localhost:3001/d/regional-comparison
- Global Behavior Index: http://localhost:3001/d/behavior-index-global

**Other Resources:**
- `docs/RUNBOOK_DASHBOARDS.md` - Dashboard troubleshooting
- `docs/OPERATOR_CONSOLE.md` - Dashboard navigation guide
- `APP_STATUS.md` - System capabilities and status
