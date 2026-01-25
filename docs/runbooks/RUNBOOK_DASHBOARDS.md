# Dashboard & Metrics Troubleshooting Runbook

**Purpose:** Guide for troubleshooting "No data" and pipeline issues in Grafana

**Last Updated:** 2026-01-19

---

## Overview

This runbook explains what to do when:
- Grafana panels show "No data"
- Risk regime heatmaps are blank
- Historical trend panels seem flat or stale
- Metrics appear incorrect or inconsistent

Use this when GATE A or GATE G is RED, or when dashboards look wrong even when alerts are quiet.

---

## 1. Quick Triage Checklist

### Step 1: Run Gate Scripts

```bash
cd /Users/thor/Projects/human-behaviour-convergence
./ops/verify_gate_a.sh
./ops/verify_gate_grafana.sh
```

### Step 2: Note Any RED Sections

Look for:
- `[FAIL]` messages in gate script output
- RED status in final result line
- Empty results from Prometheus queries

### Step 3: Use Triage Table

| Symptom | Likely Cause | Next Step |
|---------|--------------|-----------|
| All dashboards "No data" | Backend metrics not exposed | See Section 2 |
| All Grafana panels show error | Grafana or Prometheus down | See Section 3 |
| Only one region empty | Region-specific metric gap | See Section 4 |
| Trends/volatility flat for all | Not enough historical samples | See Section 5 |
| GATE G RED, targets down | Prometheus or backend is down | See Section 2 + 3 |
| GATE A RED | Core app broken | See Section 6 |
| Both gates GREEN but dashboards wrong | Time range or query issue | See Section 7 |

---

## 2. Backend /metrics Issues

### Symptom

`ops/verify_gate_grafana.sh` reports:
- `[FAIL] Could not reach backend /metrics`
- `[FAIL] Core metrics missing in /metrics`

### Diagnosis

1. **Check if backend is running:**
   ```bash
   docker compose ps backend
   ```

2. **Check backend health:**
   ```bash
   curl -sS http://localhost:8100/health
   ```
   Expected: `{"status":"ok"}`

3. **Check /metrics endpoint:**
   ```bash
   curl -sS http://localhost:8100/metrics | head -20
   ```
   Expected: Prometheus text format with metric names

4. **Check for core metrics:**
   ```bash
   curl -sS http://localhost:8100/metrics | grep "^behavior_index"
   curl -sS http://localhost:8100/metrics | grep "^parent_subindex_value"
   curl -sS http://localhost:8100/metrics | grep "^child_subindex_value"
   ```
   Expected: Non-empty output for each

### Resolution

**If backend is not running:**
```bash
docker compose up -d backend
# Wait 10s for startup
curl -sS http://localhost:8100/health
```

**If backend is running but /health fails:**
```bash
docker compose logs backend | tail -50
```
Look for:
- Python tracebacks
- Port binding errors
- Import errors
- Configuration errors

**If /health works but /metrics is empty or missing core metrics:**
1. Check if forecasts have been generated recently:
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
2. Wait 5s, then re-check /metrics
3. If metrics still missing, restart backend:
   ```bash
   docker compose restart backend
   ```

**If problem persists after restart:**
- Check `app/backend/app/main.py` for prometheus_client integration
- Confirm metrics are defined and updated in `/api/forecast` endpoint
- Escalate to engineering with logs

---

## 3. Prometheus or Grafana Down

### Symptom

`ops/verify_gate_grafana.sh` reports:
- `[FAIL] Could not reach Prometheus targets API`
- `[FAIL] Could not reach Grafana health API`

### Diagnosis

1. **Check Docker services:**
   ```bash
   docker compose ps
   ```
   Expected: All services (backend, frontend, prometheus, grafana) show "Up"

2. **Check Prometheus:**
   ```bash
   curl -sS http://localhost:9090/-/healthy
   ```
   Expected: HTTP 200 with "Prometheus is Healthy."

3. **Check Grafana:**
   ```bash
   curl -sS http://localhost:3001/api/health | python3 -m json.tool
   ```
   Expected: `{"database": "ok", "version": "..."}`

### Resolution

**If Prometheus is down:**
```bash
docker compose restart prometheus
# Wait 10s
curl -sS http://localhost:9090/-/healthy
```

**If Grafana is down:**
```bash
docker compose restart grafana
# Wait 10-15s for startup
curl -sS http://localhost:3001/api/health
```

**If both are down or won't start:**
```bash
# Full stack restart
docker compose down
docker compose up -d
# Wait 30s for all services to start
./ops/verify_gate_a.sh
./ops/verify_gate_grafana.sh
```

