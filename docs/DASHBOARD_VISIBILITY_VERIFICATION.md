# Dashboard Visibility Verification Report

## Summary

All 23 Grafana dashboards are properly wired into the main page (`app/frontend/src/pages/index.tsx`).

## Verification Results

### Phase 1: Inventory [OK]
- **Total dashboards that exist**: 23
- **Total dashboards referenced**: 23
- **Missing dashboards**: 0
- **Status**: All dashboards are referenced

### Phase 2: Rendering Logic [OK]
- **Component**: `GrafanaDashboardEmbed` properly implemented
- **Embedding pattern**: Consistent iframe-based embedding
- **Region filtering**: Properly passed via `&var-region=` parameter
- **Error handling**: Error messages displayed when dashboards fail to load

### Phase 3: Wiring [OK]
All 23 dashboards are embedded in the main page:

1. forecast-summary (appears 2x - once in Behavior Forecast, once in Analytics section)
2. forecast-overview (appears 2x - Live Playground and Live Monitoring)
3. public-overview (Results Dashboard)
4. behavior-index-global (Behavior Index Timeline)
5. subindex-deep-dive (Sub-Index Components)
6. regional-variance-explorer (Regional Variance Explorer)
7. forecast-quality-drift (Forecast Quality and Drift Analysis)
8. algorithm-model-comparison (Algorithm / Model Performance Comparison)
9. data-sources-health (Real-Time Data Source Status)
10. source-health-freshness (Source Health and Freshness)
11. cross-domain-correlation (Cross-Domain Correlation Analysis)
12. regional-deep-dive (Regional Deep Dive Analysis)
13. regional-comparison (Regional Comparison Matrix)
14. regional-signals (Regional Signals Analysis)
15. geo-map (Geographic Map Visualization)
16. anomaly-detection-center (Anomaly Detection Center)
17. risk-regimes (Risk Regimes Analysis)
18. model-performance (Model Performance Hub)
19. historical-trends (Historical Trends Analysis)
20. contribution-breakdown (Contribution Breakdown Analysis)
21. baselines (Baseline Models Comparison)
22. classical-models (Classical Forecasting Models)
23. data-sources-health-enhanced (Data Sources Health Enhanced)

### Phase 4: Component Improvements [OK]

**Changes Made to `GrafanaDashboardEmbed.tsx`**:

1. **Always Visible**: Changed from `display: none` to `opacity: 0.3` during loading
   - Ensures iframe is always in DOM and visible
   - Prevents cases where dashboards never appear if onLoad doesn't fire

2. **Timeout Fallback**: Added 3-second timeout to show iframe even if onLoad fails
   - Prevents permanent hiding if load detection fails
   - Ensures dashboards are visible even with slow connections

3. **Better Loading Indicator**: Improved loading message positioning
   - Absolute positioning for overlay effect
   - Non-blocking pointer events

4. **Minimum Height**: Added `minHeight: 200px` to iframe
   - Prevents collapse to zero height
   - Ensures visibility even with minimal content

**Changes Made to `index.tsx`**:

1. **CSS Enforcement**: Added explicit CSS rules to prevent hiding
   - `display: block !important` for dashboard sections
   - `visibility: visible !important` for dashboard embeds
   - `opacity: 1 !important` for dashboard containers
   - `min-height: 200px !important` for iframes

### Phase 5: Layout Verification [OK]

**Section Structure**:
- All sections use `dashboard-section` className
- All sections have proper `min-height: 300px`
- Grid layouts properly configured (cols-1, cols-2)
- Responsive breakpoints configured

**Container Structure**:
- All `GrafanaDashboardEmbed` components wrapped in proper containers
- All containers have `data-testid` attributes for verification
- Proper spacing and margins applied

## Potential Issues & Solutions

### Issue 1: Grafana Not Running
**Symptom**: Dashboards show error messages
**Solution**: Ensure Grafana is running at `NEXT_PUBLIC_GRAFANA_URL` (default: http://localhost:3001)

### Issue 2: Embedding Disabled
**Symptom**: Dashboards redirect to login page
**Solution**: Set `GF_SECURITY_ALLOW_EMBEDDING=true` in Grafana config

### Issue 3: CORS Issues
**Symptom**: Iframes fail to load
**Solution**: Ensure Grafana allows embedding from frontend origin

### Issue 4: Region Variable Mismatch
**Symptom**: Dashboards load but show no data
**Solution**: Verify dashboard JSON uses `region` variable name (not `Region` or `REGION`)

## Verification Utilities

Created `app/frontend/src/utils/dashboardVerification.ts` with utilities:
- `verifyDashboardsInDOM()`: Check all dashboards in DOM
- `countRenderedDashboards()`: Count total rendered dashboards
- `isDashboardVisible(uid)`: Check specific dashboard visibility

## Next Steps for Runtime Verification

To verify dashboards are actually visible at runtime:

1. **Start the stack**:
   ```bash
   docker compose up -d --build
   ```

2. **Navigate to main page**:
   ```
   http://localhost:3100/
   ```

3. **Open browser console** and run:
   ```javascript
   // Count dashboards
   document.querySelectorAll('[data-testid^="dashboard-embed-"]').length

   // Check visibility
   document.querySelectorAll('[data-testid^="dashboard-embed-"]').forEach(el => {
     const style = window.getComputedStyle(el);
     console.log(el.getAttribute('data-testid'), {
       visible: el.offsetHeight > 0 && el.offsetWidth > 0,
       display: style.display,
       visibility: style.visibility,
       opacity: style.opacity
     });
   });
   ```

4. **Check for errors**:
   ```javascript
   document.querySelectorAll('[style*="f8d7da"]').forEach(el => {
     console.log('Error:', el.textContent);
   });
   ```

## Conclusion

[OK] **All 23 dashboards are properly wired**
[OK] **Component improvements ensure visibility**
[OK] **CSS rules prevent accidental hiding**
[OK] **Error handling provides feedback**

The main page should now display all dashboards. If dashboards are still not visible, the issue is likely:
- Grafana not running
- Embedding not enabled
- Network/CORS issues
- Grafana URL misconfiguration

All code-level wiring is complete and verified.
