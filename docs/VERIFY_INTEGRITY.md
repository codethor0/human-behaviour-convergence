# How to Verify HBC Integrity

This document provides exact commands to verify system integrity, reproducibility, and correctness.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ installed
- Stack running: `docker compose up -d`

## Stack Readiness

```bash
# Check all services are healthy
curl -fsS http://localhost:8100/health
curl -fsS http://localhost:3100/ >/dev/null
curl -fsS http://localhost:9090/-/ready
curl -fsS http://localhost:3001/api/health

# Verify frontend routes
for route in / /forecast /history /live /playground; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" "http://localhost:3100${route}")
  echo "${route} -> ${code}"
done
```

## Warm-Up Verification

Grafana region dropdown populates as metrics become available. Background job takes ~5-10 minutes.

```bash
# Check current region count in Prometheus
curl -s "http://localhost:9090/api/v1/query?query=count(count%20by(region)(behavior_index))" | jq '.data.result[0].value[1]'

# Check warm-up metrics (if available)
curl -s http://localhost:8100/metrics | grep -E 'hbc_regions_with_metrics_count|hbc_warmup_progress_ratio'

# Expected: Region count increases over time (starts ~1-5, reaches 50+ after warm-up)
```

**Note**: If you see few regions immediately after stack start, wait 5-10 minutes for background metrics population, or generate a forecast manually to populate that region immediately.

## Multi-Region Forecast Proof

Generate forecasts for multiple regions and verify they differ:

```bash
# Generate forecasts
for region in us_mn us_ca city_nyc; do
  curl -sS -X POST http://localhost:8100/api/forecast \
    -H "Content-Type: application/json" \
    -d "{\"region_id\":\"$region\",\"region_name\":\"$region\",\"days_back\":30,\"forecast_horizon\":7}" \
    > /tmp/forecast_${region}.json
  echo "Generated forecast for $region"
  sleep 2
done

# Compute hashes to prove differences
python3 << 'PYEOF'
import json
import hashlib

regions = ['us_mn', 'us_ca', 'city_nyc']
for region in regions:
    with open(f'/tmp/forecast_{region}.json') as f:
        data = json.load(f)
        history = data.get('history', [])
        hist_vals = [h.get('behavior_index', 0) for h in history if isinstance(h, dict)]
        h = hashlib.sha256(str(sorted(hist_vals)).encode()).hexdigest()[:16]
        print(f"{region}: {h}")
PYEOF

# Expected: Different hashes for each region
```

## Metrics Proof

Verify metrics are multi-region and have no `region=None` labels:

```bash
# Check for region=None labels (should find none)
curl -s http://localhost:8100/metrics | grep -E 'region="None"|region=None' || echo "✓ No region=None labels"

# Query Prometheus for distinct region counts
python3 << 'PYEOF'
import requests

prometheus_url = "http://localhost:9090"
queries = {
    "behavior_index": 'count(count by(region)(behavior_index))',
    "parent_subindex_value": 'count(count by(region)(parent_subindex_value))',
    "child_subindex_value": 'count(count by(region)(child_subindex_value))',
}

for metric, query in queries.items():
    resp = requests.get(f"{prometheus_url}/api/v1/query", params={"query": query})
    data = resp.json()
    if data.get("data", {}).get("result"):
        count = int(float(data["data"]["result"][0]["value"][1]))
        print(f"{metric}: {count} distinct regions")
PYEOF

# Expected: All metrics show 50+ distinct regions (after warm-up)
```

## Data Quality Proof

Run data quality checkpoint:

```bash
# Run checkpoint
python3 scripts/run_data_quality_checkpoint.py

# View report
cat /tmp/HBC_DATA_QUALITY_REPORT.md

# Check for failures
grep -E "FAIL|❌" /tmp/HBC_DATA_QUALITY_REPORT.md || echo "✓ No failures"

# View evidence snapshots
ls -la /tmp/hbc_data_snapshots/
```

## Variance Probe Proof

Run variance probe to detect region-aware sources returning identical data:

```bash
# Run probe
python3 scripts/variance_probe.py

# View report
cat /tmp/HBC_VARIANCE_PROBE_REPORT.md

# Check alerts
grep "⚠️" /tmp/HBC_VARIANCE_PROBE_REPORT.md || echo "✓ No alerts"

# View results
cat /tmp/hbc_variance_probe_results.json | jq
```

## Dataset Expansion & Regionality Checks

When adding new data sources per `docs/ENTERPRISE_DATASET_EXPANSION_PLAN.md`:

1. **variance_probe**: Add each new REGIONAL source to `scripts/variance_probe.py` classification; run probe and ensure no alerts (REGIONAL sources must show variance).
2. **source_regionality_manifest**: Update `/tmp/source_regionality_manifest.json` (or proof-dir equivalent) with `source_id`, `class`, `geo_inputs_used`, `cache_key_fields`, `expected_variance`, `failure_mode`.
3. **Regression tests**: For each REGIONAL source, add a test that two distant regions (e.g. Illinois vs Arizona) produce different values for that source.
4. **Prometheus invariants**: No `region="None"`; multi-region series for `behavior_index` and key sub-indices; `data_source_status{source,region}` where applicable.

See Section 5 of the Enterprise Plan for the full safety net.

