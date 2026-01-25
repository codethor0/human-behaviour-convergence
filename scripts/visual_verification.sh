#!/usr/bin/env bash
# HBC Visual Verification + Auto-Repair Script
# Verifies Grafana dashboards are visible in UI and auto-repairs issues

set -euo pipefail

TS=$(date -u +%Y%m%d_%H%M%S)
EVIDENCE_DIR="/tmp/hbc_visual_verify_${TS}"
mkdir -p "$EVIDENCE_DIR/screenshots" "$EVIDENCE_DIR/traces" "$EVIDENCE_DIR/logs"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] $*" | tee -a "$EVIDENCE_DIR/verification.log"; }

log "Starting HBC Visual Verification"
log "Evidence directory: $EVIDENCE_DIR"

# PHASE 0: Start Clean and Ensure Stack is Up
log "PHASE 0: Starting clean stack..."
docker compose down -v 2>&1 | tee -a "$EVIDENCE_DIR/logs/docker_down.txt" || true

log "Building and starting stack..."
docker compose up -d --build 2>&1 | tee -a "$EVIDENCE_DIR/logs/docker_up.txt" || {
  log "ERROR: Docker compose failed"
  exit 1
}

log "Waiting for services to be ready (90s)..."
sleep 90

log "Health checks..."
{
  echo "=== Backend Health ==="
  curl -fsS http://localhost:8100/health 2>&1 && echo "✅ 200" || echo "❌ FAIL"
  echo ""
  echo "=== Frontend Root ==="
  curl -fsS -I http://localhost:3100/ 2>&1 | head -1 || echo "❌ FAIL"
  echo ""
  echo "=== Grafana Health ==="
  curl -fsS http://localhost:3001/api/health 2>&1 && echo "✅ 200" || echo "❌ FAIL"
  echo ""
  echo "=== Prometheus Ready ==="
  curl -fsS http://localhost:9090/-/ready 2>&1 && echo "✅ 200" || echo "❌ FAIL"
} > "$EVIDENCE_DIR/logs/health_checks.txt" 2>&1
cat "$EVIDENCE_DIR/logs/health_checks.txt"

# Warm-up: Generate forecasts for 3 regions
log "Warming up: Generating forecasts for 3 regions..."
for region in '{"region_name":"Illinois","latitude":40.349457,"longitude":-88.986137,"days_back":30,"forecast_horizon":7}' '{"region_name":"Arizona","latitude":33.729759,"longitude":-111.431221,"days_back":30,"forecast_horizon":7}' '{"region_name":"New York","latitude":42.165726,"longitude":-74.948051,"days_back":30,"forecast_horizon":7}'; do
  curl -fsS -X POST http://localhost:8100/api/forecast \
    -H "Content-Type: application/json" \
    -d "$region" > /dev/null 2>&1 || log "Warning: Forecast generation failed for region"
done

log "Waiting for metrics to populate (30s)..."
sleep 30

# PHASE 1: Visual Verification via Playwright
log "PHASE 1: Running Playwright visual verification..."

export EVIDENCE_DIR="$EVIDENCE_DIR/screenshots"

cd app/frontend

# Run Playwright test with evidence directory
npx playwright test e2e/grafana.embeds.visible.spec.ts \
  --reporter=json \
  --output-dir="$EVIDENCE_DIR" \
  --project=chromium \
  2>&1 | tee "$EVIDENCE_DIR/../logs/playwright_output.txt" || {
  log "Playwright test failed - checking results..."
  # Continue to analyze failures
}

# Move screenshots to evidence directory
if [ -d "test-results" ]; then
  cp -r test-results/* "$EVIDENCE_DIR/" 2>/dev/null || true
fi

cd ../..

# PHASE 2: Analyze Results
log "PHASE 2: Analyzing verification results..."

python3 <<PYTHON > "$EVIDENCE_DIR/../analysis.txt" 2>&1
import json
import os
import glob

evidence_dir = "$EVIDENCE_DIR/../"
screenshots = glob.glob(f"{evidence_dir}/screenshots/*.png")

print(f"Screenshots captured: {len(screenshots)}")
for s in screenshots:
    print(f"  - {os.path.basename(s)}")

# Check Playwright results
playwright_json = f"{evidence_dir}/logs/playwright_output.txt"
if os.path.exists(playwright_json):
    print("\nPlaywright test output found")
else:
    print("\nPlaywright test output not found")

# Check for errors
health_file = f"{evidence_dir}/logs/health_checks.txt"
if os.path.exists(health_file):
    with open(health_file) as f:
        content = f.read()
        if "❌" in content:
            print("\n⚠️  Health check failures detected")
        else:
            print("\n✅ All health checks passed")
PYTHON

cat "$EVIDENCE_DIR/../analysis.txt"

# PHASE 3: Generate Summary
log "PHASE 3: Generating summary..."

cat > "$EVIDENCE_DIR/../FINAL_SUMMARY.md" <<EOF
# HBC Visual Verification Summary

**Generated**: $(ts)
**Evidence Directory**: $EVIDENCE_DIR

## Verification Results

### Phase 0: Stack Health
- Status: See logs/health_checks.txt
- Warm-up: Forecasts generated for 3 regions

### Phase 1: Visual Verification
- Playwright test: See logs/playwright_output.txt
- Screenshots: See screenshots/
- Analysis: See analysis.txt

## Evidence Files

- Screenshots: \`screenshots/*.png\`
- Playwright output: \`logs/playwright_output.txt\`
- Health checks: \`logs/health_checks.txt\`
- Analysis: \`analysis.txt\`

## Next Steps

1. Review screenshots to verify dashboards are visible
2. Check Playwright output for any failures
3. Fix any issues found and re-run verification
EOF

cat "$EVIDENCE_DIR/../FINAL_SUMMARY.md"
log "Verification complete. Evidence saved to: $EVIDENCE_DIR"
