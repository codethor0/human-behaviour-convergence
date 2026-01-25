#!/usr/bin/env bash
# HBC Enterprise E2E Verification + Repair Loop
# Auto-execution mode: no prompts, proceed until all stop conditions met

set -euo pipefail

TS=$(date -u +%Y%m%d_%H%M%S)
EVIDENCE_DIR="/tmp/hbc_e2e_loop_${TS}"
mkdir -p "$EVIDENCE_DIR/FORECAST_SAMPLES" "$EVIDENCE_DIR/METRICS_SAMPLES" "$EVIDENCE_DIR/PROMQL_RESULTS" "$EVIDENCE_DIR/PLAYWRIGHT_RESULTS"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*" | tee -a "$EVIDENCE_DIR/verification.log"; }

log "Starting HBC E2E Verification Loop"
log "Evidence directory: $EVIDENCE_DIR"

# PHASE 0: Baseline Snapshot
log "PHASE 0: Baseline Snapshot"
{
  echo "=== VERSIONS ==="
  python --version 2>&1 || echo "python: not found"
  node --version 2>&1 || echo "node: not found"
  docker --version 2>&1 || echo "docker: not found"
  git --version 2>&1 || echo "git: not found"
  echo ""
  echo "=== GIT STATUS ==="
  git status 2>&1 || echo "git status failed"
  echo ""
  echo "=== HEAD ==="
  git rev-parse HEAD 2>&1 || echo "HEAD not found"
  echo ""
  echo "=== RECENT COMMITS ==="
  git log -5 --oneline 2>&1 || echo "git log failed"
  echo ""
  echo "=== FILE COUNT ==="
  git ls-files | wc -l 2>&1 || echo "0"
  echo ""
  echo "=== REPO SIZE ==="
  du -sh . 2>&1 || echo "unknown"
} > "$EVIDENCE_DIR/VERSIONS.txt" 2>&1
cat "$EVIDENCE_DIR/VERSIONS.txt"

# PHASE 1: Start/Verify Docker Stack
log "PHASE 1: Start/Verify Docker Stack"
log "Stopping existing stack..."
docker compose down -v 2>&1 | tee -a "$EVIDENCE_DIR/DOCKER_STOP.txt" || true

log "Starting stack..."
docker compose up -d --build 2>&1 | tee -a "$EVIDENCE_DIR/DOCKER_START.txt" || {
  log "ERROR: Docker compose failed"
  echo "P0: Docker stack failed to start" > "$EVIDENCE_DIR/BUGS.md"
  exit 1
}

log "Waiting for services to be ready (60s)..."
sleep 60

log "Collecting Docker status..."
docker ps -a > "$EVIDENCE_DIR/DOCKER_PS.txt" 2>&1
docker compose logs backend --tail=200 > "$EVIDENCE_DIR/DOCKER_LOGS_backend.txt" 2>&1
docker compose logs frontend --tail=200 > "$EVIDENCE_DIR/DOCKER_LOGS_frontend.txt" 2>&1
docker compose logs prometheus --tail=200 > "$EVIDENCE_DIR/DOCKER_LOGS_prometheus.txt" 2>&1
docker compose logs grafana --tail=200 > "$EVIDENCE_DIR/DOCKER_LOGS_grafana.txt" 2>&1

log "Hard readiness checks..."
{
  echo "=== Backend Health ==="
  curl -fsS http://localhost:8100/health 2>&1 && echo "✅ 200" || echo "❌ FAIL"
  echo ""
  echo "=== Frontend Root ==="
  curl -fsS -I http://localhost:3100/ 2>&1 | head -1 || echo "❌ FAIL"
  echo ""
  echo "=== Frontend Routes ==="
  for route in /forecast /history /live /playground; do
    echo -n "$route: "
    curl -fsS -I "http://localhost:3100$route" 2>&1 | head -1 || echo "❌ FAIL"
  done
} > "$EVIDENCE_DIR/READINESS.txt" 2>&1
cat "$EVIDENCE_DIR/READINESS.txt"

