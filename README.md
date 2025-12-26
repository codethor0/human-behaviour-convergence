# Human Behaviour Convergence
> Public-data-driven behavioral forecasting for population-scale analysis and planning.

[![CI](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/ci.yml)
[![E2E](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/e2e-playwright.yml/badge.svg?branch=main)](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/e2e-playwright.yml)
[![CodeQL](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/codeql.yml/badge.svg)](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/codeql.yml)
[![Security](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/security-harden.yml/badge.svg)](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/security-harden.yml)
[![codecov](https://codecov.io/gh/codethor0/human-behaviour-convergence/branch/main/graph/badge.svg)](https://codecov.io/gh/codethor0/human-behaviour-convergence)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![Latest Release](https://img.shields.io/github/v/release/codethor0/human-behaviour-convergence)](https://github.com/codethor0/human-behaviour-convergence/releases)
[![Gitpod Ready-to-Code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/codethor0/human-behaviour-convergence)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/codethor0/human-behaviour-convergence)
[![View SVG](https://img.shields.io/badge/View-SVG-blue)](https://codethor0.github.io/human-behaviour-convergence/diagram/behaviour-convergence.svg)
[![Tip](https://img.shields.io/badge/Tip-support-brightgreen)](https://buy.stripe.com/00w6oA7kM4wc4co5RB3Nm01)
[![Monthly](https://img.shields.io/badge/Monthly-subscribe-blue)](https://buy.stripe.com/7sY3cobB2bYEdMYa7R3Nm00)

---

## CI Status

Main branch workflows:

- **CI** (`ci.yml`): See badge above for current status on `main`.
- **E2E Playwright Tests** (`e2e-playwright.yml`): See badge above for current status on `main`.

All changes to `main` must keep both workflows green.

---

## What is this?

This project is a **public-data-driven behavioral forecasting application** that uses free, publicly available data sources to predict human behavioral patterns at population scale. The system combines economic indicators, environmental signals, and other public time-series data to produce behavioral forecasts that support research, planning, and policy scenario exploration.

**Status:** Production-ready for current feature set. Zero-known-bug state within test coverage.
**License:** Proprietary / All Rights Reserved. Repository is public for viewing and educational purposes only.
**Data:** Public sources only. No individual user data, no proprietary datasets, fully aggregated.
**Ethics:** Strict privacy-first approach. See [ETHICS.md](./ETHICS.md) for details.
**Governance:** Automated enforcement of rules and invariants. See [GOVERNANCE_RULES.md](./GOVERNANCE_RULES.md) for details.
**Roadmap:** [GitHub Milestones](https://github.com/codethor0/human-behaviour-convergence/milestones)
**Interpretability:** Forecast explanations available. See [BEHAVIOR_INDEX.md](./docs/BEHAVIOR_INDEX.md) for details.
**Playground:** Interactive multi-region comparison and scenario exploration. See `/playground` route in the web UI.
**Live Monitoring:** Near real-time behavior index tracking with automatic event detection. See `/live` route in the web UI.

### Scope and Non-Goals

**What this project does:**
- Provides population-scale behavioral forecasting using public data
- Supports research, planning, and policy scenario exploration
- Maintains strict privacy and ethical standards
- Enforces governance rules and system invariants

**What this project does not do:**
- Individual-level prediction or tracking
- Real-time targeting or manipulation
- Collection of personal or private data
- Commercial use without explicit permission (see [License](#license-and-usage))

### Three-Layer Architecture

1. **Signal Layer**: Public data sources providing time-series signals:
   - Economic indicators (market sentiment, volatility indices)
   - Environmental factors (weather patterns, climate anomalies)
   - Search interest trends (aggregated public data)
   - Public health signals (aggregated statistics)
   - Mobility and activity patterns (aggregated public data)
   - Political stress indicators (legislative volatility, executive sentiment, election proximity)
   - Crime & public safety signals (violent crime volatility, property crime rates, gun violence pressure)
   - Information integrity metrics (misinformation spread, sentiment volatility, narrative fragmentation)
   - Social cohesion indicators (community trust, mental health trends, intergroup tension)

2. **Feature Layer**: Transforms signals into unified behavioral features:
   - Time-series feature engineering (lags, moving averages, normalization)
   - Multi-source fusion (combining signals into composite indices)
   - Regional aggregation and temporal alignment

3. **Forecast Layer**: Forecasting models producing future behavioral states:
   - Classical time-series models (exponential smoothing, ARIMA)
   - Forecast outputs over configurable time horizons
   - Confidence intervals and quality indicators

### Intelligence Layer (NEW)

Advanced analytics and insights layer providing:

- **Real-Time Event Shock Detection**: Detects sudden spikes and structural breaks across all indices using Z-score, delta, and EWMA methods
- **Cross-Index Convergence Analysis**: Analyzes interactions between indices to detect reinforcing/conflicting signals and convergence patterns
- **Risk Tier Classification**: Automatically classifies regions into risk tiers (Stable, Watchlist, Elevated, High, Critical)
- **Forecast Confidence Monitoring**: Per-index confidence scores and model drift detection
- **Correlation Analytics**: Computes relationships between indices using Pearson, Spearman, and Mutual Information
- **Scenario Simulation**: Allows hypothetical scenario testing by modifying index values

See [docs/reports/INTELLIGENCE_LAYER_IMPLEMENTATION.md](./docs/reports/INTELLIGENCE_LAYER_IMPLEMENTATION.md) for detailed documentation.

---

## Architecture Overview

![diagram](diagram/behaviour-convergence.svg)

**Note:** Architecture diagram is code-derived and verified against actual implementation.

## Repository Structure

### Core Application Code
- `app/backend/app/main.py` - FastAPI application (main entry point)
- `app/main.py` - Shim module for test compatibility (forwards to backend)
- `app/core/` - Core business logic (behavior index, prediction, location normalization, etc.)
- `app/services/` - Service layer (38 files: ingestion, analytics, comparison, convergence, forecast, risk, shocks, simulation, visual)
- `app/frontend/` - Next.js frontend application (5 pages: index, forecast, playground, live, _app)
- `app/storage/` - Database layer (SQLite storage)

### Data & Connectors
- `connectors/` - Data connector modules (5 files: base, firms_fires, osm_changesets, wiki_pageviews)
- `predictors/` - Predictor registry system (2 files: registry, example_predictor)
- `data/` - Public data snapshots (9 files: CSV data and database)
- `results/` - Example output files (6 files: forecasts, metrics, ground truth, intervals, manifest)

### Development & Research
- `hbc/` - CLI utilities and forecasting functions (3 files: cli, forecasting, __init__)
- `scripts/` - Development scripts (2 files: dev bootstrap script, run_live_forecast_demo)
- `notebooks/` - Jupyter notebook demos (1 file: demo.ipynb)
- `tests/` - Test suite (240 test functions across 28+ test files)

### Documentation & Configuration
- `docs/` - Comprehensive documentation (49 files: architecture, data sources, system status, behavior index, etc.)
- `diagram/` - System architecture diagrams (Mermaid source and generated SVG/PNG)
- Root-level markdown files: README, CONTRIBUTING, SECURITY, ETHICS, GOVERNANCE_RULES, INVARIANTS, etc.

## Diagram quickstart

- Edit the source: `diagram/behaviour-convergence.mmd` (don’t edit `.svg/.png`).
- Preview/edit in your browser via Mermaid Live: https://mermaid.live
- CI behavior:
  - Pull requests: renders to a temporary location to validate Mermaid syntax (no commits).
  - Pushes: renders `svg/png` and opens an automated PR only when outputs actually change.

## Who is this for?

- **Data science teams** exploring large-scale behavioral modeling
- **Public health agencies** interested in population-level forecasting
- **Researchers** studying AI alignment, privacy, and predictive systems
- **Policy analysts** evaluating implications of pervasive surveillance

## Quick Start

1. **Explore the diagram interactively:**
   [![Mermaid Live](https://img.shields.io/badge/Edit-Mermaid%20Live-orange?logo=mermaid)](https://mermaid.live/edit#pako:eNptkktvwjAMhf-KyhVapW2AbaQuTGySTQIkTpN2mrYpTeo0qfpxQvz3OV0YQ6VW9rPzsx379oL6oUdBD5yDAiVgNBzB0B8BqE7OaDbzOJt5NJt5tJj5tJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5NJj5)

2. **Run your first forecast:**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt

   # Start the API server (choose one method)
   # Method 1: Using uvicorn directly (recommended)
   uvicorn app.backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   # Method 2: Using development script
   ./scripts/dev
   # Method 3: Using Python module
   python -m app.backend.app.main

   # Server runs on http://localhost:8000 (or http://localhost:8100 in Docker)

   # Make a forecast request
   curl -X POST "http://localhost:8000/api/forecast" \
     -H "Content-Type: application/json" \
     -d '{
       "latitude": 40.7128,
       "longitude": -74.0060,
       "region_name": "New York City",
       "days_back": 30,
       "forecast_horizon": 7
     }'

   # Check available data sources
   curl "http://localhost:8000/api/forecasting/data-sources"

   # Check available models
   curl "http://localhost:8000/api/forecasting/models"

   # Check available regions
   curl "http://localhost:8000/api/forecasting/regions"

   # Get visualization data
   curl "http://localhost:8000/api/visual/heatmap?region_name=Minnesota"
   curl "http://localhost:8000/api/visual/trends?region_name=Minnesota&latitude=46.7296&longitude=-94.6859"
   curl "http://localhost:8000/api/visual/radar?region_name=Minnesota&latitude=46.7296&longitude=-94.6859"
   curl "http://localhost:8000/api/visual/state-comparison?state_a_name=Minnesota&state_a_lat=46.7296&state_a_lon=-94.6859&state_b_name=Wisconsin&state_b_lat=44.2685&state_b_lon=-89.6165"
   ```

3. **Use the web interface:**
   ```bash
   # In a separate terminal, start the Next.js frontend
   cd app/frontend
   npm install
   npm run dev
   # Frontend runs on http://localhost:3000 (or http://localhost:3100 in Docker)

   # Available frontend routes:
   # - http://localhost:3000/ - Results dashboard (historical forecasts and metrics)
   # - http://localhost:3000/forecast - Generate forecasts interactively
   # - http://localhost:3000/playground - Multi-region comparison and scenario exploration
   # - http://localhost:3000/live - Live monitoring with automatic event detection
   ```

4. **Contribute:**
   See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## Responsible Disclosure

If you discover a security or privacy issue (including ethical concerns about the model or data), please report it responsibly:

- **Security issues:** Open a confidential issue or email the maintainer (see [SECURITY.md](./SECURITY.md))
- **Ethical concerns:** See [ETHICS.md](./ETHICS.md) for our approach to privacy, IRB compliance, and misuse mitigation

## Development

- **Prerequisites:** Python 3.10+, Node 20 (for diagram rendering)
- **Setup:**
  ```bash
  git clone https://github.com/codethor0/human-behaviour-convergence.git
  cd human-behaviour-convergence
  pip install -r requirements.txt
  pip install -r requirements-dev.txt  # for testing
  ```
- **Run tests:**
  ```bash
  pytest tests/ --cov
  ```

- **Run E2E Playwright tests:**
  ```bash
  # Start backend (in one terminal)
  python -m uvicorn app.backend.app.main:app --host 127.0.0.1 --port 8100

  # Start frontend (in another terminal)
  cd app/frontend
  PORT=3003 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8100 npm run dev

  # Run E2E tests (in a third terminal)
  cd app/frontend
  npx playwright test e2e/live-monitoring.spec.ts e2e/forecast.smoke.spec.ts e2e/playground.smoke.spec.ts
  ```

  **E2E Test Suite:**
  - Workflow: `.github/workflows/e2e-playwright.yml` (runs on push/PR + manual trigger)
  - Tests:
    - `e2e/live-monitoring.spec.ts` - Live monitoring selection and refresh tests
    - `e2e/forecast.smoke.spec.ts` - Forecast generation and results verification
    - `e2e/playground.smoke.spec.ts` - Multi-region comparison tests
  - **Gotcha:** Use explicit `isChecked()` to count checked checkboxes. `Locator.filter({ has: page.locator(':checked') })` does **not** work on bare checkbox inputs.

## Application Roadmap

We are building **Behaviour Convergence Explorer**, an interactive web application that provides access to public-data-driven behavioral forecasting through a clean API and web dashboard.

- Architecture & feature plan: [docs/app-plan.md](./docs/app-plan.md)
- System status: [docs/SYSTEM_STATUS.md](./docs/SYSTEM_STATUS.md)
- Data sources: [docs/DATA_SOURCES.md](./docs/DATA_SOURCES.md)
- Roadmap milestones: [docs/ROADMAP.md](./docs/ROADMAP.md)
- Current milestone: `app-v0.1`. Public-data ingestion, forecasting engine, API endpoints, and dashboard.
- Tech stack: Next.js (TypeScript), FastAPI (Python), Pandas, Statsmodels
- Principles: public data only, transparent ethics, extensible APIs, no individual tracking

### How It Works

1. **Signals**: The system ingests public data from multiple sources (economic indicators, weather APIs, aggregated search trends) and normalizes them into standardized time-series formats.

2. **Features**: Signal data is transformed into behavioral features through time-series engineering (lags, rolling statistics, normalization) and multi-source fusion to create composite behavioral indices.

3. **Forecasts**: Forecasting models (exponential smoothing, classical time-series methods) produce future behavioral predictions over configurable horizons with confidence intervals.

4. **API & UI**: FastAPI endpoints expose forecasts programmatically, while a Next.js dashboard provides interactive exploration of historical data, forecasts, and model metadata.

## API Endpoints

### Core Forecasting
- `POST /api/forecast` - Generate behavioral forecast with sub-indices breakdown
- `GET /api/forecasting/data-sources` - List available public data sources
- `GET /api/forecasting/models` - List available forecasting models
- `GET /api/forecasting/regions` - List all supported regions
- `GET /api/forecasting/status` - System component status
- `GET /api/forecasting/history` - Historical forecasts (returns empty, database integration pending)

### Playground & Comparison
- `POST /api/playground/compare` - Multi-region forecast comparison with optional scenario adjustments

### Live Monitoring
- `GET /api/live/summary` - Live behavior index summary for specified regions
- `POST /api/live/refresh` - Manually trigger refresh of live monitoring data

### Public Data
- `GET /api/public/{source}/latest` - Fetch latest data from public sources (wiki, osm, firms)
- `GET /api/public/synthetic_score/{h3_res}/{date}` - Compute synthetic behavioral scores
- `GET /api/public/stats` - Public data snapshot statistics

### Visualization
- `GET /api/visual/heatmap` - Heatmap data for all states and indices
- `GET /api/visual/trends` - Trendline data with slope and breakout detection
- `GET /api/visual/radar` - Radar/spider chart data for behavioral fingerprint
- `GET /api/visual/convergence-graph` - Network visualization data for index convergence
- `GET /api/visual/risk-gauge` - Risk gauge data for dial/meter visualization
- `GET /api/visual/shock-timeline` - Shock timeline data for chronological visualization
- `GET /api/visual/correlation-matrix` - Correlation matrix data for heatmap visualization
- `GET /api/visual/state-comparison` - Comprehensive comparison data between two states

### Data & Metadata
- `GET /health` - Health check endpoint
- `GET /api/forecasts` - Read forecast CSV data (with caching)
- `GET /api/metrics` - Read metrics CSV data (with caching)
- `GET /api/status` - Service metadata (version, commit)
- `GET /api/cache/status` - Cache statistics (hits, misses, size)

### API Documentation
- `GET /docs` - Interactive OpenAPI/Swagger documentation
- `GET /redoc` - Alternative API documentation interface

## Frontend Routes

The Next.js frontend provides the following routes:

- `/` - Results dashboard displaying historical forecasts and metrics
- `/forecast` - Interactive forecast generation interface
- `/playground` - Multi-region comparison and scenario exploration
- `/live` - Live monitoring dashboard with automatic event detection

All routes are accessible at `http://localhost:3000` (or `http://localhost:3100` in Docker).

## Project Status

The application is **production-ready** for its current feature set with:
- 240+ test functions passing (85% code coverage)
- 62 supported regions (51 US states + District of Columbia + 11 global cities)
- Behavior Index v2.5 with 9 sub-indices (economic, environmental, mobility, digital attention, public health, political, crime, misinformation, social cohesion)
- **Intelligence Layer** with 7 components (shock detection, convergence analysis, risk classification, confidence monitoring, drift detection, correlation analytics, scenario simulation)
- Complete location normalization system handling edge cases (Washington D.C. vs Washington state, incident location prioritization, city vs state disambiguation)
- Full-stack implementation: FastAPI backend (2295+ lines), Next.js frontend (5 pages), Docker deployment
- Comprehensive API with 20+ endpoints across forecasting, visualization, playground, live monitoring, and public data
- Zero-known-bug state within test coverage

**Note:** This project is proprietary. The repository is public for viewing and educational purposes only. See [License and Usage](#license-and-usage) for restrictions.

## Current Limitations

The following features are documented but not yet fully implemented:

- `GET /api/forecasting/history` - Returns empty list (database integration pending)
- Some data sources require API configuration (mobility, public health, search trends) and return empty data if not configured
- Frontend visualizations are basic; advanced time-series charts and forecast confidence bands are planned

## What's Next

Planned enhancements (subject to development priorities):
- Database integration for historical forecast storage
- Additional data source integrations (GDELT, OWID health data)
- Advanced forecasting models (ARIMA, Prophet)
- Multi-region batch processing
- Enhanced frontend visualizations (time-series charts, forecast confidence bands)
- Forecast accuracy tracking and historical accuracy metrics

For detailed roadmap milestones (Transparency Drop, Live Playground, Community Rails), see the [Roadmap](docs/ROADMAP.md).

## Citation

If you use this project in your research, please cite:

```bibtex
@software{human_behaviour_convergence,
  author = {codethor0},
  title = {Human Behaviour Convergence: Population-Scale Forecasting},
  year = {2025},
  url = {https://github.com/codethor0/human-behaviour-convergence}
}
```

See [CITATION.cff](./CITATION.cff) for machine-readable metadata.

## Enable Pages
To publish the rendered SVG as a static page, enable GitHub Pages in your repo settings: Settings → Pages → Deploy from a branch → Branch: `master` / (root). After a successful deploy the diagram will be available at:

`https://codethor0.github.io/human-behaviour-convergence/diagram/behaviour-convergence.svg`

---

## License and Usage

This project is proprietary and all rights are reserved by the author (Thor Thor).

The repository is public so that others can view and study the code for educational and evaluation purposes. No permission is granted to copy, modify, redistribute, or use this code in any commercial product, service, or production environment without explicit written consent from the author.

See the [LICENSE](LICENSE) file for full terms.

## Maintainer

This project is maintained by **Thor Thor**.

- Email: [codethor@gmail.com](mailto:codethor@gmail.com)
- LinkedIn: https://www.linkedin.com/in/thor-thor0 (may require manual verification due to anti-bot protection)

## Support

If this project helps you, consider supporting ongoing maintenance:

- **One-time tip:** https://buy.stripe.com/00w6oA7kM4wc4co5RB3Nm01
- **Monthly support:** https://buy.stripe.com/7sY3cobB2bYEdMYa7R3Nm00

**What you fund:** maintenance, docs, roadmap experiments, and new features.

Thank you!
