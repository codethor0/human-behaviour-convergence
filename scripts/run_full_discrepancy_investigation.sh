#!/usr/bin/env bash
set -euo pipefail

# FULL DISCREPANCY INVESTIGATION SCRIPT
# Executes all phases of the paranoid investigation
# Run this when the stack is ready: docker compose up -d

REPO="${REPO:-/Users/thor/Projects/human-behaviour-convergence}"
BACKEND="${BACKEND:-http://localhost:8100}"
FRONTEND="${FRONTEND:-http://localhost:3100}"
GRAFANA="${GRAFANA:-http://localhost:3001}"
PROM="${PROM:-http://localhost:9090}"

# Setup proof directory
export RUN_ID=$(date +%Y%m%d_%H%M%S)
export PROOF_DIR="/tmp/hbc_discrepancy_proof_$RUN_ID"
mkdir -p "$PROOF_DIR"
echo "PROOF_DIR=$PROOF_DIR" | tee "$PROOF_DIR/proof_dir.txt"

cd "$REPO"

echo "============================================================"
echo "HBC STATE DISCREPANCY PARANOID INVESTIGATION"
echo "============================================================"
echo "Timestamp: $(date +"%Y-%m-%d %H:%M:%S %Z")"
echo "Proof Dir: $PROOF_DIR"
echo ""

# Phase 2-3: Baseline + Docker Health
echo "[PHASE 2-3] Baseline Capture + Stack Health"
echo "----------------------------------------"
git rev-parse HEAD | tee "$PROOF_DIR/commit.txt"
git status --porcelain=v1 | tee "$PROOF_DIR/git_status.txt"
python3 --version | tee "$PROOF_DIR/python_version.txt"
docker --version 2>&1 | tee "$PROOF_DIR/docker_version.txt" || echo "Docker not available"

# Check stack health
echo ""
echo "Checking stack health..."
if ! curl -fsS "$BACKEND/health" > "$PROOF_DIR/backend_health.json" 2>&1; then
    echo "ERROR: Backend not reachable at $BACKEND"
    echo "Please start stack: docker compose up -d"
    echo "Then wait for readiness and re-run this script"
    exit 1
fi
echo "✓ Backend healthy"
cat "$PROOF_DIR/backend_health.json"

# Frontend routes
echo ""
echo "Checking frontend routes..."
echo "=== FRONTEND ROUTES HTTP STATUS ===" > "$PROOF_DIR/frontend_routes_http.txt"
for r in /forecast /history /live /playground; do
    code=$(curl -sS -o /dev/null -w "%{http_code}" "$FRONTEND$r" 2>&1 || echo "000")
    echo "$r $code" | tee -a "$PROOF_DIR/frontend_routes_http.txt"
    [ "$code" = "200" ] && echo "  ✓ $r OK" || echo "  ✗ $r FAILED ($code)"
done

# Phase 4: Forecast Variance Analysis
echo ""
echo "[PHASE 4] Forecast Variance Analysis (Hash-based)"
echo "----------------------------------------"
export PROOF_DIR
python3 scripts/discrepancy_harness.py 2>&1 | tee "$PROOF_DIR/discrepancy_harness.log"
HARNESS_EXIT=$?

if [ $HARNESS_EXIT -eq 1 ]; then
    echo ""
    echo "[P0] STATE COLLAPSE DETECTED - Proceeding to Phase 7"
    echo "Phase 7: Root Cause Investigation" > "$PROOF_DIR/next_phase.txt"
    P0_DETECTED=1
else
    echo ""
    echo "[OK] Variance detected - Proceeding to Phase 5"
    echo "Phase 5: Metrics Truth Layer" > "$PROOF_DIR/next_phase.txt"
    P0_DETECTED=0
fi

# Phase 5: Metrics Truth Layer
echo ""
echo "[PHASE 5] Metrics Truth Layer"
echo "----------------------------------------"
curl -fsS "$BACKEND/metrics" > "$PROOF_DIR/metrics.txt"

# Count unique region labels
echo "Analyzing metrics region labels..."
grep -E 'behavior_index\{|parent_subindex_value\{|child_subindex_value\{' "$PROOF_DIR/metrics.txt" | \
    grep -oE 'region="[^"]+"' | sort | uniq -c | sort -rn > "$PROOF_DIR/metrics_region_counts.txt"

echo "Region label counts:" | tee "$PROOF_DIR/metrics_region_samples.txt"
head -20 "$PROOF_DIR/metrics_region_counts.txt" | tee -a "$PROOF_DIR/metrics_region_samples.txt"

# Check for None/unknown regions
if grep -q 'region="None"' "$PROOF_DIR/metrics.txt" || grep -q 'region=None' "$PROOF_DIR/metrics.txt"; then
    echo "[P0] Found region=None labels in metrics!" | tee "$PROOF_DIR/p0_region_none.txt"
    grep -E 'region="None"|region=None' "$PROOF_DIR/metrics.txt" | head -10 >> "$PROOF_DIR/p0_region_none.txt"
    P0_DETECTED=1
fi

# Query Prometheus if available
if curl -fsS "$PROM/api/v1/label/region/values" >/dev/null 2>&1; then
    echo "Querying Prometheus for region values..."
    curl -G "$PROM/api/v1/label/region/values" \
        --data-urlencode 'match[]=behavior_index' \
        --data-urlencode 'match[]=parent_subindex_value' \
        --data-urlencode 'match[]=child_subindex_value' \
        > "$PROOF_DIR/prom_region_values.json" 2>&1 || true
fi

# Phase 6: Source Regionality Audit
echo ""
echo "[PHASE 6] Source Regionality Audit"
echo "----------------------------------------"
python3 scripts/source_regionality_audit.py 2>&1 | tee "$PROOF_DIR/source_regionality_audit.log" || true

# Run variance probe if forecasts exist
if [ -f "$PROOF_DIR/forecast_variance_matrix.csv" ]; then
    echo ""
    echo "Running variance probe on forecast data..."
    python3 scripts/variance_probe.py \
        --forecasts-dir "$PROOF_DIR" \
        --output-csv "$PROOF_DIR/variance_probe_report.csv" \
        --output-report "$PROOF_DIR/variance_probe_report.txt" \
        2>&1 | tee "$PROOF_DIR/variance_probe.log" || true
fi

# Phase 7: Root Cause Analysis (if P0 detected)
if [ "$P0_DETECTED" = "1" ]; then
    echo ""
    echo "[PHASE 7] Root Cause Investigation"
    echo "----------------------------------------"
    echo "P0 issues detected. Review evidence in:"
    echo "  - $PROOF_DIR/p0_collapse_detected.txt (if exists)"
    echo "  - $PROOF_DIR/p0_region_none.txt (if exists)"
    echo "  - $PROOF_DIR/discrepancy_harness.log"
    echo "  - $PROOF_DIR/variance_probe_report.txt"
fi

# Generate summary
echo ""
echo "============================================================"
echo "INVESTIGATION COMPLETE"
echo "============================================================"
echo "Proof directory: $PROOF_DIR"
echo ""
echo "Key files:"
echo "  - forecast_variance_matrix.csv: Hash comparison across regions"
echo "  - source_regionality_manifest.json: Source classification"
echo "  - variance_probe_report.txt: Per-source variance analysis"
echo "  - metrics_region_counts.txt: Prometheus region label distribution"
echo ""
if [ "$P0_DETECTED" = "1" ]; then
    echo "[P0] Issues detected - review evidence and proceed to fixes"
else
    echo "[OK] No P0 issues - variance appears correct"
fi
echo ""
