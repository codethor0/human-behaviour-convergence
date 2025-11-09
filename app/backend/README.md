# Behaviour Convergence API (FastAPI)

Minimal backend that serves CSV-backed endpoints for quick exploration.

## Endpoints

- `GET /health` – simple liveness check
- `GET /api/forecasts` – returns data from `results/forecasts.csv` if present, else a two-row stub
- `GET /api/metrics` – returns data from `results/metrics.csv` if present, else a two-row stub

The service automatically searches for a `results/` folder by walking up from the backend package location, so it works when run from inside `app/backend` or the repo root.

### CSV Normalisation & Fallbacks

- CSV columns are normalised to the public response models. For example, `location_id` or `forecast_mean` columns are converted into `series` and `value` respectively, ensuring clients always receive consistent shapes.
- When a CSV cannot be found or parsed, the stub payloads use simple `series: "A"` / `"rmse"` style keys so the frontend and tests behave deterministically.
- The endpoints apply an in-memory cache with TTL to reduce filesystem IO. Cache keys include the request limit so different pagination windows can coexist.

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
| `CACHE_MAX_SIZE` | `100` | Maximum number of `(filename, limit)` entries to keep in the in-memory cache. |
| `CACHE_TTL_MINUTES` | `5` | Cache entry lifetime. Expired entries are lazily pruned. |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated list passed to the CORS middleware. |
| `LOG_FORMAT` | `text` | Set to `json` to emit JSON-formatted structured logs. |
| `LOG_LEVEL` | `INFO` | Standard python logging level (e.g. `DEBUG`, `WARNING`). |

You can override `RESULTS_DIR` or the cache settings at runtime (or in tests) with `monkeypatch.setattr(main, "RESULTS_DIR", Path(...))`. The shim in `app/main.py` keeps these overrides in sync with the backend implementation.

## Testing

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/test_api_backend.py
```

The test-suite exercises cache eviction, CSV parsing edge cases, and response validation; keep these green before sending a PR. Continuous integration runs `pytest` with coverage enabled.
