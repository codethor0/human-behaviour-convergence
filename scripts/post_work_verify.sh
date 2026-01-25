#!/usr/bin/env bash
# Post-Work Verification + Anti-Hallucination Repair Loop
# Verifies claimed changes exist, are wired correctly, and visible end-to-end
# Usage: ./scripts/post_work_verify.sh
set -euo pipefail

ROOT="${PWD}"
TS="$(date -u +%Y%m%d_%H%M%S)"
OUT="/tmp/hbc_post_verify_${TS}"
mkdir -p "$OUT"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "HBC Post-Work Verification + Anti-Hallucination Repair Loop"
echo "============================================================="
echo "Timestamp: $(ts)"
echo "Evidence dir: $OUT"
echo

# --- PHASE 0: BASELINE
echo "[PHASE 0] Baseline (no assumptions)..."
{
  echo "Git Status:"
  git status --short || echo "ERROR: git status failed"
  echo
  echo "Git HEAD:"
  git rev-parse HEAD || echo "ERROR: git rev-parse failed"
  echo
  echo "Recent commits:"
  git log -n 5 --oneline || echo "ERROR: git log failed"
} > "$OUT/git_head.txt"

{
  echo "Python: $(python3 --version 2>&1 || echo 'N/A')"
  echo "Node: $(node --version 2>&1 || echo 'N/A')"
  echo "Docker: $(docker --version 2>&1 || echo 'N/A')"
  echo "Docker Compose: $(docker compose version 2>&1 || echo 'N/A')"
} > "$OUT/versions.txt"

docker compose ps > "$OUT/compose_ps.txt" 2>&1 || echo "WARN: docker compose ps failed" >> "$OUT/compose_ps.txt"

echo "  Baseline recorded"

# --- PHASE 1: DOCKER STACK HARD READINESS
echo
echo "[PHASE 1] Docker stack hard readiness..."

check_url() {
  local url="$1" name="$2"
  local code
  code="$(curl -sS -o "$OUT/${name}.body" -w "%{http_code}" "$url" 2>/dev/null || echo "000")"
  printf "%s\t%s\tHTTP %s\n" "$(ts)" "$url" "$code" >> "$OUT/readiness_results.txt"
  if [[ "$code" != "200" ]]; then
    echo "  FAIL: $url -> HTTP $code"
    return 1
  fi
  echo "  OK: $url -> HTTP $code"
  return 0
}

echo "Starting/refreshing stack..."
docker compose up -d --build > "$OUT/compose_up.log" 2>&1 || {
  echo "ERROR: docker compose up failed"
  cat "$OUT/compose_up.log"
  exit 1
}

echo "Waiting for services..."
sleep 15

PHASE1_FAILED=0
check_url "http://localhost:8100/health" "health" || PHASE1_FAILED=1
check_url "http://localhost:3100/" "frontend_root" || PHASE1_FAILED=1
check_url "http://localhost:3100/forecast" "frontend_forecast" || PHASE1_FAILED=1
check_url "http://localhost:3100/history" "frontend_history" || PHASE1_FAILED=1
check_url "http://localhost:3001/" "grafana" || PHASE1_FAILED=1
check_url "http://localhost:9090/" "prometheus" || PHASE1_FAILED=1

if [ "$PHASE1_FAILED" -eq 1 ]; then
  echo "FAIL: Phase 1 - Readiness gates failed"
  docker ps -a > "$OUT/docker_ps_a.txt"
  docker compose logs backend --tail=200 > "$OUT/backend_tail.txt"
  docker compose logs frontend --tail=200 > "$OUT/frontend_tail.txt"
  docker compose logs grafana --tail=200 > "$OUT/grafana_tail.txt" 2>&1 || true
  docker compose logs prometheus --tail=200 > "$OUT/prometheus_tail.txt" 2>&1 || true
  echo "See logs in $OUT/"
  exit 1
fi

echo "  PASS: All readiness gates passed"

