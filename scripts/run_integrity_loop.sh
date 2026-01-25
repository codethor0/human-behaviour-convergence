#!/usr/bin/env bash
set -euo pipefail

# Integrity Loop - Run repeatedly until data integrity is intact
# This script validates the entire stack end-to-end and produces evidence bundles

ROOT="${PWD}"
TS="$(date -u +%Y%m%d_%H%M%S)"
OUT="/tmp/hbc_integrity_loop_${TS}"
REPORT="/tmp/HBC_INTEGRITY_LOOP_REPORT.md"
BUGS_FILE="$OUT/BUGS.md"
CONSECUTIVE_PASSES=0
REQUIRED_CONSECUTIVE_PASSES=3

mkdir -p "$OUT"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "# HBC Integrity Loop Report" > "$REPORT"
echo "- Generated: $(ts)" >> "$REPORT"
echo "- Repo: $ROOT" >> "$REPORT"
echo "- Evidence dir: $OUT" >> "$REPORT"
echo "- Required consecutive passes: $REQUIRED_CONSECUTIVE_PASSES" >> "$REPORT"
echo >> "$REPORT"

# --- Helpers
check_url() {
  local url="$1" name="$2"
  local code
  code="$(curl -sS -o "$OUT/${name}.body" -w "%{http_code}" "$url" 2>&1 || echo "000")"
  printf "%s\t%s\tHTTP %s\n" "$(ts)" "$url" "$code" >> "$OUT/readiness.tsv"
  if [[ "$code" != "200" ]]; then
    echo "FAIL: $url -> HTTP $code" >> "$REPORT"
    return 1
  fi
  echo "OK: $url -> HTTP $code" >> "$REPORT"
  return 0
}

api_get() {
  local url="$1" out="$2"
  local code
  code="$(curl -sS -o "$OUT/${out}" -w "%{http_code}" "$url" 2>&1 || echo "000")"
  echo "GET $url -> HTTP $code" >> "$REPORT"
  [[ "$code" == "200" ]]
}

get_region_id() {
  local region_name="$1"
  python3 -c "
import json, sys
try:
    with open('$OUT/api_regions_direct.json', 'r') as f:
        regions = json.load(f)
    for r in regions:
        if r.get('name', '').lower() == '${region_name}'.lower():
            print(r['id'])
            sys.exit(0)
    sys.exit(1)
except:
    sys.exit(1)
" 2>/dev/null || echo ""
}

post_forecast() {
  local region_id="$1" region_name="$2" out="$3"
  local code
  code="$(curl -sS -o "$OUT/${out}.json" -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -X POST "http://localhost:8100/api/forecast" \
    -d "{\"region_id\":\"${region_id}\",\"region_name\":\"${region_name}\",\"days_back\":30,\"forecast_horizon\":7}" \
    2>&1 || echo "000")"
  echo "POST /api/forecast ${region_name} -> HTTP $code" >> "$REPORT"
  [[ "$code" == "200" ]]
}

fail_with_bug() {
  local phase="$1" invariant="$2" details="$3"
  echo >> "$BUGS_FILE"
  echo "## Bug: $invariant" >> "$BUGS_FILE"
  echo "- Phase: $phase" >> "$BUGS_FILE"
  echo "- Timestamp: $(ts)" >> "$BUGS_FILE"
  echo "- Details: $details" >> "$BUGS_FILE"
  echo "- Evidence: See $OUT/" >> "$BUGS_FILE"
  echo >> "$BUGS_FILE"
  echo "FAIL: $invariant in phase $phase" >> "$REPORT"
  return 1
}

# --- Phase 0: Clean Start
echo "## Phase 0 — Clean Start" >> "$REPORT"
if ! git diff --quiet HEAD 2>/dev/null; then
  echo "WARN: Git working directory is not clean" >> "$REPORT"
fi

docker compose down -v >/dev/null 2>&1 || true
docker compose up -d --build

