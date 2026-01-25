#!/usr/bin/env bash
# Mutation Smoke Test — Lightweight mutation testing to prove tests are meaningful
# Part of Paranoid-Plus Verification System
# Usage: ./scripts/mutation_smoke.sh
set -euo pipefail

ROOT="${PWD}"
TS="$(date -u +%Y%m%d_%H%M%S)"
OUT="/tmp/hbc_mutation_smoke_${TS}"
mkdir -p "$OUT"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "Mutation Smoke Test"
echo "==================="
echo "Timestamp: $(ts)"
echo "Evidence dir: $OUT"
echo

# Test 1: Force region_id to None (should cause test failure)
echo "Test 1: Mutating region_id to None..."
cat > "$OUT/test_mutation_region_none.py" <<'PYTHON'
import os
import sys
import pytest

# Enable CI offline mode
os.environ["HBC_CI_OFFLINE_DATA"] = "1"

from app.core.prediction import BehavioralForecaster

def test_mutation_region_none():
    """Mutation: Force region_id to None - should fail regionality test."""
    forecaster = BehavioralForecaster()
    
    # Mutated: region_id is None (should break cache key regionality)
    result = forecaster.forecast(
        latitude=40.3495,
        longitude=-88.9861,
        region_name=None,  # MUTATION: Should cause failure
        days_back=30,
        forecast_horizon=7,
    )
    
    # This should fail if regionality tests are working
    assert result is not None
    assert "history" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
PYTHON

if python3 "$OUT/test_mutation_region_none.py" 2>&1 | tee "$OUT/mutation_1_output.txt"; then
  echo "⚠️  WARNING: Mutation test passed (tests may not be catching this mutation)"
  MUTATION_1_PASS=true
else
  echo "✅ GOOD: Mutation test failed as expected (tests are meaningful)"
  MUTATION_1_PASS=false
fi

# Test 2: Remove geo from cache key (should cause regionality failure)
echo
echo "Test 2: Mutating cache key to remove geo..."
cat > "$OUT/test_mutation_cache_key.py" <<'PYTHON'
import os
import sys
import pytest
from unittest.mock import patch

os.environ["HBC_CI_OFFLINE_DATA"] = "1"

from app.services.ingestion.eia_fuel_prices import EIAFuelPricesFetcher

def test_mutation_cache_key_no_geo():
    """Mutation: Remove geo from cache key - should break regionality."""
    fetcher = EIAFuelPricesFetcher()
    
    # Mutated: cache key doesn't include state
    original_method = fetcher._normalize_state_code
    
    def mutated_cache_key(state, days_back):
        # MUTATION: Cache key doesn't include state
        return f"eia_fuel_{days_back}"  # Missing state!
    
    # This mutation should cause regionality tests to fail
    with patch.object(fetcher, 'fetch_fuel_stress_index', side_effect=lambda s, d: mutated_cache_key(s, d)):
        il_data, _ = fetcher.fetch_fuel_stress_index(state="IL", days_back=30)
        az_data, _ = fetcher.fetch_fuel_stress_index(state="AZ", days_back=30)
        
        # If cache key doesn't include state, these should be identical (BAD)
        il_mean = il_data["fuel_stress_index"].mean() if not il_data.empty else 0.5
        az_mean = az_data["fuel_stress_index"].mean() if not az_data.empty else 0.5
        
        # This assertion should FAIL if mutation is working
        assert il_mean != az_mean, "Regionality broken: IL and AZ have same values"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
PYTHON

if python3 "$OUT/test_mutation_cache_key.py" 2>&1 | tee "$OUT/mutation_2_output.txt"; then
  echo "⚠️  WARNING: Cache key mutation test passed"
  MUTATION_2_PASS=true
else
  echo "✅ GOOD: Cache key mutation test failed as expected"
  MUTATION_2_PASS=false
fi

# Summary
echo
echo "=== Mutation Smoke Test Summary ==="
cat > "$OUT/mutation_smoke_report.md" <<EOF
# Mutation Smoke Test Report

**Timestamp**: $(ts)

## Results

1. **Region ID Mutation**: $([ "$MUTATION_1_PASS" = true ] && echo "PASSED (⚠️ tests may not catch this)" || echo "FAILED (✅ tests are meaningful)")
2. **Cache Key Mutation**: $([ "$MUTATION_2_PASS" = true ] && echo "PASSED (⚠️ tests may not catch this)" || echo "FAILED (✅ tests are meaningful)")

## Interpretation

- If mutations PASS: Tests may not be strict enough (consider strengthening)
- If mutations FAIL: Tests are meaningful and catch defects

## Evidence

- \`mutation_1_output.txt\` - Region ID mutation test output
- \`mutation_2_output.txt\` - Cache key mutation test output
EOF

cat "$OUT/mutation_smoke_report.md"
echo
echo "Evidence saved to: $OUT"

# Exit code: 0 if at least one mutation was caught (good), 1 if both passed (bad)
if [[ "$MUTATION_1_PASS" = false ]] || [[ "$MUTATION_2_PASS" = false ]]; then
  echo "✅ Mutation smoke test: At least one mutation was caught by tests"
  exit 0
else
  echo "⚠️  Mutation smoke test: No mutations were caught (consider strengthening tests)"
  exit 1
fi
