# Operator Console Guide

**Purpose:** Guide for operators using the behavioral forecasting system dashboards and monitoring tools.

**Audience:** Operations team, on-call engineers, data analysts

**Last Updated:** 2026-01-19

---

## Overview

The Operator Console (`/ops`) provides a centralized index of all monitoring dashboards, system health links, and operational documentation. All analytics are powered by Grafana, with the frontend providing controls and dashboard embedding.

**Quick Access:** http://localhost:3100/ops (local dev)

---

## Runbooks

**When things break or alerts fire, follow these runbooks:**

- **`docs/RUNBOOK_ALERTS.md`** — What to do when alerts fire
  - High Behavior Index alert (> 0.8)
  - Behavior Index Spike alert (change > 0.3 over 7 days)
  - Triage steps, technical checks, escalation guidelines

- **`docs/RUNBOOK_DASHBOARDS.md`** — What to do when dashboards show "No data" or look wrong
  - Pipeline troubleshooting (Prometheus, Grafana, backend)
  - Single region issues
  - Historical data gaps
  - Escalation package preparation

**Operational Workflow (When in doubt, follow this order):**

1. **Start at `/ops`** — Operator Console (dashboard index + quick links)
2. **Check gates** — Run `./ops/verify_gate_a.sh` and `./ops/verify_gate_grafana.sh`
3. **If RED** — Follow `docs/RUNBOOK_DASHBOARDS.md`
4. **If alert fires** — Follow `docs/RUNBOOK_ALERTS.md`
5. **If gates GREEN but something looks wrong** — See `docs/RUNBOOK_DASHBOARDS.md` Section 8

---

## Dashboard Navigation

### 1. Global Behavior Index

**UID:** `behavior-index-global`
**Purpose:** Quick health check - Is the system showing elevated stress?

**When to Use:**
- Daily check-in: "How's the system looking overall?"
- Alert investigation: "What's the current index value?"
- Executive summary: "What's the headline?"

**Key Panels:**
- Behavior Index for Minnesota (baseline region)
- Parent Sub-Indices breakdown
- Forecast generation rate
- Computation latency (p95)

**Questions It Answers:**
- Is behavioral stress elevated right now?
- Which parent sub-indices are driving the index?
- Is the forecasting system performing normally?

---

### 2. Sub-Index Deep Dive

**UID:** `subindex-deep-dive`
**Purpose:** Investigation - Which specific stress factors are elevated?

**When to Use:**
- Alert fires for a specific region
- Need to understand **what** is driving high stress
- Drilling down from Global dashboard

**Key Panels:**
- Region variable (select any of 62 regions)
- Parent variable (select specific parent index)
- Parent sub-index time series
- Child sub-index details

**Questions It Answers:**
- What's driving the behavior index for this region?
- Is it economic stress, public health, mobility, or something else?
- Which child indices (specific stressors) are elevated?
- How do sub-indices correlate?

**Navigation Tip:** Use the region dropdown to switch between regions. Use the parent dropdown to filter child indices.

---

### 3. Regional Comparison

**UID:** `regional-comparison`
**Purpose:** Pattern detection - Are multiple regions affected?

**When to Use:**
- Multiple regions showing elevated stress
- Looking for systemic vs. localized patterns
- Comparing behavior across states/cities

**Key Panels:**
- Multi-region behavior index comparison (line chart)
- Behavior index heatmap (all 62 regions)
- Current behavior index snapshot (stat panel)
- Parent sub-index comparisons by category

**Questions It Answers:**
- Is stress localized to one region or widespread?
- Which regions are tracking together?
- What's the distribution of stress across the country?
- Are coastal vs. inland regions diverging?

**Navigation Tip:** Use the regions multi-select variable to compare specific regions. The heatmap shows all regions simultaneously.

---

### 4. Historical Trends & Volatility

**UID:** `historical-trends`
**Purpose:** Trend analysis - Is this a spike or sustained shift?

**When to Use:**
- Behavior Index Spike alert fires
- Need to understand trajectory (improving vs. worsening)
- Assessing volatility and stability

