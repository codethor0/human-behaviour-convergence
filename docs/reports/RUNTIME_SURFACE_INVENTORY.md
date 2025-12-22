# Runtime Surface Inventory

**Generated:** 2025-01-XX
**Purpose:** Complete enumeration of all public runtime surfaces for live validation

## FastAPI Endpoints

### Core Endpoints (app/backend/app/main.py)

| Endpoint | Method | Inputs | Outputs | Error Conditions |
|----------|--------|--------|----------|------------------|
| `/health` | GET | None | `{"status": "ok"}` | None (always succeeds) |
| `/api/forecasts` | GET | Query: `limit` (optional, int) | `ForecastResponse` with `data: List[Dict]` | Invalid limit, CSV read failure |
| `/api/metrics` | GET | None | `MetricsResponse` with `data: List[Dict]` | CSV read failure |
| `/api/status` | GET | None | `StatusResponse` with `ok`, `version`, `commit` | Environment variable read failure |
| `/api/cache/status` | GET | None | `CacheStatus` with `hits`, `misses`, `size`, `max_size`, `ttl_minutes` | None (always succeeds) |
| `/api/forecast` | POST | `ForecastRequest`: `latitude`, `longitude`, `region_name`, `days_back`, `forecast_horizon`, `region_id` (optional) | `ForecastResult` with `history`, `forecast`, `sources`, `metadata` | Invalid coordinates, invalid region_id, invalid days_back/forecast_horizon, forecast generation failure |

### Visualization Endpoints (app/backend/app/main.py)

| Endpoint | Method | Inputs | Outputs | Error Conditions |
|----------|--------|--------|----------|------------------|
| `/api/visual/heatmap` | GET | Query: `region_name` (optional), `include_forecast` (optional bool) | `HeatmapResponse` | No state data available |
| `/api/visual/trends` | GET | Query: `region_name`, `latitude`, `longitude`, `days_back` (7-365) | `TrendResponse` | No historical data available, invalid coordinates |
| `/api/visual/radar` | GET | Query: `region_name`, `latitude`, `longitude` | `RadarResponse` | No historical data available, invalid coordinates |
| `/api/visual/convergence-graph` | GET | Query: `region_name`, `latitude`, `longitude` | `ConvergenceGraphResponse` | No historical data available, invalid coordinates |
| `/api/visual/risk-gauge` | GET | Query: `region_name`, `latitude`, `longitude` | `RiskGaugeResponse` | No historical data available, invalid coordinates |
| `/api/visual/shock-timeline` | GET | Query: `region_name`, `latitude`, `longitude` | `ShockTimelineResponse` | No historical data available, invalid coordinates |
| `/api/visual/correlation-matrix` | GET | Query: `region_name`, `latitude`, `longitude` | `CorrelationMatrixResponse` | No historical data available, invalid coordinates |
| `/api/visual/state-comparison` | GET | Query: `state_a_name`, `state_a_lat`, `state_a_lon`, `state_b_name`, `state_b_lat`, `state_b_lon` | `StateComparisonResponse` | No historical data available, invalid coordinates |

### Forecasting Router (app/backend/app/routers/forecasting.py)

| Endpoint | Method | Inputs | Outputs | Error Conditions |
|----------|--------|--------|----------|------------------|
| `/api/forecasting/data-sources` | GET | None | `List[DataSourceInfo]` | None (always succeeds) |
| `/api/forecasting/regions` | GET | None | `List[RegionInfo]` | Region lookup failure |
| `/api/forecasting/models` | GET | None | `List[ModelInfo]` | None (always succeeds) |
| `/api/forecasting/status` | GET | None | `Dict[str, Any]` with system status | None (always succeeds) |
| `/api/forecasting/history` | GET | Query: `region_name` (optional), `limit` (1-1000, default 100) | `List[HistoricalForecastItem]` | Database error (returns empty list) |

### Live Router (app/backend/app/routers/live.py)

| Endpoint | Method | Inputs | Outputs | Error Conditions |
|----------|--------|--------|----------|------------------|
| `/api/live/summary` | GET | Query: `regions` (optional List[str]), `time_window_minutes` (1-1440, default 60) | `LiveSummaryResponse` | Monitor failure (500) |
| `/api/live/refresh` | POST | Query: `regions` (optional List[str]) | `Dict` with `status`, `refreshed_at`, `results` | Monitor failure (500) |

### Playground Router (app/backend/app/routers/playground.py)

