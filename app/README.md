# Behaviour Convergence App

This folder contains a minimal scaffold for a demo application:
- Backend: FastAPI serving CSV-backed endpoints.
- Frontend: Next.js (TypeScript) consuming those endpoints.

Both are intentionally lightweight and optional. The repo remains documentation- and diagram-first.

## Run locally (macOS zsh)

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

## Notes
- CORS is enabled on the backend for local dev.
- No CI is added yet for the app to keep the repo lean; we can wire one later.
- The diagram remains the source of truth: edit `diagram/behaviour-convergence.mmd` and let CI regenerate assets.# Behaviour Convergence Explorer

> Application workspace for turning the research repo into an interactive experience.

## Structure (planned)

```
app/
  frontend/   (Next.js - React + TypeScript)
  backend/    (FastAPI - Python)
```

## Setup

This folder currently contains planning materials only. Scaffolding will be added in milestone `app-v0.1`:

1. `frontend/` — Next.js bootstrap with pnpm.
2. `backend/` — FastAPI project with Poetry/uv.
3. Shared config (ESLint, Prettier, Makefile) at `app/` root.

Refer to [../docs/app-plan.md](../docs/app-plan.md) for detailed roadmap.
