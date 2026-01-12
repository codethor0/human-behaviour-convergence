# Application Status

## Backend Server - RUNNING

- **Status:** Running and healthy
- **URL:** http://localhost:8000
- **Health Check:** http://localhost:8000/health
- **Status:** `{"status":"ok"}`

### Available Backend Endpoints:

- **Health:** `GET /health`
- **Forecasting:**
  - `GET /api/forecasting/data-sources`
  - `GET /api/forecasting/models`
  - `GET /api/forecasting/regions`
  - `GET /api/forecasting/status`
- **Playground:**
  - `POST /api/playground/compare`
- **Public Data:**
  - `GET /api/public/{source}/latest`
- **API Docs:** http://localhost:8000/docs

## Frontend Server - PERMISSION ISSUE

- **Status:** Cannot start due to port binding permissions
- **Error:** `EPERM: operation not permitted 0.0.0.0:3000`

### Issue:

Next.js is trying to bind to `0.0.0.0:3000` which requires elevated permissions on macOS. This might be due to:
- macOS security settings blocking network bindings
- Firewall or security software
- Another process already using the port

### Solutions to Try:

1. **Run manually in a separate terminal:**
   ```bash
   cd app/frontend
   npm run dev
   ```

2. **Use a different port:**
   ```bash
   cd app/frontend
   PORT=3001 npm run dev
   ```

3. **Check if port is already in use:**
   ```bash
   lsof -ti:3000
   ```

4. **Grant network permissions** (may require admin rights)

### Alternative: Use Backend API Directly

Since the backend is running, you can:
- Access API docs at: http://localhost:8000/docs
- Test endpoints directly with curl
- Use the API for testing location normalization

## Test Results Summary

- All location normalization tests passed (18/18)
- Backend API responding correctly
- Health checks passing

## Recent Updates

- **2026-01-12:** State lifetime semantics stabilized (61b05c7). Added reset_cache() to BehavioralForecaster, reset() to LiveMonitor, and reset_live_monitor() function. All 11 tests in test_state_lifetime.py now pass.
- **2026-01-12:** Forecast page regression resolved (770ded4). Backend, frontend, and integrity gate green; CI and E2E workflows passing on main.

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

- Richer charts and visualizations for risk and convergence
- Enhanced UX around behavior index decomposition
- Improved mobile responsiveness
- Better performance for multi-region comparisons

### Operations and Infrastructure

- Test classification: Standardize marks for core vs network-dependent tests
- Refine ops/check_integrity.sh once test marks are standardized
- Improve CI reliability for Docker-based E2E tests
- Enhanced monitoring and observability for production deployments
