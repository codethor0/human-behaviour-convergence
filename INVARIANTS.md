# INVARIANTS
**Status:** AUTHORITATIVE
**Date:** 2025-01-XX
**Authority:** Governance Rules

---

## INVARIANT DEFINITIONS

### I1: Normalized Weight Sum

**Statement:** After normalization, all weights sum to exactly 1.0

**Formal:** `Σ(normalized_weight[i]) = 1.0` (when total_weight > 0)

**Proof:** By construction in `app/core/behavior_index.py` lines 99-119

**Test:** `tests/test_behavior_index.py::test_compute_behavior_index_weights_normalization`

**Violation Detection:** Test failure if normalization doesn't produce sum = 1.0

---

### I2: Relative Proportions Preserved

**Statement:** Normalization preserves relative proportions between weights

**Formal:** `∀ i, j: normalized_weight[i] / normalized_weight[j] = raw_weight[i] / raw_weight[j]`

**Proof:** Mathematical (division by same constant)

**Test:** None (mathematical proof sufficient)

**Violation Detection:** Would require test comparing ratios

---

### I3: Zero Weight Exclusion

**Statement:** Sub-indices with zero weight are excluded from computation

**Formal:** `If raw_weight[i] = 0, then normalized_weight[i] = 0 AND sub_index[i] excluded`

**Proof:** Code lines 83-90, 104-118, 584-597 show conditional inclusion

**Test:** `tests/test_new_indices.py::test_behavior_index_without_new_indices`

**Violation Detection:** Test failure if zero-weight sub-index included

---

### I4: Sub-Index Count Consistency

**Statement:** Number of sub-indices in code equals documented count

**Formal:** `count(code_sub_indices) = count(documented_sub_indices) = 9`

**Proof:** Manual verification (code has 9 weight parameters, docs state 9)

**Test:** CI check G2 (proposed)

**Violation Detection:** CI failure if counts mismatch

---

### I5: Behavior Index Range

**Statement:** behavior_index is always in range [0.0, 1.0]

**Formal:** `0.0 ≤ behavior_index ≤ 1.0` (always)

**Proof:** Code line 600: `df["behavior_index"] = behavior_index.clip(0.0, 1.0)`

**Test:** `tests/test_behavior_index.py::test_behavior_index_clipping`

**Violation Detection:** Test failure if value outside range

---

### I6: Sub-Index Range

**Statement:** All sub-indices are in range [0.0, 1.0]

**Formal:** `∀ i: 0.0 ≤ sub_index[i] ≤ 1.0`

**Proof:** Each sub-index computation includes `.clip(0.0, 1.0)` (e.g., lines 258, 303, 313)

**Test:** Multiple tests validate sub-index ranges

**Violation Detection:** Test failure if sub-index outside range

---

### I7: No Sub-Index Without Weight

**Statement:** Every sub-index used in computation has a corresponding weight > 0

**Formal:** `∀ sub_index[i] used: ∃ weight[i] > 0`

**Proof:** Conditional checks in lines 584-597

**Test:** None (structural guarantee)

**Violation Detection:** Would require static analysis

---

### I8: No Weight Without Sub-Index

**Statement:** Every weight parameter has a corresponding sub-index computation

**Formal:** `∀ weight[i]: ∃ sub_index[i] computation`

**Proof:** One-to-one mapping enforced by code structure

**Test:** None (structural guarantee)

**Violation Detection:** Would require static analysis

---

### I9: No Division by Zero

**Statement:** Normalization never divides by zero

**Formal:** `total_weight > 0` before division

**Proof:** Code line 93: `if total_weight > 0:` guard

**Test:** None (edge case)

**Violation Detection:** Would require test with total_weight = 0

---

### I10: No NaN from Normalization

**Statement:** Normalization never produces NaN (when inputs are valid)

**Formal:** `If ∀ i: isfinite(raw_weight[i]), then ∀ i: isfinite(normalized_weight[i])`

**Proof:** Conditional (requires input validation)

**Test:** None (requires input validation)

**Violation Detection:** Would require test with NaN inputs

---

### I11: GATE A — CORS Configuration (LOCKED)

