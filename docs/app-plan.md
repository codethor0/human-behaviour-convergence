# Behavior Convergence Explorer — Product Plan

## Vision
Build an interactive application that provides access to public-data-driven behavioral forecasting through a clean API and web dashboard. The system ingests public signals (economic, environmental, search trends), transforms them into behavioral features, and produces forecasts using classical time-series models.

## Target Users
- **Policy analysts** evaluating socio-technical interventions.
- **Research reviewers** validating methodology and reproducibility.
- **Data science teams** investigating large-scale behavioral models.

## Goals
1. Present the architecture and maturity of each pipeline component.
2. Allow exploration of synthetic forecast results (time series, intervals, metrics).
3. Expose ethical and privacy safeguards transparently.
4. Provide clear contribution pathways and API documentation for future collaborators.

## Non-Goals (v0.1)
- Individual-level predictions or targeting capabilities.
- Proprietary or sensitive datasets.
- Production hardening for high-traffic public use.
- Real-time individual tracking or micro-targeting.

---

## Product Pillars
1. **Explainability** — interactive diagram with tooltips, maturity colouring, and code links.
2. **Exploration** — charts, filters, and downloadable synthetic results.
3. **Transparency** — embedded ethics statements, audit logs for downloads.
4. **Extensibility** — documented API endpoints, modular architecture.

---

## Architecture Overview

### Three-Layer Forecasting System

1. **Signal Layer** (`app/services/ingestion/`):
   - Public data source connectors (economic, weather, search trends)
   - Standardized time-series format
   - Error handling and caching

2. **Feature Layer** (`app/services/ingestion/processor.py`):
   - Time-series feature engineering (lags, rolling statistics, normalization)
   - Multi-source fusion and harmonization
   - Behavioral index computation

3. **Forecast Layer** (`app/core/prediction.py`):
   - Time-series forecasting models (exponential smoothing, classical methods)
   - Forecast generation with confidence intervals
   - Model metadata and quality indicators

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| UI | Next.js (React + TypeScript), Tailwind CSS | SPA with SSR, charts, Mermaid integration |
| API | FastAPI (Python 3.10+) | Serve forecasts, historical data, metadata |
| Data | Public APIs (economic, weather), CSVs in `results/` | Real-time public data + cached results |
| Forecasting | Statsmodels, Pandas | Classical time-series models |
| Infra | GitHub Actions → Vercel (frontend) + Render (API) | Automated deploy on main |

> _Rationale:_ Next.js provides a great developer experience, static export for GitHub Pages fallback, and first-class TypeScript support. FastAPI aligns with existing Python tooling and lets us reuse notebook logic for future iterations.

---

## Feature Roadmap

### Milestone 0: Scaffold (Week 1)
- [ ] Create `/app` workspace with turborepo or pnpm (frontend + backend packages).
- [ ] Next.js skeleton with landing page and global navigation.
- [ ] FastAPI skeleton with health check and `/api/results` stub.
- [ ] GitHub Action `app-test.yml` running lint/build for both packages.
- [ ] Update root README with "Application Roadmap" section.

### Milestone 1: Diagram Explorer (Week 2)
- [ ] Render Mermaid diagram via `@mermaid-js/mermaid-cli` or dynamic component.
- [ ] Attach metadata YAML describing node maturity, code links, documentation references.
- [ ] Tooltip overlay showing maturity (green/yellow/red) and link to repo assets.

### Milestone 2: Results Explorer (Week 3)
- [ ] API endpoint `GET /api/forecasts` returning synthetic data with filters (location, date range).
- [ ] Frontend charts (line + interval band) using Recharts or Visx.
- [ ] Metrics summary card pulling from `/results/metrics.csv`.
- [ ] Download buttons (CSV). Audit log stored in server logs (synthetic only).

### Milestone 3: Ethics & Transparency (Week 4)
- [ ] Render `ETHICS.md` and `SECURITY.md` as HTML pages.
- [ ] Add disclaimers to charts and downloads.
- [ ] Implement "Counterfactual mode" page describing failure scenarios.

### Milestone 4: Packaging & Release (Week 5)
- [ ] Playwright smoke tests.
- [ ] SSG export for GitHub Pages fallback.
- [ ] Deployment guides + `docs/app-usage.md`.
- [ ] Tag `app-v0.1` release and add to CHANGELOG.

---

## Technical Tasks
- Frontend state management with React Query or SWR.
- Markdown rendering pipeline with `next-mdx-remote` for docs.
- CI caching for pnpm dependencies.
- Type-safe client/server contract via `pydantic` → `zod` schemas.
- Config-driven diagram metadata: `diagram/metadata.yml`.
- Logging (structured) with Pino (frontend API calls) and Loguru (backend).

## Security & Privacy Checklist
- Synthetic data only; flagged via banners.
- Rate limiting on API (e.g., SlowAPI middleware).
- CORS restricted to trusted domains.
- Security headers via Next.js middleware & FastAPI `SecurityMiddleware`.
- Secrets stored in GitHub Actions → deployment platform secrets.

## Open Questions
- Will we provide a hosted environment beyond synthetic data? (requires legal review)
- Should the dashboard support user-uploaded edge lists? (phase 2 feature)
- How to integrate with future DVC-managed datasets? (potential data catalog)

## Next Steps
- Approve the plan and create GitHub milestone `app-v0.1`.
- Spin up branch `feat/app-scaffold` once approved.
- Coordinate with design/UX for visual system if needed.
