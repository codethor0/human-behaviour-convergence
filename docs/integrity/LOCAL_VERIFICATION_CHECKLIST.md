# Local Verification Checklist

Run these commands from `/Users/thor/Projects/human-behaviour-convergence` to verify the repo is in a green state.

## 1. Repo State Verification

```bash
cd /Users/thor/Projects/human-behaviour-convergence

# Confirm we're in a git repo
git rev-parse --is-inside-work-tree
# Expected: true

# Confirm branch
git branch --show-current
# Expected: main

# Confirm remote
git remote -v
# Expected: origin https://github.com/codethor0/human-behaviour-convergence.git

# Check status
git status --short
# Expected: Clean working tree or only intentional changes
```

## 2. Python Compilation & Targeted Tests

```bash
source .venv/bin/activate

# Compile check
python -m compileall app -q
# Expected: No errors

# Targeted test suite (all should pass)
python -m pytest tests/test_explainability.py -k "risk_classification" -v
python -m pytest tests/test_explainability.py::TestTraceCompleteness::test_confidence_calculation_has_trace -v
python -m pytest tests/test_explainability.py::TestTraceCompleteness::test_convergence_analysis_has_trace -v
python -m pytest tests/test_explainability.py::TestTraceCompleteness::test_shock_detection_has_trace -v
python -m pytest tests/test_factor_quality_metrics.py::TestHierarchicalQualityReconciliation::test_quality_metrics_preserve_reconciliation -v
python -m pytest tests/test_gdelt_connector.py::TestGDELTEventsFetcher::test_fetch_event_tone_success -v
python -m pytest tests/test_intelligence_layer.py::TestRiskClassifier::test_classify_risk_stable -v
python -m pytest tests/test_state_lifetime.py::TestStateReset::test_singleton_reset -v
```

## 3. Backend Smoke Test

```bash
source .venv/bin/activate

# Start backend in background
uvicorn app.backend.app.main:app --host 127.0.0.1 --port 8100 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for startup
sleep 5

# Health check
curl -f http://127.0.0.1:8100/health
# Expected: {"status":"ok"}

# Regions endpoint
curl -f http://127.0.0.1:8100/api/forecasting/regions | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Regions: {len(data)}'); print(f'Minnesota: {any(r.get(\"id\")==\"us_mn\" for r in data)}')"
# Expected: Regions: 62, Minnesota: True

# Data sources endpoint
curl -f http://127.0.0.1:8100/api/forecasting/data-sources | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Sources: {len(data)}')"
# Expected: Sources: 11

# Cleanup
kill $BACKEND_PID
```

## 4. Frontend Build

```bash
cd app/frontend
npm run build
# Expected: Build succeeds (warnings OK, errors not OK)
cd ../..
```

## 5. Integrity Gate (Local)

```bash
./ops/check_integrity.sh --skip-regression
# Expected: Exit code 0
# Note: Full suite may timeout due to network-dependent tests; that's acceptable if documented
```

## 6. GitHub Actions Verification (Manual)

In GitHub UI:
1. Navigate to: https://github.com/codethor0/human-behaviour-convergence/actions
2. Filter by branch: `main`
3. Verify latest runs for these workflows are green:
   - **CI** (ci.yml)
   - **E2E Playwright Tests** (e2e-playwright.yml)
   - **CodeQL Security Analysis**
   - **Security Harden**
   - **Release**
   - **Frontend Lint** (should be green after commit `daf58cc`)

## 7. Recent Commits Verification

```bash
git log --oneline -5
# Expected to see:
# daf58cc fix(frontend): remove unused regionsResponse variable in e2e test
# a0ede00 docs: update resolution with correct commit hash
# 770ded4 fix: resolve forecast page regression and restore integrity gates
# 0c719da docs: record resolution for forecast page regression
```

## Expected Results Summary

- All Python files compile
- All targeted tests pass (8/8)
- Backend endpoints respond correctly
- Frontend builds successfully
- Integrity gate passes (or times out on network tests, which is acceptable)
- GitHub Actions workflows are green on main

If all checks pass, the repo is in a green state.