**If services still won't start:**
```bash
docker compose logs prometheus | tail -100
docker compose logs grafana | tail -100
```
Look for:
- Port conflicts (already in use)
- Configuration errors
- Volume mount issues
- Network errors

---

## 4. Prometheus Not Scraping Backend

### Symptom

- Backend /metrics returns data
- Prometheus is up
- But Prometheus targets show backend as "DOWN" or "UNKNOWN"

### Diagnosis

1. **Check Prometheus targets:**
   ```bash
   curl -sS "http://localhost:9090/api/v1/targets" | python3 -m json.tool | grep -A10 backend
   ```

2. **Look for target health:**
   - `"health": "up"` - Good
   - `"health": "down"` - Problem
   - `"lastError": "..."` - Check error message

### Resolution

**If target shows "connection refused":**
- Backend may be on wrong port
- Check `infra/prometheus/prometheus.yml`:
  ```yaml
  scrape_configs:
    - job_name: 'behavior-forecasting'
      static_configs:
        - targets: ['backend:8000']  # Should be backend:8000, not 8100
  ```
- Correct target should be `backend:8000` (internal Docker network)
- External access is `localhost:8100`

**If target shows "context deadline exceeded":**
- Scrape timeout too short
- Check `scrape_interval` and `scrape_timeout` in prometheus.yml
- Increase if forecast generation takes > 10s

**If target shows "404" or "bad content-type":**
- /metrics endpoint may not exist or returns wrong format
- Verify manually:
  ```bash
  curl -sS http://localhost:8100/metrics | head -5
  ```
- Should start with `# HELP` and `# TYPE` lines

**If target is missing entirely:**
- Prometheus may not have loaded config
- Restart Prometheus:
  ```bash
  docker compose restart prometheus
  ```

---

## 5. Single Region Shows "No Data"

### Symptom

- Most regions show data in dashboards
- One specific region is empty or shows "No data"
- Both gates are GREEN

### Diagnosis

1. **Check if region exists:**
   ```bash
   curl -sS http://localhost:8100/api/forecasting/regions | \
     python3 -m json.tool | grep -i "region_id_here"
   ```

2. **Check if metrics exist for that region:**
   ```bash
   curl -sS http://localhost:8100/metrics | grep 'region="us_mn"'
   ```
   Replace `us_mn` with the region ID in question

3. **Check Grafana time range:**
   - Top-right time picker in Grafana
   - If set to "Last 6 hours" but forecast was generated > 6 hours ago, panel will be empty
   - Try "Last 24 hours" or "Last 7 days"

4. **Check region variable:**
   - Top-left region dropdown in dashboard
   - Ensure it matches the region ID exactly (case-sensitive)

### Resolution

**If region doesn't exist in /api/forecasting/regions:**
- Region may have been removed from source configuration
- Check `app/backend/app/main.py` or region configuration
- Escalate to engineering

**If metrics don't exist for that region:**
1. Generate a forecast for that region:
   ```bash
   curl -X POST http://localhost:8100/api/forecast \
     -H "Content-Type: application/json" \
     -d '{
       "region_id": "us_ny",
       "region_name": "New York (US)",
       "days_back": 30,
       "forecast_horizon": 7
     }'
   ```
2. Wait 30s for Prometheus to scrape
3. Refresh Grafana dashboard
4. Check metrics again:
   ```bash
   curl -sS http://localhost:8100/metrics | grep 'region="us_ny"'
   ```

**If time range or variable was wrong:**
- Adjust time picker or region dropdown
- Refresh dashboard
- Document the correct settings for this use case

**If metrics exist but dashboard still empty:**
- Check PromQL query in panel (Edit Panel → Query)
- Verify query syntax is correct
- Try query directly in Prometheus: http://localhost:9090/graph
- If query is broken, file bug with:
  - Dashboard name
  - Panel title
  - Query text
  - Expected vs actual result

---

## 6. Historical Panels Empty or Flat

### Symptom

- Current behavior index shows data
- But volatility, derivative, or trend panels are empty
- Or panels show flat lines at 0

### Diagnosis

1. **Check historical data availability:**
   - Volatility and trend queries need 7-30 days of data
   - If system was just started, historical data doesn't exist yet

2. **Check query time range:**
   ```bash
   # Test a 7-day volatility query in Prometheus
   curl -sG "http://localhost:9090/api/v1/query" \
     --data-urlencode 'query=stddev_over_time(behavior_index{region="us_mn"}[7d])'
   ```
   If result is empty or `"result": []`, not enough historical samples

3. **Check if metrics are being continuously exported:**
   ```bash
   # Get behavior_index metric with timestamp
   curl -sS http://localhost:8100/metrics | grep 'behavior_index{region="us_mn"}'
   ```
   Check timestamp - should be recent (< 1 hour)

