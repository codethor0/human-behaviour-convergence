#!/usr/bin/env bash
set -euo pipefail

# Run from repo root or normalize relative to this script
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "=== [GATE G] Grafana / Prometheus Verification ==="

FAIL=0

echo
echo "[1] Docker stack status"
if command -v docker >/dev/null 2>&1; then
  docker compose ps || { echo "[FAIL] docker compose ps"; FAIL=1; }
else
  echo "[FAIL] docker not available on PATH"
  FAIL=1
fi

echo
echo "[2] Backend /metrics basic check (behavior_index / parent_subindex_value / child_subindex_value)"
if curl -sS http://localhost:8100/metrics >/tmp/gateg_metrics.txt 2>/tmp/gateg_metrics_err.txt; then
  if grep -q "^behavior_index" /tmp/gateg_metrics.txt && \
     grep -q "^parent_subindex_value" /tmp/gateg_metrics.txt && \
     grep -q "^child_subindex_value" /tmp/gateg_metrics.txt; then
    echo "[OK] Core metrics found in /metrics"
  else
    echo "[FAIL] Core metrics missing in /metrics (behavior_index/parent_subindex_value/child_subindex_value)"
    FAIL=1
  fi
else
  echo "[FAIL] Could not reach backend /metrics on http://localhost:8100/metrics"
  FAIL=1
fi

echo
echo "[3] Prometheus targets: backend scrape status"
if curl -sS "http://localhost:9090/api/v1/targets" > /tmp/gateg_targets.json 2>/tmp/gateg_targets_err.txt; then
  python3 - << 'PY'
import json, sys
data = json.load(open("/tmp/gateg_targets.json"))
targets = data.get("data", {}).get("activeTargets", [])
backend_targets = [t for t in targets if "backend" in t.get("labels", {}).get("job", "") or "backend" in t.get("scrapeUrl", "")]
if not backend_targets:
    print("[FAIL] No backend targets found in Prometheus")
    sys.exit(1)
bad = [t for t in backend_targets if t.get("health") != "up"]
if bad:
    print("[FAIL] Backend targets present but not all healthy:")
    for t in bad:
        print("  - job={job} health={health} scrapeUrl={url}".format(
            job=t.get("labels", {}).get("job"),
            health=t.get("health"),
            url=t.get("scrapeUrl"),
        ))
    sys.exit(1)
print("[OK] Backend Prometheus target(s) present and healthy")
PY
  if [ $? -ne 0 ]; then
    FAIL=1
  fi
else
  echo "[FAIL] Could not reach Prometheus targets API on http://localhost:9090/api/v1/targets"
  FAIL=1
fi

echo
echo "[4] Prometheus queries for dashboard metrics"
prom_query() {
  local name="$1"
  local query="$2"
  local encoded_query="$(python3 -c "import urllib.parse; print(urllib.parse.quote('${query}'))")"
  local url="http://localhost:9090/api/v1/query?query=${encoded_query}"
  echo "  - ${name}: ${query}"
  if ! curl -sS "${url}" > /tmp/gateg_query.json 2>/tmp/gateg_query_err.txt; then
    echo "    [FAIL] HTTP error talking to Prometheus"
    FAIL=1
    return
  fi
  python3 - << 'PY'
import json, sys
data = json.load(open("/tmp/gateg_query.json"))
if data.get("status") != "success":
    print("    [FAIL] Prometheus query status:", data.get("status"))
    sys.exit(1)
results = data.get("data", {}).get("result", [])
if not results:
    print("    [FAIL] No data returned (empty result)")
    sys.exit(1)
print("    [OK] Non-empty result, series count:", len(results))
PY
  if [ $? -ne 0 ]; then
    FAIL=1
  fi
}

echo "[4.1] Global Behavior Index dashboard queries"
prom_query "behavior_index (us_mn)" "behavior_index{region=\"us_mn\"}"
prom_query "behavior_index (all regions)" "behavior_index"
prom_query "parent_subindex_value (us_mn)" "parent_subindex_value{region=\"us_mn\"}"
prom_query "forecast rate" "rate(forecasts_generated_total{status=\"success\"}[5m])"

# Note: histogram queries may return empty if no data in time window
echo "  - forecast p95 duration (histogram - may be empty if no recent forecasts)"
encoded_query="$(python3 -c "import urllib.parse; print(urllib.parse.quote('histogram_quantile(0.95, sum(rate(forecast_computation_duration_seconds_bucket[5m])) by (le, region))'))")"
curl -sS "http://localhost:9090/api/v1/query?query=${encoded_query}" > /tmp/gateg_histogram.json 2>&1
if python3 -c "import json; d=json.load(open('/tmp/gateg_histogram.json')); exit(0 if d.get('status')=='success' else 1)" 2>/dev/null; then
  echo "    [OK] Histogram query executed (status=success)"
else
  echo "    [FAIL] Histogram query failed"
  FAIL=1
fi

echo
echo "[4.2] Sub-Index Deep Dive dashboard queries"
prom_query "parent_subindex_value (all)" "parent_subindex_value"
prom_query "parent_subindex_value (us_mn, economic_stress)" "parent_subindex_value{region=\"us_mn\", parent=\"economic_stress\"}"
prom_query "child_subindex_value (all)" "child_subindex_value"
prom_query "child_subindex_value (us_mn)" "child_subindex_value{region=\"us_mn\"}"

