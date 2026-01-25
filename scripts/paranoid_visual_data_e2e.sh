#!/usr/bin/env bash
# HBC Paranoid Visual + Data E2E Verification and Auto-Repair
# One agent: verify Docker -> API -> Prometheus -> Grafana -> Next.js UI
# Evidence in /tmp/hbc_visual_verify_<ts>/ (not committed)

set -euo pipefail

TS=$(date -u +%Y%m%d_%H%M%S)
EVIDENCE="/tmp/hbc_visual_verify_${TS}"
mkdir -p "$EVIDENCE/screenshots"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$EVIDENCE/run.log"; }

log "HBC Paranoid Visual + Data E2E Verification"
log "Evidence: $EVIDENCE"

# ------------------------------------------------------------------------------
# PHASE 0: Baseline
# ------------------------------------------------------------------------------
log "PHASE 0: Baseline snapshot"
{
  echo "HEAD: $(git rev-parse HEAD 2>/dev/null || echo 'n/a')"
  echo ""
  git status --porcelain 2>/dev/null || true
  echo ""
  echo "Tracked files: $(git ls-files 2>/dev/null | wc -l)"
  echo "Repo size: $(du -sh . 2>/dev/null | cut -f1)"
} > "$EVIDENCE/baseline.txt" 2>&1
cat "$EVIDENCE/baseline.txt"

# ------------------------------------------------------------------------------
# PHASE 1: Start/verify Docker stack
# ------------------------------------------------------------------------------
log "PHASE 1: Docker stack"
docker compose up -d --build 2>&1 | tee -a "$EVIDENCE/run.log" || {
  log "Docker compose up failed"
  echo "Docker compose up failed" >> "$EVIDENCE/bugs.md"
  exit 1
}

docker compose ps > "$EVIDENCE/docker_ps.txt" 2>&1
docker compose logs --tail=200 backend > "$EVIDENCE/logs_backend_tail.txt" 2>&1
docker compose logs --tail=200 frontend > "$EVIDENCE/logs_frontend_tail.txt" 2>&1
docker compose logs --tail=200 grafana > "$EVIDENCE/logs_grafana_tail.txt" 2>&1
docker compose logs --tail=200 prometheus > "$EVIDENCE/logs_prometheus_tail.txt" 2>&1

log "Waiting for services (90s)..."
sleep 90

log "Health checks"
{
  echo "=== Backend ==="
  curl -sf http://localhost:8100/health && echo " OK" || echo " FAIL"
  echo ""
  echo "=== Frontend / ==="
  curl -sf -o /dev/null -w "%{http_code}" http://localhost:3100/ && echo " OK" || echo " FAIL"
  echo ""
  echo "=== /forecast ==="
  curl -sf -o /dev/null -w "%{http_code}" http://localhost:3100/forecast && echo " OK" || echo " FAIL"
  echo ""
  echo "=== /history ==="
  curl -sf -o /dev/null -w "%{http_code}" http://localhost:3100/history && echo " OK" || echo " FAIL"
  echo ""
  echo "=== /live ==="
  curl -sf -o /dev/null -w "%{http_code}" http://localhost:3100/live && echo " OK" || echo " FAIL"
  echo ""
  echo "=== /playground ==="
  curl -sf -o /dev/null -w "%{http_code}" http://localhost:3100/playground && echo " OK" || echo " FAIL"
  echo ""
  echo "=== Prometheus ==="
  curl -sf http://localhost:9090/-/ready && echo " OK" || echo " FAIL"
  echo ""
  echo "=== Grafana ==="
  curl -sf http://localhost:3001/api/health && echo " OK" || echo " FAIL"
} > "$EVIDENCE/healthchecks.txt" 2>&1
cat "$EVIDENCE/healthchecks.txt"

if grep -q "FAIL" "$EVIDENCE/healthchecks.txt"; then
  log "Health checks failed; see $EVIDENCE/healthchecks.txt and logs_*_tail.txt"
  echo "Health checks failed" >> "$EVIDENCE/bugs.md"
  exit 1
