# Application Status

## Current Architecture: Grafana-First Analytics

**Status:** [PRODUCTION-READY]

The application has migrated to a **Grafana-first analytics model** where:
- **Primary Analytics Surface:** Grafana dashboards (embedded in frontend pages)
- **Secondary Surface:** Thin React frontend for controls and navigation
- **Data Flow:** Backend → Prometheus metrics → Grafana visualization

### Services (Docker Stack)

All services run via `docker compose` and are managed through `ops/dev_watch_docker.sh`:

1. **Backend (FastAPI)** - `http://localhost:8100`
   - Status: [OK] Running and healthy
   - Health: `GET /health` → `{"status":"ok"}`
   - Metrics: `GET /metrics` (Prometheus format)

2. **Frontend (Next.js)** - `http://localhost:3100`
   - Status: [OK] Running and healthy
   - Pages: `/forecast`, `/playground`, `/live` (all embed Grafana dashboards)

3. **Prometheus** - `http://localhost:9090`
   - Status: [OK] Running
   - Scraping: Backend metrics every 15s
   - Targets: Backend at `backend:8000/metrics`

4. **Grafana** - `http://localhost:3001`
   - Status: [OK] Running and healthy
   - Dashboards: Auto-provisioned from `infrastructure/grafana/dashboards/`
     - Global Behavior Index (UID: `behavior-index-global`)
     - Sub-Index Deep Dive (UID: `subindex-deep-dive`)
     - Regional Comparison (UID: `regional-comparison`) - Multi-region analytics
     - Historical Trends & Volatility (UID: `historical-trends`) - Trend analysis & volatility tracking
     - Behavioral Risk Regimes (UID: `risk-regimes`) - Risk classification & regime monitoring
   - Datasource: Prometheus at `http://prometheus:9090`
   - Alerts: Auto-provisioned from `infrastructure/grafana/provisioning/alerting/`

### Available Backend Endpoints

- **Health:** `GET /health`
- **Forecasting:**
  - `GET /api/forecasting/data-sources`
  - `GET /api/forecasting/models`
  - `GET /api/forecasting/regions` (62 regions)
  - `GET /api/forecasting/status`
  - `POST /api/forecast` (core forecasting endpoint)
- **Playground:**
  - `POST /api/playground/compare`
- **Live Monitoring:**
  - `GET /api/live/summary`
- **Metrics:**
  - `GET /metrics` (Prometheus exposition format)
- **API Docs:** http://localhost:8100/docs

### Frontend Pages (Grafana-Embedded)

All frontend pages embed Grafana dashboards for analytics:

1. **Operator Console** (`/ops`) - **NEW**
   - Centralized dashboard index with descriptions and direct links
   - System health quick links (Alerts, Prometheus, API docs)
   - Documentation links (Runbooks, guides)
   - Navigation to all other pages

2. **Forecast Page** (`/forecast`)
   - Region selection + forecast generation controls
   - Embedded dashboards: Global Behavior Index, Sub-Index Deep Dive
   - Minimal React state, heavy analytics via Grafana

3. **Playground Page** (`/playground`)
   - Interactive region exploration
   - Same embedded dashboards with dynamic region filtering

4. **Live Monitoring Page** (`/live`)
   - Real-time behavior monitoring
   - Auto-refresh controls (10s to 10m intervals)
   - Live dashboards with configurable refresh rates

## Test Results Summary

- All location normalization tests passed (18/18)
- Backend API responding correctly
- Health checks passing

## Recent Updates