# Wait for services
echo "Waiting for services..." >> "$REPORT"
for i in {1..60}; do
  if curl -fsS "http://localhost:8100/health" >/dev/null 2>&1 && \
     curl -fsS "http://localhost:3100/" >/dev/null 2>&1; then
    break
  fi
  sleep 2
  if [[ $i -eq 60 ]]; then
    fail_with_bug "Phase 0" "I1" "Services did not become ready within 120 seconds"
    exit 1
  fi
done
sleep 3  # Extra buffer

# --- Phase 1: Readiness Gates
echo >> "$REPORT"
echo "## Phase 1 — Readiness Gates (I1)" >> "$REPORT"
check_url "http://localhost:8100/health" "backend_health" || \
  fail_with_bug "Phase 1" "I1" "Backend health check failed" || exit 1
check_url "http://localhost:3100/" "frontend_root" || \
  fail_with_bug "Phase 1" "I1" "Frontend root failed" || exit 1
check_url "http://localhost:3100/forecast" "route_forecast" || \
  fail_with_bug "Phase 1" "I1" "Route /forecast failed" || exit 1
check_url "http://localhost:3100/history" "route_history" || \
  fail_with_bug "Phase 1" "I1" "Route /history failed" || exit 1
check_url "http://localhost:3100/live" "route_live" || \
  fail_with_bug "Phase 1" "I1" "Route /live failed" || exit 1
check_url "http://localhost:3100/playground" "route_playground" || \
  fail_with_bug "Phase 1" "I1" "Route /playground failed" || exit 1

# --- Phase 2: API Baseline + Proxy Parity
echo >> "$REPORT"
echo "## Phase 2 — API Baseline + Proxy Parity (I2)" >> "$REPORT"
api_get "http://localhost:8100/api/forecasting/regions" "api_regions_direct.json" || \
  fail_with_bug "Phase 2" "I2" "Direct regions API failed" || exit 1
api_get "http://localhost:3100/api/forecasting/regions" "api_regions_proxy.json" || \
  fail_with_bug "Phase 2" "I2" "Proxy regions API failed (proxy/base mismatch)" || exit 1

# Compare proxy vs direct
if ! diff -q "$OUT/api_regions_direct.json" "$OUT/api_regions_proxy.json" >/dev/null 2>&1; then
  fail_with_bug "Phase 2" "I2" "Proxy and direct regions responses differ"
  exit 1
fi

# --- Phase 3: Seed Multi-Region Forecasts (10 regions)
echo >> "$REPORT"
echo "## Phase 3 — Seed Multi-Region Forecasts (I3)" >> "$REPORT"
REGIONS=(
  "Illinois:us_il"
  "Arizona:us_az"
  "Florida:us_fl"
  "Washington:us_wa"
  "California:us_ca"
  "New York:us_ny"
  "Texas:us_tx"
  "Minnesota:us_mn"
  "Colorado:us_co"
  "London:city_london"
)

> "$OUT/forecast_seed_results.csv"
echo "region_name,region_id,behavior_index,economic_stress,fuel_stress,environmental_stress,political_stress,response_time_ms,has_sub_indices" >> "$OUT/forecast_seed_results.csv"

forecast_count=0
for region_pair in "${REGIONS[@]}"; do
  IFS=':' read -r region_name region_id <<< "$region_pair"
  
  # Look up actual region_id if needed
  if [[ -z "$region_id" ]] || [[ "$region_id" == "unknown" ]]; then
    region_id=$(get_region_id "$region_name")
    if [[ -z "$region_id" ]]; then
      echo "WARN: Could not find region_id for $region_name, skipping" >> "$REPORT"
      continue
    fi
  fi
  
  start_time=$(date +%s%N)
  if post_forecast "$region_id" "$region_name" "forecast_${region_id}"; then
    end_time=$(date +%s%N)
    response_time=$(( (end_time - start_time) / 1000000 ))
    
    # Extract metrics from forecast
    python3 - <<PY > "$OUT/forecast_${region_id}_metrics.txt" 2>/dev/null || true
