# HBC Full-Stack Bug Hunt Report

Generated: 2026-01-28
Protocol: HBC Full-Stack Bug Hunt + Surgical Fix

## Phase 0 – Context and Inventory

**Services:** backend (FastAPI/uvicorn, port 8100), frontend (Next.js, 3100), prometheus (9090), grafana (3001), test (pytest).

**Critical flows:** Load Hub page; select region; embed Grafana dashboards (27 UIDs); run forecast; view anomaly/data health panels.

**Risk map (priority):** (1) Data correctness and forecasts; (2) Metrics and dashboard availability; (3) Security/secrets; (4) Performance and health checks.

---

## Bug List (Structured)

### BUG-001
- **bug_id:** BUG-001
- **severity:** P1
- **category:** static_code
- **component:** backend
- **location:** app/backend/app/main.py, startup_event / shutdown_event
- **symptom:** DeprecationWarning: on_event is deprecated, use lifespan event handlers.
- **root_cause:** FastAPI deprecated @app.on_event("startup") and @app.on_event("shutdown") in favor of lifespan context manager.
- **impact:** Warnings in logs; future FastAPI versions may remove on_event.
- **proposed_fix:** Replace on_event with lifespan in FastAPI app creation.
- **verification_steps:** Run pytest; confirm no DeprecationWarning for on_event.

### BUG-002
- **bug_id:** BUG-002
- **severity:** P2
- **category:** resilience
- **component:** backend
- **location:** app/backend/app/main.py, GET /health
- **symptom:** Health endpoint returns {"status":"ok"} without checking DB or critical dependencies.
- **root_cause:** Health is a simple liveness check only.
- **impact:** Load balancer or orchestrator may route traffic to an instance that cannot reach DB or Prometheus.
- **proposed_fix:** Optionally add readiness checks (DB ping, optional Prometheus reachability) behind a query param or separate /ready endpoint; keep /health minimal for liveness.
- **verification_steps:** When DB is down, /health still 200; document that /health is liveness-only.

### BUG-003
- **bug_id:** BUG-003
- **severity:** P2
- **category:** dashboard
- **component:** grafana
- **location:** infra/grafana/dashboards/executive_storyboard.json, panel id 3 "Global Volatility"
- **symptom:** Panel query uses $time_range. When the same expr is sent to Prometheus API without variable substitution (e.g. external test or script), Prometheus returns 400 Bad Request.
- **root_cause:** PromQL expr is stddev_over_time(behavior_index[$time_range]); $time_range is a Grafana template variable and is not valid literal in Prometheus.
- **impact:** Any automated or external query replay of this panel fails unless variables are substituted.
- **proposed_fix:** Use a concrete duration for the range so the query is valid standalone: e.g. stddev_over_time(behavior_index[7d]) to align with dashboard default (7d). Dashboard variable time_range can remain for narrative text; the stat panel will show 7d volatility.
- **verification_steps:** Run Prometheus query stddev_over_time(behavior_index[7d]); confirm 200 and non-empty result.

### BUG-004
- **bug_id:** BUG-004
- **severity:** P3
- **category:** security
- **component:** backend
- **location:** app/services/monitor.py, SOURCE_HEALTH_ENDPOINTS["fred"]
- **symptom:** URL contains api_key=test for FRED health check.
- **root_cause:** Placeholder used for connectivity check; FRED allows limited requests without key or with test key.
- **impact:** Low; "test" is not a real secret but should not be in repo as default.
- **proposed_fix:** Use env var FRED_API_KEY if set, otherwise omit api_key param (or use empty) so no literal "test" in code.
- **verification_steps:** With FRED_API_KEY unset, health check still runs; no literal api_key=test in default code path.

### BUG-005
- **bug_id:** BUG-005
- **severity:** P2
- **category:** data_integrity / dashboard
- **component:** grafana
- **location:** Multiple dashboards (data-quality-lineage, economic-behavior-convergence, regional-comparison-storyboard, shock-recovery-timeline)
- **symptom:** Panels return no data (FAIL_EMPTY) when queried with substituted $region=city_nyc and 24h range (see data coverage report).
- **root_cause:** Queries may depend on metrics not yet emitted (e.g. economic FRED series, new metric names), or different label/time range expectations.
- **impact:** Users see "No data" on those panels.
- **proposed_fix:** Per-dashboard: align panel queries with existing Prometheus metric names and labels, or add backend metrics that match panel expectations; document which panels require which data sources.
- **verification_steps:** Re-run panel query tests after metric/query alignment; confirm PASS for critical panels.

### BUG-006
- **bug_id:** BUG-006
- **severity:** P3
- **category:** config
- **component:** grafana
- **location:** docker-compose.yml, grafana service
- **symptom:** GF_SECURITY_ADMIN_PASSWORD=admin is default.
- **root_cause:** Default admin password for dev convenience.
- **impact:** In production, default password is insecure.
- **proposed_fix:** Document that production must set GF_SECURITY_ADMIN_PASSWORD via env/secret; do not change default in repo to avoid breaking dev; add deployment checklist.
- **verification_steps:** Deployment docs updated.

---

## Fix Roadmap

1. **P0:** None identified.
2. **P1:** BUG-001 (FastAPI lifespan) – apply fix.
3. **P2:** BUG-002 (health/readiness), BUG-003 (executive_storyboard Global Volatility), BUG-005 (panel data alignment) – apply BUG-003; document BUG-002 and BUG-005.
4. **P3:** BUG-004 (monitor.py api_key=test), BUG-006 (Grafana admin password) – apply BUG-004; document BUG-006.

---

## Summary

| Severity | Count |
|----------|-------|
| P0 | 0 |
| P1 | 1 |
| P2 | 4 |
| P3 | 2 |

**Total: 7 bugs.**
**By category:** static_code 1, resilience 1, dashboard 2, security 1, data_integrity 1, config 1.

**Prioritized:** Fix BUG-001 (lifespan), BUG-003 (Global Volatility panel), BUG-004 (remove api_key=test). Document BUG-002, BUG-005, BUG-006.
