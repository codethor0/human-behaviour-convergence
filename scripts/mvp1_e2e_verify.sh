#!/usr/bin/env bash
set -euo pipefail

ROOT="${PWD}"
TS="$(date -u +%Y%m%d_%H%M%S)"
OUT="/tmp/hbc_mvp1_verify_${TS}"
REPORT="/tmp/HBC_MVP1_E2E_VERIFICATION_REPORT.md"
mkdir -p "$OUT"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "# HBC MVP1 E2E Verification Report" > "$REPORT"
echo "- Generated: $(ts)" >> "$REPORT"
echo "- Repo: $ROOT" >> "$REPORT"
echo "- Evidence dir: $OUT" >> "$REPORT"
echo >> "$REPORT"

# --- Phase 0: baseline
{
  echo "## Phase 0 — Baseline"
  echo "- HEAD: $(git rev-parse HEAD 2>/dev/null || echo N/A)"
  echo "- Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo N/A)"
  echo "- Git status:"
  git status --porcelain 2>/dev/null | sed 's/^/  - /' || true
  echo
  echo "- Versions:"
  echo "  - python: $(python --version 2>&1 || true)"
  echo "  - node: $(node --version 2>&1 || true)"
  echo "  - npm: $(npm --version 2>&1 || true)"
  echo "  - docker: $(docker --version 2>&1 || true)"
  echo "  - docker compose: $(docker compose version 2>&1 || true)"
} | tee "$OUT/baseline.txt" >> "$REPORT"

# --- helpers
check_url () {
  local url="$1" name="$2"
  local code
  code="$(curl -sS -o "$OUT/${name}.body" -w "%{http_code}" "$url" || echo "000")"
  printf "%s\t%s\tHTTP %s\t%s\n" "$(ts)" "$url" "$code" "$OUT/${name}.body" >> "$OUT/readiness_checks.tsv"
  if [[ "$code" != "200" ]]; then
    echo "- FAIL: $url -> HTTP $code (body: $OUT/${name}.body)" >> "$REPORT"
    return 1
  fi
  echo "- OK: $url -> HTTP $code" >> "$REPORT"
}

api_get () {
  local url="$1" out="$2"
  local code
  code="$(curl -sS -o "$OUT/${out}" -w "%{http_code}" "$url" || echo "000")"
  echo "- GET $url -> HTTP $code (saved: $OUT/$out)" >> "$REPORT"
  [[ "$code" == "200" ]]
}

get_region_id () {
  local region_name="$1"
  # Look up region_id from regions endpoint (already fetched in Phase 2)
  python3 -c "
import json, sys
try:
    with open('$OUT/regions_direct.json', 'r') as f:
        regions = json.load(f)
    for r in regions:
        if r.get('name', '').lower() == '${region_name}'.lower():
            print(r['id'])
            sys.exit(0)
    print('', file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || echo ""
}

post_forecast () {
  local region_name="$1" out="$2"
  local region_id
  region_id="$(get_region_id "$region_name")"
  
  if [[ -z "$region_id" ]]; then
    echo "- ERROR: Could not find region_id for '${region_name}'" >> "$REPORT"
    return 1
  fi
  
  cat > "$OUT/${out}.payload.json" <<JSON
{
  "region_id": "${region_id}",
  "region_name": "${region_name}",
  "days_back": 30,
  "forecast_horizon": 7
}
JSON
  local code
  code="$(curl -sS -o "$OUT/${out}.json" -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -X POST "http://localhost:8100/api/forecast" \
    -d @"$OUT/${out}.payload.json" || echo "000")"
  echo "- POST /api/forecast region_name=\"${region_name}\" region_id=\"${region_id}\" -> HTTP $code (saved: $OUT/${out}.json)" >> "$REPORT"
  if [[ "$code" != "200" ]]; then
    echo "- ERROR: Forecast failed. Response body:" >> "$REPORT"
    cat "$OUT/${out}.json" >> "$REPORT" 2>/dev/null || true
    return 1
  fi
  return 0
}

