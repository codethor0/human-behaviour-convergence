# Roadmap

This document tracks planned future work for the Human Behaviour Convergence project.
The repository is **production-ready for the current feature set**. Items below are **future enhancements**, not current bugs or regressions.

## Project Stewardship

Primary maintainer: **Thor Thor**
Email: [codethor@gmail.com](mailto:codethor@gmail.com)
LinkedIn: https://www.linkedin.com/in/thor-thor0 (may require manual verification due to anti-bot protection)

---

## Milestone 2: Transparency Drop

**Status:** Planned / Future Enhancement

**Goal:** Improve transparency, interpretability, and explainability of forecasts.

**Description:** This milestone focuses on making the forecasting pipeline fully reproducible and transparent by publishing public datasets and documentation. The goal is to improve transparency, interpretability, and explainability of forecasts.

### Tasks

- [ ] 100k synthetic row shard on Hugging Face datasets + DVC pointer
- [ ] DVC pipeline stage that reproduces the notebook end-to-end
- [ ] HTML report published to GitHub Pages (dvc metrics show --html)
- [ ] Model card (model-card.md) filled with limitations, ethical risks

**Note:** This roadmap item was previously tracked as GitHub Issue #8. It has been migrated to this documentation to keep the Issues list focused on current bugs and actionable work.

---

## Milestone 3: Live Playground

**Status:** Implemented

**Goal:** Give visitors an instant 'aha' moment through an interactive exploration interface.

**Description:** An interactive web-based playground that allows users to explore forecasts across multiple regions and test "what-if" scenarios with optional post-processing adjustments. The playground provides side-by-side comparison of behavioral forecasts with explanations.

### Implemented Features

- [x] Multi-region comparison endpoint (`POST /api/playground/compare`)
- [x] Interactive playground UI (`/playground` route)
- [x] Optional scenario adjustments (post-processing transformations for exploration)
- [x] Side-by-side forecast comparison with explanations
- [x] Configurable historical days and forecast horizon
- [x] Graceful error handling for invalid regions

### Future Enhancements

- [ ] Streamlit/Gradio app that loads the public shard and shows:
  - world map with predicted behavioural index slider
  - 'upload your CSV' adapter (accepts same schema)
- [ ] Host free on Hugging Face Spaces (zero infra cost)
- [ ] Embed screenshot + link at top of README → instant demo

**Note:** This roadmap item was previously tracked as GitHub Issue #9. Core playground functionality is now implemented. Remaining items are stretch goals for future enhancements.

---

## Milestone 3.5: Live Monitoring and Dashboard

**Status:** Implemented

**Goal:** Provide near real-time monitoring of behavior index values with automatic event detection.

**Description:** A live monitoring system that maintains rolling snapshots of behavior index data per region, automatically detects major events (spikes in digital attention, health stress elevation, environmental shocks, economic volatility), and provides a Grafana-like dashboard experience for tracking behavioral patterns over time.

### Implemented Features

- [x] Live monitoring backend module (`app/core/live_monitor.py`)
- [x] In-memory snapshot storage with rolling window (configurable max snapshots per region)
- [x] Background refresh mechanism (automatic periodic updates)
- [x] Major event detection (rule-based heuristics for digital attention spikes, health stress, environmental shocks, economic volatility)
- [x] Live monitoring API endpoints (`GET /api/live/summary`, `POST /api/live/refresh`)
- [x] Live dashboard UI (`/live` route) with:
  - Multi-region selection
  - Auto-refresh with configurable interval
  - Time window configuration
  - Event flag visualization
  - Historical snapshot display
- [x] Integration with existing data sources (GDELT, OWID, USGS participate in event detection)

### Future Enhancements

- [ ] Persistent storage for snapshots (SQLite or lightweight database)
- [ ] More sophisticated event detection (machine learning-based anomaly detection)
- [ ] Alerting system (email/webhook notifications for major events)
- [ ] Chart visualizations for trend analysis
- [ ] Export functionality (CSV/JSON download of historical snapshots)

**Note:** Live monitoring uses the same Behavior Index math and weights as standard forecasts. Event detection flags are for interpretation and highlighting only, not for modifying core computations.

---

## Milestone 4: Community Rails

**Status:** Planned / Future Enhancement

**Goal:** Make it easier for others to experiment safely with structured contributions.

**Description:** Establish community governance, contribution workflows, and regular engagement channels to support long-term project sustainability. This includes guardrails for inputs and configuration, templates for community-contributed regions or indicators, and documentation for extension points.

### Tasks

- [ ] all-contributors bot installed → auto-update README avatars
- [ ] RFC template + lightweight Technical Steering Committee (TSC) draft
- [ ] Monthly open Zoom call (calendar file + .ics in repo)
- [ ] 'good first issue' bot that labels PRs ≤20 lines

**Note:** This roadmap item was previously tracked as GitHub Issue #10. It has been migrated to this documentation to keep the Issues list focused on current bugs and actionable work.

---

## Current Status

**Active Development:** v0.1 - Production-ready for current feature set

**Current Focus:**
- Core forecasting engine and API endpoints (complete)
- Public data connectors and ingestion pipelines (operational)
- Web dashboard for interactive exploration (functional)
- Documentation and reproducibility (maintained)

**Status:** All roadmap items above are **planned / future** and do NOT indicate current bugs or regressions. The repository is production-ready for its current feature set with 129 tests passing, 85% coverage, and zero-known-bug state within test coverage.

For detailed feature planning, see [docs/app-plan.md](./app-plan.md).
