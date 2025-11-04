# Behaviour Convergence API (FastAPI)

Minimal backend that serves CSV-backed endpoints for quick exploration.

## Endpoints

- `GET /health` – simple liveness check
- `GET /api/forecasts` – returns data from `results/forecasts.csv` if present, else stub
- `GET /api/metrics` – returns data from `results/metrics.csv` if present, else stub

The service automatically searches for a `results/` folder by walking up from the backend package location, so it works when run from inside `app/backend` or the repo root.

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