import json, sys
try:
    with open('$OUT/forecast_${region_id}.json', 'r') as f:
        data = json.load(f)
    
    # Extract from first forecast point
    forecast = data.get('forecast', [])
    if forecast and isinstance(forecast[0], dict):
        first = forecast[0]
        bi = first.get('behavior_index', 'N/A')
        sub_indices = first.get('sub_indices') or first.get('subIndices', {})
        child_indices = first.get('child_sub_indices') or first.get('childSubIndices', {})
        
        economic = sub_indices.get('economic_stress', 'N/A') if isinstance(sub_indices, dict) else 'N/A'
        fuel = child_indices.get('fuel_stress', 'N/A') if isinstance(child_indices, dict) else 'N/A'
        env = sub_indices.get('environmental_stress', 'N/A') if isinstance(sub_indices, dict) else 'N/A'
        pol = sub_indices.get('political_stress', 'N/A') if isinstance(sub_indices, dict) else 'N/A'
        has_sub = 'yes' if (sub_indices or child_indices) else 'no'
        
        print(f"{bi},{economic},{fuel},{env},{pol},{has_sub}")
    else:
        print("N/A,N/A,N/A,N/A,N/A,no")
except:
    print("N/A,N/A,N/A,N/A,N/A,no")
PY
    
    metrics=$(cat "$OUT/forecast_${region_id}_metrics.txt" 2>/dev/null || echo "N/A,N/A,N/A,N/A,N/A,no")
    echo "$region_name,$region_id,$metrics,$response_time" >> "$OUT/forecast_seed_results.csv"
    ((forecast_count++))
  else
    echo "WARN: Forecast failed for $region_name" >> "$REPORT"
  fi
done

echo "Generated $forecast_count forecasts" >> "$REPORT"
if [[ $forecast_count -lt 2 ]]; then
  fail_with_bug "Phase 3" "I3" "Could not generate at least 2 forecasts (got $forecast_count)"
  exit 1
fi

# --- Phase 4: Variance / Discrepancy Check
echo >> "$REPORT"
echo "## Phase 4 — Variance / Discrepancy Check (I3)" >> "$REPORT"
python3 - <<'PY' > "$OUT/forecast_variance_report.txt" 2>/dev/null || true
import json
import hashlib
import csv
import os
import sys

out_dir = os.environ.get("OUT", "/tmp")
csv_path = os.path.join(out_dir, "forecast_seed_results.csv")

try:
    # Read CSV
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if len(rows) < 2:
        print("ERROR: Need at least 2 forecasts for variance check")
        sys.exit(1)
    
    # Extract behavior_index values
    bi_values = []
    for row in rows:
        bi_str = row.get('behavior_index', 'N/A')
        try:
            bi_values.append(float(bi_str))
        except:
            pass
    
    if len(bi_values) < 2:
        print("ERROR: Could not extract enough behavior_index values")
        sys.exit(1)
    
    # Check variance
    unique_values = len(set(bi_values))
    min_val = min(bi_values)
    max_val = max(bi_values)
    variance = max_val - min_val
    
    print(f"=== Variance Analysis ===")
    print(f"Total forecasts: {len(rows)}")
    print(f"Unique behavior_index values: {unique_values}")
    print(f"Min behavior_index: {min_val:.6f}")
    print(f"Max behavior_index: {max_val:.6f}")
    print(f"Variance range: {variance:.6f}")
    
    # Check hash uniqueness (forecast arrays)
    hashes = []
    for row in rows:
        region_id = row.get('region_id', '')
        forecast_path = os.path.join(out_dir, f"forecast_{region_id}.json")
        if os.path.exists(forecast_path):
            try:
                with open(forecast_path, 'r') as f:
                    data = json.load(f)
                forecast = data.get('forecast', [])
                forecast_str = json.dumps(forecast, sort_keys=True)
                h = hashlib.sha256(forecast_str.encode()).hexdigest()
                hashes.append(h[:16])
            except:
                pass
    
    unique_hashes = len(set(hashes))
    print(f"\n=== Hash Uniqueness ===")
    print(f"Unique forecast hashes: {unique_hashes} / {len(hashes)}")
    
    if unique_hashes < len(hashes) * 0.2:  # Less than 20% unique
        print("WARNING: High hash collision rate - possible discrepancy bug")
        sys.exit(1)
    
    # Check variance threshold
    EPSILON = 0.005
    if variance < EPSILON:
        print(f"\nWARNING: Variance {variance:.6f} < epsilon {EPSILON}")
        print("Regional variance may be insufficient")
    else:
        print(f"\nOK: Variance {variance:.6f} >= epsilon {EPSILON}")
    
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
PY