- **2026-01-19:** **Phase 4 - ChangeSet 19: Production Config & Deployment Guide.** Comprehensive deployment documentation for local, staging, and production environments. Environment-specific CORS configuration, secrets management, high availability setup, rollback procedures, and post-deployment checklist. GATE A + GATE G GREEN.
- **2026-01-19:** **Phase 4 - ChangeSet 18: Alert Runbook + Failure Paths.** Comprehensive operational runbooks for alert response (`RUNBOOK_ALERTS.md`) and dashboard troubleshooting (`RUNBOOK_DASHBOARDS.md`). Gate scripts now reference runbooks on failure. Complete operator workflow documented. GATE A + GATE G GREEN.
- **2026-01-19:** **Phase 4 - ChangeSet 17: Operator Console & Dashboard Index.** New `/ops` page provides centralized index of all Grafana dashboards with descriptions, purposes, and direct links. Includes system health quick links and documentation references. Operator Console Guide added to docs. GATE A + GATE G GREEN.
- **2026-01-19:** **Phase 3 - ChangeSet 16: Behavioral Risk Regimes.** New risk classification system (Stable/Elevated/Unstable/Critical) with dedicated Grafana dashboard. Pure PromQL-based regimes using existing behavior_index and volatility metrics. 30-day regime history, distribution charts, and top movers. GATE A + GATE G GREEN.
- **2026-01-19:** **Phase 3 - ChangeSet 15: Alert Tuning & Runbooks.** Created comprehensive alert response runbook (`docs/runbooks/ALERT_RESPONSE.md`) with operational procedures, escalation criteria, and verification commands. Enhanced alert annotations with dashboard links, runbook URLs, and recommended actions. GATE A + GATE G GREEN.
- **2026-01-19:** **Phase 3 - ChangeSet 14: Historical Trends & Volatility.** New Grafana dashboard with rolling volatility (7d/30d standard deviation), trend derivatives, and multi-region volatility comparison. PromQL-based trend analysis without new metrics. GATE A + GATE G GREEN.
- **2026-01-19:** **Phase 3 - ChangeSet 13: Regional Comparison Dashboard.** New Grafana dashboard for multi-region analytics with behavior index comparison, heatmap, and parent sub-index comparison across selected regions. Multi-select region variable. GATE A + GATE G GREEN.
- **2026-01-19:** **Phase 2 Complete (ChangeSets 10-12).** Verification scripts hardened (validate Grafana embedding), Grafana alert rules for behavioral thresholds, CI/CD pipeline via GitHub Actions. Both gates automated and GREEN.
- **2026-01-19:** **Grafana-First Migration Complete (ChangeSets 7-8).** All three frontend pages (`/forecast`, `/playground`, `/live`) now embed Grafana dashboards. Heavy React charting logic removed. Analytics now powered by Prometheus metrics + Grafana visualizations. Both GATE A and GATE G verified GREEN.
- **2026-01-19:** **Metrics Pipeline Operational (ChangeSet 6).** Backend exports `behavior_index`, `parent_subindex_value` (9 series), `child_subindex_value` (48 series) to Prometheus. Grafana dashboards show live data. `ops/verify_gate_grafana.sh` added.
- **2026-01-19:** **Grafana Provisioning Added (ChangeSet 5).** Dashboards auto-provision from `infrastructure/grafana/dashboards/`. Datasource configured via `infrastructure/grafana/provisioning/`. Docker volumes mounted correctly.

## Current Capabilities

### Behavior Forecast System

- **Regions**: 62 regions supported (51 US states + DC + 10 global cities)
- **Behavior Index**: Composite index with 9 sub-indices:
  - Economic stress
  - Environmental stress
  - Mobility activity
  - Digital attention
  - Public health stress
  - Political stress
  - Crime stress
  - Misinformation stress
  - Social cohesion stress
- **Intelligence Layer**:
  - Risk tier classification (stable, low, elevated, high, critical)
  - Shock detection and analysis
  - Convergence analysis
  - Confidence scoring
  - Model drift detection
  - Correlation analysis
  - Scenario simulation

### Behavioral Risk Regimes

The system classifies regions into four operational risk categories:

- **Stable** (Index < 0.4, Volatility < 0.05): Baseline conditions, routine monitoring
- **Elevated** (Index 0.4-0.7, Volatility < 0.1): Moderate stress, increased attention
- **Unstable** (Index < 0.7, Volatility ≥ 0.1): High volatility, investigate causes
- **Critical** (Index ≥ 0.7): High stress, immediate investigation required