| Endpoint | Method | Inputs | Outputs | Error Conditions |
|----------|--------|--------|----------|------------------|
| `/api/playground/compare` | POST | `PlaygroundCompareRequest`: `regions` (List[str], 1-10), `historical_days` (7-365), `forecast_horizon_days` (1-30), `include_explanations` (bool), `scenario` (optional) | `PlaygroundCompareResponse` | Invalid regions (400), comparison failure (500) |

### Public Router (app/backend/app/routers/public.py)

| Endpoint | Method | Inputs | Outputs | Error Conditions |
|----------|--------|--------|----------|------------------|
| `/api/public/{source}/latest` | GET | Path: `source` (wiki|osm|firms), Query: `date` (optional YYYY-MM-DD) | `PublicDataResponse` | Unknown source (400), fetch failure (500) |
| `/api/public/synthetic_score/{h3_res}/{date}` | GET | Path: `h3_res` (5-9), `date` (YYYY-MM-DD) | `SyntheticScoreResponse` | Invalid h3_res (422), invalid date format (422), computation failure (500) |
| `/api/public/stats` | GET | None | `PublicSnapshotResponse` | JSON decode error (returns error in response) |

## CLI Entry Points (hbc/cli.py)

| Command | Entry Point | Inputs | Outputs | Error Conditions |
|---------|-------------|--------|---------|------------------|
| `hbc-cli` (forecast) | `main()` → `_run_forecast()` | `--region`, `--horizon` (1-30), `--modalities` (optional), `--json` (flag) | JSON forecast payload | Invalid horizon, forecast generation failure |
| `hbc-cli sync-public-data` | `main()` → `_run_sync_public_data()` | `--date` (optional YYYY-MM-DD), `--output-dir`, `--sources` (optional), `--wiki-hours` (1-24), `--osm-max-bytes`, `--apply` (flag), `--summary` (flag) | Exit code 0/1, optional JSON summary | Invalid date format, connector failure |

## Frontend Routes (app/frontend/src/pages/)

| Route | File | Backend Calls | Error Handling |
|-------|------|---------------|----------------|
| `/` (index) | `index.tsx` | `GET /api/forecasting/history?limit=10`, `GET /api/metrics` | Catches fetch errors, displays error message |
| `/forecast` | `forecast.tsx` | `POST /api/forecast` | Catches fetch errors, displays error message |
| `/playground` | `playground.tsx` | `POST /api/playground/compare` | Catches fetch errors, displays error message |
| `/live` | `live.tsx` | `GET /api/live/summary`, `POST /api/live/refresh` | Catches fetch errors, displays error message |

## Data Ingestion Paths

| Path | Source | Destination | Error Conditions |
|------|--------|-------------|------------------|
| CSV files (`results/forecasts.csv`, `results/metrics.csv`) | File system | `/api/forecasts`, `/api/metrics` endpoints | File not found (returns stub), malformed CSV (may return 500) |
| Public data sync (`hbc-cli sync-public-data`) | External APIs (Wiki, OSM, FIRMS) | `data/public/{date}/` | API failure, network error, disk write failure |
| Database (`data/hbc.db`) | SQLite | `/api/forecasting/history` | Database locked, corruption, missing table |

## Boundary Values

### Coordinate Validation
- Latitude: -90 to 90 (inclusive)
- Longitude: -180 to 180 (inclusive)
- Invalid: Returns 400 with error message

### Forecast Parameters
- `days_back`: 1 to 365 (inclusive)
- `forecast_horizon`: 1 to 30 (inclusive)
- Invalid: Returns 400 with error message

### Region IDs
- Valid: Returns region data
- Invalid: Returns 404 with "Region not found" message

### Query Parameters
- `limit` (forecasts, history): 1 to 1000 (inclusive)
- `time_window_minutes`: 1 to 1440 (inclusive)
- `h3_res`: 5 to 9 (inclusive)
- Invalid: Returns 422 or 400 with validation error

## Error Response Patterns

| Status Code | Meaning | Example |
|-------------|---------|---------|
| 200 | Success | `{"status": "ok"}` |
| 400 | Bad Request | `{"detail": "Invalid coordinates"}` |
| 404 | Not Found | `{"detail": "Region not found: invalid_region"}` |
| 422 | Validation Error | `{"detail": "h3_res must be between 5 and 9"}` |
| 500 | Internal Server Error | `{"detail": "Forecast generation failed: ..."}` |
