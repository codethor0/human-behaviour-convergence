# Main Page Dashboard Troubleshooting Guide

## Current Status

All 23 Grafana dashboards are embedded on the main page (`app/frontend/src/pages/index.tsx`) in the following order:

1. **Behavior Forecast** - `forecast-summary` dashboard
2. **Live Playground** - `forecast-overview` dashboard  
3. **Live Monitoring** - `forecast-overview` dashboard
4. **Results Dashboard** - `public-overview` dashboard
5. **Analytics Powered by Grafana** - Section with 8 primary dashboards + 13 additional dashboards
6. **Forecast Configuration** - Region selector and forecast generation controls

## If Dashboards Don't Display

### 1. Check Grafana is Running

```bash
# Check if Grafana container is running
docker ps | grep grafana

# Or check Grafana health
curl http://localhost:3001/api/health
```

Expected response: `{"commit":"...","database":"ok","version":"..."}`

### 2. Check Environment Variables

The frontend needs `NEXT_PUBLIC_GRAFANA_URL` set:

```bash
# In docker-compose.yml (already set):
NEXT_PUBLIC_GRAFANA_URL=http://localhost:3001

# For local development, create app/frontend/.env.local:
NEXT_PUBLIC_GRAFANA_URL=http://localhost:3001
```

**Important**: Next.js requires environment variables starting with `NEXT_PUBLIC_` to be available at build time. If you change them, restart the dev server.

### 3. Rebuild/Restart Frontend

```bash
cd app/frontend
npm run dev
```

Or if using Docker:
```bash
docker compose restart frontend
```

### 4. Check Browser Console

Open browser DevTools (F12) and check:
- **Console tab**: Look for errors or debug logs from `GrafanaDashboardEmbed`
- **Network tab**: Check if requests to `http://localhost:3001` are failing
- **Console logs**: In development mode, you should see logs like:
  ```
  [GrafanaDashboardEmbed] Loading dashboard: forecast-summary
  [GrafanaDashboardEmbed] Successfully loaded: forecast-summary
  ```

### 5. Verify Grafana Embedding Settings

Grafana must allow embedding. Check `docker-compose.yml`:

```yaml
environment:
  - GF_SECURITY_ALLOW_EMBEDDING=true
  - GF_AUTH_ANONYMOUS_ENABLED=true
  - GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
```

### 6. Check Prometheus Has Data

Dashboards query Prometheus. If Prometheus has no metrics, dashboards will be empty:

```bash
# Check Prometheus is running
curl http://localhost:9090/-/healthy

# Check if behavior_index metric exists
curl 'http://localhost:9090/api/v1/label/region/values'
```

### 7. Verify Region Format

Grafana dashboards expect region IDs like `city_nyc`, not full names like `New York City (US)`. The component correctly uses `regionId` from the region selector.

### 8. Hard Refresh Browser

Sometimes cached JavaScript prevents updates:
- **Mac**: Cmd + Shift + R
- **Windows/Linux**: Ctrl + Shift + R

### 9. Check iframe Loading

The `GrafanaDashboardEmbed` component shows:
- **Loading spinner**: While dashboard loads
- **Error message**: If loading fails (red box with error details)
- **Empty iframe**: If Grafana returns empty content

If you see error messages, they include specific troubleshooting steps.

## Debug Mode

The component now includes debug logging in development mode. Check browser console for:
- Dashboard UID being loaded
- Region ID being passed
- Source URL being constructed
- Success/failure messages

## Common Issues

### Issue: "Grafana requires authentication"
**Solution**: Verify `GF_AUTH_ANONYMOUS_ENABLED=true` in Grafana environment

### Issue: "Failed to load Grafana dashboard"
**Solution**: 
1. Check Grafana is running: `curl http://localhost:3001/api/health`
2. Check embedding is enabled: `GF_SECURITY_ALLOW_EMBEDDING=true`
3. Check network connectivity from browser to Grafana

### Issue: Dashboards show "No data"
**Solution**: 
1. Prometheus needs metrics - wait 5-10 minutes after stack start
2. Backend needs to be running and generating metrics
3. Check Prometheus targets: `http://localhost:9090/targets`

### Issue: Region selector shows "No regions available"
**Solution**: 
1. Backend must be running at `http://localhost:8100`
2. Check `/api/forecasting/regions` endpoint: `curl http://localhost:8100/api/forecasting/regions`

## Verification Checklist

- [ ] Grafana container is running (`docker ps`)
- [ ] Grafana health check passes (`curl http://localhost:3001/api/health`)
- [ ] Frontend container is running (`docker ps`)
- [ ] `NEXT_PUBLIC_GRAFANA_URL` is set correctly
- [ ] Browser console shows no errors
- [ ] Network tab shows successful requests to Grafana
- [ ] Prometheus is running and has metrics
- [ ] Backend is running and generating metrics
- [ ] Hard refresh browser (Cmd/Ctrl + Shift + R)

## Still Not Working?

1. Check the browser console for specific error messages
2. Check Grafana logs: `docker logs human-behaviour-grafana`
3. Check frontend logs: `docker logs <frontend-container-name>`
4. Verify all services are on the same Docker network
5. Try accessing Grafana directly: `http://localhost:3001` (should show login or dashboards)
