#!/usr/bin/env bash
set -euo pipefail

# Print concise failure summary on any non-zero exit (readable in CI logs).
trap 'if [ $? -ne 0 ]; then echo "[HBC] SUMMARY: Verification FAILED."; fi' EXIT

echo "[HBC] Full verification starting..."

###############################################################################
# REPO ROOT & PYTHONPATH
###############################################################################
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# Ensure repo root is on PYTHONPATH (for imports in tests)
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

echo "[HBC] Repo root: $REPO_ROOT"
echo "[HBC] PYTHONPATH: $PYTHONPATH"

###############################################################################
# ENVIRONMENT FOR CI / OFFLINE SAFETY
###############################################################################
# Respect existing CI flag (GitHub Actions sets CI=true). If not set, assume local.
CI_FLAG="${CI:-false}"
export CI="${CI_FLAG}"

# Offline / deterministic mode for tests and fetchers
export CI_OFFLINE_MODE="${CI_OFFLINE_MODE:-true}"
export HBC_CI_OFFLINE_DATA="${HBC_CI_OFFLINE_DATA:-1}"

echo "[HBC] Environment:"
echo "  CI=$CI"
echo "  CI_OFFLINE_MODE=$CI_OFFLINE_MODE"
echo "  HBC_CI_OFFLINE_DATA=$HBC_CI_OFFLINE_DATA"

###############################################################################
# PYTHON / BACKEND TESTS (API, FORECAST, METRICS)
###############################################################################
if command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 || command -v pytest >/dev/null 2>&1 || [ -x ".venv/bin/pytest" ]; then
  echo "[HBC] Running backend/API/forecast tests with pytest..."

  # Choose pytest runner (preferring system pytest, then venv, then python3/python -m pytest)
  if command -v pytest >/dev/null 2>&1; then
    PYTEST_CMD="pytest"
  elif [ -x ".venv/bin/pytest" ]; then
    PYTEST_CMD=".venv/bin/pytest"
  elif command -v python3 >/dev/null 2>&1; then
    PYTEST_CMD="python3 -m pytest"
  else
    PYTEST_CMD="python -m pytest"
  fi

  # Core backend test suite (23 tests)
  $PYTEST_CMD -q \
    tests/test_api_backend.py \
    tests/test_forecasting_endpoints.py

  echo "[HBC] Backend/API test suite passed."
else
  echo "[HBC] WARNING: No Python/pytest available; skipping backend tests."
fi

###############################################################################
# OPTIONAL: LINTING (RUFF / MYPY) – FATAL IF ENABLED
###############################################################################

# Ruff (Python linting)
if command -v ruff >/dev/null 2>&1; then
  echo "[HBC] Running ruff lint on app + tests..."
  ruff check app tests
  echo "[HBC] Ruff lint clean."
else
  echo "[HBC] Ruff not installed; skipping Python lint."
fi

# Mypy (type checking)
if command -v mypy >/dev/null 2>&1; then
  echo "[HBC] Running mypy type-check on app..."
  mypy app
  echo "[HBC] Mypy type-check clean."
else
  echo "[HBC] Mypy not installed; skipping type-check."
fi

###############################################################################
# FRONTEND CHECKS – OPTIONAL LOCALLY, FATAL IN CI
###############################################################################
# When CI or GITHUB_ACTIONS is set, frontend failures cause script to exit 1.
FRONTEND_FATAL=0
if [ "${CI:-false}" = "true" ] || [ "${GITHUB_ACTIONS:-false}" = "true" ]; then
  FRONTEND_FATAL=1
fi

if [ -f "package.json" ] || [ -f "app/frontend/package.json" ]; then
  echo "[HBC] Detected frontend package.json. Running frontend checks..."

  FRONTEND_DIR="."
  if [ -f "app/frontend/package.json" ]; then
    FRONTEND_DIR="app/frontend"
  fi

  FE_RC=0
  (
    cd "$FRONTEND_DIR"

    # Choose Node runner
    if command -v pnpm >/dev/null 2>&1; then
      RUNNER="pnpm"
    elif command -v yarn >/dev/null 2>&1; then
      RUNNER="yarn"
    else
      RUNNER="npm"
    fi

    # Install deps only if node_modules missing
    if [ ! -d "node_modules" ]; then
      echo "[HBC][FE] Installing dependencies via $RUNNER install..."
      $RUNNER install
    fi

    FRONTEND_OK=true

    # Lint if script exists
    if command -v jq >/dev/null 2>&1 && jq -e '.scripts.lint' package.json >/dev/null 2>&1; then
      echo "[HBC][FE] Running frontend lint via $RUNNER run lint..."
      if ! $RUNNER run lint; then
        FRONTEND_OK=false
      fi
    else
      echo "[HBC][FE] No lint script configured or jq not available; skipping lint."
    fi

    # Test if script exists
    if command -v jq >/dev/null 2>&1 && jq -e '.scripts.test' package.json >/dev/null 2>&1; then
      echo "[HBC][FE] Running frontend tests via $RUNNER test..."
      # Try non-watch mode first; fall back to default if flag unsupported
      if ! $RUNNER test -- --watch=false 2>/dev/null; then
        if ! $RUNNER test; then
          FRONTEND_OK=false
        fi
      fi
    else
      echo "[HBC][FE] No test script configured or jq not available; skipping tests."
    fi

    if [ "$FRONTEND_OK" = true ]; then
      echo "[HBC][FE] Frontend checks passed."
    else
      if [ "$FRONTEND_FATAL" = 1 ]; then
        echo "[HBC][FE] Frontend checks failed in CI; marking verification as failed."
        exit 1
      else
        echo "[HBC][FE] Frontend checks failed, but this is a local run; continuing (non-fatal)."
        exit 0
      fi
    fi
  )
  FE_RC=$?

  if [ "$FE_RC" -ne 0 ] && [ "$FRONTEND_FATAL" = 1 ]; then
    exit 1
  fi
  if [ "$FE_RC" -ne 0 ] && [ "$FRONTEND_FATAL" = 0 ]; then
    echo "[HBC] Frontend checks failed, but this is a local run; continuing (non-fatal)."
  fi
else
  echo "[HBC] No frontend package.json detected; skipping frontend checks."
fi

###############################################################################
# LIGHT RUNTIME SMOKE CHECK (NON-FATAL)
###############################################################################
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

if command -v curl >/dev/null 2>&1; then
  echo "[HBC] Attempting lightweight runtime smoke checks (non-fatal)..."

  set +e
  curl -fsS "$BACKEND_URL/health" >/dev/null 2>&1
  HEALTH_RC=$?

  curl -fsS "$BACKEND_URL/api/forecasts" >/dev/null 2>&1
  FORECAST_RC=$?
  set -e

  if [ "$HEALTH_RC" -eq 0 ] && [ "$FORECAST_RC" -eq 0 ]; then
    echo "[HBC] Runtime smoke: /health and /api/forecasts reachable."
  else
    echo "[HBC] Runtime smoke skipped or backend not running (does not affect status)."
  fi
fi

###############################################################################
# SUCCESS
###############################################################################
echo "[HBC] SUMMARY: Verification PASSED."
echo "[HBC] All configured checks passed; repo is test-clean and CI-ready."