**Statement:** FastAPI backend has exactly one CORS middleware block, immediately after `app = FastAPI(...)`, with dev-friendly configuration.

**Formal:**
- `count(CORSMiddleware instances) == 1`
- `CORSMiddleware.position == immediately_after_FastAPI_instantiation`
- `allow_origins == ["*"]`
- `allow_credentials == False`
- `allow_methods == ["*"]`
- `allow_headers == ["*"]`

**Proof:** By construction in `app/backend/app/main.py` lines 91-98

**Test:** Manual verification + `python3 -m compileall app/backend/app/main.py -q`

**Violation Detection:**
- Compile error if duplicate middleware
- CORS preflight failures if configuration incorrect
- `curl -is -X OPTIONS /api/forecast` should show `Access-Control-Allow-Origin: *`

**Rationale:** Enables local/Docker frontends (ports 3000, 3003, 3100) to POST JSON to `/api/forecast` without CORS failures. This is the canonical dev infrastructure invariant.

---

### I12: GATE A — Canonical Docker Dev Loop (LOCKED)

**Statement:** `ops/dev_watch_docker.sh` is the canonical Docker development loop and must remain green.

**Formal:**
- Script exists at `ops/dev_watch_docker.sh`
- Script is executable (`chmod +x`)
- Script execution sequence:
  1. `docker compose build`
  2. `docker compose up -d`
  3. Wait for `http://localhost:8100/health` (60s timeout)
  4. Wait for `http://localhost:3100/forecast` (60s timeout)
  5. Run OPTIONS CORS preflight on `/api/forecast` with `Origin: http://localhost:3100`
  6. Show `docker compose ps`
  7. Tail `docker compose logs -f backend frontend`

**Proof:** By construction in `ops/dev_watch_docker.sh`

**Test:** Manual execution: `./ops/dev_watch_docker.sh` must complete all steps without errors

**Violation Detection:**
- Script exits non-zero if any step fails
- Missing CORS headers in OPTIONS response
- Backend or frontend fails health check

**Rationale:** Provides a single, repeatable entrypoint for Docker development that verifies both service health and CORS configuration.

---

### I13: GATE A — Forecast Contract (LOCKED)

**Statement:** Core forecast API contract must remain intact across all ChangeSets.

**Formal:**
- `GET /api/forecasting/regions` → `count(regions) == 62`
- `POST /api/forecast` (valid payload) → `30 ≤ len(history) ≤ 40` AND `len(forecast) == 7`
- Required keys present: `history`, `forecast`, `risk_tier`, `sources`, `metadata`, `explanations.subindices`, `explanations.subindices_details`

**Proof:** By runtime verification in `ops/verify_subindices_global_superset.sh` and related scripts

**Test:**
- `curl -sS http://localhost:8100/api/forecasting/regions | jq 'length' == 62`
- `curl -sS -X POST http://localhost:8100/api/forecast ... | jq '.history | length, .forecast | length'`

**Violation Detection:** Script assertions fail if contract not met

**Rationale:** Ensures backward compatibility and UI reliability. Any ChangeSet that breaks this contract must be rejected.

---

## INVARIANT ENFORCEMENT

**Tested Invariants:** I1, I3, I5, I6
**CI-Enforced Invariants:** I4 (proposed)
**Structurally Guaranteed:** I7, I8
**Edge Cases:** I9, I10 (require additional tests)
**GATE A (Infrastructure) — LOCKED:** I11, I12, I13

**Status:**
- **Behavior Index Invariants:** Partial enforcement — critical invariants tested, consistency invariants require CI
- **GATE A (Infrastructure):** ✅ GREEN — CORS normalized, dev loop verified, forecast contract preserved

## GATE A STATUS (2025-01-XX)

**Current State:** ✅ LOCKED

**Last Verified:** 2025-01-XX

**Verification Commands:**
```bash
# Backend CORS check
python3 -m compileall app/backend/app/main.py -q

# Dev loop verification
./ops/dev_watch_docker.sh

# Forecast contract check
curl -sS http://localhost:8100/api/forecasting/regions | jq 'length'  # Must be 62
curl -sS -X POST http://localhost:8100/api/forecast ... | jq '.history | length, .forecast | length'
```