**Dashboard**: [Behavioral Risk Regimes](http://localhost:3001/d/risk-regimes) provides:
- Current risk distribution across all 62 regions
- Critical and unstable regions tables with current metrics
- 30-day regime history heatmap
- Top movers by volatility and index

### Alerting & Thresholds

- **High Behavior Index Alert**: Triggers when `behavior_index > 0.8` for any region
  - Annotations include dashboard links, runbook URL, recommended actions
  - Duration: 5 minutes sustained
- **Behavior Index Spike Alert**: Triggers when behavior index changes by >0.3 over 7 days
  - Annotations include trend analysis dashboard link
  - Duration: 5 minutes sustained
- **Configuration**: Alert rules provisioned via `infrastructure/grafana/provisioning/alerting/rules.yml`
- **Policy**: Thresholds defined as warning severity; no notification channels configured in version control
- **Monitoring**: Alerts visible in Grafana UI at `http://localhost:3001/alerting/list`

### Runbooks & Operator Workflow

**Status:** [OK] Comprehensive operational documentation

Operators have access to complete runbooks for alert response and troubleshooting:

- **`docs/OPERATOR_CONSOLE.md`** — Dashboard navigation guide
  - Overview of all 5 Grafana dashboards
  - When to use each dashboard
  - Key panels and their interpretation
  - Navigation workflows for common scenarios

- **`docs/RUNBOOK_ALERTS.md`** — Alert response procedures
  - High Behavior Index alert (> 0.8): immediate triage, root cause analysis, escalation
  - Behavior Index Spike alert (Δ > 0.3 over 7d): trend analysis, real vs. anomaly distinction
  - General alert response workflow with timing guidelines (0-5min triage, 5-10min validation, 10-20min root cause)
  - Technical pipeline sanity checks (gate verification)
  - Common false positives and post-incident review templates

- **`docs/RUNBOOK_DASHBOARDS.md`** — Dashboard & metrics troubleshooting
  - Quick triage checklist with symptom-to-resolution mapping
  - Backend /metrics issues (diagnosis and resolution)
  - Prometheus scraping failures
  - Grafana health issues
  - Single region "No data" scenarios
  - Historical data gaps (insufficient samples)
  - GATE A/G failure resolution paths
  - Escalation package preparation (what to include when escalating)

**Operator Workflow:**

1. Use `/ops` as the primary entry point (dashboard index + quick links)
2. Run both gates (`./ops/verify_gate_a.sh`, `./ops/verify_gate_grafana.sh`) before escalating
3. Follow the appropriate runbook:
   - Alert fired → `docs/RUNBOOK_ALERTS.md`
   - Dashboard looks wrong → `docs/RUNBOOK_DASHBOARDS.md`
4. Include full gate outputs and escalation package when escalating to engineering

**Gate Scripts:** Both verification scripts now reference runbooks on failure, providing immediate guidance

### Deployment & Environment Configuration

**Status:** [OK] Comprehensive deployment documentation

The system supports deployment across three environments with appropriate security configurations:

- **`docs/DEPLOYMENT_GUIDE.md`** — Complete deployment guide (900+ lines)
  - Local development deployment (Docker Compose, permissive settings)
  - Staging deployment (tighter security, real domains, secrets management)
  - Production deployment (high availability, locked-down CORS, monitoring required)
  - Environment variables reference with dev/staging/prod values
  - Security considerations (CORS, secrets, network policies)
  - Monitoring & health checks (uptime, Grafana alerts, log aggregation)
  - Rollback procedures (Docker Compose and Kubernetes)
  - Troubleshooting common deployment issues
  - Post-deployment checklist

- **`docs/ENVIRONMENT_VARIABLES.md`** — Updated with environment-specific patterns
  - `BEHAVIOR_API_CORS_ORIGINS`: Dev (`*`) vs Staging/Prod (specific domains)
  - `NEXT_PUBLIC_GRAFANA_URL`: Environment-specific URLs
  - Security notes and secrets management guidance

**Environment-Specific CORS:**
- **Development:** `allow_origins=["*"]` (permissive for fast iteration)
- **Staging/Production:** `BEHAVIOR_API_CORS_ORIGINS` environment variable with specific origins only
- Backend reads from environment and applies appropriate restrictions

**Deployment Targets:**
- Docker Compose (local, staging, single-host production)
- Kubernetes (recommended for production, includes manifests)
- Blue-green deployment support
- Automated CI/CD pipeline examples

**Security Hardening:**
- Secrets management (AWS Secrets Manager, Vault, K8s Secrets)
- SSL/TLS required for staging/production
- Network policies for inter-service communication
- Grafana auth disabled anonymous access in production
- **Runbook**: Alert response procedures documented in `docs/runbooks/ALERT_RESPONSE.md`

### Data Sources

Currently implemented connectors:
- Economic indicators (FRED)
- Environmental impact (weather, earthquakes via USGS)
- Market sentiment (VIX, SPY)
- Search trends (Wikipedia Pageviews)
- Public health (OWID, health stress indices)
- Mobility patterns
- Political stress indicators
- Crime and public safety signals
- Misinformation stress signals
- Social cohesion indicators
- GDELT events (legislative, enforcement)
- Emergency management (OpenFEMA)
- Legislative activity (OpenStates)
- Weather alerts (NWS)
- Cybersecurity (CISA KEV)

### Quality and Testing

- State lifetime tests: All 11 tests passing
- Explainability tests: Core tests passing
- Intelligence layer tests: Core tests passing
- Backend endpoints: All health, regions, data-sources endpoints responding correctly
- Frontend: Build succeeds
- Local integrity: Compileall passes, core tests green

## Roadmap - Next Features

### Additional Data Connectors (to be implemented behind configuration flags)

- FBI crime statistics (violent crime, property crime, gun-violence pressure)
- Legislative activity (bill volume, passage rates, vetoes, policy shocks)
- Enhanced public health sources (additional epidemiological indicators)
- Enhanced mobility sources (refined travel and movement patterns)

### Analytics Enhancements

- Deeper forecast quality metrics and error tracking
- More detailed convergence and explainability visualizations
- Enhanced risk tier breakdown and attribution
- Improved shock event categorization and impact analysis

### Frontend Improvements

- [COMPLETED] Migrated to Grafana-first architecture (all 3 pages embed dashboards)
- Additional specialized Grafana dashboards (regional comparisons, historical trends)
- Grafana alert rules for behavior index thresholds
- Optimized dashboard refresh strategies based on data update frequency
- Enhanced mobile responsiveness for embedded dashboards

### Operations and Infrastructure

- [COMPLETED] Gate verification scripts (`ops/verify_gate_a.sh`, `ops/verify_gate_grafana.sh`)
- [COMPLETED] CI/CD workflow (`.github/workflows/gates.yml`) runs gates on push/PR
- [COMPLETED] Grafana alert rules provisioned automatically
- Test classification: Standardize marks for core vs network-dependent tests
- Refine ops/check_integrity.sh once test marks are standardized
- Enhanced monitoring and observability for production deployments

### CI/CD Pipeline

The repository includes automated verification via GitHub Actions:

**Workflow: `gates.yml`**
- **Triggers:** Push to main/feat branches, PRs to main
- **Jobs:**
  1. **Static Checks** (runs on all PRs/pushes):
     - Python syntax check (`compileall`)
     - Core backend tests
     - Frontend lint + build
  2. **Docker Gates** (runs on push to main/feat only):
     - Full Docker stack (backend, frontend, prometheus, grafana)
     - GATE A verification (core app invariants + Grafana embedding)
     - GATE G verification (metrics pipeline + dashboards + alerts)

**Local Development:**
- Run gates locally before pushing: `./ops/verify_gate_a.sh && ./ops/verify_gate_grafana.sh`
- Both scripts must be GREEN before merging