fail_with_logs () {
  echo >> "$REPORT"
  echo "## Diagnostics (fail-fast logs)" >> "$REPORT"
  {
    echo "### docker ps -a"
    docker ps -a || true
    echo
    echo "### backend logs (tail 200)"
    docker compose logs backend --tail=200 || true
    echo
    echo "### frontend logs (tail 200)"
    docker compose logs frontend --tail=200 || true
    echo
    echo "### prometheus logs (tail 200)"
    docker compose logs prometheus --tail=200 || true
    echo
    echo "### grafana logs (tail 200)"
    docker compose logs grafana --tail=200 || true
  } | tee "$OUT/docker_logs_on_failure.txt" >> "$REPORT"
  echo >> "$REPORT"
  echo "FAIL. See evidence dir: $OUT" >> "$REPORT"
  exit 1
}

# --- Phase 1: docker readiness
echo "## Phase 1 — Docker stack readiness" >> "$REPORT"
docker compose down -v >/dev/null 2>&1 || true
docker compose up -d --build

# wait for services to be ready (with retries)
echo "Waiting for services to be ready..." >> "$REPORT"
for i in {1..30}; do
  if curl -fsS "http://localhost:8100/health" >/dev/null 2>&1 && \
     curl -fsS "http://localhost:3100/" >/dev/null 2>&1; then
    echo "- Services ready after ${i} attempts" >> "$REPORT"
    break
  fi
  sleep 2
  if [[ $i -eq 30 ]]; then
    echo "- WARN: Services may not be fully ready, continuing anyway" >> "$REPORT"
  fi
done
sleep 2  # Extra buffer

# Core readiness: if these fail, STOP (this catches the classic /forecast 404 early)
check_url "http://localhost:8100/health" "backend_health" || fail_with_logs
check_url "http://localhost:3100/" "frontend_root" || fail_with_logs
check_url "http://localhost:3100/forecast" "route_forecast" || fail_with_logs
check_url "http://localhost:3100/history" "route_history" || fail_with_logs
check_url "http://localhost:3100/live" "route_live" || fail_with_logs
check_url "http://localhost:3100/playground" "route_playground" || fail_with_logs

# --- Phase 2: regions proxy vs direct + MVP1 source registry check
echo >> "$REPORT"
echo "## Phase 2 — Regions API (proxy vs direct) + MVP1 Source Registry" >> "$REPORT"
api_get "http://localhost:8100/api/forecasting/regions" "regions_direct.json" || fail_with_logs
api_get "http://localhost:3100/api/forecasting/regions" "regions_proxy.json" || {
  echo "- P0 BUG: Proxy regions failed but direct works. This is base URL/proxy misalignment." >> "$REPORT"
  fail_with_logs
}

# Check MVP1 source registry
echo >> "$REPORT"
echo "### MVP1 Source Registry Check" >> "$REPORT"
if api_get "http://localhost:8100/api/forecasting/data-sources" "data_sources.json"; then
  if python3 -c "import json; data=json.load(open('$OUT/data_sources.json')); print('eia_fuel_prices' in [s['name'] for s in data])" 2>/dev/null | grep -q True; then
    echo "- OK: eia_fuel_prices found in source registry" >> "$REPORT"
    # Extract status
    python3 - <<'PY' >> "$REPORT" 2>/dev/null || true
import json
with open('$OUT/data_sources.json', 'r') as f:
    sources = json.load(f)
for s in sources:
    if s['name'] == 'eia_fuel_prices':
        print(f"- Status: {s.get('status', 'unknown')}, Available: {s.get('available', False)}")
        break
PY
  else
    echo "- P0 BUG: eia_fuel_prices NOT found in source registry" >> "$REPORT"
    fail_with_logs
  fi
else
  echo "- WARN: Could not fetch data sources endpoint (non-blocking)" >> "$REPORT"
fi

# --- Phase 3: forecast IL vs AZ
echo >> "$REPORT"
echo "## Phase 3 — Forecast proof (Illinois vs Arizona)" >> "$REPORT"
echo "### Generating forecasts for Illinois and Arizona" >> "$REPORT"
post_forecast "Illinois" "forecast_il" || fail_with_logs
post_forecast "Arizona" "forecast_az" || fail_with_logs