**Key Panels:**
- Current vs 7-day trend (with derivative)
- Current vs 30-day trend
- 7-day rolling volatility (StdDev)
- 30-day rolling volatility
- Multi-region volatility comparison
- Trend direction indicator (stat)
- Current volatility (stat)

**Questions It Answers:**
- Is the index trending up (worsening) or down (improving)?
- How volatile is the situation? (Rapid changes vs. gradual)
- Is this a short-term spike or long-term shift?
- Which regions are most volatile right now?

**Key Metrics:**
- **7-day derivative:** Positive = increasing stress, Negative = decreasing
- **7-day StdDev:** > 0.1 = high volatility, < 0.05 = stable
- **30-day average:** Smoothed longer-term trend

---

### 5. Behavioral Risk Regimes

**UID:** `risk-regimes`
**Purpose:** Prioritization - Which regions need immediate attention?

**When to Use:**
- Daily operational triage
- Identifying regions at risk of alert
- Watching for regime transitions

**Key Panels:**
- Risk regime definitions (reference)
- Critical regions table (index ≥ 0.7)
- Unstable regions table (high volatility)
- Risk distribution pie chart
- Top 10 by volatility
- Top 10 by index
- 30-day regime history heatmap

**Regime Definitions:**
| Regime | Index | Volatility | Action |
|--------|-------|------------|--------|
| **Stable** | < 0.4 | < 0.05 | Routine monitoring |
| **Elevated** | 0.4-0.7 | < 0.1 | Increased attention |
| **Unstable** | < 0.7 | ≥ 0.1 | Investigate causes |
| **Critical** | ≥ 0.7 | Any | Immediate investigation |

**Questions It Answers:**
- Which regions are in Critical state right now?
- Which regions are Unstable (high volatility)?
- How is risk distributed across all regions?
- Are regions transitioning between regimes?

**Operational Priority:** Critical > Unstable > Elevated > Stable

---

## System Health Monitoring

### Alert List

**URL:** http://localhost:3001/alerting/list

**Purpose:** View active and resolved alerts

**When to Check:**
- Alert notification received
- Daily health check
- Post-incident review

**What to Look For:**
- Firing alerts: Requires investigation
- Pending alerts: About to fire
- Normal state: No action needed

**Alert Types:**
- **High Behavior Index:** Index > 0.8 for 5 minutes
- **Behavior Index Spike:** Change > 0.3 over 7 days

**Response:** See [Alert Response Runbook](runbooks/ALERT_RESPONSE.md)

---

### Prometheus Targets

**URL:** http://localhost:9090/targets

**Purpose:** Verify metrics scraping health

**When to Check:**
- Dashboards show "No Data"
- Metrics appear stale
- After backend deployment

**What to Look For:**
- All targets: **UP**
- Last scrape: < 1 minute ago
- Scrape duration: < 500ms

**If Target is Down:**
1. Check backend health: `curl http://localhost:8100/health`
2. Check backend logs: `docker compose logs backend | tail -50`
3. Restart backend if needed: `docker compose restart backend`

---

### Backend API Docs

**URL:** http://localhost:8100/docs

**Purpose:** Interactive FastAPI documentation

**When to Use:**
- Testing API endpoints manually
- Understanding request/response schemas
- Debugging forecast generation

**Key Endpoints:**
- `GET /health` - Backend health check
- `GET /api/forecasting/regions` - List all 62 regions
- `POST /api/forecast` - Generate forecast for a region
- `GET /api/forecasting/data-sources` - View data source status

---

## Operational Workflows

### Daily Health Check

1. Open `/ops` page
2. Click **Behavioral Risk Regimes** dashboard
3. Check:
   - Any regions in Critical table?
   - Elevated risk distribution (pie chart)
4. Click **Alert List**
5. Check for firing alerts
6. If alerts present: Follow [Alert Response Runbook](runbooks/ALERT_RESPONSE.md)

**Time Required:** 2-3 minutes

---

### Alert Investigation

When an alert fires:

1. **Identify Region + Metric:**
   - Check alert annotation for region label
   - Note current value and threshold