### Resolution

**If system is newly started (< 7 days old):**
- Historical panels will remain empty until enough data accumulates
- Document: "Insufficient historical window - need 7-30 days"
- Set expectations: Panels will populate over time as forecasts are generated
- Consider generating forecasts daily via cron to build history faster

**If system has been running > 7 days but panels still empty:**
1. Check Prometheus retention:
   - Default is 15 days
   - Check `infra/prometheus/prometheus.yml` for `--storage.tsdb.retention.time`
   - If retention is too short, increase it

2. Check if metrics have been exported consistently:
   ```bash
   # Query Prometheus for historical data
   curl -sG "http://localhost:9090/api/v1/query_range" \
     --data-urlencode 'query=behavior_index{region="us_mn"}' \
     --data-urlencode 'start=2026-01-12T00:00:00Z' \
     --data-urlencode 'end=2026-01-19T23:59:59Z' \
     --data-urlencode 'step=1h' | python3 -m json.tool
   ```
   If gaps exist, forecasts may not have been generated daily

3. Check query syntax in panel:
   - Ensure `[7d]` or `[30d]` range selectors are used correctly
   - Ensure `stddev_over_time`, `avg_over_time`, `deriv` functions are used correctly

**If metrics are stale (> 1 hour old):**
- Backend may have stopped exporting metrics
- Restart backend:
  ```bash
  docker compose restart backend
  ```
- Generate fresh forecast to update metrics

---

## 7. GATE A Failures (Core App Issues)

### Symptom

`ops/verify_gate_a.sh` reports RED with failures like:
- `[FAIL] Backend /health did not respond`
- `[FAIL] /api/forecasting/regions: wrong count`
- `[FAIL] CORS preflight failed`
- `[FAIL] Forecast contract broken`

### Resolution

**Backend /health failure:**
- See Section 2: Backend /metrics Issues

**Regions count wrong:**
1. Check current count:
   ```bash
   curl -sS http://localhost:8100/api/forecasting/regions | \
     python3 -c "import sys,json; print(len(json.load(sys.stdin)))"
   ```
2. Expected: 62
3. If wrong:
   - Check region source configuration
   - Check for recent code changes to regions endpoint
   - Escalate to engineering

