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

- **2026-01-12:** Forecast page regression resolved (a3b5235e225028d4e31063b9e708a9956ef6ced7). Backend, frontend, and integrity gate green; CI and E2E workflows passing on main.