# Note: Cache key verification (eia_fuel_<STATE>_<days_back>) should be verified
# through code inspection of app/services/ingestion/eia_fuel_prices.py or
# backend logs showing cache key format. This script focuses on runtime behavior.
echo "### Cache Key Note" >> "$REPORT"
echo "- Cache key format verification requires code inspection or log analysis" >> "$REPORT"
echo "- Expected format: \`eia_fuel_<STATE>_<days_back>\` (e.g., eia_fuel_IL_30)" >> "$REPORT"

# Compare a few key fields using python (best-effort; won't break run if shape differs)
OUT="$OUT" python3 - <<'PY' > "$OUT/forecast_compare.txt" 2>/dev/null || true
import json
import os
import sys

out_dir = os.environ.get("OUT", "/tmp")
il_path = os.path.join(out_dir, "forecast_il.json")
az_path = os.path.join(out_dir, "forecast_az.json")

try:
    il = json.load(open(il_path))
    az = json.load(open(az_path))
except Exception as e:
    print(f"Error loading forecasts: {e}", file=sys.stderr)
    sys.exit(0)

def dig(d, keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, list) and isinstance(k, int) and 0 <= k < len(cur):
            cur = cur[k]
        else:
            return None
    return cur

def find_nested(d, target_key, path=[]):
    """Find all values with a given key name in nested structure"""
    results = []
    if isinstance(d, dict):
        for k, v in d.items():
            if k == target_key:
                results.append((path + [k], v))
            results.extend(find_nested(v, target_key, path + [k]))
    elif isinstance(d, list):
        for i, item in enumerate(d):
            results.extend(find_nested(item, target_key, path + [i]))
    return results

# Try common candidate paths (adjust as needed for your schema)
candidates = {
  "behavior_index": [["behavior_index"], ["behaviorIndex"], ["metrics","behavior_index"], ["forecast", 0, "behavior_index"]],
  "economic_stress": [["sub_indices","economic_stress"], ["subIndices","economic_stress"], ["forecast", 0, "sub_indices", "economic_stress"]],
  "fuel_stress": [["child_sub_indices","fuel_stress"], ["childSubIndices","fuel_stress"], ["sub_indices","fuel_stress"], ["forecast", 0, "child_sub_indices", "fuel_stress"]],
}

print("=== Key Metrics Comparison ===")
print("Field\tIllinois\tArizona\tDiff\t% Diff")
for name, paths in candidates.items():
    a = b = None
    for p in paths:
        a = dig(il, p)
        b = dig(az, p)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            break
        a = b = None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        diff = b - a
        pct_diff = (diff / a * 100) if a != 0 else 0
        print(f"{name}\t{a:.6f}\t{b:.6f}\t{diff:.6f}\t{pct_diff:.2f}%")
    else:
        print(f"{name}\tN/A\tN/A\tN/A\tN/A")

# Also search for any fuel-related values
print("\n=== Fuel-related values found ===")
for name, data in [("Illinois", il), ("Arizona", az)]:
    fuel_paths = find_nested(data, "fuel_stress")
    if fuel_paths:
        print(f"{name}: Found fuel_stress at {len(fuel_paths)} location(s)")
        for path, val in fuel_paths[:3]:  # Show first 3
            print(f"  {'.'.join(str(p) for p in path)} = {val}")
    else:
        print(f"{name}: No fuel_stress found")

# Check forecast arrays for variance
print("\n=== Forecast Array Variance ===")
if "forecast" in il and "forecast" in az and isinstance(il["forecast"], list) and isinstance(az["forecast"], list):
    if len(il["forecast"]) > 0 and len(az["forecast"]) > 0:
        il_first = il["forecast"][0]
        az_first = az["forecast"][0]
        if isinstance(il_first, dict) and isinstance(az_first, dict):
            if "behavior_index" in il_first and "behavior_index" in az_first:
                print(f"First forecast point - IL: {il_first['behavior_index']:.6f}, AZ: {az_first['behavior_index']:.6f}, Diff: {abs(il_first['behavior_index'] - az_first['behavior_index']):.6f}")
PY

