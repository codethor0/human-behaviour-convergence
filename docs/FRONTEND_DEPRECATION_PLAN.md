# Frontend Deprecation Plan: Migration to Grafana-Only UI

## Executive Summary

This document outlines the strategy for deprecating the custom Next.js frontend in favor of a Grafana-first user experience. The migration will be executed in phases to minimize disruption and maintain system stability.

## Current State

**Active Routes:**
- `/` - Landing page with project overview
- `/forecast` - Forecast generation UI with Grafana dashboard embeds
- `/playground` - Live comparison tool
- `/live` - Real-time monitoring dashboard
- `/history` - Historical forecast review
- `/ops` - Operator console with system health

**Dependencies:**
- Next.js 14+ with React 18
- TypeScript frontend codebase
- Docker build via Dockerfile.frontend
- CI/E2E tests using Playwright (e2e-playwright.yml)
- Frontend lint/build checks in ci.yml

## Migration Strategy

### Phase 1: Mark Frontend as Deprecated (NON-DESTRUCTIVE)

**Goal:** Signal deprecation without breaking existing functionality.

**Actions:**
1. Add deprecation notice to `APP_STATUS.md`
2. Update README.md to point users to Grafana as primary UI
3. Add banner to frontend routes indicating Grafana is preferred
4. Create Grafana dashboard index page for easy discovery
5. Document all Grafana URLs in operator docs

**Testing:**
- All existing CI checks must pass
- Playwright tests continue to run
- No code deletion

**Timeline:** Immediate (completed as part of Grafana migration)

### Phase 2: Create Grafana Dashboard Catalog

**Goal:** Provide Grafana-native navigation and dashboard discovery.

**Actions:**
1. Create "Dashboard Home" in Grafana with:
   - Links to all 5 operational dashboards
   - Quick filters by region/time range
   - Embedded documentation
2. Configure Grafana navigation menu:
   - Pin key dashboards
   - Create folders for organization (Forecasting, Operations, Analysis)
3. Update operator console (`/ops`) to link directly to Grafana dashboards
4. Create bookmarkable Grafana URLs with pre-set variables

**Deliverables:**
- Grafana Dashboard Home JSON
- Updated provisioning configs
- Operator documentation updates

**Testing:**
- Verify all dashboard links work
- Test region variable passing
- Ensure bookmarked URLs load correctly

**Timeline:** 1-2 weeks after Phase 1

### Phase 3: Functional Parity Check

**Goal:** Ensure Grafana provides all capabilities of current frontend.

**Feature Mapping:**

| Frontend Route | Grafana Equivalent | Status | Notes |
|---------------|-------------------|--------|-------|
| `/forecast` | Global Behavior Index + Sub-Index Deep Dive | Complete | Already embedded |
| `/playground` | Regional Comparison dashboard | Complete | Side-by-side comparison |
| `/live` | Historical Trends dashboard with refresh | Complete | Auto-refresh configured |
| `/history` | Historical Trends + Risk Regimes | Complete | Full time range selection |
| `/ops` | Grafana Alerting + Prometheus targets | Partial | Need alert dashboard |

**Missing Capabilities:**
- Forecast generation trigger (POST /api/forecast)
- Quick summary cards with risk tier
- Download forecast CSV

**Solutions:**
1. **Forecast triggering:**
   - Option A: Keep minimal Next.js page just for forecast generation
   - Option B: Create Grafana plugin for forecast triggering
   - Option C: Provide CLI tool for forecast generation
   - Recommendation: Option A (minimal disruption)

2. **Quick summary:**
   - Use Grafana stat panels with threshold colors
   - Create dedicated "Quick Summary" dashboard row

3. **CSV download:**
   - Use Grafana's built-in "Export CSV" on panels
   - Add annotation with API endpoint for raw download

**Testing:**
- User acceptance testing with operators
- Feature parity checklist validation
- Performance comparison

**Timeline:** 2-3 weeks after Phase 2

### Phase 4: Gradual Frontend Reduction (REVERSIBLE)

**Goal:** Remove custom frontend code while maintaining fallback path.

**Approach:**
1. Replace `/forecast`, `/playground`, `/live`, `/history` with redirect pages
2. Redirect pages show brief message and meta-refresh to Grafana
3. Keep redirect logic in place for 2-4 weeks for monitoring
4. Preserve `/ops` route as lightweight system health check

**Modified Routes:**
```typescript
// Example: app/frontend/src/pages/forecast.tsx
export default function ForecastRedirect() {
  useEffect(() => {
    window.location.href = 'http://localhost:3001/d/behavior-index-global';
  }, []);
  
  return (
    <div>
      <p>Redirecting to Grafana dashboard...</p>
      <a href="http://localhost:3001/d/behavior-index-global">
        Click here if not redirected automatically
      </a>
    </div>
  );
}
```

**Rollback Plan:**
- Git tag before changes: `pre-frontend-deprecation`
- Keep original pages in `pages/_deprecated/`
- Simple revert if issues discovered

**Testing:**
- Verify redirects work in all environments
- Check analytics for redirect bounce rate
- Monitor user feedback

**Timeline:** 3-4 weeks after Phase 3

### Phase 5: Remove Frontend Service (DESTRUCTIVE)

