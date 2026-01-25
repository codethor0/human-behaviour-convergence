# Main Page Dashboard Hub Documentation

## Overview

The main page (`app/frontend/src/pages/index.tsx`) serves as the comprehensive command center for the Human Behaviour Convergence platform. It aggregates 30+ Grafana dashboard embeds organized into 6 logical sections, providing a single source of truth for all analytics without requiring navigation.

## Architecture

### Layout Structure

The page uses a CSS Grid-based layout system with responsive breakpoints:

- **Desktop (≥1280px)**: Full grid layout (1, 2, or 4 columns as specified)
- **Tablet (768px-1279px)**: Maximum 2 columns, grids collapse appropriately
- **Mobile (<768px)**: Single column, all dashboards stack vertically

### Dashboard Sections

#### Section 1: Executive Command Center
**Purpose**: C-level summary, above the fold without scrolling

**Dashboards**:
1. Behavior Index Timeline (`behavior-index-global`) - Full width, 400px height
2. Current Behavior Index (`forecast-summary` panel 1) - Stat panel
3. Risk Tier (`forecast-summary` panel 2) - Stat panel
4. Trend Direction (`forecast-summary` panel 3) - Stat panel
5. Data Freshness (`source-health-freshness`) - Stat panel
6. Public Overview (`public-overview`) - Executive summary
7. Historical Trends (`historical-trends`) - Volatility analysis

#### Section 2: Forecast & Prediction Center
**Purpose**: Forward-looking intelligence

**Dashboards**:
1. Behavior Forecast (`forecast-summary`) - Full width, 500px height
2. Forecast Quality & Drift Analysis (`forecast-quality-drift`) - Half width
3. Algorithm Performance Comparison (`algorithm-model-comparison`) - Half width

#### Section 3: Real-Time Operations
**Purpose**: Live monitoring, auto-refreshing (30s interval)

**Dashboards**:
1. Live Monitoring (`forecast-overview`) - Full width, 400px height
2. Real-Time Data Source Status (`data-sources-health`) - Half width
3. Source Health & Freshness (`source-health-freshness`) - Half width

#### Section 4: Multi-Dimensional Analysis
**Purpose**: Deep dive into drivers and correlations

**Dashboards**:
1. Sub-Index Components (`subindex-deep-dive`) - Full width, 450px height
2. Economic Behavior Convergence (`cross-domain-correlation`) - Half width
3. Environmental Impact Analysis (`regional-deep-dive`) - Half width
4. Social Sentiment Intelligence (`regional-comparison`) - Half width
5. Mobility & Movement Patterns (`regional-variance-explorer`) - Half width
6. Contribution Breakdown (`regional-signals`) - Half width
7. Geo Map (`geo-map`) - Half width
8. Forecast Overview (`forecast-overview`) - Full width, 500px height

#### Section 5: Anomaly & Risk Detection
**Purpose**: Alerts and outliers

**Dashboards**:
1. Anomaly Detection Center (`anomaly-detection-center`) - Full width, 500px height
2. Geopolitical Risk Monitor (`risk-regimes`) - Half width
3. Cross-Domain Correlation Analysis (`cross-domain-correlation`) - Half width
4. Shock Intelligence Dashboard (`baselines`) - Half width
5. Classical Forecasting Models (`classical-models`) - Half width

#### Section 6: Data Integrity & System Health
**Purpose**: Trust and transparency, bottom of page

**Dashboards**:
1. Data Quality & Lineage (`source-health-freshness`) - Full width, 400px height
2. Prometheus System Health (`data-sources-health-enhanced`) - Half width
3. Data Pipeline Health Status (`data-sources-health`) - Half width
4. Model Performance Metrics (`model-performance`) - Full width, 400px height

## Global Region Selector

A sticky header contains a global region selector that synchronizes all dashboards:

- **Location**: Top of page, sticky positioning
- **Behavior**: When region changes, all iframes with `regionId` prop refresh to new URL
- **Implementation**: React state (`selectedRegion`) passed to all `GrafanaDashboardEmbed` components
- **Default**: Automatically selects "New York City (US)" or first available region on load

## Grafana Embed Component

### Component: `GrafanaDashboardEmbed`

**Location**: `app/frontend/src/components/GrafanaDashboardEmbed.tsx`

**Props**:
- `dashboardUid` (required): Grafana dashboard UID
- `title` (required): Display title for the dashboard
- `regionId` (optional): Region ID to filter dashboard data
- `height` (optional): Iframe height in pixels or CSS string
- `refreshInterval` (optional): Auto-refresh interval (default: "5m" for historical, "30s" for live)
- `panelId` (optional): Specific panel ID to embed (for stat panels)

**Features**:
- Automatic error handling with visual error messages
- Loading state with spinner
- Sandbox security (`allow-scripts allow-same-origin`)
- Key-based remounting on region change (forces iframe reload)
- Default heights per dashboard type
- Kiosk mode (`kiosk=tv`) for clean embedding