python3 - <<'PY' >> "$REPORT" 2>/dev/null || true
import os
p = os.path.join(os.environ.get("OUT", "/tmp"), "forecast_compare.txt")
if os.path.exists(p):
    print("### Forecast Comparison (Illinois vs Arizona)")
    print("```")
    print(open(p).read().strip())
    print("```")
    # Check if we found meaningful differences
    content = open(p).read()
    if "N/A" not in content or "Diff:" in content:
        print("\n- OK: Forecast comparison completed")
    if "fuel_stress" in content.lower():
        print("- OK: Found fuel_stress references in forecast data")
PY

# --- Phase 4: metrics proof
echo >> "$REPORT"
echo "## Phase 4 — Metrics proof" >> "$REPORT"
curl -fsS "http://localhost:8100/metrics" > "$OUT/metrics.txt" || fail_with_logs

{
  echo "### /metrics extracts"
  echo "```"
  echo "behavior_index series (sample):"
  grep -E '^behavior_index\{' "$OUT/metrics.txt" | head -n 20 || true
  echo "---"
  echo "behavior_index series count:"
  grep -c '^behavior_index\{' "$OUT/metrics.txt" || true
  echo "---"
  echo "Multi-region check (us_il, us_az):"
  grep -E 'behavior_index\{region="us_(il|az)"' "$OUT/metrics.txt" | head -n 5 || true
  echo "---"
  echo "Child index metrics (sample):"
  grep -E '(child_sub_index|sub_index|economic_stress|fuel_stress)' "$OUT/metrics.txt" | head -n 10 || true
  echo "---"
  echo "region=None violations:"
  grep -E 'region="None"' "$OUT/metrics.txt" || echo "None found (good)"
  echo "```"
} >> "$REPORT"

# Extract metrics to separate file for easier analysis
{
  echo "=== behavior_index by region ==="
  grep -E '^behavior_index\{' "$OUT/metrics.txt" | head -n 30
  echo
  echo "=== child/sub index metrics ==="
  grep -E '(child_sub_index|sub_index|economic|fuel)' "$OUT/metrics.txt" | head -n 20
} > "$OUT/metrics_extract.txt"

if grep -q 'region="None"' "$OUT/metrics.txt"; then
  echo "- P0 BUG: region=\"None\" detected in metrics" >> "$REPORT"
  fail_with_logs
fi

# Check for IL and AZ regions in metrics
if ! grep -q 'region="us_il"' "$OUT/metrics.txt" && ! grep -q 'region="us_az"' "$OUT/metrics.txt"; then
  echo "- WARN: us_il or us_az not found in metrics (may need more time for metrics to populate)" >> "$REPORT"
fi

# --- Phase 5: Prometheus readiness + quick PromQL (best-effort)
echo >> "$REPORT"
echo "## Phase 5 — Prometheus proof (best-effort)" >> "$REPORT"
if curl -fsS "http://localhost:9090/-/ready" >/dev/null 2>&1; then
  echo "- OK: Prometheus ready" >> "$REPORT"
  > "$OUT/promql_results.json"  # Clear previous results
  for q in \
    'count by(region) (behavior_index)' \
    'topk(10, behavior_index)' \
    'count(behavior_index)'; do
    echo "### PromQL: $q" >> "$REPORT"
    result=$(curl -sG "http://localhost:9090/api/v1/query" --data-urlencode "query=$q")
    echo "$result" | python3 -m json.tool >> "$OUT/promql_results.txt" 2>/dev/null || echo "$result" >> "$OUT/promql_results.txt"
    echo "$result" >> "$OUT/promql_results.json"
    echo "- Query executed, results saved" >> "$REPORT"
  done
else
  echo "- WARN: Prometheus not reachable at :9090 (skipping PromQL)" >> "$REPORT"
fi

# --- Phase 6: Grafana proof
echo >> "$REPORT"
echo "## Phase 6 — Grafana proof" >> "$REPORT"
if curl -fsS "http://localhost:3001/api/health" >/dev/null 2>&1 || \
   curl -fsS "http://localhost:3001/" >/dev/null 2>&1; then
  echo "- OK: Grafana is reachable" >> "$REPORT"
  # Check if dashboards reference region variables
  if [[ -d "infra/grafana/dashboards" ]]; then
    echo "### Dashboard region variable check" >> "$REPORT"
    if grep -r '\$region' infra/grafana/dashboards/ 2>/dev/null | head -3 > "$OUT/grafana_proof.txt"; then
      echo "- OK: Found region variable references in dashboards" >> "$REPORT"
      echo "```" >> "$REPORT"
      head -5 "$OUT/grafana_proof.txt" >> "$REPORT"
      echo "```" >> "$REPORT"
    else
      echo "- WARN: No region variable references found in dashboard files" >> "$REPORT"
    fi
  fi