variance_result=$(cat "$OUT/forecast_variance_report.txt" 2>/dev/null || echo "")
echo "### Variance Report" >> "$REPORT"
echo '```' >> "$REPORT"
echo "$variance_result" >> "$REPORT"
echo '```' >> "$REPORT"

# Check if variance is sufficient
if echo "$variance_result" | grep -q "Variance.*< epsilon\|High hash collision"; then
  fail_with_bug "Phase 4" "I3" "Insufficient regional variance or high hash collision"
  exit 1
fi

# --- Phase 5: Metrics Integrity
echo >> "$REPORT"
echo "## Phase 5 — Metrics Integrity (I4)" >> "$REPORT"
curl -fsS "http://localhost:8100/metrics" > "$OUT/metrics.txt" || \
  fail_with_bug "Phase 5" "I4" "Could not fetch metrics" || exit 1

# Check for region="None"
if grep -q 'region="None"' "$OUT/metrics.txt"; then
  fail_with_bug "Phase 5" "I4" "Found region='None' in metrics"
  exit 1
fi

# Extract distinct regions
REGION_COUNT=$(grep -oE 'behavior_index\{region="[^"]+"' "$OUT/metrics.txt" | \
  sed 's/.*region="\([^"]*\)".*/\1/' | sort -u | wc -l | tr -d ' ')

echo "Distinct regions in metrics: $REGION_COUNT" >> "$REPORT"
if [[ $REGION_COUNT -lt 2 ]]; then
  fail_with_bug "Phase 5" "I4" "Found only $REGION_COUNT distinct region(s), need >= 2"
  exit 1
fi

# Check for child index metrics
{
  echo "=== behavior_index by region ==="
  grep -E '^behavior_index\{' "$OUT/metrics.txt" | head -20
  echo
  echo "=== child/sub index metrics ==="
  grep -E '(child_sub_index|fuel_stress|economic_stress)' "$OUT/metrics.txt" | head -10
} > "$OUT/metrics_extract.txt"

# --- Phase 6: Prometheus Proof
echo >> "$REPORT"
echo "## Phase 6 — Prometheus Proof (I5)" >> "$REPORT"
if curl -fsS "http://localhost:9090/-/ready" >/dev/null 2>&1; then
  echo "OK: Prometheus ready" >> "$REPORT"
  > "$OUT/promql_results.json"
  for q in \
    'count by(region) (behavior_index)' \
    'topk(10, behavior_index)' \
    'count(behavior_index)'; do
    result=$(curl -sG "http://localhost:9090/api/v1/query" --data-urlencode "query=$q" 2>&1)
    echo "$result" | python3 -m json.tool >> "$OUT/promql_results.txt" 2>/dev/null || echo "$result" >> "$OUT/promql_results.txt"
    echo "$result" >> "$OUT/promql_results.json"
  done
else
  fail_with_bug "Phase 6" "I5" "Prometheus not reachable"
  exit 1
fi

# --- Phase 7: Grafana Proof
echo >> "$REPORT"
echo "## Phase 7 — Grafana Proof (I6)" >> "$REPORT"
if curl -fsS "http://localhost:3001/api/health" >/dev/null 2>&1 || \
   curl -fsS "http://localhost:3001/" >/dev/null 2>&1; then
  echo "OK: Grafana is reachable" >> "$REPORT"
  # Check dashboard files for region variables
  if [[ -d "infra/grafana/dashboards" ]]; then
    if grep -r '\$region' infra/grafana/dashboards/ 2>/dev/null | head -3 > "$OUT/grafana_proof.txt"; then
      echo "OK: Found region variable references" >> "$REPORT"
    fi
  fi
else
  echo "WARN: Grafana not reachable (non-blocking)" >> "$REPORT"
fi

