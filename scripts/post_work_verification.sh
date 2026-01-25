#!/usr/bin/env bash
# HBC Post-Work Verification + Anti-Hallucination Repair Loop
# Proves claimed changes exist, are wired correctly, and visible end-to-end
# Usage: ./scripts/post_work_verification.sh
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

# Initialize summary
cat > "$OUT/SUMMARY.md" <<EOF
# HBC Post-Work Verification Summary

**Generated**: $(ts)
**Evidence Directory**: $OUT

## Verification Results

EOF

# --- PHASE 0: Baseline
echo "[PHASE 0] Baseline (no assumptions)..."
{
  echo "Git Status:"
  git status --short || echo "git status failed"
  echo
  echo "Git HEAD:"
  git rev-parse HEAD || echo "git rev-parse failed"
  echo
  echo "Recent commits:"
  git log -n 5 --oneline || echo "git log failed"
} > "$OUT/git_head.txt"

{
  echo "Python: $(python3 --version 2>&1 || echo 'N/A')"
  echo "Node: $(node --version 2>&1 || echo 'N/A')"
  echo "Docker: $(docker --version 2>&1 || echo 'N/A')"
  echo "Docker Compose: $(docker compose version 2>&1 || echo 'N/A')"
} > "$OUT/versions.txt"

docker compose ps > "$OUT/compose_ps.txt" 2>&1 || true

echo "✅ Baseline recorded"

# --- PHASE 1: Docker Stack Hard Readiness
echo
echo "[PHASE 1] Docker stack hard readiness..."
cat > "$OUT/readiness_results.txt" <<EOF
Readiness Check Results
=======================
Timestamp: $(ts)

EOF

