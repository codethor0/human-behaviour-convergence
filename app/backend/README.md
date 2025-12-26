# Behavior Convergence API (FastAPI)

Public-data-driven behavioral forecasting API that serves real-time
forecasts and historical data.

## Core Forecasting Endpoints

- `POST /api/forecast` – Generate behavioral forecast using public
  economic and weather data
  - Request: `{ latitude, longitude, region_name, days_back, forecast_horizon }`
  - Response: `{ history, forecast, sources, metadata }`
- `POST /api/forecasting/run` – Alias for `/api/forecast`
- `GET /api/forecasting/data-sources` – List available public data sources
- `GET /api/forecasting/models` – List available forecasting models
- `GET /api/forecasting/status` – System health and component status
- `GET /api/forecasting/history` – Historical forecasts
  - Query parameters:
    - `region_name` (optional): Filter by region name using substring match
    - `date_from` (optional): Filter by minimum timestamp (ISO format)
    - `date_to` (optional): Filter by maximum timestamp (ISO format)
    - `limit` (default: 100, max: 1000): Maximum number of records to return
    - `sort_order` (default: "DESC"): Sort order - "ASC" (oldest first) or "DESC" (newest first)
  - Returns list of historical forecast entries with metadata and accuracy scores
  - Forecasts are automatically saved to SQLite database when created via `POST /api/forecast`
  - Each entry includes: `forecast_id`, `region_name`, `forecast_date`, `forecast_horizon`, `model_type`, `sources`, and optional `accuracy_score`
  - Accessible via web UI at `/history` route with interactive filters and sorting

## Live Monitoring Endpoints

- `GET /api/live/summary` – Get live behavior index summary for specified regions
  - Query parameters:
    - `regions` (optional): List of region IDs (e.g., `regions=us_dc&regions=us_mn`)
    - `time_window_minutes` (default: 60): Time window for historical snapshots (1-1440 minutes)
  - Returns live data including:
    - Latest behavior index and sub-indices for each region
    - Historical snapshots within the time window
    - **Intelligence summary** with:
      - `risk_tier`: Risk classification (Stable, Watchlist, Elevated, High, Critical)
      - `top_contributing_indices`: Top 3 contributing indices with contribution scores
      - `shock_status`: Shock detection status (None, RecentShock, OngoingShock)
  - Accessible via web UI at `/live` route with Intelligence Summary panel

- `POST /api/live/refresh` – Manually trigger refresh of live data for specified regions
  - Query parameters:
    - `regions` (optional): List of region IDs to refresh (if not provided, refreshes all regions)
  - Returns refresh results with success status per region

## Data Endpoints

- `GET /health` – Simple liveness check
- `GET /api/forecasts` – Returns data from `results/forecasts.csv`
  if present, else a stub
- `GET /api/metrics` – Returns data from `results/metrics.csv` if present, else a stub
- `GET /api/status` – Service metadata (version, commit)
- `GET /api/cache/status` – Cache statistics (hits, misses, size)

The service automatically searches for a `results/` folder by walking up
from the backend package location, so it works when run from inside
`app/backend` or the repo root.

### CSV Normalisation & Fallbacks

- CSV columns are normalised to the public response models. For example,
  `location_id` or `forecast_mean` columns are converted into `series` and
  `value` respectively, ensuring clients always receive consistent shapes.
- When a CSV cannot be found or parsed, the stub payloads use simple
  `series: "A"` / `"rmse"` style keys so the frontend and tests behave
  deterministically.
- The endpoints apply an in-memory cache with TTL to reduce filesystem IO.
  Cache keys include the request limit so different pagination windows can
  coexist.

## Quickstart (macOS zsh)

```bash
# From repo root
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/backend/requirements.txt

# Run dev server with autoreload
python -m app.backend.app.main
# Server runs on http://localhost:8000
```

Optional: run via uvicorn explicitly
```bash
uvicorn app.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_MAX_SIZE` | `100` | Maximum number of `(filename, limit)` entries
  to keep in the in-memory cache. |
| `CACHE_TTL_MINUTES` | `5` | Cache entry lifetime. Expired entries are lazily pruned. |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` |
  Comma-separated list passed to the CORS middleware. |
| `LOG_FORMAT` | `text` | Set to `json` to emit JSON-formatted structured logs. |
| `LOG_LEVEL` | `INFO` | Standard python logging level (e.g. `DEBUG`, `WARNING`). |

You can override `RESULTS_DIR` or the cache settings at runtime (or in tests)
with `monkeypatch.setattr(main, "RESULTS_DIR", Path(...))`. The shim in
`app/main.py` keeps these overrides in sync with the backend implementation.

## Testing

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/test_api_backend.py
```

The test-suite exercises cache eviction, CSV parsing edge cases, and response
validation; keep these green before sending a PR. Continuous integration runs
`pytest` with coverage enabled.

## Docker E2E Smoke Tests

The repository includes a Docker Compose setup for running the full stack in containers
and validating it with Playwright E2E tests.

**Quick start:**
```bash
# Build and start services
docker compose up -d --build

# Wait for healthchecks (or verify manually)
curl -f http://localhost:8100/health  # Backend
curl -f http://localhost:3100/        # Frontend

# Run E2E smoke tests
cd app/frontend
PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/forecast.smoke.spec.ts e2e/history.smoke.spec.ts

# Cleanup
docker compose down -v
```

**Configuration:**
- Backend container: Port 8000 (exposed as 8100 on host)
- Frontend container: Port 3000 (exposed as 3100 on host)
- Frontend API base: `http://backend:8000` (internal Docker network)
- Healthchecks: Backend `/health`, Frontend `/` (root page)

The CI workflow includes a `docker-e2e` job that automatically validates the Docker stack
on every push and pull request.