echo
echo "[4.3] Regional Comparison dashboard queries"
prom_query "behavior_index (multi-region)" "behavior_index{region=~\"us_mn|us_ny|us_ca\"}"
prom_query "parent_subindex (economic, multi-region)" "parent_subindex_value{region=~\"us_mn|us_ny\", parent=\"economic_stress\"}"

echo
echo "[4.4] Historical Trends & Volatility dashboard queries"
prom_query "behavior_index 7-day average" "avg_over_time(behavior_index{region=\"us_mn\"}[7d])"
prom_query "behavior_index 7-day derivative" "deriv(behavior_index{region=\"us_mn\"}[7d])"
prom_query "behavior_index 7-day volatility" "stddev_over_time(behavior_index{region=\"us_mn\"}[7d])"

echo
echo "[4.5] Risk Regimes dashboard queries"
# Note: critical regions query may legitimately return empty if no regions are currently critical
echo "  - critical regions (>= 0.7): behavior_index >= 0.7"
encoded_query="$(python3 -c "import urllib.parse; print(urllib.parse.quote('behavior_index >= 0.7'))")"
curl -sS "http://localhost:9090/api/v1/query?query=${encoded_query}" > /tmp/gateg_critical.json 2>&1
if python3 -c "import json; d=json.load(open('/tmp/gateg_critical.json')); exit(0 if d.get('status')=='success' else 1)" 2>/dev/null; then
  series_count=$(python3 -c "import json; print(len(json.load(open('/tmp/gateg_critical.json')).get('data',{}).get('result',[])))")
  echo "    [OK] Query successful, series count: ${series_count} (0 = no critical regions, expected in healthy system)"
else
  echo "    [FAIL] Query failed"
  FAIL=1
fi

# Note: unstable regions query may legitimately return empty if all regions have low volatility
echo "  - unstable regions (volatility): stddev_over_time(behavior_index[7d]) >= 0.1"
encoded_query="$(python3 -c "import urllib.parse; print(urllib.parse.quote('stddev_over_time(behavior_index[7d]) >= 0.1'))")"
curl -sS "http://localhost:9090/api/v1/query?query=${encoded_query}" > /tmp/gateg_unstable.json 2>&1
if python3 -c "import json; d=json.load(open('/tmp/gateg_unstable.json')); exit(0 if d.get('status')=='success' else 1)" 2>/dev/null; then
  series_count=$(python3 -c "import json; print(len(json.load(open('/tmp/gateg_unstable.json')).get('data',{}).get('result',[])))")
  echo "    [OK] Query successful, series count: ${series_count} (0 = low volatility system-wide, expected)"
else
  echo "    [FAIL] Query failed"
  FAIL=1
fi

prom_query "regime count (all)" "count(behavior_index)"

echo
echo "[5] Grafana health"
if curl -sS http://localhost:3001/api/health > /tmp/gateg_grafana_health.json 2>/tmp/gateg_grafana_health_err.txt; then
  python3 - << 'PY'
import json, sys
data = json.load(open("/tmp/gateg_grafana_health.json"))
db = data.get("database")
version = data.get("version")
if db != "ok":
    print("[FAIL] Grafana health database status:", db)
    sys.exit(1)
print("[OK] Grafana database=ok, version=", version)
PY
  if [ $? -ne 0 ]; then
    FAIL=1
  fi
else
  echo "[FAIL] Could not reach Grafana health API on http://localhost:3001/api/health"
  FAIL=1
fi

echo
echo "[6] Dashboard JSON presence (filesystem)"
for dashboard in global_behavior_index.json subindex_deep_dive.json regional_comparison.json historical_trends.json risk_regimes.json; do
  if [ -f "infrastructure/grafana/dashboards/${dashboard}" ]; then
    echo "[OK] ${dashboard} present"
  else
    echo "[FAIL] ${dashboard} missing"
    FAIL=1
  fi
done

echo
echo "[7] Alert rules provisioning (filesystem)"
if [ -f "infrastructure/grafana/provisioning/alerting/rules.yml" ]; then
  echo "[OK] rules.yml present (behavior index alerts)"
  # Validate YAML syntax
  if python3 -c "import yaml; yaml.safe_load(open('infrastructure/grafana/provisioning/alerting/rules.yml'))" 2>/dev/null; then
    echo "[OK] rules.yml is valid YAML"
  else
    echo "[FAIL] rules.yml is not valid YAML"
    FAIL=1
  fi
else
  echo "[FAIL] rules.yml missing"
  FAIL=1
fi

echo
if [ "$FAIL" -eq 0 ]; then
  echo "=== [GATE G RESULT] GREEN: Prometheus + Grafana pipeline healthy, queries return data ==="
else
  echo "=== [GATE G RESULT] RED: One or more checks failed; see messages above ==="
  echo
  echo "📖 Troubleshooting Guide:"
  echo "   See docs/RUNBOOK_DASHBOARDS.md for detailed troubleshooting steps"
  echo "   Common issues:"
  echo "   - Backend metrics not exposed → Section 2"
  echo "   - Prometheus targets down → Section 3, 4"
  echo "   - Grafana health issues → Section 3"
  echo "   - Empty queries → Section 5, 6"
fi

exit "$FAIL"