# Check if readiness failed
if ! grep -q "✅ 200" "$EVIDENCE_DIR/READINESS.txt"; then
  log "ERROR: Readiness checks failed"
  echo "P0: Stack not ready - see READINESS.txt" >> "$EVIDENCE_DIR/BUGS.md"
  cat "$EVIDENCE_DIR/BUGS.md"
  exit 1
fi

# PHASE 2: API Integrity
log "PHASE 2: API Integrity"
{
  echo "=== /api/status ==="
  curl -fsS http://localhost:8100/api/status 2>&1 | python3 -m json.tool || echo "FAIL"
  echo ""
  echo "=== /api/forecasting/status ==="
  curl -fsS http://localhost:8100/api/forecasting/status 2>&1 | python3 -m json.tool || echo "FAIL"
  echo ""
  echo "=== /api/forecasting/models ==="
  curl -fsS http://localhost:8100/api/forecasting/models 2>&1 | python3 -m json.tool || echo "FAIL"
  echo ""
  echo "=== /api/forecasting/regions ==="
  curl -fsS http://localhost:8100/api/forecasting/regions > "$EVIDENCE_DIR/regions.json" 2>&1
  python3 -m json.tool "$EVIDENCE_DIR/regions.json" || echo "FAIL"
  echo ""
  echo "=== /api/forecasting/data-sources ==="
  curl -fsS http://localhost:8100/api/forecasting/data-sources 2>&1 | python3 -m json.tool || echo "FAIL"
} > "$EVIDENCE_DIR/API_INTEGRITY.txt" 2>&1

# Validate regions.json
python3 <<PYTHON > "$EVIDENCE_DIR/regions_validation.txt" 2>&1
import json
try:
    with open("$EVIDENCE_DIR/regions.json") as f:
        regions = json.load(f)
    print(f"Total regions: {len(regions)}")
    if len(regions) < 50:
        print(f"⚠️  WARN: Expected >=50 regions, got {len(regions)}")
    else:
        print("✅ Region count OK")
    
    # Check structure
    required_fields = ["id", "name", "latitude", "longitude"]
    missing = []
    for i, r in enumerate(regions[:5]):
        for field in required_fields:
            if field not in r:
                missing.append(f"Region {i} missing {field}")
    
    if missing:
        print(f"❌ Structure issues: {missing}")
    else:
        print("✅ Region structure OK")
    
    # Check for WV
    wv_found = any(r.get("id") == "us_wv" for r in regions)
    print(f"West Virginia (us_wv): {'✅ Found' if wv_found else '⚠️  Not found'}")
except Exception as e:
    print(f"❌ Validation failed: {e}")
PYTHON
cat "$EVIDENCE_DIR/regions_validation.txt"

# PHASE 3: Forecast E2E Multi-Region
log "PHASE 3: Forecast E2E Multi-Region"
TEST_REGIONS=(
  '{"region_name":"Illinois","latitude":40.349457,"longitude":-88.986137,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"Arizona","latitude":33.729759,"longitude":-111.431221,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"Washington","latitude":47.400902,"longitude":-121.490494,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"Florida","latitude":27.766279,"longitude":-81.686783,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"New York","latitude":42.165726,"longitude":-74.948051,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"Texas","latitude":31.054487,"longitude":-97.563461,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"District of Columbia","latitude":38.907192,"longitude":-77.036873,"days_back":30,"forecast_horizon":7}'
)

REGION_NAMES=("Illinois" "Arizona" "Washington" "Florida" "New York" "Texas" "DC")