## Contract Tests

Run contract tests to verify correctness invariants:

```bash
# Run contract tests
pytest tests/test_analytics_contracts.py -v

# Run metrics integrity tests
pytest tests/test_metrics_integrity.py -v

# Expected: All tests pass
```

## Global vs Regional Indices

**Global indices** (expected identical across regions):
- `economic_stress` (FRED - US national data)
- `mobility_activity` (TSA - US national data)
- `digital_attention` (GDELT - global events)
- `public_health_stress` (OWID - country-level data)

**Regional indices** (expected to vary):
- `environmental_stress` (weather - region-specific)
- `behavior_index` (composite - varies due to regional components)

Verify regional indices differ:

```bash
python3 << 'PYEOF'
import requests

regions = ['us_mn', 'us_ca', 'us_mi']
for region in regions:
    query = f'parent_subindex_value{{region="{region}",parent="environmental_stress"}}'
    resp = requests.get("http://localhost:9090/api/v1/query", params={"query": query})
    data = resp.json()
    if data.get("data", {}).get("result"):
        val = float(data["data"]["result"][0]["value"][1])
        print(f"{region}: {val:.6f}")
PYEOF

# Expected: Different values for each region
```

## Troubleshooting

### Few regions in Grafana dropdown

**Cause**: Warm-up not complete or no forecasts generated yet.

**Solution**:
1. Wait 5-10 minutes for background metrics population
2. Generate a forecast manually via API or UI
3. Check warm-up metrics: `curl -s http://localhost:8100/metrics | grep hbc_warmup`

### All regions show identical values

**Cause**: Some indices are global by design (see Global vs Regional Indices above).

**Solution**: Check `environmental_stress` or `behavior_index` - these should differ. Global indices being identical is expected.

### Metrics not appearing in Prometheus

**Cause**: Prometheus not scraping backend or backend not emitting metrics.

**Solution**:
1. Check Prometheus targets: `curl -s http://localhost:9090/api/v1/targets | jq`
2. Check backend logs: `docker compose logs backend | tail -50`
3. Verify `/metrics` endpoint: `curl -s http://localhost:8100/metrics | head -20`

## Grafana Dashboard Verification

Verify that Grafana dashboards are provisioned and accessible:

```bash
# List all dashboards via Grafana API
curl -sS -u admin:admin "http://localhost:3001/api/search?type=dash-db" | jq -r '.[] | "\(.uid): \(.title)"'

# Expected dashboards include:
# - regional-variance-explorer
# - forecast-quality-drift
# - algorithm-model-comparison
# - source-health-freshness
# - regional-deep-dive
# - geo-map
# - public-overview
# - data-sources-health-enhanced

# Verify dashboard JSON files exist
ls -1 infra/grafana/dashboards/*.json | wc -l
# Expected: 20+ dashboard files

# Verify dashboard provisioning config
cat infra/grafana/provisioning/dashboards/dashboards.yml
# Expected: Path points to /var/lib/grafana/dashboards

# Verify PromQL queries return data for dashboard panels
curl -sS "http://localhost:9090/api/v1/query?query=behavior_index" | jq '.data.result | length'
# Expected: > 0 results

curl -sS "http://localhost:9090/api/v1/query?query=child_subindex_value{parent=\"economic_stress\", child=\"fuel_stress\"}" | jq '.data.result | length'
# Expected: > 0 results (if MVP1 implemented)

# Verify UI embeds dashboards
curl -sS http://localhost:3100/forecast | grep -o 'dashboardUid="[^"]*"' | sort -u
# Expected: Multiple dashboard UIDs found
```

**Dashboard Access**:
- Direct URLs: `http://localhost:3001/d/{dashboard-uid}`
- Embedded in UI: `/forecast` page shows dashboards as iframes
- Variables: Region variable populated from `label_values(behavior_index, region)`

**Verification Checklist**:
- [ ] All dashboard JSON files valid (no syntax errors)
- [ ] Dashboards appear in Grafana UI
- [ ] PromQL queries return data for at least 2 regions
- [ ] UI embeds render (check iframe src contains dashboard UIDs)
- [ ] Region variables populate correctly
- [ ] No blank dashboards (all panels have data or show "no data" message)

## Evidence Bundles

For reproducible proof, create an evidence bundle:

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /tmp/hbc_proof_${TIMESTAMP}

# Save all evidence
curl -s http://localhost:8100/api/forecasting/regions > /tmp/hbc_proof_${TIMESTAMP}/regions.json
curl -s http://localhost:8100/metrics > /tmp/hbc_proof_${TIMESTAMP}/metrics.txt
curl -s "http://localhost:9090/api/v1/query?query=behavior_index" > /tmp/hbc_proof_${TIMESTAMP}/promql_behavior_index.json
python3 scripts/run_data_quality_checkpoint.py
cp /tmp/HBC_DATA_QUALITY_REPORT.md /tmp/hbc_proof_${TIMESTAMP}/
python3 scripts/variance_probe.py
cp /tmp/HBC_VARIANCE_PROBE_REPORT.md /tmp/hbc_proof_${TIMESTAMP}/

echo "Evidence bundle: /tmp/hbc_proof_${TIMESTAMP}/"
```
