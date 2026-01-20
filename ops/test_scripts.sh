#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Quick test script to validate ops scripts work as expected.
# Run this after creating/modifying ops scripts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "Testing ops scripts..."
echo ""

# Make scripts executable
chmod +x ops/*.sh ops/*.py 2>/dev/null || true

# Test 1: check_integrity.sh (may fail if tests fail, that's OK)
echo "1. Testing check_integrity.sh (config validation only)..."
if ./ops/check_integrity.sh --skip-tests --skip-regression 2>&1 | head -20; then
    echo "  ✓ Config validation works"
else
    echo "  ✗ Config validation failed"
fi
echo ""

# Test 2: Regression script syntax
echo "2. Testing run_forecast_regression.py syntax..."
if python3 -m py_compile ops/run_forecast_regression.py 2>&1; then
    echo "  ✓ Python syntax valid"
else
    echo "  ✗ Python syntax error"
    exit 1
fi
echo ""

# Test 3: Support bundle script syntax
echo "3. Testing collect_support_bundle.sh syntax..."
if bash -n ops/collect_support_bundle.sh 2>&1; then
    echo "  ✓ Bash syntax valid"
else
    echo "  ✗ Bash syntax error"
    exit 1
fi
echo ""

# Test 4: Log gap scanner syntax
echo "4. Testing scan_log_gaps.sh syntax..."
if bash -n ops/scan_log_gaps.sh 2>&1; then
    echo "  ✓ Bash syntax valid"
else
    echo "  ✗ Bash syntax error"
    exit 1
fi
echo ""

# Test 5: K8s scripts (if kubectl available)
if command -v kubectl &> /dev/null; then
    echo "5. Testing k8s scripts syntax..."
    if bash -n ops/k8s_health_check.sh && bash -n ops/k8s_apply_safe.sh 2>&1; then
        echo "  ✓ K8s script syntax valid"
    else
        echo "  ✗ K8s script syntax error"
        exit 1
    fi
else
    echo "5. Skipping K8s script tests (kubectl not available)"
fi
echo ""

echo "✅ All script syntax checks passed"
echo ""
echo "Next steps:"
echo "  1. Run: ./ops/check_integrity.sh (full run)"
echo "  2. Run: python3 ops/run_forecast_regression.py --verbose --markdown"
echo "  3. Test breaking config and verify failures are caught"