**Locked Configuration:**
- CORS: Single middleware block at `app/backend/app/main.py` lines 91-98
- Dev Loop: `ops/dev_watch_docker.sh` (canonical entrypoint)
- Forecast Contract: 62 regions, history in [30,40], forecast=7

**Do NOT modify without:**
1. Explicit justification
2. Full regression testing
3. Update to this INVARIANTS.md document

---

### I14: GATE G — Grafana Provisioning (LOCKED)

**Statement:** Grafana dashboards are auto-provisioned from the filesystem and must remain accessible and functional.

**Formal:**
- Datasource provisioning file exists: `infrastructure/grafana/provisioning/datasources/prometheus.yml`
  - Points to `http://prometheus:9090`
  - Set as default datasource
  - Type: `prometheus`, Access: `proxy`
- Dashboard provisioning file exists: `infrastructure/grafana/provisioning/dashboards/dashboards.yml`
  - Provider name: "Behavior Forecast Dashboards"
  - Path: `/var/lib/grafana/dashboards`
- Docker volume mounts in `docker-compose.yml`:
  - `./infrastructure/grafana/provisioning/datasources:/etc/grafana/provisioning/datasources`
  - `./infrastructure/grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards`
  - `./infrastructure/grafana/dashboards:/var/lib/grafana/dashboards`
- Dashboard JSON files exist:
  - `infrastructure/grafana/dashboards/global_behavior_index.json` (UID: `behavior-index-global`)
  - `infrastructure/grafana/dashboards/subindex_deep_dive.json` (UID: `subindex-deep-dive`)

**Proof:** By construction in Docker Compose configuration and file presence

**Test:** `ops/verify_gate_grafana.sh` checks:
- Grafana health: `GET http://localhost:3001/api/health` → `{"database": "ok"}`
- Dashboard files exist on filesystem
- Prometheus datasource configured and healthy

**Violation Detection:**
- Grafana health check fails
- Dashboard files missing
- Datasource misconfigured (dashboards show "No data")

**Rationale:** Ensures Grafana dashboards are reliably provisioned and accessible for embedded analytics in frontend pages.

---

### I15: Frontend Grafana Embedding Pattern (LOCKED)

**Statement:** Frontend pages embed Grafana dashboards via iframes following a standard pattern.

**Formal:**
- Environment variable `NEXT_PUBLIC_GRAFANA_URL` defined (default: `http://localhost:3001`)
- Each frontend page (`/forecast`, `/playground`, `/live`) embeds at least one Grafana dashboard
- Embedding pattern:
  - Base URL: `${NEXT_PUBLIC_GRAFANA_URL}/d/${dashboardUid}`
  - Query parameters: `?orgId=1&theme=light&kiosk=tv&var-region=${regionId}`
  - Iframe: `width: 100%`, `height: 600px`, `border: none`
- Region selection updates dashboard via `var-region` parameter
- Frontend preserves:
  - Region loading (62 regions from `/api/forecasting/regions`)
  - Forecast API calls (for metrics generation)
  - Error handling via centralized API helper

**Proof:** By construction in `app/frontend/src/pages/forecast.tsx`, `playground.tsx`, `live.tsx`

**Test:** Manual verification:
- `npm run build` succeeds
- Pages load at `http://localhost:3100/forecast`, `/playground`, `/live`
- Grafana iframes render and show data
- Region selection updates dashboard dynamically

**Violation Detection:**
- Frontend build fails
- Pages return 404 or 500
- Grafana iframes show blank or error
- Region parameter not updating dashboards

**Rationale:** Standardizes Grafana embedding across all frontend pages, ensuring consistent analytics UX and maintainability.

---

## GATE G STATUS (2026-01-19)

**Current State:** ✅ LOCKED

**Last Verified:** 2026-01-19

**Verification Commands:**
```bash
# Run comprehensive GATE G verification
./ops/verify_gate_grafana.sh

# Manual checks
curl -sS http://localhost:8100/metrics | grep behavior_index
curl -sS http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job | contains("backend"))'
curl -sS http://localhost:3001/api/health | jq '.database'
```