**URL Construction**:
```
${GRAFANA_BASE}/d/${dashboardUid}?orgId=1&theme=light&kiosk=tv&refresh=${refresh}&var-region=${regionId}&panelId=${panelId}
```

## Adding New Dashboards

### Step 1: Verify Dashboard Exists
Ensure the dashboard JSON exists in `infra/grafana/dashboards/` and has a valid `uid` field.

### Step 2: Add to Appropriate Section
Add a `GrafanaDashboardEmbed` component to the relevant section in `index.tsx`:

```tsx
<GrafanaDashboardEmbed
  dashboardUid="your-dashboard-uid"
  title="Your Dashboard Title"
  regionId={selectedRegion}
  height={400}
/>
```

### Step 3: Add Default Height (Optional)
If the dashboard needs a specific default height, add it to `DEFAULT_HEIGHTS` in `GrafanaDashboardEmbed.tsx`:

```tsx
const DEFAULT_HEIGHTS: Record<string, string> = {
  // ... existing heights
  'your-dashboard-uid': '500px',
};
```

### Step 4: Update Tests
Ensure Playwright tests still pass (they check for ≥18 iframes, so adding more is fine).

## Troubleshooting

### Dashboard Shows "Panel not found"
**Cause**: Wrong `panelId` in embed URL  
**Fix**: Query Grafana API for correct panel IDs: `GET /api/dashboards/uid/{dashboardUid}`

### Region Variable Not Applied
**Cause**: Missing `&var-region=` in URL or variable name mismatch  
**Fix**: Check dashboard JSON for exact variable name (usually `"name": "region"`). Ensure `regionId` prop is passed to component.

### Dashboard Too Tall/Cut Off
**Cause**: Fixed height too small for content  
**Fix**: Increase `height` prop by 100px increments until full dashboard visible.

### CSS Collapse (0 height)
**Cause**: Parent container has no explicit height  
**Fix**: Ensure section has `min-height: 300px` (already applied via `.dashboard-section` class).

### CORS/Embedding Blocked
**Cause**: Grafana `allow_embedding = false` or auth required  
**Fix**: Verify Grafana config:
- `GF_SECURITY_ALLOW_EMBEDDING=true`
- `GF_AUTH_ANONYMOUS_ENABLED=true`
- `GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer`

### Dashboard Appears Empty
**Possible Causes**:
1. Dashboard has no data (check Grafana directly)
2. Region filter excludes all data (try removing `regionId` prop)
3. Time range too narrow (check dashboard time picker)
4. Data source connection issue (check Grafana data sources)

**Debug Steps**:
1. Open dashboard directly in Grafana: `http://localhost:3001/d/{dashboardUid}`
2. Verify data appears
3. Check browser console for iframe errors
4. Verify network tab shows 200 status for iframe requests

## Testing

### Automated Tests
Playwright tests in `app/frontend/e2e/main-page-dashboards.spec.ts` verify:
- All 6 sections render
- 18+ iframes load
- Region selector functionality
- Responsive layout
- No console errors
- All iframe URLs return 200 OK

### Visual Verification
Run visual verification tests:
```bash
cd app/frontend
npx playwright test e2e/main-page-visual-verify.spec.ts
```

Screenshots are saved to `/tmp/hbc_mainpage_visual_verify/after/`.

### Manual Testing Checklist
- [ ] All 6 sections visible without scrolling (on 1920×1080)
- [ ] Region selector changes update all dashboards
- [ ] Mobile view (<768px) stacks to single column
- [ ] No horizontal scroll on 1366×768
- [ ] All dashboards show data (no "No data" messages)
- [ ] Live dashboards (Section 3) refresh every 30s
- [ ] No console errors

## Performance Considerations

- **Initial Load**: 30 iframes loading simultaneously may be slow. Consider lazy loading below-the-fold sections.
- **Memory**: Each iframe consumes memory. Monitor browser memory usage with many dashboards.
- **Network**: All dashboards query Grafana simultaneously. Ensure Grafana can handle concurrent requests.

## Future Enhancements

1. **Lazy Loading**: Load dashboards as user scrolls
2. **Tabbed Sections**: Use tabs/accordions for better organization
3. **Dashboard Search**: Filter/search dashboards by name
4. **Customizable Layout**: Allow users to rearrange sections
5. **Export/Share**: Generate PDF or shareable link of current view

## Related Files

- Main page: `app/frontend/src/pages/index.tsx`
- Embed component: `app/frontend/src/components/GrafanaDashboardEmbed.tsx`
- Region hook: `app/frontend/src/hooks/useRegions.ts`
- Tests: `app/frontend/e2e/main-page-dashboards.spec.ts`
- Visual tests: `app/frontend/e2e/main-page-visual-verify.spec.ts`
- Dashboard JSONs: `infra/grafana/dashboards/*.json`