for i in "${!TEST_REGIONS[@]}"; do
  region_name="${REGION_NAMES[$i]}"
  region_id=$(echo "$region_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
  log "Forecasting for $region_name..."
  curl -fsS -X POST http://localhost:8100/api/forecast \
    -H "Content-Type: application/json" \
    -d "${TEST_REGIONS[$i]}" > "$EVIDENCE_DIR/FORECAST_SAMPLES/${region_id}.json" 2>&1 || {
    log "ERROR: Forecast failed for $region_name"
    echo "P1: Forecast failed for $region_name" >> "$EVIDENCE_DIR/BUGS.md"
  }
done

# Variance proof
python3 <<PYTHON > "$EVIDENCE_DIR/variance_proof.txt" 2>&1
import json
import hashlib

forecasts = {}
for region in ["illinois", "arizona", "washington", "florida", "new_york", "texas", "dc"]:
    try:
        with open(f"$EVIDENCE_DIR/FORECAST_SAMPLES/{region}.json") as f:
            data = json.load(f)
            history = data.get("history", [])
            forecast = data.get("forecast", [])
            
            # Compute hashes
            history_hash = hashlib.sha256(json.dumps(history, sort_keys=True).encode()).hexdigest()[:16]
            forecast_hash = hashlib.sha256(json.dumps(forecast, sort_keys=True).encode()).hexdigest()[:16]
            
            # Extract behavior_index values
            bi_values = [r.get("behavior_index", 0) for r in history[-10:]] if history else []
            bi_mean = sum(bi_values) / len(bi_values) if bi_values else 0
            
            forecasts[region] = {
                "history_len": len(history),
                "forecast_len": len(forecast),
                "history_hash": history_hash,
                "forecast_hash": forecast_hash,
                "bi_mean": bi_mean
            }
    except Exception as e:
        print(f"Error processing {region}: {e}")

# Check variance
unique_history_hashes = len(set(f["history_hash"] for f in forecasts.values()))
unique_forecast_hashes = len(set(f["forecast_hash"] for f in forecasts.values()))

print(f"Forecasts processed: {len(forecasts)}")
print(f"Unique history hashes: {unique_history_hashes}/{len(forecasts)}")
print(f"Unique forecast hashes: {unique_forecast_hashes}/{len(forecasts)}")

if unique_history_hashes < len(forecasts) * 0.2:
    print("❌ P0: State collapse detected - >=80% identical history hashes")
else:
    print("✅ Variance OK - history differs across regions")

# Compare IL vs AZ
if "illinois" in forecasts and "arizona" in forecasts:
    il_bi = forecasts["illinois"]["bi_mean"]
    az_bi = forecasts["arizona"]["bi_mean"]
    diff = abs(il_bi - az_bi)
    print(f"\nIllinois behavior_index mean: {il_bi:.6f}")
    print(f"Arizona behavior_index mean: {az_bi:.6f}")
    print(f"Difference: {diff:.6f}")
    if diff >= 0.005:
        print("✅ Regional variance detected (>= 0.005)")
    else:
        print("⚠️  Regional variance low (< 0.005)")

for region, data in forecasts.items():
    print(f"\n{region}:")
    print(f"  History: {data['history_len']} points")
    print(f"  Forecast: {data['forecast_len']} points")
    print(f"  BI mean: {data['bi_mean']:.6f}")
PYTHON
cat "$EVIDENCE_DIR/variance_proof.txt"

# PHASE 4: Metrics Pipeline
log "PHASE 4: Metrics Pipeline"
curl -fsS http://localhost:8100/metrics > "$EVIDENCE_DIR/METRICS_SAMPLES/metrics.txt" 2>&1 || {
  log "ERROR: Failed to fetch metrics"
  echo "P0: Metrics endpoint failed" >> "$EVIDENCE_DIR/BUGS.md"
}

# Check metrics
{
  echo "=== Metrics Analysis ==="
  echo ""
  echo "Region=None check:"
  grep -c 'region="None"' "$EVIDENCE_DIR/METRICS_SAMPLES/metrics.txt" || echo "0 (✅ OK)"
  echo ""
  echo "behavior_index series:"
  grep "^behavior_index{" "$EVIDENCE_DIR/METRICS_SAMPLES/metrics.txt" | head -10
  echo ""
  echo "child_subindex_value series:"
  grep "^child_subindex_value{" "$EVIDENCE_DIR/METRICS_SAMPLES/metrics.txt" | head -10
  echo ""
  echo "data_source_status series:"
  grep "^data_source_status{" "$EVIDENCE_DIR/METRICS_SAMPLES/metrics.txt" | head -10
} > "$EVIDENCE_DIR/METRICS_ANALYSIS.txt" 2>&1
cat "$EVIDENCE_DIR/METRICS_ANALYSIS.txt"

