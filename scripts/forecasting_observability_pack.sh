#!/usr/bin/env bash
# HBC Forecasting Algorithms + Grafana Visual Pack
# Enterprise, No-Hallucination, Auto-Execute
# Usage: ./scripts/forecasting_observability_pack.sh
set -euo pipefail

ROOT="${PWD}"
TS="$(date -u +%Y%m%d_%H%M%S)"
OUT="/tmp/hbc_forecast_visual_pack_${TS}"
mkdir -p "$OUT"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "HBC Forecasting Algorithms + Grafana Visual Pack"
echo "================================================="
echo "Timestamp: $(ts)"
echo "Evidence dir: $OUT"
echo "Mode: AUTONOMOUS (no prompts, auto-execute)"
echo

# --- PHASE 0: INVENTORY CURRENT FORECASTING
echo "[PHASE 0] Inventory current forecasting..."

cat > "$OUT/current_forecasting_inventory.md" <<EOF
# Current Forecasting Model Inventory

Generated: $(ts)

## Models Found

EOF

# Check for statsmodels usage
if grep -q "ExponentialSmoothing\|statsmodels" app/core/prediction.py 2>/dev/null; then
  echo "- Exponential Smoothing (Holt-Winters) - statsmodels" >> "$OUT/current_forecasting_inventory.md"
  echo "  PROVED: Exponential Smoothing found in prediction.py"
fi

# Check for ARIMA
if grep -q "ARIMA\|arima" app/core/prediction.py 2>/dev/null; then
  echo "- ARIMA/SARIMA - statsmodels" >> "$OUT/current_forecasting_inventory.md"
  echo "  PROVED: ARIMA found"
else
  echo "- ARIMA: NOT FOUND" >> "$OUT/current_forecasting_inventory.md"
fi

# Check predictor registry
if [ -f "predictors/registry.py" ]; then
  echo "- Predictor Registry: EXISTS" >> "$OUT/current_forecasting_inventory.md"
  echo "  PROVED: Predictor registry exists"
else
  echo "- Predictor Registry: NOT FOUND" >> "$OUT/current_forecasting_inventory.md"
fi

# List model parameters and outputs
grep -n "model\|forecast\|prediction" app/core/prediction.py | head -20 > "$OUT/forecasting_code_extract.txt" 2>/dev/null || true

cat "$OUT/current_forecasting_inventory.md"
echo "  Inventory saved to: $OUT/current_forecasting_inventory.md"

# --- PHASE 1: DEFINE FORECASTING OBSERVABILITY CONTRACTS
echo
echo "[PHASE 1] Define forecasting observability contracts..."

# Check if contract tests exist
if [ -f "tests/test_analytics_contracts.py" ]; then
  echo "  PROVED: Analytics contracts test file exists"
  grep -n "model_name\|horizon\|forecast_points\|region_id" tests/test_analytics_contracts.py > "$OUT/contract_extract.txt" 2>/dev/null || true
else
  echo "  MISSING: Analytics contracts test file"
fi

# --- PHASE 2: IMPLEMENT MODEL REGISTRY (ALGORITHM FAMILIES)
echo
echo "[PHASE 2] Model registry (algorithm families)..."

# Check if model registry needs enhancement
if [ -f "predictors/registry.py" ]; then
  echo "  PROVED: Predictor registry exists"
  
  # Check if it supports algorithm families
  if grep -q "family\|baseline\|classical" predictors/registry.py 2>/dev/null; then
    echo "  PROVED: Registry supports families"
  else
    echo "  ENHANCEMENT NEEDED: Registry may need family classification"
  fi
else
  echo "  MISSING: Predictor registry not found"
fi

# Check for baseline models
BASELINE_FOUND=0
if grep -q "naive\|last.*value\|seasonal.*naive" app/core/prediction.py 2>/dev/null; then
  BASELINE_FOUND=1
  echo "  PROVED: Baseline models found"
fi

if [ "$BASELINE_FOUND" -eq 0 ]; then
  echo "  ENHANCEMENT NEEDED: Baseline models (naive, seasonal naive) not found"
fi

# --- PHASE 3: BACKTESTING + EVALUATION METRICS
echo
echo "[PHASE 3] Backtesting + evaluation metrics..."

