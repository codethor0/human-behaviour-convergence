# Grafana Migration Status

## Current State (2026-01-19)

### Overview
The Human Behaviour Convergence application has successfully integrated Grafana as the primary visualization layer. Grafana dashboards are now provisioned, accessible, and embedded in the Next.js frontend.

### Architecture

**Data Flow:**
```
Backend API (FastAPI)
  → Exports /metrics endpoint (Prometheus format)
  → Prometheus scrapes backend:8000/metrics
  → Grafana queries Prometheus datasource
  → Dashboards visualize behavior_index and sub-indices
  → Frontend embeds Grafana dashboards via iframes
```

**Services:**
- **Backend:** FastAPI at http://localhost:8100 (exposed as :8000 in Docker)
- **Prometheus:** http://localhost:9090 (scrapes backend metrics)
- **Grafana:** http://localhost:3001 (serves dashboards)
- **Frontend:** Next.js at http://localhost:3100

### Grafana Dashboards

Five operational dashboards provisioned from `infra/grafana/dashboards/`:

1. **Global Behavior Index** (behavior-index-global)
   - Primary behavior index visualization
   - Time series plots with regional filtering

2. **Sub-Index Deep Dive** (subindex-deep-dive)
   - Detailed sub-index breakdowns
   - Economic, environmental, mobility, digital attention metrics

3. **Historical Trends & Volatility** (historical-trends)
   - Long-term trend analysis
   - Volatility and derivative metrics

4. **Regional Comparison** (regional-comparison)
   - Side-by-side regional comparisons
   - Heatmaps and correlation analysis

5. **Behavioral Risk Regimes** (risk-regimes)
   - Risk tier classification
   - Alert thresholds and regime transitions

### Access Points

**Direct Grafana Access:**
- URL: http://localhost:3001
- Credentials: admin / admin (default, change in production)
- Datasource: Prometheus (pre-configured)

**Frontend Integration:**
- Forecast page: http://localhost:3100/forecast
- Dashboards embedded via iframes with region variables
- Query parameters: `?orgId=1&theme=light&kiosk=tv&var-region=<region_id>`

### Technical Details

**Iframe Embedding:**
- Enabled via `GF_SECURITY_ALLOW_EMBEDDING=true` in docker-compose.yml
- Frontend sets iframe `src` dynamically based on selected region
- No X-Frame-Options blocking

**Dashboard Provisioning:**
- Provisioning config: `infra/grafana/provisioning/dashboards/dashboards.yml`
- Dashboard files: `infra/grafana/dashboards/*.json`
- Auto-loaded on Grafana startup
- Editable in UI (changes not persisted to files)

**Data Source:**
- Type: Prometheus
- URL: http://prometheus:9090 (internal Docker network)
- Provisioning: `infra/grafana/provisioning/datasources/prometheus.yml`

### Known Limitations

1. **Dashboard Variables:**
   - Some dashboards may show variable validation warnings on initial load
   - Warnings do not prevent visualization (cosmetic issue)

2. **Frontend Deprecation Path:**
   - Current Next.js frontend still includes custom charts
   - Long-term goal: Grafana-only UI
   - See FRONTEND_DEPRECATION_PLAN.md for migration strategy

3. **No Data Scenarios:**
   - Fresh Grafana installations show empty dashboards until backend metrics populate
   - Prometheus requires 1-2 scrape intervals (30-60s) to show data

### Verification Commands

**Check Grafana dashboards:**
```bash
curl -u "admin:admin" "http://localhost:3001/api/search?type=dash-db" | jq '.[] | .title'
```

**Check Prometheus scraping:**
```bash
curl "http://localhost:9090/api/v1/targets" | jq '.data.activeTargets[] | select(.labels.job=="backend") | .health'
```

**Query behavior metrics:**
```bash
curl "http://localhost:9090/api/v1/query?query=behavior_index" | jq '.data.result | length'
```

**Test Grafana datasource:**
```bash
curl -u "admin:admin" "http://localhost:3001/api/datasources/proxy/1/api/v1/query?query=behavior_index" | jq '.data.result | length'
```

### Troubleshooting

**Dashboards not appearing:**
- Check Grafana logs: `docker logs human-behaviour-grafana | grep -i provision`
- Verify dashboard JSON is valid: `jq empty infra/grafana/dashboards/*.json`
- Ensure title field at root level (not nested under "dashboard")

**Iframes show "Refused to display":**
- Verify `GF_SECURITY_ALLOW_EMBEDDING=true` in container: `docker inspect human-behaviour-grafana | grep EMBEDDING`
- Restart Grafana after docker-compose.yml changes: `docker compose restart grafana`

**No data in panels:**
- Verify Prometheus target health: `curl http://localhost:9090/api/v1/targets`
- Check backend metrics endpoint: `curl http://localhost:8100/metrics | grep behavior_index`
- Wait 30-60s for Prometheus to scrape

### Future Work

See `docs/FRONTEND_DEPRECATION_PLAN.md` for planned migration to Grafana-only UI.

### Related Documentation

- `APP_STATUS.md` - Overall application status
- `docs/ENVIRONMENT_VARIABLES.md` - Configuration reference
- `infra/grafana/` - Grafana provisioning configs
- `ops/verify_gate_grafana.sh` - Automated Grafana health check