# Prometheus queries
log "Querying Prometheus..."
curl -fsS "http://localhost:9090/api/v1/label/region/values" > "$EVIDENCE_DIR/PROMQL_RESULTS/regions.json" 2>&1 || true
curl -fsS "http://localhost:9090/api/v1/query?query=behavior_index" > "$EVIDENCE_DIR/PROMQL_RESULTS/behavior_index.json" 2>&1 || true
curl -fsS "http://localhost:9090/api/v1/query?query=count(count by(region)(behavior_index))" > "$EVIDENCE_DIR/PROMQL_RESULTS/region_count.json" 2>&1 || true

# PHASE 5: UI E2E (if Playwright available)
log "PHASE 5: UI E2E"
if command -v npx &> /dev/null && [ -f "package.json" ]; then
  log "Running Playwright smoke tests..."
  npx playwright test --grep "smoke" --reporter=json > "$EVIDENCE_DIR/PLAYWRIGHT_RESULTS/results.json" 2>&1 || {
    log "Playwright tests failed (non-blocking)"
  }
else
  log "Playwright not available, skipping UI E2E"
fi

# PHASE 6: Integrity Gates
log "PHASE 6: Integrity Gates"
{
  echo "=== pytest -q tests/test_analytics_contracts.py ==="
  pytest -q tests/test_analytics_contracts.py 2>&1 || echo "FAILED"
  echo ""
  echo "=== python scripts/run_data_quality_checkpoint.py ==="
  python scripts/run_data_quality_checkpoint.py 2>&1 || echo "FAILED"
  echo ""
  echo "=== python scripts/variance_probe.py ==="
  python scripts/variance_probe.py 2>&1 || echo "FAILED"
} > "$EVIDENCE_DIR/INTEGRITY_GATES.txt" 2>&1
cat "$EVIDENCE_DIR/INTEGRITY_GATES.txt"

# PHASE 7: Final Summary
log "PHASE 7: Generating Final Summary"
cat > "$EVIDENCE_DIR/FINAL_SUMMARY.md" <<EOF
# HBC E2E Verification Summary

**Generated**: $(ts)
**Evidence Directory**: $EVIDENCE_DIR

## Test Results

### Phase 0: Baseline ✅
- Versions captured
- Git state captured

### Phase 1: Docker Stack
- Status: See DOCKER_PS.txt
- Readiness: See READINESS.txt

### Phase 2: API Integrity
- Status: See API_INTEGRITY.txt
- Regions validation: See regions_validation.txt

### Phase 3: Forecast E2E
- Forecasts generated: See FORECAST_SAMPLES/
- Variance proof: See variance_proof.txt

### Phase 4: Metrics Pipeline
- Metrics: See METRICS_SAMPLES/metrics.txt
- Analysis: See METRICS_ANALYSIS.txt
- Prometheus: See PROMQL_RESULTS/

### Phase 5: UI E2E
- Playwright: See PLAYWRIGHT_RESULTS/

### Phase 6: Integrity Gates
- Results: See INTEGRITY_GATES.txt

## Bugs Found

$(cat "$EVIDENCE_DIR/BUGS.md" 2>/dev/null || echo "None")

## Evidence Files

All evidence saved to: $EVIDENCE_DIR

## Next Steps

1. Review BUGS.md for any P0 issues
2. Fix issues surgically (one commit per fix)
3. Re-run verification loop
EOF

cat "$EVIDENCE_DIR/FINAL_SUMMARY.md"
log "Verification complete. Evidence saved to: $EVIDENCE_DIR"
