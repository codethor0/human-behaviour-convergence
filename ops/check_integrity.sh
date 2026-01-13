#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Integrity check script for CI/CD.
# Inspired by DevOps-Bash-tools checks/* pattern.
#
# Usage:
#   ./ops/check_integrity.sh [--skip-tests] [--skip-regression]
#
# Exit codes:
#   0: All checks pass
#   1: One or more checks fail
#   2: Setup/configuration error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKIP_TESTS=false
SKIP_REGRESSION=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-regression)
            SKIP_REGRESSION=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 2
            ;;
    esac
done

cd "${REPO_ROOT}"

echo "Running integrity checks..."
echo ""

FAILURES=0

# 1. Config validation
echo "1. Validating calibration config..."
if ! python3 -c "
from app.services.calibration.config import (
    BEHAVIOR_INDEX_WEIGHTS, SHOCK_MULTIPLIER, REALITY_BLEND_WEIGHTS
)
# Check that weights are valid
assert all(0 <= w <= 1 for w in BEHAVIOR_INDEX_WEIGHTS.values()), 'Weights must be in [0,1]'
assert SHOCK_MULTIPLIER['threshold'] >= 0, 'Shock threshold must be non-negative'
assert SHOCK_MULTIPLIER['max_behavior_index'] <= 1.0, 'Max behavior_index must be <= 1.0'
print('  ✓ Config validation passed')
" 2>&1; then
    echo "  ✗ Config validation failed"
    FAILURES=$((FAILURES + 1))
fi

# 2. Unit tests (if not skipped)
if [ "${SKIP_TESTS}" = "false" ]; then
    echo ""
    echo "2. Running unit tests (fast integrity: excluding network and slow tests)..."
    if [ -d "tests" ]; then
        if python3 -m pytest tests/ -m "not network and not slow" -v --tb=short 2>&1 | tee /tmp/integrity_tests.log; then
            echo "  ✓ Unit tests passed"
        else
            echo "  ✗ Unit tests failed"
            FAILURES=$((FAILURES + 1))
        fi
    else
        echo "  ⚠ No tests directory found, skipping"
    fi
else
    echo ""
    echo "2. Skipping unit tests (--skip-tests)"
fi

# 3. Forecast regression (if not skipped)
if [ "${SKIP_REGRESSION}" = "false" ]; then
    echo ""
    echo "3. Running forecast regression tests..."
    if python3 ops/run_forecast_regression.py --output-dir ops/regression_results --markdown 2>&1 | tee /tmp/integrity_regression.log; then
        echo "  ✓ Regression tests passed"
        # Show latest markdown report location
        LATEST_REPORT=$(ls -t ops/regression_results/*.md 2>/dev/null | head -1)
        if [ -n "${LATEST_REPORT}" ]; then
            echo "    Report: ${LATEST_REPORT}"
        fi
    else
        echo "  ✗ Regression tests failed"
        FAILURES=$((FAILURES + 1))
        # Show latest markdown report location even on failure
        LATEST_REPORT=$(ls -t ops/regression_results/*.md 2>/dev/null | head -1)
        if [ -n "${LATEST_REPORT}" ]; then
            echo "    Report: ${LATEST_REPORT}"
        fi
    fi
else
    echo ""
    echo "3. Skipping regression tests (--skip-regression)"
fi

# 4. Code quality checks (optional, if tools available)
echo ""
echo "4. Running code quality checks..."
if command -v pylint &> /dev/null; then
    if python3 -m pylint app/core/prediction.py app/services/calibration/config.py \
        --disable=all --enable=import-error,undefined-variable 2>&1 | grep -q "rated at 10.00"; then
        echo "  ✓ Pylint passed"
    else
        echo "  ⚠ Pylint warnings (non-blocking)"
    fi
else
    echo "  ⚠ Pylint not available, skipping"
fi

# Summary
echo ""
echo "============================================================"
if [ ${FAILURES} -eq 0 ]; then
    echo "✓ All integrity checks passed"
    exit 0
else
    echo "✗ ${FAILURES} check(s) failed"
    exit 1
fi
