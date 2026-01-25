#!/usr/bin/env bash
# HBC Grafana Visual Expansion Program
# Enterprise, Evidence-Driven, No-Hallucination, Auto-Execute
# Usage: ./scripts/grafana_visual_expansion.sh
set -euo pipefail

ROOT="${PWD}"
TS="$(date -u +%Y%m%d_%H%M%S)"
OUT="/tmp/hbc_grafana_expansion_${TS}"
mkdir -p "$OUT"/{promql_proof,grafana_proof,ui_proof}

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "HBC Grafana Visual Expansion Program"
echo "======================================"
echo "Timestamp: $(ts)"
echo "Evidence dir: $OUT"
echo "Mode: AUTONOMOUS (no prompts, auto-execute)"
echo

# --- PHASE 0: BASELINE + INVENTORY
echo "[PHASE 0] Baseline + Inventory..."

# Start stack
echo "  Starting Docker stack..."
docker compose down -v > "$OUT/docker_down.log" 2>&1 || true
docker compose up -d --build > "$OUT/docker_up.log" 2>&1
sleep 20

# Confirm services
check_service() {
  local url="$1" name="$2"
  local code
  code="$(curl -sS -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")"
  if [[ "$code" == "200" ]]; then
    echo "  OK: $name -> HTTP $code"
    return 0
  else
    echo "  FAIL: $name -> HTTP $code"
    return 1
  fi
}

SERVICES_OK=1
check_service "http://localhost:8100/health" "Backend" || SERVICES_OK=0
check_service "http://localhost:3100/" "Frontend" || SERVICES_OK=0
check_service "http://localhost:3001/" "Grafana" || SERVICES_OK=0
check_service "http://localhost:9090/-/ready" "Prometheus" || SERVICES_OK=0

if [ "$SERVICES_OK" -eq 0 ]; then
  echo "ERROR: Services not ready"
  exit 1
fi

# Identify Grafana provisioning
echo
echo "  Identifying Grafana provisioning structure..."
cat > "$OUT/grafana_provisioning_structure.txt" <<EOF
Grafana Provisioning Structure
==============================

Dashboards directory: infra/grafana/dashboards/
Provisioning YAML: infra/grafana/provisioning/dashboards/dashboards.yml

Existing dashboards:
EOF

find infra/grafana/dashboards -name "*.json" -type f | sort | while read -r dash; do
  UID=$(jq -r '.uid // "unknown"' "$dash" 2>/dev/null || echo "unknown")
  TITLE=$(jq -r '.title // "unknown"' "$dash" 2>/dev/null || echo "unknown")
  echo "  - $dash (UID: $UID, Title: $TITLE)" >> "$OUT/grafana_provisioning_structure.txt"
done

# Extract available metrics
echo
echo "  Extracting available Prometheus metrics..."
curl -fsS "http://localhost:8100/metrics" > "$OUT/metrics_dump.txt" 2>/dev/null || {
  echo "  WARN: Could not fetch metrics"
}

# Extract relevant metric names
grep -E "^behavior_index|^parent_subindex|^child_subindex|^data_source_status|^forecast_|^hbc_" "$OUT/metrics_dump.txt" | \
  cut -d'{' -f1 | sort -u > "$OUT/metric_names.txt" 2>/dev/null || true

echo "  Found $(wc -l < "$OUT/metric_names.txt" | tr -d ' ') unique metric families"

# Create inventory document
cat > "$OUT/inventory.md" <<EOF
# HBC Grafana Visual Expansion Inventory

Generated: $(ts)

## Services Status
- Backend: OK
- Frontend: OK
- Grafana: OK
- Prometheus: OK

## Existing Dashboards
$(find infra/grafana/dashboards -name "*.json" -type f | wc -l | tr -d ' ') dashboard JSON files found

## Available Metrics
$(cat "$OUT/metric_names.txt" | head -20 | sed 's/^/  - /')

## Next Steps
1. Verify required dashboards exist
2. Add missing metrics if needed
3. Enhance dashboards
4. Update UI embeds
5. Verify end-to-end
EOF

cat "$OUT/inventory.md"
echo "  Inventory saved to: $OUT/inventory.md"
