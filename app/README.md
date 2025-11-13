# Behavior Convergence App

This folder contains the Behavior Convergence Explorer application workspace:
- **Backend:** FastAPI serving CSV-backed endpoints (`app/backend/`)
- **Frontend:** Next.js (TypeScript) consuming those endpoints (`app/frontend/`)

Both are intentionally lightweight and optional. The repo remains documentation- and diagram-first.

## Current Structure

```
app/
  backend/          FastAPI application (Python)
  frontend/         Next.js application (TypeScript)
  main.py           Module shim for backend compatibility
  README.md         This file
```

## Run Locally

Open two terminals at the repo root.

### 1) Backend (FastAPI)
```bash
# Terminal A
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/backend/requirements.txt
python -m app.backend.app.main
# -> http://localhost:8000
```

Optional: if you have CSVs in `results/` (e.g., `results/forecasts.csv`, `results/metrics.csv`), the API will serve them. Otherwise it returns stub data.

### 2) Frontend (Next.js)
```bash
# Terminal B
cd app/frontend
npm install
npm run dev
# -> http://localhost:3000
```

The frontend expects the backend at `http://localhost:8000`. You can override with an env var:
```bash
# Terminal B
export NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000"
npm run dev
```

## Development Notes

- CORS is enabled on the backend for local dev.
- CI workflows exist for both backend and frontend (`.github/workflows/app-ci.yml`).
- The diagram remains the source of truth: edit `diagram/behaviour-convergence.mmd` and let CI regenerate assets.

## Roadmap

For detailed product plan and milestones, see [../docs/app-plan.md](../docs/app-plan.md).
