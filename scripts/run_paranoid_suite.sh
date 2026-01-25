#!/usr/bin/env bash
# Paranoid-Plus Verification Suite Runner
# Runs property-based, metamorphic, and mutation tests with evidence collection
# Usage: ./scripts/run_paranoid_suite.sh

set -euo pipefail

ROOT="${PWD}"
TS="$(date -u +%Y%m%d_%H%M%S)"
OUT="/tmp/hbc_paranoid_plus_${TS}"
REPORT="/tmp/HBC_PARANOID_PLUS_REPORT.md"

mkdir -p "$OUT"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "Paranoid-Plus Verification Suite"
echo "================================="
echo "Timestamp: $(ts)"
echo "Evidence dir: $OUT"
echo

# Initialize report
cat > "$REPORT" <<EOF
# HBC Paranoid-Plus Verification Report

**Generated**: $(ts)
**Repo**: $ROOT
**Evidence Directory**: $OUT

## Properties Tested

- **P1**: Regionality - Different regions produce different outputs for regional indices
- **P2**: Determinism - Same inputs produce identical outputs in CI offline mode
- **P3**: Cache key regionality - Regional sources include geo in cache keys
- **P4**: Metrics truth - After forecasting N regions, metrics show N unique region labels
- **P5**: No label collapse - No region="None"; no "unknown_*" explosion
- **P6**: Metamorphic monotonicity - Input changes produce expected output changes
- **P7**: Data quality - Values are in valid ranges, no NaNs

## Test Results

EOF

# Run property-based tests
echo "[PHASE B] Running property-based tests..."
if HBC_CI_OFFLINE_DATA=1 pytest tests/test_property_invariants.py -v --tb=short 2>&1 | tee "$OUT/property_tests.log"; then
  echo "✅ Property tests PASSED" | tee -a "$REPORT"
  PROPERTY_PASS=true
else
  echo "❌ Property tests FAILED" | tee -a "$REPORT"
  PROPERTY_PASS=false
fi

# Run metamorphic tests
echo
echo "[PHASE C] Running metamorphic tests..."
if HBC_CI_OFFLINE_DATA=1 pytest tests/test_metamorphic_regionality.py -v --tb=short 2>&1 | tee "$OUT/metamorphic_tests.log"; then
  echo "✅ Metamorphic tests PASSED" | tee -a "$REPORT"
  METAMORPHIC_PASS=true
else
  echo "❌ Metamorphic tests FAILED" | tee -a "$REPORT"
  METAMORPHIC_PASS=false
fi

# Run paranoid metrics contracts tests
echo
echo "[PHASE E] Running paranoid metrics contracts tests..."
if pytest tests/test_metrics_contracts_paranoid.py -v --tb=short 2>&1 | tee "$OUT/metrics_contracts_tests.log"; then
  echo "✅ Metrics contracts tests PASSED" | tee -a "$REPORT"
  METRICS_PASS=true
else
  echo "❌ Metrics contracts tests FAILED" | tee -a "$REPORT"
  METRICS_PASS=false
fi

# Run mutation smoke test
echo
echo "[PHASE D] Running mutation smoke test..."
if bash scripts/mutation_smoke.sh 2>&1 | tee "$OUT/mutation_smoke.log"; then
  echo "✅ Mutation smoke test PASSED (mutations were caught)" | tee -a "$REPORT"
  MUTATION_PASS=true
else
  echo "⚠️  Mutation smoke test: Mutations not caught (tests may need strengthening)" | tee -a "$REPORT"
  MUTATION_PASS=false
fi

# Generate summary
echo >> "$REPORT"
echo "## Summary" >> "$REPORT"
echo >> "$REPORT"
echo "| Test Suite | Status |" >> "$REPORT"
echo "|------------|--------|" >> "$REPORT"
echo "| Property-based (P1-P7) | $([ "$PROPERTY_PASS" = true ] && echo "✅ PASS" || echo "❌ FAIL") |" >> "$REPORT"
echo "| Metamorphic | $([ "$METAMORPHIC_PASS" = true ] && echo "✅ PASS" || echo "❌ FAIL") |" >> "$REPORT"
echo "| Metrics contracts | $([ "$METRICS_PASS" = true ] && echo "✅ PASS" || echo "❌ FAIL") |" >> "$REPORT"
echo "| Mutation smoke | $([ "$MUTATION_PASS" = true ] && echo "✅ PASS" || echo "⚠️  WARN") |" >> "$REPORT"
echo >> "$REPORT"

# Create BUGS.md if any failures
if [[ "$PROPERTY_PASS" = false ]] || [[ "$METAMORPHIC_PASS" = false ]] || [[ "$METRICS_PASS" = false ]]; then
  cat > "$OUT/BUGS.md" <<EOF
# Paranoid-Plus Verification Bugs

**Generated**: $(ts)

## Failing Properties

EOF

  if [[ "$PROPERTY_PASS" = false ]]; then
    echo "- **Property tests failed**: See $OUT/property_tests.log" >> "$OUT/BUGS.md"
    echo "  - Check which properties (P1-P7) failed" >> "$OUT/BUGS.md"
    echo "  - Minimal reproduction: \`HBC_CI_OFFLINE_DATA=1 pytest tests/test_property_invariants.py -v\`" >> "$OUT/BUGS.md"
  fi

  if [[ "$METAMORPHIC_PASS" = false ]]; then
    echo "- **Metamorphic tests failed**: See $OUT/metamorphic_tests.log" >> "$OUT/BUGS.md"
    echo "  - Check which metamorphic transformations failed" >> "$OUT/BUGS.md"
    echo "  - Minimal reproduction: \`HBC_CI_OFFLINE_DATA=1 pytest tests/test_metamorphic_regionality.py -v\`" >> "$OUT/BUGS.md"
  fi

  if [[ "$METRICS_PASS" = false ]]; then
    echo "- **Metrics contracts failed**: See $OUT/metrics_contracts_tests.log" >> "$OUT/BUGS.md"
    echo "  - Check which metrics contracts were violated" >> "$OUT/BUGS.md"
    echo "  - Minimal reproduction: \`pytest tests/test_metrics_contracts_paranoid.py -v\`" >> "$OUT/BUGS.md"
  fi

  echo >> "$OUT/BUGS.md"
  echo "## Evidence" >> "$OUT/BUGS.md"
  echo "- All test logs: $OUT/" >> "$OUT/BUGS.md"
fi

# Final verdict
echo
echo "=== Paranoid-Plus Verification Summary ==="
cat "$REPORT"
echo
echo "Evidence saved to: $OUT"
echo "Report saved to: $REPORT"

# Exit code
if [[ "$PROPERTY_PASS" = true ]] && [[ "$METAMORPHIC_PASS" = true ]] && [[ "$METRICS_PASS" = true ]]; then
  echo "✅ All paranoid verification tests PASSED"
  exit 0
else
  echo "❌ Some paranoid verification tests FAILED - see $OUT/BUGS.md"
  exit 1
fi