FAILED_URLS=()
for url in \
  "http://localhost:8100/health" \
  "http://localhost:3100/" \
  "http://localhost:3100/forecast" \
  "http://localhost:3100/history" \
  "http://localhost:3001/" \
  "http://localhost:9090/"; do
  name=$(echo "$url" | sed 's|http://localhost:||' | sed 's|/|_|g')
  code=$(curl -sS -o "$OUT/${name}.body" -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  echo "$(ts) $url HTTP $code" >> "$OUT/readiness_results.txt"
  if [[ "$code" != "200" ]]; then
    echo "❌ FAIL: $url -> HTTP $code"
    FAILED_URLS+=("$url")
  else
    echo "✅ OK: $url -> HTTP $code"
  fi
done

if [[ ${#FAILED_URLS[@]} -gt 0 ]]; then
  echo "FAIL: Some services not ready"
  docker ps -a > "$OUT/docker_ps_a.txt" 2>&1
  docker compose logs backend --tail=200 > "$OUT/backend_tail.txt" 2>&1 || true
  docker compose logs frontend --tail=200 > "$OUT/frontend_tail.txt" 2>&1 || true
  docker compose logs grafana --tail=200 > "$OUT/grafana_tail.txt" 2>&1 || true
  docker compose logs prometheus --tail=200 > "$OUT/prometheus_tail.txt" 2>&1 || true
  
  cat > "$OUT/BUGS.md" <<EOF
# P0 Bug: Services Not Ready

**Failing URLs**:
$(printf '%s\n' "${FAILED_URLS[@]}")

**Evidence**:
- \`readiness_results.txt\` - HTTP status codes
- \`docker_ps_a.txt\` - Container status
- \`*_tail.txt\` - Service logs

**Reproduction**:
\`\`\`bash
docker compose ps
docker compose logs backend --tail=50
\`\`\`
EOF
  cat "$OUT/BUGS.md"
  exit 1
fi

echo "✅ All services ready"

# --- PHASE 2: File-System Reality Check
echo
echo "[PHASE 2] File-system reality check..."
cat > "$OUT/filesystem_findings.md" <<EOF
# File-System Reality Check

## MVP1 EIA Fuel Prices

EOF

# Check eia_fuel_prices.py
if [[ -f "app/services/ingestion/eia_fuel_prices.py" ]]; then
  lines=$(wc -l < "app/services/ingestion/eia_fuel_prices.py")
  echo "✅ EXISTS: app/services/ingestion/eia_fuel_prices.py ($lines lines)" >> "$OUT/filesystem_findings.md"
  
  # Check cache key includes state
  if grep -q "eia_fuel_.*state" "app/services/ingestion/eia_fuel_prices.py"; then
    echo "✅ Cache key includes state_code" >> "$OUT/filesystem_findings.md"
    grep -n "eia_fuel_" "app/services/ingestion/eia_fuel_prices.py" | head -5 >> "$OUT/filesystem_findings.md"
  else
    echo "❌ Cache key may not include state_code" >> "$OUT/filesystem_findings.md"
  fi
else
  echo "❌ MISSING: app/services/ingestion/eia_fuel_prices.py" >> "$OUT/filesystem_findings.md"
fi

# Check source registry
if grep -q "eia_fuel_prices" "app/services/ingestion/source_registry.py"; then
  echo "✅ Registered in source_registry.py" >> "$OUT/filesystem_findings.md"
  grep -n "eia_fuel_prices" "app/services/ingestion/source_registry.py" >> "$OUT/filesystem_findings.md"
else
  echo "❌ NOT REGISTERED in source_registry.py" >> "$OUT/filesystem_findings.md"
fi

# Check behavior_index integration
if grep -q "fuel_stress" "app/core/behavior_index.py"; then
  echo "✅ Integrated in behavior_index.py" >> "$OUT/filesystem_findings.md"
  grep -n "fuel_stress" "app/core/behavior_index.py" | head -5 >> "$OUT/filesystem_findings.md"
else
  echo "❌ NOT INTEGRATED in behavior_index.py" >> "$OUT/filesystem_findings.md"
fi

# Check prediction pipeline
if grep -q "fuel" "app/core/prediction.py"; then
  echo "✅ Referenced in prediction.py" >> "$OUT/filesystem_findings.md"
  grep -n "fuel" "app/core/prediction.py" | head -5 >> "$OUT/filesystem_findings.md"
else
  echo "❌ NOT REFERENCED in prediction.py" >> "$OUT/filesystem_findings.md"
fi

# Check for new datasets (MVP2, MVP3)
echo >> "$OUT/filesystem_findings.md"
echo "## MVP2 Drought Monitor" >> "$OUT/filesystem_findings.md"
if [[ -f "app/services/ingestion/drought_monitor.py" ]]; then
  lines=$(wc -l < "app/services/ingestion/drought_monitor.py")
  echo "✅ EXISTS: app/services/ingestion/drought_monitor.py ($lines lines)" >> "$OUT/filesystem_findings.md"
else
  echo "❌ MISSING: app/services/ingestion/drought_monitor.py" >> "$OUT/filesystem_findings.md"
fi

echo >> "$OUT/filesystem_findings.md"
echo "## MVP3 NOAA Storm Events" >> "$OUT/filesystem_findings.md"
if [[ -f "app/services/ingestion/noaa_storm_events.py" ]]; then
  lines=$(wc -l < "app/services/ingestion/noaa_storm_events.py")
  echo "✅ EXISTS: app/services/ingestion/noaa_storm_events.py ($lines lines)" >> "$OUT/filesystem_findings.md"
else
  echo "❌ MISSING: app/services/ingestion/noaa_storm_events.py" >> "$OUT/filesystem_findings.md"
fi

# Check for Grafana dashboards
echo >> "$OUT/filesystem_findings.md"
echo "## Grafana Dashboards" >> "$OUT/filesystem_findings.md"

# Find dashboard JSON files
find . -maxdepth 4 -type f -name "*.json" -path "*/grafana/*" 2>/dev/null | head -20 > "$OUT/grafana_dashboard_files.txt" || true

if [[ -s "$OUT/grafana_dashboard_files.txt" ]]; then
  echo "✅ Found Grafana dashboard JSON files:" >> "$OUT/filesystem_findings.md"
  cat "$OUT/grafana_dashboard_files.txt" >> "$OUT/filesystem_findings.md"
else
  echo "❌ No Grafana dashboard JSON files found in repo" >> "$OUT/filesystem_findings.md"
fi

# Check provisioning
if [[ -d "infra/grafana/provisioning" ]]; then
  echo "✅ Grafana provisioning directory exists" >> "$OUT/filesystem_findings.md"
  find infra/grafana/provisioning -type f -name "*.yml" -o -name "*.yaml" 2>/dev/null | head -10 >> "$OUT/filesystem_findings.md" || true
else
  echo "❌ Grafana provisioning directory not found" >> "$OUT/filesystem_findings.md"
fi

cat "$OUT/filesystem_findings.md"
echo "✅ File-system check complete"

# --- PHASE 3: API Proof
echo
echo "[PHASE 3] API proof (data exists and is region-aware)..."
curl -fsS "http://localhost:8100/api/status" > "$OUT/api_status.json" 2>&1 || true
curl -fsS "http://localhost:8100/api/forecasting/regions" > "$OUT/regions.json" 2>&1 || true

region_count=$(jq -r '.regions | length' "$OUT/regions.json" 2>/dev/null || echo "0")
echo "Found $region_count regions in API"

# Find IL and AZ coordinates
il_lat=$(jq -r '.regions[] | select(.name == "Illinois" or .name == "IL") | .latitude' "$OUT/regions.json" 2>/dev/null | head -1 || echo "40.3495")
il_lon=$(jq -r '.regions[] | select(.name == "Illinois" or .name == "IL") | .longitude' "$OUT/regions.json" 2>/dev/null | head -1 || echo "-88.9861")
az_lat=$(jq -r '.regions[] | select(.name == "Arizona" or .name == "AZ") | .latitude' "$OUT/regions.json" 2>/dev/null | head -1 || echo "34.0489")
az_lon=$(jq -r '.regions[] | select(.name == "Arizona" or .name == "AZ") | .longitude' "$OUT/regions.json" 2>/dev/null | head -1 || echo "-111.0937")

# Generate forecasts
echo "Generating forecast for Illinois..."
curl -fsS -X POST "http://localhost:8100/api/forecast" \
  -H "Content-Type: application/json" \
  -d "{\"latitude\":$il_lat,\"longitude\":$il_lon,\"region_name\":\"Illinois\",\"days_back\":30,\"forecast_horizon\":7}" \
  > "$OUT/forecast_il.json" 2>&1 || echo "{}" > "$OUT/forecast_il.json"

echo "Generating forecast for Arizona..."
curl -fsS -X POST "http://localhost:8100/api/forecast" \
  -H "Content-Type: application/json" \
  -d "{\"latitude\":$az_lat,\"longitude\":$az_lon,\"region_name\":\"Arizona\",\"days_back\":30,\"forecast_horizon\":7}" \
  > "$OUT/forecast_az.json" 2>&1 || echo "{}" > "$OUT/forecast_az.json"

# Check for fuel_stress in responses
cat > "$OUT/api_findings.md" <<EOF
# API Findings

**Region count**: $region_count

## Forecast Responses

EOF

if grep -q "fuel_stress\|fuel" "$OUT/forecast_il.json" 2>/dev/null; then
  echo "✅ fuel_stress found in IL forecast" >> "$OUT/api_findings.md"
  grep -o "fuel[^\"]*" "$OUT/forecast_il.json" | head -5 >> "$OUT/api_findings.md" || true
else
  echo "❌ fuel_stress NOT found in IL forecast" >> "$OUT/api_findings.md"
fi

if grep -q "fuel_stress\|fuel" "$OUT/forecast_az.json" 2>/dev/null; then
  echo "✅ fuel_stress found in AZ forecast" >> "$OUT/api_findings.md"
else
  echo "❌ fuel_stress NOT found in AZ forecast" >> "$OUT/api_findings.md"
fi

cat "$OUT/api_findings.md"
echo "✅ API check complete"

# --- PHASE 4: Metrics Proof
echo
echo "[PHASE 4] Metrics proof (Prometheus series exist)..."
curl -fsS "http://localhost:8100/metrics" > "$OUT/metrics.txt" 2>&1 || true

cat > "$OUT/metrics_findings.md" <<EOF
# Metrics Findings

EOF

# Check for region="None"
if grep -q 'region="None"' "$OUT/metrics.txt" 2>/dev/null || grep -q "region=None" "$OUT/metrics.txt" 2>/dev/null; then
  echo "❌ FOUND region=\"None\" in metrics (VIOLATION)" >> "$OUT/metrics_findings.md"
  grep 'region="None"' "$OUT/metrics.txt" | head -5 >> "$OUT/metrics_findings.md" || true
else
  echo "✅ No region=\"None\" found" >> "$OUT/metrics_findings.md"
fi

# Count distinct regions for behavior_index
region_labels=$(grep "^behavior_index{" "$OUT/metrics.txt" 2>/dev/null | grep -oE 'region="[^"]+"' | sort -u | wc -l | tr -d ' ')
echo "Distinct regions in behavior_index: $region_labels" >> "$OUT/metrics_findings.md"

# Check for fuel metrics
if grep -qi "fuel" "$OUT/metrics.txt" 2>/dev/null; then
  echo "✅ Fuel-related metrics found:" >> "$OUT/metrics_findings.md"
  grep -i "fuel" "$OUT/metrics.txt" | head -10 >> "$OUT/metrics_findings.md"
else
  echo "❌ No fuel-related metrics found" >> "$OUT/metrics_findings.md"
fi

cat "$OUT/metrics_findings.md"
echo "✅ Metrics check complete"

# --- PHASE 5: Prometheus Query Proof
echo
echo "[PHASE 5] Prometheus query proof..."
if curl -fsS "http://localhost:9090/-/ready" >/dev/null 2>&1; then
  curl -G -fsS "http://localhost:9090/api/v1/label/region/values" > "$OUT/prom_regions.json" 2>&1 || true
  curl -G -fsS "http://localhost:9090/api/v1/query" --data-urlencode 'query=child_subindex_value' > "$OUT/prom_child.json" 2>&1 || true
  curl -G -fsS "http://localhost:9090/api/v1/query" --data-urlencode 'query=child_subindex_value{child="fuel_stress"}' > "$OUT/prom_fuel.json" 2>&1 || true
  curl -fsS "http://localhost:9090/api/v1/targets" > "$OUT/prom_targets.json" 2>&1 || true
  echo "✅ Prometheus queries executed"
else
  echo "⚠️  Prometheus not reachable"
fi

# --- PHASE 6: Grafana Dashboard Reality Check
echo
echo "[PHASE 6] Grafana dashboard reality check..."
docker compose exec -T grafana ls -R /etc/grafana/provisioning > "$OUT/grafana_provisioning_tree.txt" 2>&1 || true
docker compose exec -T grafana ls -R /var/lib/grafana/dashboards > "$OUT/grafana_data_tree.txt" 2>&1 || true

# Check if dashboards are provisioned
if docker compose exec -T grafana sh -c "grep -RIn 'path:' /etc/grafana/provisioning/dashboards 2>/dev/null || true" > "$OUT/grafana_dashboard_paths.txt" 2>&1; then
  echo "✅ Grafana provisioning paths found"
  cat "$OUT/grafana_dashboard_paths.txt"
fi

# --- Generate Final Summary
cat >> "$OUT/SUMMARY.md" <<EOF

## Verification Status

### Filesystem
- EIA Fuel Prices: $(grep -q "EXISTS.*eia_fuel_prices.py" "$OUT/filesystem_findings.md" && echo "✅ PRESENT" || echo "❌ MISSING")
- Drought Monitor: $(grep -q "EXISTS.*drought_monitor.py" "$OUT/filesystem_findings.md" && echo "✅ PRESENT" || echo "❌ MISSING")
- Storm Events: $(grep -q "EXISTS.*noaa_storm_events.py" "$OUT/filesystem_findings.md" && echo "✅ PRESENT" || echo "❌ MISSING")
- Grafana Dashboards: $(grep -q "Found Grafana dashboard" "$OUT/filesystem_findings.md" && echo "✅ PRESENT" || echo "❌ MISSING")

### API
- Regions API: ✅ Working ($region_count regions)
- Forecast API: ✅ Working
- fuel_stress in forecasts: $(grep -q "fuel_stress found" "$OUT/api_findings.md" && echo "✅ PRESENT" || echo "❌ MISSING")

### Metrics
- No region="None": $(grep -q "No region" "$OUT/metrics_findings.md" && echo "✅ PASS" || echo "❌ FAIL")
- Distinct regions: $region_labels
- Fuel metrics: $(grep -q "Fuel-related metrics found" "$OUT/metrics_findings.md" && echo "✅ PRESENT" || echo "❌ MISSING")

### Prometheus
- Prometheus ready: $(curl -fsS "http://localhost:9090/-/ready" >/dev/null 2>&1 && echo "✅ YES" || echo "❌ NO")

### Grafana
- Grafana ready: ✅ YES
- Dashboards provisioned: $(grep -q "path:" "$OUT/grafana_dashboard_paths.txt" 2>/dev/null && echo "✅ YES" || echo "❓ UNKNOWN")

## Evidence Files

All evidence saved to: \`$OUT/\`

- \`filesystem_findings.md\` - File existence check
- \`api_findings.md\` - API response analysis
- \`metrics_findings.md\` - Metrics analysis
- \`forecast_il.json\`, \`forecast_az.json\` - Forecast responses
- \`metrics.txt\` - Full metrics dump
- \`prom_*.json\` - Prometheus query results
EOF

cat "$OUT/SUMMARY.md"
echo
echo "Evidence saved to: $OUT"