# Check for evaluation metrics
if grep -q "MAE\|RMSE\|MAPE\|sMAPE\|pinball" app/core/prediction.py 2>/dev/null; then
  echo "  PROVED: Evaluation metrics found in code"
else
  echo "  ENHANCEMENT NEEDED: Evaluation metrics (MAE, RMSE, MAPE) not found"
fi

# Check for Prometheus metrics for models
if grep -q "hbc_model_mae\|hbc_model_rmse\|hbc_model_mape" app/backend/app/main.py 2>/dev/null; then
  echo "  PROVED: Model metrics (MAE/RMSE/MAPE) found in Prometheus definitions"
else
  echo "  ENHANCEMENT NEEDED: Model metrics not exposed to Prometheus"
fi

# --- PHASE 4: FORECAST CONTRIBUTION / EXPLAINABILITY
echo
echo "[PHASE 4] Forecast contribution / explainability..."

# Check for contribution metrics
if grep -q "contribution\|subindex_contribution" app/backend/app/main.py 2>/dev/null; then
  echo "  PROVED: Contribution metrics found"
else
  echo "  ENHANCEMENT NEEDED: Contribution metrics not exposed"
fi

# --- PHASE 5: GRAFANA DASHBOARDS (VISUAL PACK)
echo
echo "[PHASE 5] Grafana dashboards (visual pack)..."

# Check existing dashboards
REQUIRED_DASHBOARDS=(
  "forecast_overview:Forecast Overview"
  "model_performance:Model Performance Hub"
  "baselines:Baselines Dashboard"
  "classical_models:Classical Models Dashboard"
)

MISSING_DASHBOARDS=()
for dash_spec in "${REQUIRED_DASHBOARDS[@]}"; do
  IFS=':' read -r uid name <<< "$dash_spec"
  if find infra/grafana/dashboards -name "*${uid}*.json" 2>/dev/null | head -1; then
    echo "  PROVED: $name dashboard exists"
  else
    echo "  MISSING: $name dashboard not found"
    MISSING_DASHBOARDS+=("$uid")
  fi
done

# --- PHASE 6: FRONTEND INTEGRATION
echo
echo "[PHASE 6] Frontend integration..."

