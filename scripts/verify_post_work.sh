#!/usr/bin/env bash
# Post-Work Verification Script
# Verifies claimed changes exist and are wired correctly end-to-end
# Usage: ./scripts/verify_post_work.sh

set -euo pipefail

EVIDENCE_DIR="/tmp/hbc_post_verify_$(date -u +%Y%m%d_%H%M%S)"
mkdir -p "$EVIDENCE_DIR"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "HBC Post-Work Verification"
echo "=========================="
echo "Timestamp: $(ts)"
echo "Evidence dir: $EVIDENCE_DIR"
echo

# Phase 1: Docker Stack Hard Readiness
echo "[PHASE 1] Docker stack hard readiness..."
{
  echo "Testing endpoints..."
  curl -fsS http://localhost:8100/health && echo "✅ Backend health: OK" || echo "❌ Backend health: FAIL"
  curl -fsS http://localhost:3100/ && echo "✅ Frontend root: OK" || echo "❌ Frontend root: FAIL"
  curl -fsS http://localhost:3100/forecast && echo "✅ Frontend forecast: OK" || echo "❌ Frontend forecast: FAIL"
  curl -fsS http://localhost:3100/history && echo "✅ Frontend history: OK" || echo "❌ Frontend history: FAIL"
  curl -fsS http://localhost:3001/ && echo "✅ Grafana: OK" || echo "❌ Grafana: FAIL"
  curl -fsS http://localhost:9090/ && echo "✅ Prometheus: OK" || echo "❌ Prometheus: FAIL"
} > "$EVIDENCE_DIR/readiness_results.txt" 2>&1 || true

cat "$EVIDENCE_DIR/readiness_results.txt"

# Phase 3: API Proof
echo
echo "[PHASE 3] API proof..."
curl -fsS http://localhost:8100/api/status > "$EVIDENCE_DIR/api_status.json" 2>&1 || true
curl -fsS http://localhost:8100/api/forecasting/regions > "$EVIDENCE_DIR/regions.json" 2>&1 || true

# Generate forecasts for IL and AZ
echo "Generating forecast for Illinois..."
curl -fsS -X POST http://localhost:8100/api/forecast \
  -H "Content-Type: application/json" \
  -d '{"region_id":"us_il","region_name":"Illinois","days_back":30,"forecast_horizon":7}' \
  > "$EVIDENCE_DIR/forecast_il.json" 2>&1 || true

echo "Generating forecast for Arizona..."
curl -fsS -X POST http://localhost:8100/api/forecast \
  -H "Content-Type: application/json" \
  -d '{"region_id":"us_az","region_name":"Arizona","days_back":30,"forecast_horizon":7}' \
  > "$EVIDENCE_DIR/forecast_az.json" 2>&1 || true

# Phase 4: Metrics Proof
echo
echo "[PHASE 4] Metrics proof..."
curl -fsS http://localhost:8100/metrics > "$EVIDENCE_DIR/metrics.txt" 2>&1 || true

# Check for region="None"
if grep -q 'region="None"' "$EVIDENCE_DIR/metrics.txt" 2>/dev/null; then
  echo "❌ Found region='None' in metrics"
else
  echo "✅ No region='None' found"
fi

# Count distinct regions
DISTINCT=$(grep -oE 'region="[^"]+"' "$EVIDENCE_DIR/metrics.txt" 2>/dev/null | sort -u | wc -l || echo "0")
echo "Distinct regions in metrics: $DISTINCT"

# Check for fuel_stress
if grep -qi "fuel" "$EVIDENCE_DIR/metrics.txt" 2>/dev/null; then
  echo "✅ Fuel metrics found"
  grep -i "fuel" "$EVIDENCE_DIR/metrics.txt" | head -20 > "$EVIDENCE_DIR/metrics_fuel_extract.txt" || true
else
  echo "❌ No fuel metrics found"
fi

# Phase 5: Prometheus Query Proof
echo
echo "[PHASE 5] Prometheus query proof..."
curl -fsS "http://localhost:9090/api/v1/label/region/values" > "$EVIDENCE_DIR/prom_regions.json" 2>&1 || true
curl -fsS "http://localhost:9090/api/v1/query?query=child_subindex_value{child=\"fuel_stress\"}" > "$EVIDENCE_DIR/prom_fuel.json" 2>&1 || true
curl -fsS "http://localhost:9090/api/v1/targets" > "$EVIDENCE_DIR/prom_targets.json" 2>&1 || true

# Phase 6: Grafana Dashboard Reality Check
echo
echo "[PHASE 6] Grafana dashboard reality check..."
docker compose exec -T grafana ls -R /etc/grafana/provisioning > "$EVIDENCE_DIR/grafana_provisioning_tree.txt" 2>&1 || true
docker compose exec -T grafana ls -R /var/lib/grafana/dashboards > "$EVIDENCE_DIR/grafana_dashboard_jsons.txt" 2>&1 || true

# Generate summary
cat > "$EVIDENCE_DIR/SUMMARY.md" <<EOF
# Post-Work Verification Summary

**Generated**: $(ts)
**Evidence Directory**: $EVIDENCE_DIR

## Verification Results

### Phase 1: Docker Stack Readiness
- See: \`readiness_results.txt\`

### Phase 3: API Proof
- Status: \`api_status.json\`
- Regions: \`regions.json\`
- Forecast IL: \`forecast_il.json\`
- Forecast AZ: \`forecast_az.json\`

### Phase 4: Metrics Proof
- Metrics dump: \`metrics.txt\`
- Fuel extract: \`metrics_fuel_extract.txt\`
- Distinct regions: $DISTINCT

### Phase 5: Prometheus
- Regions: \`prom_regions.json\`
- Fuel query: \`prom_fuel.json\`
- Targets: \`prom_targets.json\`

### Phase 6: Grafana
- Provisioning tree: \`grafana_provisioning_tree.txt\`
- Dashboard JSONs: \`grafana_dashboard_jsons.txt\`

## Next Steps

1. Review evidence files in: $EVIDENCE_DIR
2. Check for any failures in readiness_results.txt
3. Verify fuel_stress appears in forecast JSONs
4. Verify fuel_stress metrics exist
5. Verify Grafana dashboards are loaded
EOF

cat "$EVIDENCE_DIR/SUMMARY.md"
echo
echo "Evidence saved to: $EVIDENCE_DIR"