# --- Phase 8: UI Contract Proof
echo >> "$REPORT"
echo "## Phase 8 — UI Contract Proof (I7)" >> "$REPORT"
{
  echo "### /forecast page check"
  if grep -qiE 'region|select|generate' "$OUT/route_forecast.body" 2>/dev/null; then
    echo "OK: Found region/select/generate elements"
  else
    echo "WARN: Could not verify region select"
  fi
  echo
  echo "### /history page check"
  if grep -qiE 'history|table|filter' "$OUT/route_history.body" 2>/dev/null; then
    echo "OK: Found history/table/filter elements"
  else
    echo "WARN: Could not verify history page structure"
  fi
} > "$OUT/ui_contract_proof.txt"

# --- Phase 9: Final Report
echo >> "$REPORT"
echo "## Phase 9 — Final Status" >> "$REPORT"

# Check if BUGS.md exists
if [[ -f "$BUGS_FILE" ]]; then
  echo "❌ FAIL: Bugs found. See $BUGS_FILE" >> "$REPORT"
  echo >> "$REPORT"
  cat "$BUGS_FILE" >> "$REPORT"
  CONSECUTIVE_PASSES=0
else
  echo "✅ PASS: All integrity checks passed" >> "$REPORT"
  ((CONSECUTIVE_PASSES++))
  echo "Consecutive passes: $CONSECUTIVE_PASSES / $REQUIRED_CONSECUTIVE_PASSES" >> "$REPORT"
fi

echo >> "$REPORT"
echo "### Evidence Artifacts" >> "$REPORT"
echo "All evidence saved to: \`$OUT\`" >> "$REPORT"
echo "- \`forecast_seed_results.csv\` - Forecast results for 10 regions" >> "$REPORT"
echo "- \`forecast_variance_report.txt\` - Variance analysis" >> "$REPORT"
echo "- \`metrics.txt\` + \`metrics_extract.txt\` - Prometheus metrics" >> "$REPORT"
echo "- \`promql_results.json\` - Prometheus queries" >> "$REPORT"
echo "- \`docker_logs_*.txt\` - Container logs" >> "$REPORT"

# Save container logs
{
  echo "### Backend logs (tail 100)"
  docker compose logs backend --tail=100 2>&1 || true
} > "$OUT/docker_logs_backend_tail.txt"

{
  echo "### Frontend logs (tail 100)"
  docker compose logs frontend --tail=100 2>&1 || true
} > "$OUT/docker_logs_frontend_tail.txt"

{
  echo "### Prometheus logs (tail 100)"
  docker compose logs prometheus --tail=100 2>&1 || true
} > "$OUT/prometheus_tail.txt"

{
  echo "### Grafana logs (tail 100)"
  docker compose logs grafana --tail=100 2>&1 || true
} > "$OUT/grafana_tail.txt"

# Final verdict
if [[ -f "$BUGS_FILE" ]]; then
  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  echo "❌ INTEGRITY LOOP FAILED"
  echo "═══════════════════════════════════════════════════════════════"
  echo "Report: $REPORT"
  echo "Bugs: $BUGS_FILE"
  echo "Evidence: $OUT"
  echo "═══════════════════════════════════════════════════════════════"
  exit 1
elif [[ $CONSECUTIVE_PASSES -ge $REQUIRED_CONSECUTIVE_PASSES ]]; then
  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  echo "✅ INTEGRITY LOOP PASSED ($CONSECUTIVE_PASSES consecutive passes)"
  echo "═══════════════════════════════════════════════════════════════"
  echo "Report: $REPORT"
  echo "Evidence: $OUT"
  echo "═══════════════════════════════════════════════════════════════"
  exit 0
else
  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  echo "⚠️  INTEGRITY LOOP PASSED (run $CONSECUTIVE_PASSES / $REQUIRED_CONSECUTIVE_PASSES)"
  echo "═══════════════════════════════════════════════════════════════"
  echo "Report: $REPORT"
  echo "Evidence: $OUT"
  echo "Run again to achieve $REQUIRED_CONSECUTIVE_PASSES consecutive passes"
  echo "═══════════════════════════════════════════════════════════════"
  exit 0
fi