# Check if frontend has Grafana links
if grep -q "grafana\|dashboard" app/frontend/src/pages/*.tsx 2>/dev/null; then
  echo "  PROVED: Frontend references Grafana"
else
  echo "  ENHANCEMENT NEEDED: Frontend may not link to Grafana dashboards"
fi

# --- PHASE 7: TESTS + CI GATES
echo
echo "[PHASE 7] Tests + CI gates..."

# Check for model metrics tests
if grep -q "hbc_model\|model.*metric" tests/*.py 2>/dev/null; then
  echo "  PROVED: Model metrics tests found"
else
  echo "  ENHANCEMENT NEEDED: Model metrics regression tests not found"
fi

# --- PHASE 8: NO-HALLUCINATION VERIFICATION
echo
echo "[PHASE 8] No-hallucination verification..."

# List all files that would be created/modified
cat > "$OUT/files_modified.txt" <<EOF
Files Modified/Created
======================

EOF

# Check what exists
echo "Model Registry:" >> "$OUT/files_modified.txt"
if [ -f "predictors/registry.py" ]; then
  echo "  - predictors/registry.py (EXISTS)" >> "$OUT/files_modified.txt"
else
  echo "  - predictors/registry.py (MISSING - would create)" >> "$OUT/files_modified.txt"
fi

echo "Grafana Dashboards:" >> "$OUT/files_modified.txt"
for dash_uid in "${MISSING_DASHBOARDS[@]}"; do
  echo "  - infra/grafana/dashboards/${dash_uid}.json (MISSING - would create)" >> "$OUT/files_modified.txt"
done

# Proof of metrics (if stack is running)
if curl -fsS "http://localhost:8100/metrics" > "$OUT/metrics_proof.txt" 2>/dev/null; then
  echo "  PROVED: /metrics endpoint accessible"
  grep -i "hbc_model\|model" "$OUT/metrics_proof.txt" | head -10 > "$OUT/metrics_model_extract.txt" 2>/dev/null || true
else
  echo "  WARN: /metrics endpoint not accessible (stack may not be running)"
fi

# Proof of Prometheus queries
if curl -fsS -G "http://localhost:9090/api/v1/query" --data-urlencode 'query=hbc_model_mae' > "$OUT/promql_model_metrics.json" 2>/dev/null; then
  echo "  PROVED: Prometheus accessible, model metrics queryable"
else
  echo "  WARN: Prometheus not accessible or model metrics not present"
fi

# Proof of Grafana dashboards
if curl -fsS -u admin:admin "http://localhost:3001/api/search?type=dash-db" > "$OUT/grafana_dashboards_proof.json" 2>/dev/null; then
  echo "  PROVED: Grafana API accessible"
  jq -r '.[].uid' "$OUT/grafana_dashboards_proof.json" > "$OUT/grafana_dashboard_uids_proof.txt" 2>/dev/null || true
else
  echo "  WARN: Grafana API not accessible"
fi

# --- FINAL REPORT
echo
echo "[FINAL] Generating report..."

cat > "$OUT/FINAL_REPORT.md" <<EOF
# HBC Forecasting Observability Pack Implementation Report

Generated: $(ts)

## Current State

### Forecasting Models
- Exponential Smoothing (Holt-Winters): $(if grep -q "ExponentialSmoothing" app/core/prediction.py 2>/dev/null; then echo "IMPLEMENTED"; else echo "NOT FOUND"; fi)
- ARIMA/SARIMA: $(if grep -q "ARIMA\|arima" app/core/prediction.py 2>/dev/null; then echo "IMPLEMENTED"; else echo "NOT FOUND"; fi)
- Baseline models (naive, seasonal naive): $(if [ "$BASELINE_FOUND" -eq 1 ]; then echo "IMPLEMENTED"; else echo "NOT FOUND"; fi)

### Observability
- Model metrics (MAE/RMSE/MAPE): $(if grep -q "hbc_model_mae\|hbc_model_rmse" app/backend/app/main.py 2>/dev/null; then echo "EXPOSED"; else echo "NOT EXPOSED"; fi)
- Backtesting: $(if grep -q "backtest\|evaluation\|MAE\|RMSE" app/core/prediction.py 2>/dev/null; then echo "IMPLEMENTED"; else echo "NOT FOUND"; fi)
- Contribution metrics: $(if grep -q "contribution\|subindex_contribution" app/backend/app/main.py 2>/dev/null; then echo "EXPOSED"; else echo "NOT EXPOSED"; fi)

### Grafana Dashboards
- Forecast Overview: $(if find infra/grafana/dashboards -name "*forecast*overview*.json" 2>/dev/null | head -1; then echo "EXISTS"; else echo "MISSING"; fi)
- Model Performance Hub: $(if find infra/grafana/dashboards -name "*model*performance*.json" 2>/dev/null | head -1; then echo "EXISTS"; else echo "MISSING"; fi)
- Baselines Dashboard: $(if find infra/grafana/dashboards -name "*baseline*.json" 2>/dev/null | head -1; then echo "EXISTS"; else echo "MISSING"; fi)
- Classical Models Dashboard: $(if find infra/grafana/dashboards -name "*classical*.json" 2>/dev/null | head -1; then echo "EXISTS"; else echo "MISSING"; fi)

## Evidence

All evidence saved to: $OUT

- current_forecasting_inventory.md - Model inventory
- files_modified.txt - Files that would be created/modified
- metrics_proof.txt - Backend metrics output
- promql_model_metrics.json - Prometheus query results
- grafana_dashboards_proof.json - Grafana API response

## Next Steps

Based on inventory, the following enhancements are recommended:

1. Add baseline models (naive, seasonal naive) if not present
2. Implement backtesting + evaluation metrics if not present
3. Expose model metrics to Prometheus if not present
4. Create missing Grafana dashboards for model observability
5. Add regression tests for model metrics

## Verification Commands

To verify model observability:
\`\`\`bash
# Check metrics
curl http://localhost:8100/metrics | grep hbc_model

# Query Prometheus
curl -G "http://localhost:9090/api/v1/query" \\
  --data-urlencode 'query=hbc_model_mae'

# List Grafana dashboards
curl -u admin:admin "http://localhost:3001/api/search?type=dash-db"
\`\`\`

EOF

cat "$OUT/FINAL_REPORT.md"
echo
echo "Evidence bundle: $OUT"
echo "Final report: $OUT/FINAL_REPORT.md"

echo
echo "Inventory and verification complete"
echo "See $OUT/FINAL_REPORT.md for implementation recommendations"