2. **Check Sub-Index Deep Dive:**
   - Select the region from dropdown
   - Identify which parent sub-indices are elevated
   - Review child indices for specific stressors

3. **Check Historical Trends:**
   - Select the region
   - Review 7-day derivative: Is this increasing or decreasing?
   - Check volatility: Is this a sudden spike?

4. **Check Regional Comparison:**
   - Is this affecting multiple regions?
   - Compare to nearby regions

5. **Document Findings:**
   - What caused the alert?
   - Is it legitimate or a data anomaly?
   - What action was taken?

**See:** [Alert Response Runbook](runbooks/ALERT_RESPONSE.md) for detailed procedures

---

### Multi-Region Pattern Analysis

When multiple regions show elevated stress:

1. **Regional Comparison Dashboard:**
   - Multi-select regions of interest
   - Look for correlated behavior

2. **Risk Regimes Dashboard:**
   - Check risk distribution pie chart
   - Review regime history heatmap for transitions

3. **Global Behavior Index:**
   - Review parent sub-indices
   - Identify common stressors

**Common Patterns:**
- **National event:** All regions elevated simultaneously
- **Regional event:** Geographic cluster elevated
- **Economic downturn:** Economic stress elevated nationwide
- **Weather event:** Environmental stress in specific regions

---

## Dashboard Best Practices

### Variable Usage

Most dashboards have **region variables**:
- Single-select: One region at a time (Deep Dive, Trends)
- Multi-select: Compare multiple regions (Comparison)

**Tip:** Bookmark commonly used region combinations in Grafana

---

### Time Range

Default time ranges:
- **Global Index:** 24 hours
- **Deep Dive:** 7 days
- **Trends:** 30 days
- **Risk Regimes:** 30 days

**Tip:** Use Grafana's time picker (top right) to adjust range

---

### Refresh

Dashboards auto-refresh:
- **Global Index:** 30 seconds
- **Deep Dive:** 1 minute
- **Trends:** 1 minute
- **Risk Regimes:** 1 minute

**Tip:** Click refresh icon to force immediate update

---

## Troubleshooting

### Dashboard Shows "No Data"

**Causes:**
1. Prometheus not scraping backend
2. Backend metrics not exporting
3. Query syntax error

**Fixes:**
1. Check Prometheus targets: http://localhost:9090/targets
2. Check backend /metrics: `curl http://localhost:8100/metrics | grep behavior_index`
3. Check Grafana query syntax (edit panel)

---

### Stale Data

**Symptoms:** Metrics timestamp is old

**Causes:**
1. Backend stopped generating forecasts
2. Prometheus scrape interval too long

**Fixes:**
1. Generate a forecast via `/forecast` page
2. Check Prometheus scrape config (should be 15s)
3. Restart Prometheus if needed

---

### Dashboard Not Listed

**Causes:**
1. Dashboard JSON not in `infrastructure/grafana/dashboards/`
2. Grafana provisioning not loaded

**Fixes:**
1. Check file exists: `ls infrastructure/grafana/dashboards/*.json`
2. Restart Grafana: `docker compose restart grafana`
3. Check Grafana logs: `docker compose logs grafana | grep provision`

---

## Additional Resources

- **Alert Response Runbook:** `docs/runbooks/ALERT_RESPONSE.md`
- **Application Status:** `APP_STATUS.md`
- **System Invariants:** `INVARIANTS.md`
- **Deployment Guide:** (Coming in ChangeSet 19)

---

## Quick Reference: Dashboard URLs

**Local Development:**

- Operator Console: http://localhost:3100/ops
- Global Index: http://localhost:3001/d/behavior-index-global
- Deep Dive: http://localhost:3001/d/subindex-deep-dive
- Comparison: http://localhost:3001/d/regional-comparison
- Trends: http://localhost:3001/d/historical-trends
- Risk Regimes: http://localhost:3001/d/risk-regimes
- Alerts: http://localhost:3001/alerting/list
- Prometheus: http://localhost:9090
- Backend API: http://localhost:8100/docs

**Production:** Replace `localhost` with your actual domain/IP addresses