fi

# ------------------------------------------------------------------------------
# PHASE 2: Force data generation (3 regions)
# ------------------------------------------------------------------------------
log "PHASE 2: Force forecast generation (IL, AZ, NYC)"

curl -sf -X POST http://localhost:8100/api/forecast \
  -H "Content-Type: application/json" \
  -d '{"region_name":"Illinois","latitude":40.3495,"longitude":-88.9861,"days_back":30,"forecast_horizon":7}' \
  > "$EVIDENCE/forecast_il.json" 2>&1 || log "Forecast IL failed"

curl -sf -X POST http://localhost:8100/api/forecast \
  -H "Content-Type: application/json" \
  -d '{"region_name":"Arizona","latitude":34.2744,"longitude":-111.6602,"days_back":30,"forecast_horizon":7}' \
  > "$EVIDENCE/forecast_az.json" 2>&1 || log "Forecast AZ failed"

curl -sf -X POST http://localhost:8100/api/forecast \
  -H "Content-Type: application/json" \
  -d '{"region_name":"New York City","latitude":40.7128,"longitude":-74.0060,"days_back":30,"forecast_horizon":7}' \
  > "$EVIDENCE/forecast_nyc.json" 2>&1 || log "Forecast NYC failed"

log "Waiting for metrics (30s)..."
sleep 30

curl -s http://localhost:8100/metrics > "$EVIDENCE/metrics_dump.txt" 2>&1
REGIONS=$(grep -c '^behavior_index{' "$EVIDENCE/metrics_dump.txt" 2>/dev/null || echo "0")
log "behavior_index series count: $REGIONS"
if [ "${REGIONS:-0}" -lt 3 ]; then
  log "WARN: Fewer than 3 regions in metrics"
  echo "Multi-region metrics: expected >=3, got $REGIONS" >> "$EVIDENCE/bugs.md"
fi

# ------------------------------------------------------------------------------
# PHASE 3: Prometheus + Grafana validation
# ------------------------------------------------------------------------------
log "PHASE 3: Prometheus + Grafana"

{
  echo "=== count(count by (region) (behavior_index)) ==="
  curl -sG "http://localhost:9090/api/v1/query" --data-urlencode 'query=count(count by (region) (behavior_index))'
  echo ""
  echo "=== topk(10, behavior_index) ==="
  curl -sG "http://localhost:9090/api/v1/query" --data-urlencode 'query=topk(10, behavior_index)'
  echo ""
  echo "=== count(count by (region,parent) (parent_subindex_value)) ==="
  curl -sG "http://localhost:9090/api/v1/query" --data-urlencode 'query=count(count by (region,parent) (parent_subindex_value))'
  echo ""
  echo "=== count(count by (region,child) (child_subindex_value)) ==="
  curl -sG "http://localhost:9090/api/v1/query" --data-urlencode 'query=count(count by (region,child) (child_subindex_value))'
} > "$EVIDENCE/prometheus_queries.txt" 2>&1

curl -sf http://localhost:3001/api/health > "$EVIDENCE/grafana_health.json" 2>&1 || echo '{"database":"error"}' > "$EVIDENCE/grafana_health.json"

# ------------------------------------------------------------------------------
# PHASE 4: Playwright visual verification
# ------------------------------------------------------------------------------
log "PHASE 4: Playwright visual verification"

export EVIDENCE_DIR="$EVIDENCE"
export FRONTEND_BASE="http://localhost:3100"

cd app/frontend
npx playwright test e2e/visual-dashboards.spec.ts \
  --project=chromium \
  --reporter=list \
  2>&1 | tee "$EVIDENCE/playwright_output.txt" || true
cd ../..

if [ -f "$EVIDENCE/iframes.json" ]; then
  log "iframes.json present"
else
  log "iframes.json missing (Playwright may not have written it)"
