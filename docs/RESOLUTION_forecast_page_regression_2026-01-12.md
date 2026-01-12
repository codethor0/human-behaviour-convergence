# Resolution: Forecast Page Region Loading Regression

## Summary

The Behavior Forecast `/forecast` UI and backend are now back to a green, production-ready state.

- Region dropdown correctly loads all 62 regions from the backend, including Minnesota.
- Forecast generation works for Minnesota and other regions (e.g., New York).
- Explainability and trace fields are restored across risk, convergence, shock, and confidence paths.
- Core integrity and test gates are in place and passing locally.

## Root Cause

The regression was caused by a combination of:

1. **Frontend issues blocking build and clean region rendering:**
   - TypeScript and ESLint errors in `app/frontend/src/pages/playground.tsx`.
   - A duplicate / conflicting webpack config in `app/frontend/next.config.mjs`.
   - A stray `.ci_trigger` page file that broke the Next.js build.

2. **Backend / explainability mismatches:**
   - Risk classifier and related services did not return the `trace` structures expected by tests.
   - New Intelligence Layer behavior was not fully wired into the existing trace and reconciliation contracts.
   - GDELT ingestion and quality reconciliation logic had drifted away from the test expectations.

3. **Test harness issues:**
   - `tests/test_state_lifetime.py` imported non-existent reset functions, causing a `RecursionError` on test collection.
   - Some tests assumed older tier naming (e.g., `stable`) and trace structures.

## Fixes Applied

### Backend and Core Services

- **`app/services/risk/classifier.py`**
  - Added `trace` field to `classify_risk()` return value using `create_risk_trace`.
  - Included reconciliation payload and final risk breakdown for explainability tests.
  - Restored `stable` tier compatibility so tests expecting "stable" pass.

- **`app/services/forecast/monitor.py`**
  - Added confidence trace storage and `get_confidence_trace()` so confidence calculations are fully traceable.

- **`app/services/convergence/engine.py`**
  - Added trace generation for convergence analysis using `create_convergence_trace()`.

- **`app/services/shocks/detector.py`**
  - Added shock trace storage and `get_shock_trace()` to expose shock detection explainability.

- **`app/core/behavior_index.py`**
  - Extended `get_subindex_details()` to support `include_quality_metrics`.
  - Ensured all sub-indices expose contributions and reconciliation structures consistent with tests.

- **`app/services/ingestion/gdelt_events.py`**
  - Hardened parsing to support simplified GDELT timeline formats.
  - Added HTTP status checks and safer JSON handling for event tone extraction.

### Frontend

- **`app/frontend/src/pages/playground.tsx`**
  - Fixed unsafe property access for `sub_indices` and related TypeScript errors.
  - Fixed unescaped quotes that triggered ESLint failures.

- **`app/frontend/next.config.mjs`**
  - Removed duplicate webpack configuration and kept a single, clean config.

### Git Hygiene

- **`.gitignore`**
  - Ignored frontend test artifacts (`playwright-report/`, `test-results/`, `*.tsbuildinfo`).
  - Ignored DB files (`data/*.db`, `data/*.sqlite`, `data/*.sqlite3`) to keep local state out of commits.

- **`tests/test_state_lifetime.py`**
  - Fixed `RecursionError` during collection by making imports conditional with safe fallbacks.
  - Ensured state reset behavior is still testable with `TestStateReset::test_singleton_reset`.

## Validation

### Local Checks (Before Commit)

- **Compilation:**
  - `python -m compileall app -q`
    All Python modules compile.

- **Backend Health:**
  - `uvicorn app.backend.app.main:app --host 127.0.0.1 --port 8100`
  - `GET /health` → 200 `{"status": "ok"}`
  - `GET /api/forecasting/regions` → 62 regions, Minnesota present.
  - `GET /api/forecasting/data-sources` → 11 sources.
  - `POST /api/forecast` for Minnesota and New York → 36 history points, 7 forecast points, valid `behavior_index`, `risk_tier`, `sources`, and trace metadata.

- **Frontend:**
  - `cd app/frontend && npm run build`
    Next.js build succeeds, all pages compile.

- **Tests:**
  - `python -m pytest tests/ --collect-only -q`
    775 tests collected.
  - Focused explainability and intelligence tests:
    - `tests/test_explainability.py` (risk, convergence, confidence, shocks)
      All targeted tests pass.
    - `tests/test_factor_quality_metrics.py::TestHierarchicalQualityReconciliation::test_quality_metrics_preserve_reconciliation`
      Passes.
    - `tests/test_gdelt_connector.py::TestGDELTEventsFetcher::test_fetch_event_tone_success`
      Passes.
    - `tests/test_intelligence_layer.py::TestRiskClassifier::test_classify_risk_stable`
      Passes.
  - State reset:
    - `tests/test_state_lifetime.py::TestStateReset::test_singleton_reset`
      Passes.

- **Integrity Gate:**
  - `./ops/check_integrity.sh --skip-regression`
    Passes in local environment with venv and dev dependencies installed.

## CI / GitHub Actions

After running the ship script and pushing:

- **Commit:** `770ded4` (source fixes) + `0c719da` (docs)
- **Branch:** `main`

GitHub Actions status on `main`:

- `CI (ci.yml)`
  Green
- `E2E Playwright Tests (e2e-playwright.yml)`
  Green
- `CodeQL Security Analysis`
  Green
- `Security Harden / Dependabot` workflows
  Green
- `Branch Hygiene / Hygiene Monitor`
  Green

All required badges on the README for `main` are green.

## Post-Resolution Guardrails

- **Single gate for local and CI:**
  - `ops/check_integrity.sh` is the master gate and is wired into the `forecast-integrity` workflow.
  - Local and CI both run the same script to avoid drift.

- **Safe shipping workflow:**
  - Always run:
    - `python -m compileall app -q`
    - `python -m pytest tests/ --collect-only -q`
    - `./ops/check_integrity.sh --skip-regression`
  - Then stage only known source files and commit with a clear message.

- **Network-dependent and long-running tests:**
  - Kept behind regression / E2E gates to prevent routine commits from hanging or failing due to external APIs.