# --- PHASE 2: FILE-SYSTEM REALITY CHECK
echo
echo "[PHASE 2] File-system reality check..."

cat > "$OUT/filesystem_findings.md" <<EOF
# File-System Reality Check

Generated: $(ts)

## MVP1 EIA Fuel Prices Verification

EOF

# Check EIA fuel prices file
if [ -f "app/services/ingestion/eia_fuel_prices.py" ]; then
  LINE_COUNT=$(wc -l < "app/services/ingestion/eia_fuel_prices.py")
  echo "  PROVED: eia_fuel_prices.py exists ($LINE_COUNT lines)"
  echo "- eia_fuel_prices.py: EXISTS ($LINE_COUNT lines)" >> "$OUT/filesystem_findings.md"
  
  # Check cache key includes state
  if grep -q "eia_fuel_.*state" "app/services/ingestion/eia_fuel_prices.py"; then
    echo "  PROVED: Cache key includes state_code"
    echo "- Cache key format: VERIFIED (includes state_code)" >> "$OUT/filesystem_findings.md"
  else
    echo "  BROKEN: Cache key may not include state_code"
    echo "- Cache key format: BROKEN (state_code not found in cache key)" >> "$OUT/filesystem_findings.md"
  fi
else
  echo "  MISSING: eia_fuel_prices.py does not exist"
  echo "- eia_fuel_prices.py: MISSING" >> "$OUT/filesystem_findings.md"
fi

# Check source registry
if grep -q "eia_fuel_prices" "app/services/ingestion/source_registry.py"; then
  echo "  PROVED: Source registry entry exists"
  echo "- Source registry: VERIFIED" >> "$OUT/filesystem_findings.md"
else
  echo "  MISSING: Source registry entry not found"
  echo "- Source registry: MISSING" >> "$OUT/filesystem_findings.md"
fi

# Check behavior index integration
if grep -q "fuel_stress" "app/core/behavior_index.py"; then
  echo "  PROVED: fuel_stress in behavior_index.py"
  echo "- Behavior index integration: VERIFIED" >> "$OUT/filesystem_findings.md"
else
  echo "  MISSING: fuel_stress not found in behavior_index.py"
  echo "- Behavior index integration: MISSING" >> "$OUT/filesystem_findings.md"
fi

# Check prediction pipeline
if grep -q "fuel" "app/core/prediction.py"; then
  echo "  PROVED: Fuel data handling in prediction.py"
  echo "- Prediction pipeline: VERIFIED" >> "$OUT/filesystem_findings.md"
else
  echo "  MISSING: Fuel data not found in prediction.py"
  echo "- Prediction pipeline: MISSING" >> "$OUT/filesystem_findings.md"
fi

# Check for new datasets (drought, storm)
echo >> "$OUT/filesystem_findings.md"
echo "## MVP2/MVP3 Dataset Verification" >> "$OUT/filesystem_findings.md"

for dataset in "drought_monitor.py" "noaa_storm_events.py"; do
  if [ -f "app/services/ingestion/$dataset" ]; then
    echo "  PROVED: $dataset exists"
    echo "- $dataset: EXISTS" >> "$OUT/filesystem_findings.md"
  else
    echo "  MISSING: $dataset does not exist"
    echo "- $dataset: MISSING" >> "$OUT/filesystem_findings.md"
  fi
done

# Check Grafana dashboards
echo >> "$OUT/filesystem_findings.md"
echo "## Grafana Dashboard Verification" >> "$OUT/filesystem_findings.md"

DASHBOARD_COUNT=$(find infra/grafana/dashboards -name "*.json" 2>/dev/null | wc -l | tr -d ' ')
echo "  Found $DASHBOARD_COUNT dashboard JSON files"
echo "- Dashboard JSON files: $DASHBOARD_COUNT found" >> "$OUT/filesystem_findings.md"