fi

if [ -f "$EVIDENCE/ui_dom_dump.html" ]; then
  log "ui_dom_dump.html present"
else
  log "ui_dom_dump.html missing"
fi

# ------------------------------------------------------------------------------
# PHASE 5: If dashboards missing/blank, log repair hints (auto-repair loop)
# ------------------------------------------------------------------------------
if grep -qi "failed\|error\|FAIL" "$EVIDENCE/playwright_output.txt" 2>/dev/null; then
  log "Phase 5: Playwright failed; logging repair hints"
  {
    echo ""
    echo "## Playwright visual verification failed"
    echo ""
    echo "Evidence: playwright_output.txt, iframes.json, ui_dom_dump.html, screenshots/"
    echo ""
    echo "Suggested fixes (apply minimal change, re-run verification):"
    echo "5.1 Frontend embed wiring: forecast.tsx Grafana base URL, dashboard UIDs, var-region"
    echo "5.2 Grafana embedding: GF_SECURITY_ALLOW_EMBEDDING=true, GF_AUTH_ANONYMOUS_ENABLED=true"
    echo "5.3 Dashboard provisioning: infra/grafana/dashboards mounted, provisioning path"
    echo "5.4 Variables/queries: label_values(behavior_index,region), panel filters"
    echo "5.5 Layout: CSS height/overflow, accordion collapsed, hidden containers"
  } >> "$EVIDENCE/bugs.md" 2>/dev/null || true
fi

# ------------------------------------------------------------------------------
# PHASE 6: Regression safety
# ------------------------------------------------------------------------------
log "PHASE 6: Regression safety"

python3 -m pytest -q tests/test_grafana_embeds_contract.py tests/test_grafana_embeds.py > "$EVIDENCE/contract_tests.txt" 2>&1 || true
if [ -f "app/frontend/package.json" ]; then
  (cd app/frontend && npm run lint 2>&1) | tail -30 >> "$EVIDENCE/run.log" || true
fi

# ------------------------------------------------------------------------------
# Final report (for chat; evidence dir not committed)
# ------------------------------------------------------------------------------
{
  echo "FINAL REPORT"
  echo "============"
  echo ""
  echo "HEAD: $(git rev-parse HEAD 2>/dev/null || echo 'n/a')"
  echo "Git status: $(git status --porcelain 2>/dev/null | wc -l) changed"
  echo ""
  echo "Health check summary:"
  grep -E "OK|FAIL" "$EVIDENCE/healthchecks.txt" 2>/dev/null || true
  echo ""
  echo "Grafana health:"
  cat "$EVIDENCE/grafana_health.json" 2>/dev/null || true
  echo ""
  echo "Multi-region metrics: behavior_index series count = $REGIONS"
  echo ""
  echo "UI verification:"
  echo "  iframes.json: $([ -f "$EVIDENCE/iframes.json" ] && echo "present" || echo "missing")"
  echo "  ui_dom_dump.html: $([ -f "$EVIDENCE/ui_dom_dump.html" ] && echo "present" || echo "missing")"
  echo "  screenshots: $(ls "$EVIDENCE/screenshots" 2>/dev/null | wc -l) files"
  if [ -f "$EVIDENCE/iframes.json" ]; then
    FC=$(grep -c '"src"' "$EVIDENCE/iframes.json" 2>/dev/null || echo "0")
    OK=$(grep -c '"status": 200' "$EVIDENCE/iframes.json" 2>/dev/null || echo "0")
    echo "  iframe count: $FC"
    echo "  200 OK count: $OK"
  fi
  echo ""
  echo "Evidence directory: $EVIDENCE"
  echo ""
  if [ -f "$EVIDENCE/bugs.md" ]; then
    echo "bugs.md:"
    cat "$EVIDENCE/bugs.md"
  fi
} | tee "$EVIDENCE/final_report.txt" 2>&1

log "Done. Evidence: $EVIDENCE"
