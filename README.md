# Human Behaviour Convergence
> Public-data-driven behavioral forecasting for population-scale analysis and planning.

[![CI](https://github.com/codethor0/human-behaviour-convergence/actions/workflows/ci.yml/badge.svg)](https://github.com/codethor0/human-behaviour-convergence/actions)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Gitpod Ready-to-Code](https://img.shields.io/badge/Gitpod-ready--to--code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/codethor0/human-behaviour-convergence)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/codethor0/human-behaviour-convergence)
[![View SVG](https://img.shields.io/badge/View-SVG-blue)](https://codethor0.github.io/human-behaviour-convergence/diagram/behaviour-convergence.svg)
[![Tip](https://img.shields.io/badge/Tip-support-brightgreen)](https://buy.stripe.com/00w6oA7kM4wc4co5RB3Nm01)
[![Monthly](https://img.shields.io/badge/Monthly-subscribe-blue)](https://buy.stripe.com/7sY3cobB2bYEdMYa7R3Nm00)

---

## What is this?

This project is a **public-data-driven behavioral forecasting application** that uses free, publicly available data sources to predict human behavioral patterns at population scale. The system combines economic indicators, environmental signals, and other public time-series data to produce behavioral forecasts that support research, planning, and policy scenario exploration.

**Status:** Production-ready for current feature set — zero-known-bug state within test coverage
**License:** Proprietary / All Rights Reserved — repository is public for viewing and educational purposes only
**Data:** Public sources only — no individual user data, no proprietary datasets, fully aggregated
**Ethics:** Strict privacy-first approach — see [ETHICS.md](./ETHICS.md) for details
**Roadmap:** [GitHub Milestones](https://github.com/codethor0/human-behaviour-convergence/milestones)
**Interpretability:** Forecast explanations available — see [BEHAVIOR_INDEX.md](./docs/BEHAVIOR_INDEX.md) for details
**Playground:** Interactive multi-region comparison and scenario exploration — see `/playground` route in the web UI
**Live Monitoring:** Near real-time behavior index tracking with automatic event detection — see `/live` route in the web UI

### Three-Layer Architecture

1. **Signal Layer** — Public data sources providing time-series signals:
   - Economic indicators (market sentiment, volatility indices)
   - Environmental factors (weather patterns, climate anomalies)
   - Search interest trends (aggregated public data)
   - Public health signals (aggregated statistics)
   - Mobility and activity patterns (aggregated public data)

2. **Feature Layer** — Transforms signals into unified behavioral features:
   - Time-series feature engineering (lags, moving averages, normalization)
   - Multi-source fusion (combining signals into composite indices)
   - Regional aggregation and temporal alignment

3. **Forecast Layer** — Forecasting models producing future behavioral states:
   - Classical time-series models (exponential smoothing, ARIMA)
   - Forecast outputs over configurable time horizons
   - Confidence intervals and quality indicators

---

## Architecture Overview

![diagram](diagram/behaviour-convergence.svg)

## What's inside
| File | Purpose |
|------|---------|
| `diagram/behaviour-convergence.mmd` | Source Mermaid diagram – edit here |
| `diagram/behaviour-convergence.svg` | Auto-generated vector (perfect for docs / slides) |
| `diagram/behaviour-convergence.png` | Hi-res PNG (2400 px) – social cards, posters |
| `notebooks/` | Jupyter notebooks with end-to-end demos |
| `results/` | Ground truth, forecasts, and error metrics (CSV) |
| `tests/` | Unit tests and CI validation |

## Diagram quickstart

- Edit the source: `diagram/behaviour-convergence.mmd` (don’t edit `.svg/.png`).
- Preview/edit in your browser via Mermaid Live: https://mermaid.live
- CI behavior:
  - Pull requests: renders to a temporary location to validate Mermaid syntax (no commits).
  - Pushes: renders `svg/png` and opens an automated PR only when outputs actually change.

## Who is this for?

- **Data science teams** exploring large-scale behavioural modelling
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

   # Start the API server
   python -m app.backend.app.main
   # Server runs on http://localhost:8000 (or 8100 in Docker)

   # Make a forecast request
   curl -X POST "http://localhost:8100/api/forecast" \
     -H "Content-Type: application/json" \
     -d '{
       "latitude": 40.7128,
       "longitude": -74.0060,
       "region_name": "New York City",
       "days_back": 30,
       "forecast_horizon": 7
     }'

   # Check available data sources
   curl "http://localhost:8100/api/forecasting/data-sources"

   # Check available models
   curl "http://localhost:8100/api/forecasting/models"
   ```

3. **Use the web interface:**
   ```bash
   # In a separate terminal, start the Next.js frontend
   cd app/frontend
   npm install
   npm run dev
   # Frontend runs on http://localhost:3000 (or 3100 in Docker)
   # Navigate to http://localhost:3100/forecast to generate forecasts interactively
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

## Application Roadmap

We are building **Behaviour Convergence Explorer**, an interactive web application that provides access to public-data-driven behavioral forecasting through a clean API and web dashboard.

- Architecture & feature plan: [docs/app-plan.md](./docs/app-plan.md)
- System status: [docs/SYSTEM_STATUS.md](./docs/SYSTEM_STATUS.md)
- Data sources: [docs/DATA_SOURCES.md](./docs/DATA_SOURCES.md)
- Roadmap milestones: [docs/ROADMAP.md](./docs/ROADMAP.md)
- Current milestone: `app-v0.1` — public-data ingestion, forecasting engine, API endpoints, and dashboard
- Tech stack: Next.js (TypeScript), FastAPI (Python), Pandas, Statsmodels
- Principles: public data only, transparent ethics, extensible APIs, no individual tracking

### How It Works

1. **Signals**: The system ingests public data from multiple sources (economic indicators, weather APIs, aggregated search trends) and normalizes them into standardized time-series formats.

2. **Features**: Signal data is transformed into behavioral features through time-series engineering (lags, rolling statistics, normalization) and multi-source fusion to create composite behavioral indices.

3. **Forecasts**: Forecasting models (exponential smoothing, classical time-series methods) produce future behavioral predictions over configurable horizons with confidence intervals.

4. **API & UI**: FastAPI endpoints expose forecasts programmatically, while a Next.js dashboard provides interactive exploration of historical data, forecasts, and model metadata.

## Project Status

The application is **production-ready** for its current feature set with:
- 129 tests passing (85% code coverage)
- 62 supported regions (51 US states + District of Columbia + 11 global cities)
- Behavior Index v2.5 with 5 sub-indices (economic, environmental, mobility, digital attention, public health)
- Complete location normalization system handling edge cases (Washington D.C. vs Washington state, incident location prioritization, city vs state disambiguation)
- Full-stack implementation: FastAPI backend, Next.js frontend, Docker deployment
- Zero-known-bug state within test coverage

**Note:** This project is proprietary. The repository is public for viewing and educational purposes only. See [License and Usage](#license-and-usage) for restrictions.

## What's Next

Planned enhancements (subject to development priorities):
- Additional data source integrations (GDELT, OWID health data)
- Advanced forecasting models (ARIMA, Prophet)
- Multi-region batch processing
- Forecast comparison tools
- Frontend visualizations (time-series charts, forecast confidence bands)
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
- LinkedIn: [https://www.linkedin.com/in/thor-thor0](https://www.linkedin.com/in/thor-thor0)

## Support

If this project helps you, consider supporting ongoing maintenance:

- **One-time tip:** https://buy.stripe.com/00w6oA7kM4wc4co5RB3Nm01
- **Monthly support:** https://buy.stripe.com/7sY3cobB2bYEdMYa7R3Nm00

**What you fund:** maintenance, docs, roadmap experiments, and new features.

Thank you!
