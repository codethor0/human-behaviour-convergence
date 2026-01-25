#!/usr/bin/env bash
# Agent 3: Data Integrity + Regional Variance + Source Regionality
# Proves data pipeline produces meaningful regional variance

set -euo pipefail

TS=$(date -u +%Y%m%d_%H%M%S)
EVIDENCE_DIR="/tmp/hbc_agent3_variance_${TS}"
mkdir -p "$EVIDENCE_DIR/forecasts" "$EVIDENCE_DIR/metrics" "$EVIDENCE_DIR/logs"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*" | tee -a "$EVIDENCE_DIR/logs/execution.log"; }

log "Agent 3: Data Integrity + Regional Variance + Source Regionality"
log "Evidence directory: $EVIDENCE_DIR"

# PHASE 0: Bring up stack and warm-up
log "PHASE 0: Starting stack..."
docker compose up -d --build 2>&1 | tee -a "$EVIDENCE_DIR/logs/docker_up.txt" || {
  log "ERROR: Docker compose failed"
  exit 1
}

log "Waiting for services (90s)..."
sleep 90

# PHASE 1: Regional variance harness
log "PHASE 1: Running regional variance harness..."

# Generate forecasts for 10+ regions
REGIONS=(
  '{"region_name":"Illinois","latitude":40.3495,"longitude":-88.9861,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"Arizona","latitude":34.2744,"longitude":-111.6602,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"Washington","latitude":47.4009,"longitude":-121.4905,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"Florida","latitude":27.7663,"longitude":-81.6868,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"New York","latitude":42.1657,"longitude":-74.9481,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"Texas","latitude":31.0545,"longitude":-97.5635,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"California","latitude":36.1162,"longitude":-119.6816,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"Minnesota","latitude":46.7296,"longitude":-94.6859,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"New York City","latitude":40.7128,"longitude":-74.0060,"days_back":30,"forecast_horizon":7}'
  '{"region_name":"London","latitude":51.5074,"longitude":-0.1278,"days_back":30,"forecast_horizon":7}'
)

REGION_NAMES=("Illinois" "Arizona" "Washington" "Florida" "New York" "Texas" "California" "Minnesota" "NYC" "London")

python3 <<PYTHON > "$EVIDENCE_DIR/variance_matrix.csv" 2>&1
import json
import hashlib
import requests
import csv

forecasts = {}
for i, region_name in enumerate(${REGION_NAMES[@]}):
    try:
        response = requests.post(
            "http://localhost:8100/api/forecast",
            json=json.loads('${REGIONS[$i]}'),
            timeout=60
        )
        data = response.json()
        
        history = data.get("history", [])
        forecast = data.get("forecast", [])
        sub_indices = data.get("history", [{}])[-1] if history else {}
        
        # Compute hashes
        history_hash = hashlib.sha256(json.dumps(history, sort_keys=True).encode()).hexdigest()[:16]
        forecast_hash = hashlib.sha256(json.dumps(forecast, sort_keys=True).encode()).hexdigest()[:16]
        
        # Extract sub-indices
        economic = sub_indices.get("economic_stress", 0)
        environmental = sub_indices.get("environmental_stress", 0)
        behavior_index = sub_indices.get("behavior_index", 0)
        
        forecasts[region_name] = {
            "history_hash": history_hash,
            "forecast_hash": forecast_hash,
            "behavior_index": behavior_index,
            "economic_stress": economic,
            "environmental_stress": environmental,
        }
        
        # Save full response
        with open(f"$EVIDENCE_DIR/forecasts/{region_name.lower().replace(' ', '_')}.json", "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error for {region_name}: {e}")