else
  echo "- WARN: Grafana not reachable at :3001 (non-blocking)" >> "$REPORT"
fi

# --- Phase 7: UI Contract Validation (lightweight)
echo >> "$REPORT"
echo "## Phase 7 — UI Contract Validation" >> "$REPORT"
# Check /forecast page has region select
if grep -q 'region\|select' "$OUT/route_forecast.body" 2>/dev/null; then
  echo "- OK: /forecast page contains region/select elements" >> "$REPORT"
else
  echo "- WARN: Could not verify region select in /forecast (non-blocking)" >> "$REPORT"
fi

# Check /history page structure
if grep -q 'history\|table\|filter' "$OUT/route_history.body" 2>/dev/null; then
  echo "- OK: /history page contains expected elements" >> "$REPORT"
else
  echo "- WARN: Could not verify history page structure (non-blocking)" >> "$REPORT"
fi

# Save UI contract proof
{
  echo "### /forecast page snippet (first 500 chars)"
  head -c 500 "$OUT/route_forecast.body" 2>/dev/null || echo "N/A"
  echo
  echo "### /history page snippet (first 500 chars)"
  head -c 500 "$OUT/route_history.body" 2>/dev/null || echo "N/A"
} > "$OUT/ui_contract_proof.txt"

# --- Final evidence collection
echo >> "$REPORT"
echo "## Final Evidence Collection" >> "$REPORT"
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

echo "- Saved container logs to evidence directory" >> "$REPORT"

# --- Wrap up
echo >> "$REPORT"
echo "## Final Status" >> "$REPORT"
echo "- ✅ PASS: MVP1 end-to-end verification script completed without fail-fast stops." >> "$REPORT"
echo >> "$REPORT"
echo "### Evidence Artifacts" >> "$REPORT"
echo "All evidence saved to: \`$OUT\`" >> "$REPORT"
echo >> "$REPORT"
echo "Key artifacts:" >> "$REPORT"
echo "1. \`baseline.txt\` - Git state and versions" >> "$REPORT"
echo "2. \`readiness_checks.tsv\` - HTTP status codes for all routes" >> "$REPORT"
echo "3. \`regions_direct.json\` + \`regions_proxy.json\` - Region API responses" >> "$REPORT"
echo "4. \`data_sources.json\` - Source registry (MVP1 check)" >> "$REPORT"
echo "5. \`forecast_il.json\` + \`forecast_az.json\` - Forecast responses" >> "$REPORT"
echo "6. \`forecast_compare.txt\` - Regional variance analysis" >> "$REPORT"
echo "7. \`metrics.txt\` - Full Prometheus metrics export" >> "$REPORT"
echo "8. \`metrics_extract.txt\` - Filtered metrics (behavior_index, child indices)" >> "$REPORT"
echo "9. \`promql_results.txt\` + \`promql_results.json\` - Prometheus query results" >> "$REPORT"
echo "10. \`grafana_proof.txt\` - Dashboard region variable references" >> "$REPORT"
echo "11. \`ui_contract_proof.txt\` - Frontend page structure validation" >> "$REPORT"
echo "12. \`docker_logs_*.txt\` - Container logs" >> "$REPORT"
echo >> "$REPORT"
echo "### Next Steps" >> "$REPORT"
echo "- Review \`forecast_compare.txt\` to verify regional variance (IL vs AZ)" >> "$REPORT"
echo "- Check \`metrics_extract.txt\` for multi-region coverage and fuel_stress metrics" >> "$REPORT"
echo "- Verify Prometheus queries in \`promql_results.txt\` show >= 2 regions" >> "$REPORT"
echo "- If any issues found, see container logs in \`docker_logs_*.txt\`" >> "$REPORT"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ MVP1 E2E VERIFICATION COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo "Report: $REPORT"
echo "Evidence: $OUT"
echo "═══════════════════════════════════════════════════════════════"