**Locked Configuration:**
- Grafana Provisioning: `infrastructure/grafana/` directory structure (I14)
- Frontend Embedding: Iframe pattern in all 3 pages (I15)
- Metrics Export: Backend exposes Prometheus-format metrics at `/metrics`

**Do NOT modify without:**
1. Explicit justification
2. Full GATE G verification (`./ops/verify_gate_grafana.sh`)
3. Update to this INVARIANTS.md document

---

## BEHAVIORAL RISK REGIMES

### Risk Regime Definitions

**Purpose:** Classify regions into operational risk categories for prioritized monitoring and response.

**Regime Classification:**

| Regime | Behavior Index | 7-Day Volatility (StdDev) | Interpretation |
|--------|----------------|---------------------------|----------------|
| **Stable** | < 0.4 | < 0.05 | Low stress, low volatility - baseline conditions |
| **Elevated** | [0.4, 0.7) | < 0.1 | Moderate stress, manageable volatility - increased monitoring |
| **Unstable** | < 0.7 | ≥ 0.1 | High volatility regardless of index - rapid changes, investigate causes |
| **Critical** | ≥ 0.7 | Any | High stress - immediate investigation required |

**Implementation:**
- Pure PromQL-based classification using existing metrics
- No new backend metrics required
- Dashboard: `infrastructure/grafana/dashboards/risk_regimes.json` (UID: `risk-regimes`)

**PromQL Logic:**
```promql
# Critical: behavior_index >= 0.7
behavior_index >= 0.7

# Unstable: high volatility, not critical
behavior_index < 0.7 and stddev_over_time(behavior_index[7d]) >= 0.1

# Elevated: moderate index, low volatility
behavior_index >= 0.4 and behavior_index < 0.7 and stddev_over_time(behavior_index[7d]) < 0.1

# Stable: low index, low volatility
behavior_index < 0.4 and stddev_over_time(behavior_index[7d]) < 0.05
```

**Rationale:**
- Separates acute stress (high index) from volatility (rapid change)
- Enables prioritization: Critical > Unstable > Elevated > Stable
- Unstable regions may spike to Critical quickly
- Thresholds chosen based on historical data distribution

---

## ALERTING & THRESHOLDS

### Behavior Index Alert Semantics

**Purpose:** Provide actionable signals for behavioral stress monitoring without requiring constant dashboard observation.

**Alert Rules:**

1. **High Behavior Index Alert**
   - **Condition:** `behavior_index > 0.8` for any region
   - **Severity:** Warning
   - **Duration:** 5 minutes sustained
   - **Meaning:** Region is experiencing elevated behavioral stress
   - **Action:** Review sub-indices to identify primary stressors
   - **Annotations:**
     - Description with current value
     - Direct link to Sub-Index Deep Dive dashboard (filtered to region)
     - Runbook URL for response procedures
     - Recommended action checklist

2. **Behavior Index Spike Alert**
   - **Condition:** `abs(behavior_index - behavior_index offset 7d) > 0.3` for any region
   - **Severity:** Warning
   - **Duration:** 5 minutes sustained
   - **Meaning:** Significant change in behavioral stress over past week
   - **Action:** Investigate recent events in region
   - **Annotations:**
     - Description with change magnitude
     - Direct link to Historical Trends dashboard (filtered to region)
     - Runbook URL for response procedures
     - Recommended action checklist

**Alert Configuration:**
- Location: `infrastructure/grafana/provisioning/alerting/rules.yml`
- Notification: Rules defined without specific notification channels (policy layer only)
- Labels: Include `severity`, `component`, and `region` for filtering

**Alert Response:**
- Full runbook: `docs/runbooks/ALERT_RESPONSE.md`
- Quick reference: Annotations include dashboard links and recommended actions
- Escalation criteria documented in runbook

**Rationale:**
- Thresholds are conservative (0.8 for "high", 0.3 for "spike") to minimize false positives
- 5-minute duration prevents transient spikes from firing alerts
- Annotations provide context-aware links directly to relevant dashboards
- No automatic notifications configured in version control (site-specific policy)
- Alerts complement, not replace, dashboard-based monitoring