# Write CSV
with open("$EVIDENCE_DIR/variance_matrix.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(["region", "history_hash", "forecast_hash", "behavior_index", "economic_stress", "environmental_stress"])
    for region, data in forecasts.items():
        writer.writerow([
            region,
            data["history_hash"],
            data["forecast_hash"],
            data["behavior_index"],
            data["economic_stress"],
            data["environmental_stress"],
        ])

# Check for state collapse
unique_history_hashes = len(set(f["history_hash"] for f in forecasts.values()))
unique_forecast_hashes = len(set(f["forecast_hash"] for f in forecasts.values()))

print(f"Regions processed: {len(forecasts)}")
print(f"Unique history hashes: {unique_history_hashes}/{len(forecasts)}")
print(f"Unique forecast hashes: {unique_forecast_hashes}/{len(forecasts)}")

if unique_history_hashes < len(forecasts) * 0.2:
    print("❌ P0: State collapse detected - >=80% identical history hashes")
else:
    print("✅ Variance OK - history differs across regions")

# Compare IL vs AZ
il = forecasts.get("Illinois", {})
az = forecasts.get("Arizona", {})
if il and az:
    bi_diff = abs(il["behavior_index"] - az["behavior_index"])
    econ_diff = abs(il["economic_stress"] - az["economic_stress"])
    env_diff = abs(il["environmental_stress"] - az["environmental_stress"])
    
    print(f"\nIllinois vs Arizona:")
    print(f"  Behavior Index diff: {bi_diff:.6f}")
    print(f"  Economic Stress diff: {econ_diff:.6f}")
    print(f"  Environmental Stress diff: {env_diff:.6f}")
    
    if bi_diff >= 0.005 or econ_diff >= 0.005 or env_diff >= 0.005:
        print("✅ Regional variance detected (>= 0.005)")
    else:
        print("⚠️  Regional variance low (< 0.005)")
PYTHON

cat "$EVIDENCE_DIR/variance_matrix.csv"

# PHASE 2: fuel_stress proof
log "PHASE 2: Verifying fuel_stress is real..."

curl -fsS http://localhost:8100/metrics > "$EVIDENCE_DIR/metrics/raw_metrics.txt" 2>&1

python3 <<PYTHON > "$EVIDENCE_DIR/fuel_stress_proof.txt" 2>&1
import re

with open("$EVIDENCE_DIR/metrics/raw_metrics.txt") as f:
    metrics = f.read()

# Check for fuel_stress
fuel_lines = [l for l in metrics.split('\n') if 'fuel_stress' in l.lower()]

print(f"fuel_stress metrics found: {len(fuel_lines)}")
if fuel_lines:
    print("\nSample fuel_stress metrics:")
    for line in fuel_lines[:10]:
        print(f"  {line[:100]}")
    
    # Extract regions
    regions = set()
    for line in fuel_lines:
        match = re.search(r'region="([^"]+)"', line)
        if match:
            regions.add(match.group(1))
    
    print(f"\nRegions with fuel_stress: {sorted(regions)}")
    
    if len(regions) >= 2:
        print("✅ fuel_stress exists for multiple regions")
    else:
        print("⚠️  fuel_stress found for < 2 regions")
else:
    print("❌ fuel_stress metrics not found")
PYTHON

cat "$EVIDENCE_DIR/fuel_stress_proof.txt"

# PHASE 3: Cache key audit
log "PHASE 3: Cache key audit..."

if [ -f "scripts/cache_key_audit.py" ]; then
  python3 scripts/cache_key_audit.py > "$EVIDENCE_DIR/cache_key_audit.txt" 2>&1 || true
  cat "$EVIDENCE_DIR/cache_key_audit.txt"
else
  log "Cache key audit script not found, creating static check..."
  
  python3 <<PYTHON > "$EVIDENCE_DIR/cache_key_audit.txt" 2>&1
import re
import os

# Check eia_fuel_prices.py for cache key
fuel_file = "app/services/ingestion/eia_fuel_prices.py"
if os.path.exists(fuel_file):
    with open(fuel_file) as f:
        content = f.read()
    
    # Check if cache key includes state_code
    if "state_code" in content and "cache_key" in content:
        if re.search(r'cache_key.*state_code|state_code.*cache_key', content):
            print("✅ eia_fuel_prices cache key includes state_code")
        else:
            print("❌ eia_fuel_prices cache key may not include state_code")
    else:
        print("⚠️  Could not verify cache key structure")
else:
    print("⚠️  eia_fuel_prices.py not found")
PYTHON
  cat "$EVIDENCE_DIR/cache_key_audit.txt"
fi

# PHASE 4: Variance probe
log "PHASE 4: Running variance probe..."

if [ -f "scripts/variance_probe.py" ]; then
  python3 scripts/variance_probe.py > "$EVIDENCE_DIR/variance_probe_report.txt" 2>&1 || true
  cat "$EVIDENCE_DIR/variance_probe_report.txt"
else
  log "Variance probe script not found"
fi

# Final report
cat > "$EVIDENCE_DIR/FINAL_REPORT.md" <<EOF
# Agent 3: Data Integrity + Regional Variance - Final Report

**Generated**: $(ts)
**Evidence Directory**: $EVIDENCE_DIR

## Verification Results

### Phase 1: Regional Variance Harness
- Variance matrix: \`variance_matrix.csv\`
- Forecasts: \`forecasts/*.json\`

### Phase 2: fuel_stress Proof
- Metrics check: \`fuel_stress_proof.txt\`
- Raw metrics: \`metrics/raw_metrics.txt\`

### Phase 3: Cache Key Audit
- Audit results: \`cache_key_audit.txt\`

### Phase 4: Variance Probe
- Probe report: \`variance_probe_report.txt\`

## Findings

See individual evidence files for detailed results.

## Next Steps

1. Review variance matrix
2. Verify fuel_stress presence
3. Fix any cache key issues
4. Address any P0 discrepancies
EOF

cat "$EVIDENCE_DIR/FINAL_REPORT.md"
log "Agent 3 complete. Evidence saved to: $EVIDENCE_DIR"
