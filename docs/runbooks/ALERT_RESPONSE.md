# Alert Response Runbook

## Purpose

This runbook provides operational procedures for responding to alerts raised by the Human Behavior Convergence forecasting system.

## Alert Severity Levels

- **P0 (Critical)**: System-wide failure, data corruption, or security breach
- **P1 (High)**: Regional forecast failure, data source outage, or significant metric degradation
- **P2 (Medium)**: Individual region issues, transient errors, or minor quality degradation
- **P3 (Low)**: Performance warnings, approaching thresholds, or informational alerts

## General Response Workflow

1. **Acknowledge**: Confirm receipt of alert via monitoring system
2. **Assess**: Determine severity, scope, and impact
3. **Investigate**: Use diagnostic tools and dashboards to identify root cause
4. **Mitigate**: Apply immediate fixes or workarounds
5. **Resolve**: Implement permanent fix and verify resolution
6. **Document**: Update incident log and runbook if needed

## Common Alert Types

### Data Source Outage

**Symptoms:**
- `data_source_status{source="X"}` drops to 0
- Forecast quality degrades for affected regions
- Missing metrics for specific sub-indices

**Response:**
1. Check Grafana "Data Sources Health" dashboard
2. Verify external API status (FRED, Open-Meteo, USGS, etc.)
3. Review backend logs for API errors
4. If temporary: Wait for automatic retry
5. If persistent: Enable fallback data mode or disable affected source

### Forecast Generation Failure

**Symptoms:**
- `forecasts_generated_total{status="error"}` increases
- Regions return 500 errors from `/api/forecast`
- Missing forecast history or prediction arrays

**Response:**
1. Check `/health` endpoint status
2. Review backend logs for exceptions
3. Verify Prometheus metrics are being scraped
4. Test forecast generation manually via curl
5. Restart backend service if needed

### Metrics Export Failure

**Symptoms:**
- Prometheus target shows "down"
- Grafana panels show "No data"
- `/metrics` endpoint errors or timeouts

**Response:**
1. Verify Prometheus scrape configuration
2. Check `/metrics` endpoint accessibility
3. Review backend metrics export code for errors
4. Restart Prometheus if scrape config changed
5. Verify network connectivity between services

### High Behavior Index Alert

**Symptoms:**
- `behavior_index{region="X"} >= 0.7`
- Risk tier elevated to "high" or "critical"
- Multiple sub-indices showing stress signals

**Response:**
1. Open "Sub-Index Deep Dive" dashboard for affected region
2. Identify which sub-indices are elevated
3. Check contributing data sources for anomalies
4. Verify with external sources (news, social media, etc.)
5. If legitimate: Notify stakeholders
6. If false positive: Investigate data quality issues

## Diagnostic Tools

- **Grafana Dashboards**: http://localhost:3001
  - Behavior Index Global
  - Sub-Index Deep Dive
  - Data Sources Health
  - Forecast Summary
- **Prometheus**: http://localhost:9090
  - Query metrics directly
  - Check scrape targets
- **Backend Logs**: `docker logs <backend-container>`
- **Health Endpoint**: `curl http://localhost:8100/health`
- **Metrics Endpoint**: `curl http://localhost:8100/metrics`

## Escalation Paths

1. **On-call engineer** (first responder): Assess and mitigate
2. **Backend team**: For API, data ingestion, or forecasting logic issues
3. **Infrastructure team**: For Docker, networking, or deployment issues
4. **Data science team**: For model accuracy or sub-index weighting issues

## Post-Incident

1. Document incident in tracking system
2. Update affected region forecasts if needed
3. Review alert thresholds if false positive
4. Add lessons learned to this runbook
5. Schedule post-mortem if P0/P1 incident

## Related Documentation

- [Operator Console](../OPERATOR_CONSOLE.md)
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)
- [Testing Guide](../../TESTING_GUIDE.md)