**Goal:** Full removal of Next.js frontend from deployment.

**Actions:**
1. Remove `frontend` service from docker-compose.yml
2. Remove Dockerfile.frontend
3. Archive `app/frontend/` directory (keep in git history)
4. Remove Playwright E2E tests (or port to Grafana testing)
5. Remove frontend CI checks from `.github/workflows/ci.yml`
6. Update all documentation

**Modified Files:**
- `docker-compose.yml`: Remove frontend service
- `.github/workflows/ci.yml`: Remove npm build/lint
- `.github/workflows/e2e-playwright.yml`: Archive or adapt
- `README.md`: Remove frontend setup instructions
- `DEPLOYMENT.md`: Update deployment steps
- `APP_STATUS.md`: Reflect Grafana-only architecture

**New Architecture:**
```
Backend (FastAPI) ← API calls from operators/CLI
    ↓ /metrics
Prometheus ← scrapes backend
    ↓ datasource
Grafana ← primary UI
```

**Testing:**
- Full stack integration test without frontend
- Verify all ops scripts work
- Validate gates without frontend checks

**Risks:**
- Loss of custom forecast generation UI
- Learning curve for operators unfamiliar with Grafana
- Potential performance differences

**Mitigation:**
- Provide operator training on Grafana
- Create comprehensive Grafana user guide
- Maintain CLI forecast tool for automation

**Timeline:** 4-6 weeks after Phase 4 (with user feedback evaluation)

## Decision Points

### Go/No-Go Criteria for Phase 5

Before executing final frontend removal, ALL must be true:

1. Grafana dashboards have 99%+ uptime for 2+ weeks
2. Zero critical bugs in Grafana dashboard functionality
3. All operators trained and comfortable with Grafana UI
4. Alternative forecast triggering mechanism in place
5. No regression in forecast quality or frequency
6. Stakeholder sign-off obtained

### Abort Conditions

Revert to Phase 1 (frontend active) if:
- Grafana availability drops below 95% for 48 hours
- Critical data visualization bugs discovered
- Operator productivity significantly impacted
- Loss of required compliance/audit capability

## Rollback Procedures

**Phase 4 Rollback (Redirect Removal):**
```bash
git revert <redirect-commit-sha>
docker compose up -d --build frontend
```

**Phase 5 Rollback (Frontend Restoration):**
```bash
git revert <removal-commit-sha>
# Restore docker-compose.yml frontend service
docker compose up -d --build frontend
# Re-enable CI frontend checks
```

## Success Metrics

### Technical Metrics
- Grafana dashboard load time < 2s (p95)
- Zero iframe embedding errors
- 100% dashboard uptime (30-day rolling)
- Query response time < 500ms (p95)

### User Metrics
- Operator satisfaction score ≥ 4/5
- Training completion rate 100%
- Support tickets related to UI ≤ 2/week
- No critical workflow blockers

### Operational Metrics
- Reduced maintenance burden (fewer services)
- Simplified deployment (no frontend build)
- Faster CI pipeline (no npm steps)
- Lower infrastructure costs (one fewer container)

## Documentation Updates

All following docs must be updated after each phase:

- `README.md` - Setup and architecture
- `APP_STATUS.md` - Current system state
- `DEPLOYMENT.md` - Deployment procedures
- `docs/ENVIRONMENT_VARIABLES.md` - Remove NEXT_PUBLIC_* vars
- `docs/OPERATOR_GUIDE.md` - Grafana-focused operations
- `TESTING_GUIDE.md` - Remove frontend test sections

## Training Materials

Required training for operators:

1. **Grafana Basics (1 hour)**
   - Navigation and dashboard browsing
   - Time range selection
   - Variable filters (region selection)
   - Panel interactions and drill-downs

2. **Forecast Workflow (30 min)**
   - Triggering forecasts via CLI/API
   - Monitoring forecast status in dashboards
   - Interpreting behavior index panels
   - Alert threshold configuration

3. **Troubleshooting (30 min)**
   - Checking Prometheus targets
   - Dashboard "No Data" scenarios
   - Grafana datasource health
   - Log access and interpretation

## Cost-Benefit Analysis

### Benefits
- Unified visualization platform (no context switching)
- Leverage Grafana's mature ecosystem (plugins, alerting)
- Reduced codebase complexity (-5000 LOC)
- Simplified deployment architecture
- Better performance for time-series data
- Industry-standard tool (easier onboarding)

### Costs
- Migration effort (~6-10 weeks)
- Operator training (2 hours per person)
- Potential temporary productivity dip
- Loss of some custom UI features
- Dependency on Grafana stability

**Net Assessment:** Benefits significantly outweigh costs. Migration recommended.

## Conclusion

The migration to a Grafana-only UI is technically feasible and operationally beneficial. The phased approach minimizes risk while delivering incremental value. Execution should begin immediately with Phase 1 and proceed based on clearly defined success criteria.

**Recommendation:** Proceed with Phase 1-3. Evaluate Phase 4-5 after 30 days of Grafana-primary usage.

**Next Actions:**
1. Update APP_STATUS.md with deprecation notice
2. Create Grafana Dashboard Home (Phase 2 start)
3. Schedule operator training sessions
4. Set up monitoring for Grafana performance metrics