**CORS preflight failure:**
1. Check CORS config in `app/backend/app/main.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=False,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
2. If config is wrong, fix and restart backend
3. If config is correct but preflight still fails, check for duplicate middleware

**Forecast contract broken:**
1. Test forecast manually:
   ```bash
   curl -X POST http://localhost:8100/api/forecast \
     -H "Content-Type: application/json" \
     -d '{
       "region_id": "us_mn",
       "region_name": "Minnesota (US)",
       "days_back": 30,
       "forecast_horizon": 7
     }' | python3 -m json.tool > /tmp/forecast_test.json
   ```
2. Check contract:
   ```bash
   python3 << 'EOF'
   import json
   data = json.load(open("/tmp/forecast_test.json"))
   print("history length:", len(data.get("history", [])))
   print("forecast length:", len(data.get("forecast", [])))
   print("keys present:", list(data.keys()))
   EOF
   ```
3. Expected:
   - history length: 30-40
   - forecast length: 7
   - keys: history, forecast, behavior_index, risk_tier, metadata, sources, sub_indices
4. If wrong:
   - Check for recent code changes to forecasting endpoint
   - Check Pydantic schema definitions
   - Escalate to engineering with test output

---

## 8. Both Gates GREEN But Dashboards Still Wrong

### Symptom

- `./ops/verify_gate_a.sh` → GREEN
- `./ops/verify_gate_grafana.sh` → GREEN
- But Grafana dashboards show unexpected data or patterns

### Diagnosis

This is the hardest scenario because infrastructure is healthy but data looks wrong.

**Possible causes:**
1. Time range issue
2. Region variable not set
3. Query logic error
4. Data quality issue (real)
5. Forecasting model issue

### Resolution

**Step 1: Rule out time range / variable issues**
- Check Grafana time picker: Use "Last 7 days" or "Last 30 days"
- Check region variable: Select a known region like `us_mn`
- Refresh dashboard manually

**Step 2: Test queries directly in Prometheus**
1. Open Prometheus: http://localhost:9090/graph
2. Run the panel's query manually:
   ```
   behavior_index{region="us_mn"}
   ```
3. Check if results match what Grafana shows
4. If Prometheus shows different data than Grafana:
   - Grafana may be caching
   - Restart Grafana: `docker compose restart grafana`

**Step 3: Compare to raw /metrics**
```bash
curl -sS http://localhost:8100/metrics | grep 'behavior_index{region="us_mn"}'
```
- If raw metrics differ from Prometheus query results:
  - Prometheus may not have scraped recently
  - Wait 30s and re-check
- If raw metrics match Prometheus but dashboard looks wrong:
  - Panel query may have aggregation or transformation applied
  - Check panel settings (Edit Panel → Transform, Overrides)

**Step 4: Generate fresh forecast and observe**
1. Generate forecast for the suspicious region
2. Watch /metrics update in real-time:
   ```bash
   watch -n 5 'curl -sS http://localhost:8100/metrics | grep behavior_index | head -5'
   ```
3. Observe if metrics change as expected
4. If metrics look wrong at /metrics level:
   - Forecasting code may have issue
   - Escalate to engineering with:
     - Region ID
     - Expected vs actual metric values
     - Recent code changes

**Step 5: Check for known data quality issues**
- Missing data sources (check `GET /api/forecasting/data-sources`)
- Stale data sources (check `last_updated` timestamps)
- Known gaps in public data feeds
- Recent changes to data ingestion

---

## 9. Escalation Package

When you've exhausted this runbook and need to escalate:

**Include:**
1. **Gate outputs:**
   ```bash
   ./ops/verify_gate_a.sh > /tmp/gate_a_output.txt 2>&1
   ./ops/verify_gate_grafana.sh > /tmp/gate_g_output.txt 2>&1
   ```

2. **Docker status:**
   ```bash
   docker compose ps > /tmp/docker_status.txt
   docker compose logs backend | tail -200 > /tmp/backend_logs.txt
   docker compose logs prometheus | tail -100 > /tmp/prometheus_logs.txt
   docker compose logs grafana | tail -100 > /tmp/grafana_logs.txt
   ```

3. **Raw metrics sample:**
   ```bash
   curl -sS http://localhost:8100/metrics > /tmp/metrics_snapshot.txt
   ```

4. **Prometheus targets:**
   ```bash
   curl -sS "http://localhost:9090/api/v1/targets" > /tmp/prometheus_targets.json
   ```

5. **Screenshots:**
   - Dashboard showing the problem
   - Grafana panel edit view showing the query
   - Prometheus query result showing raw data

6. **Description:**
   - What you expected to see
   - What you actually see
   - When the problem started
   - What actions you've already taken
   - Which sections of this runbook you followed

---

## 10. Preventive Maintenance

To avoid dashboard issues:

**Daily:**
- Run both gate scripts as a sanity check
- Generate forecasts for key regions to keep metrics fresh

**Weekly:**
- Check Prometheus storage usage:
  ```bash
  docker exec human-behaviour-convergence-prometheus-1 du -sh /prometheus
  ```
- Rotate logs if needed
- Review alert history in Grafana

**Monthly:**
- Review Prometheus retention settings
- Check for stale data sources
- Update dependencies if security patches available

**After code changes:**
- Always run both gates before and after deployment
- Test forecast generation for multiple regions
- Refresh all dashboards to confirm data still flows

---

## Quick Reference

**Gate Scripts:**
```bash
./ops/verify_gate_a.sh      # Core app health
./ops/verify_gate_grafana.sh  # Metrics pipeline health
```

**Common URLs:**
- Backend /metrics: http://localhost:8100/metrics
- Backend /health: http://localhost:8100/health
- Prometheus: http://localhost:9090
- Prometheus targets: http://localhost:9090/targets
- Grafana: http://localhost:3001
- Grafana health: http://localhost:3001/api/health
- Operator Console: http://localhost:3100/ops

**Docker Commands:**
```bash
docker compose ps                    # Check all services
docker compose logs backend          # View backend logs
docker compose restart backend       # Restart backend
docker compose down && docker compose up -d  # Full restart
```

**Test Commands:**
```bash
# Test backend health
curl -sS http://localhost:8100/health

# Test regions endpoint
curl -sS http://localhost:8100/api/forecasting/regions | python3 -m json.tool

# Test forecast generation
curl -X POST http://localhost:8100/api/forecast \
  -H "Content-Type: application/json" \
  -d '{"region_id":"us_mn","region_name":"Minnesota (US)","days_back":30,"forecast_horizon":7}'

# Check metrics
curl -sS http://localhost:8100/metrics | grep behavior_index | head -5

# Check Prometheus scrape
curl -sS "http://localhost:9090/api/v1/targets" | python3 -m json.tool | grep -A5 backend
```

**Related Documentation:**
- `docs/RUNBOOK_ALERTS.md` - Alert response procedures
- `docs/OPERATOR_CONSOLE.md` - Dashboard navigation guide
- `INVARIANTS.md` - System invariants and expectations
- `APP_STATUS.md` - Current capabilities and status