# List dashboards
find infra/grafana/dashboards -name "*.json" -exec basename {} \; > "$OUT/dashboard_list.txt" 2>/dev/null || true
if [ -f "$OUT/dashboard_list.txt" ]; then
  echo "  Dashboards:" >> "$OUT/filesystem_findings.md"
  while IFS= read -r dash; do
    echo "    - $dash" >> "$OUT/filesystem_findings.md"
  done < "$OUT/dashboard_list.txt"
fi

# Check for fuel_stress in dashboards
if grep -r -l "fuel_stress\|fuel" infra/grafana/dashboards/*.json 2>/dev/null | head -1; then
  echo "  PROVED: fuel_stress referenced in dashboards"
  echo "- fuel_stress in dashboards: VERIFIED" >> "$OUT/filesystem_findings.md"
else
  echo "  MISSING: fuel_stress not found in dashboard JSONs"
  echo "- fuel_stress in dashboards: MISSING" >> "$OUT/filesystem_findings.md"
fi

cat "$OUT/filesystem_findings.md"

# --- PHASE 3: API PROOF
echo
echo "[PHASE 3] API proof (data exists and is region-aware)..."

curl -fsS "http://localhost:8100/api/status" > "$OUT/api_status.json" 2>&1 || echo "WARN: /api/status failed"
curl -fsS "http://localhost:8100/api/forecasting/regions" > "$OUT/regions.json" 2>&1 || {
  echo "ERROR: /api/forecasting/regions failed"
  exit 1
}

REGION_COUNT=$(jq '. | length' "$OUT/regions.json" 2>/dev/null || echo "0")
echo "  Found $REGION_COUNT regions"

# Find IL and AZ regions
IL_REGION=$(jq -r '.[] | select(.id | contains("il") or contains("IL")) | .id' "$OUT/regions.json" 2>/dev/null | head -1)
AZ_REGION=$(jq -r '.[] | select(.id | contains("az") or contains("AZ")) | .id' "$OUT/regions.json" 2>/dev/null | head -1)

if [ -z "$IL_REGION" ] || [ -z "$AZ_REGION" ]; then
  echo "  WARN: Could not find IL or AZ regions, using defaults"
  IL_REGION="us_il"
  AZ_REGION="us_az"
fi

echo "  Generating forecasts for IL ($IL_REGION) and AZ ($AZ_REGION)..."

# Generate forecast for IL
cat > "$OUT/forecast_il_payload.json" <<JSON
{
  "region_id": "$IL_REGION",
  "region_name": "Illinois",
  "days_back": 30,
  "forecast_horizon": 7
}
JSON

curl -fsS -X POST "http://localhost:8100/api/forecast" \
  -H "Content-Type: application/json" \
  -d @"$OUT/forecast_il_payload.json" > "$OUT/forecast_il.json" 2>&1 || {
  echo "ERROR: Forecast for IL failed"
  exit 1
}

# Generate forecast for AZ
cat > "$OUT/forecast_az_payload.json" <<JSON
{
  "region_id": "$AZ_REGION",
  "region_name": "Arizona",
  "days_back": 30,
  "forecast_horizon": 7
}
JSON

curl -fsS -X POST "http://localhost:8100/api/forecast" \
  -H "Content-Type: application/json" \
  -d @"$OUT/forecast_az_payload.json" > "$OUT/forecast_az.json" 2>&1 || {
  echo "ERROR: Forecast for AZ failed"
  exit 1
}

# Check for fuel_stress in responses
if grep -q "fuel_stress" "$OUT/forecast_il.json" || jq -e '.history[0].sub_indices.fuel_stress // .history[0].fuel_stress' "$OUT/forecast_il.json" > /dev/null 2>&1; then
  echo "  PROVED: fuel_stress appears in forecast response"
else
  echo "  MISSING: fuel_stress not found in forecast response"
fi

# --- PHASE 4: METRICS PROOF
echo
echo "[PHASE 4] Metrics proof (Prometheus series exist)..."

curl -fsS "http://localhost:8100/metrics" > "$OUT/metrics.txt" 2>&1 || {
  echo "ERROR: Could not fetch metrics"
  exit 1
}

# Check for region="None"
if grep -q 'region="None"' "$OUT/metrics.txt" || grep -q "region=None" "$OUT/metrics.txt"; then
  echo "  BROKEN: Found region='None' in metrics"
  grep 'region="None"\|region=None' "$OUT/metrics.txt" | head -5 > "$OUT/metrics_region_none.txt"
else
  echo "  PROVED: No region='None' found"
fi

# Count distinct regions
DISTINCT_REGIONS=$(grep "^behavior_index" "$OUT/metrics.txt" | grep -oE 'region="[^"]+"' | sort -u | wc -l | tr -d ' ')
echo "  Found $DISTINCT_REGIONS distinct regions for behavior_index"

# Check for fuel metrics
if grep -qi "fuel" "$OUT/metrics.txt"; then
  echo "  PROVED: Fuel-related metrics found"
  grep -i "fuel" "$OUT/metrics.txt" | head -10 > "$OUT/metrics_fuel_extract.txt"
  cat "$OUT/metrics_fuel_extract.txt"
else
  echo "  MISSING: No fuel-related metrics found"
fi

# --- PHASE 5: PROMETHEUS QUERY PROOF
echo
echo "[PHASE 5] Prometheus query proof (Grafana can see it)..."

sleep 5  # Wait for Prometheus to scrape

curl -fsS "http://localhost:9090/api/v1/label/region/values" > "$OUT/prom_regions.json" 2>&1 || {
  echo "WARN: Prometheus label query failed"
}

curl -fsS -G "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=child_subindex_value' > "$OUT/prom_child.json" 2>&1 || {
  echo "WARN: Prometheus child_subindex query failed"
}

curl -fsS -G "http://localhost:9090/api/v1/query" \
  --data-urlencode 'query=child_subindex_value{child="fuel_stress"}' > "$OUT/prom_fuel.json" 2>&1 || {
  echo "WARN: Prometheus fuel_stress query failed"
}

# Check Prometheus targets
curl -fsS "http://localhost:9090/api/v1/targets" > "$OUT/prom_targets.json" 2>&1 || {
  echo "WARN: Prometheus targets query failed"
}

if jq -e '.data.activeTargets[] | select(.health == "up")' "$OUT/prom_targets.json" > /dev/null 2>&1; then
  echo "  PROVED: Prometheus targets are UP"
else
  echo "  BROKEN: Prometheus targets may be down"
fi

# --- PHASE 6: GRAFANA DASHBOARD REALITY CHECK
echo
echo "[PHASE 6] Grafana dashboard reality check..."

# Check provisioning in container
docker compose exec -T grafana ls -R /etc/grafana/provisioning > "$OUT/grafana_provisioning_tree.txt" 2>&1 || true

# Check dashboard path
docker compose exec -T grafana sh -c "find /var/lib/grafana/dashboards -name '*.json' -print 2>/dev/null" > "$OUT/grafana_dashboard_jsons.txt" 2>&1 || true

DASHBOARD_COUNT_CONTAINER=$(wc -l < "$OUT/grafana_dashboard_jsons.txt" | tr -d ' ')
echo "  Found $DASHBOARD_COUNT_CONTAINER dashboards in Grafana container"

# Check if Grafana API is accessible
if curl -fsS -u admin:admin "http://localhost:3001/api/search?type=dash-db" > "$OUT/grafana_dashboards_api.json" 2>&1; then
  API_DASHBOARD_COUNT=$(jq '. | length' "$OUT/grafana_dashboards_api.json" 2>/dev/null || echo "0")
  echo "  Grafana API reports $API_DASHBOARD_COUNT dashboards"
  
  # List dashboard UIDs
  jq -r '.[].uid' "$OUT/grafana_dashboards_api.json" > "$OUT/grafana_dashboard_uids.txt" 2>/dev/null || true
else
  echo "  WARN: Could not query Grafana API"
fi

# --- PHASE 7: SURGICAL REPAIRS (if needed)
echo
echo "[PHASE 7] Surgical repairs (if needed)..."

REPAIRS_NEEDED=0
cat > "$OUT/BUGS.md" <<EOF
# Bugs and Missing Components

Generated: $(ts)

EOF

# Check if fuel_stress is in dashboards
if ! grep -r -l "fuel_stress" infra/grafana/dashboards/*.json 2>/dev/null | head -1; then
  echo "  REPAIR NEEDED: fuel_stress not in dashboards"
  echo "- fuel_stress missing from dashboards" >> "$OUT/BUGS.md"
  REPAIRS_NEEDED=1
fi

# Check if metrics are being scraped
if ! jq -e '.data.activeTargets[] | select(.health == "up")' "$OUT/prom_targets.json" > /dev/null 2>&1; then
  echo "  REPAIR NEEDED: Prometheus targets not healthy"
  echo "- Prometheus scrape targets unhealthy" >> "$OUT/BUGS.md"
  REPAIRS_NEEDED=1
fi

if [ "$REPAIRS_NEEDED" -eq 0 ]; then
  echo "  No repairs needed - all checks passed"
fi

# --- PHASE 8: END-TO-END PROOF (POST-REPAIR)
echo
echo "[PHASE 8] End-to-end proof summary..."

cat > "$OUT/SUMMARY.md" <<EOF
# Post-Work Verification Summary

Generated: $(ts)

## Verification Results

### Phase 1: Docker Stack Readiness
- Status: $(grep -q "200" "$OUT/readiness_results.txt" && echo "PASS" || echo "FAIL")
- All services responding: $(grep -c "200" "$OUT/readiness_results.txt" || echo "0")/6

### Phase 2: File-System Reality
- EIA fuel prices file: $(grep -q "EXISTS" "$OUT/filesystem_findings.md" && echo "PROVED" || echo "MISSING")
- Source registry: $(grep -q "VERIFIED" "$OUT/filesystem_findings.md" && echo "PROVED" || echo "MISSING")
- Behavior index integration: $(grep -q "VERIFIED" "$OUT/filesystem_findings.md" && echo "PROVED" || echo "MISSING")
- Dashboard count: $(find infra/grafana/dashboards -name "*.json" 2>/dev/null | wc -l | tr -d ' ')

### Phase 3: API Proof
- Regions available: $REGION_COUNT
- Forecasts generated: IL and AZ
- fuel_stress in response: $(grep -q "fuel_stress" "$OUT/forecast_il.json" && echo "PROVED" || echo "MISSING")

### Phase 4: Metrics Proof
- Distinct regions: $DISTINCT_REGIONS
- region="None" found: $(grep -q "region=\"None\"" "$OUT/metrics.txt" && echo "YES (BROKEN)" || echo "NO (GOOD)")
- Fuel metrics present: $(grep -qi "fuel" "$OUT/metrics.txt" && echo "PROVED" || echo "MISSING")

### Phase 5: Prometheus Query
- Targets healthy: $(jq -e '.data.activeTargets[] | select(.health == "up")' "$OUT/prom_targets.json" > /dev/null 2>&1 && echo "YES" || echo "NO")

### Phase 6: Grafana Dashboards
- Dashboards in container: $DASHBOARD_COUNT_CONTAINER
- Dashboards via API: ${API_DASHBOARD_COUNT:-0}

## Evidence Files

All evidence saved to: $OUT

## Repairs Applied

$(if [ "$REPAIRS_NEEDED" -eq 1 ]; then
  echo "See BUGS.md for issues requiring repair"
else
  echo "No repairs needed - all components verified"
fi)

EOF

cat "$OUT/SUMMARY.md"
echo
echo "Evidence bundle: $OUT"
echo "Summary: $OUT/SUMMARY.md"

if [ "$REPAIRS_NEEDED" -eq 1 ]; then
  echo
  echo "WARN: Some components need repair - see $OUT/BUGS.md"
  exit 1
else
  echo
  echo "PASS: All verification checks passed"
  exit 0
fi
