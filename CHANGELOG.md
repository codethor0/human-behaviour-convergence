# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] — Live Monitoring, Playground, and Transparency Drop

_2025-11-27_

This release turns the Human Behaviour Convergence project into a full observability stack for human behavior signals: forecasts, explanations, multi-region comparisons, and live monitoring — all under a proprietary license.

### Added

- **Live Monitoring Backend**
  - Implemented `LiveMonitor` with snapshot storage and event detection logic.
  - Integrated rule-based event flags using existing data sources:
    - GDELT events for digital attention spikes.
    - OWID health indicators for elevated health stress.
    - USGS earthquake feeds for environmental shocks.
  - Background refresh:
    - Thread-based, non-blocking refresh loop with startup/shutdown hooks.
    - Graceful handling of upstream API failures (skips update, keeps system running).
  - Explanation integration:
    - Live monitor now calls `generate_explanation()` from `app.core.explanations` to attach deterministic, human-readable explanations to live snapshots.

- **Live Monitoring API**
  - `GET /api/live/summary`
    - Returns current live snapshots per region, including:
      - `behavior_index`, sub-indices, recent history, explanation summary, and event flags.
  - `POST /api/live/refresh`
    - Triggers an on-demand refresh of live data.
  - Both endpoints include input validation and robust error handling.

- **Live Dashboard UI**
  - New page: `/live`
    - Region selection for monitoring multiple regions.
    - Auto-refresh with configurable interval.
    - Visualization of event flags and behavior changes over time.
    - Error handling to keep the UI responsive even if the API temporarily fails.

- **Live Playground (Scenario Explorer)**
  - Backend:
    - `app/core/playground.py` with:
      - `compare_regions()` for multi-region comparison.
      - `apply_scenario()` for post-processing "what-if" scenario adjustments.
      - `recompute_behavior_index_from_sub_indices()` using fixed global weights.
    - `app/backend/app/routers/playground.py` with:
      - `POST /api/playground/compare` endpoint.
      - Pydantic request/response models and invalid-region handling.
  - Frontend:
    - `/playground` page with:
      - Multi-region selection (checkbox grid).
      - Controls for historical window, forecast horizon, and optional explanations.
      - Scenario offsets per sub-index, clamped to `[0.0, 1.0]`.
      - Side-by-side display of behavior index, sub-indices, and explanations.
      - Clear warnings that scenarios are experimental/hypothetical.

- **Transparency / Explanations**
  - `app/core/explanations.py`:
    - Deterministic, rule-based explanations at three levels:
      - Overall summary,
      - Per sub-index,
      - Per component (where available).
    - Integrates signals from GDELT, OWID, USGS, and existing indicators.
  - Optional `explanations` field in forecast responses:
    - Backward-compatible and fully typed via Pydantic.
  - Frontend "Why This Forecast?" section on the forecast page.

### Changed

- **Forecast & Playground Internals**
  - Kept Behavior Index weights fixed at:
    - Economic: 0.25
    - Environmental: 0.25
    - Mobility: 0.20
    - Digital Attention: 0.15
    - Public Health: 0.15
  - All scenario adjustments are post-processing only and clearly labeled.
  - Core forecast endpoint `/api/forecast` remains unchanged and backward compatible.

- **Documentation**
  - `README.md`:
    - Updated with sections for:
      - Transparency Drop (explanations),
      - Live Playground,
      - Live Monitoring.
    - Clarified proprietary licensing and current project status.
  - `docs/BEHAVIOR_INDEX.md`:
    - Added sections on:
      - Interpretability and explanation schema.
      - Live Playground behavior.
      - Live monitoring and how it reuses the same index math.
  - `docs/DATA_SOURCES.md`:
    - Documented how GDELT, OWID, USGS feed into sub-indices and live event flags.
  - `docs/ROADMAP.md`:
    - Marked Milestone 3 (Live Playground) as implemented.
    - Documented live monitoring/dashboard work and remaining future enhancements.

### Fixed

- **Live Explanation Integration**
  - Issue: The live monitor initially attempted to read explanations from forecast responses where they weren't present.
  - Fix: `app/core/live_monitor.py` now generates explanations directly via `generate_explanation()` from `app.core.explanations`, ensuring consistent behavior across forecast, playground, and live views.

- **General Quality / Hygiene**
  - Ensured:
    - No emojis in source, tests, docs, or workflows.
    - No prompt/master-prompt files tracked in the repository.
    - All new files carry PROPRIETARY SPDX headers.
  - Verified:
    - All imports are non-circular.
    - All Python files compile without syntax errors.
    - TypeScript/React code builds cleanly.

### Quality & Compliance

- **Tests and Coverage**
  - Existing tests maintained and still passing.
  - Additional tests:
    - 12 unit tests for live monitor and event detection logic.
    - 5 tests for live API endpoints.
    - New tests for playground core logic and endpoints.
  - Overall coverage is 78% (2941 statements, 657 missing).

- **Linting & Build**
  - `ruff` check: clean (no errors or warnings).
  - `black --check`: clean.
  - `npm run build`: succeeds with no new TypeScript or build-time errors.
  - Docker:
    - Backend and frontend containers build and run successfully.
    - Health checks pass.

- **Backward Compatibility**
  - `/api/forecast` endpoint preserved exactly; all existing clients continue to work.
  - New fields and endpoints are additive and optional.
  - Location normalization behavior, region catalog, and Behavior Index math are unchanged.

- **Licensing**
  - Repository remains proprietary / all rights reserved.
  - `LICENSE`, `pyproject.toml`, README, and SPDX headers are aligned with the proprietary model.

---

This version is production-ready for the current feature set and provides a full pipeline for human behavior analysis: forecasting, explanation, interactive playground exploration, and live monitoring with event-aware signals.
