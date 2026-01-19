#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "=== [GATE A] Core App Invariants Verification ==="
echo

FAIL=0
BASE_BACKEND="${BASE_BACKEND:-http://localhost:8100}"
BASE_FRONTEND="${BASE_FRONTEND:-http://localhost:3100}"

############################################
# 1. Git status
############################################
echo "[1] Git status"
git status -sb || { echo "[FAIL] git status"; FAIL=1; }
echo

############################################
# 2. CORS configuration check
############################################
echo "[2] CORS middleware check"
if grep -q "CORSMiddleware" app/backend/app/main.py && \
   grep -q 'allow_origins=\["\*"\]' app/backend/app/main.py; then
  echo "[OK] CORSMiddleware found with allow_origins=[\"*\"]"
else
  echo "[FAIL] CORSMiddleware not configured correctly"
  FAIL=1
fi
echo

############################################
# 3. Backend health + endpoints
############################################
echo "[3] Backend health"
if curl -fsS "${BASE_BACKEND}/health" > /dev/null 2>&1; then
  echo "[OK] ${BASE_BACKEND}/health responds"
else
  echo "[FAIL] Backend health check failed"
  FAIL=1
fi

echo
echo "[4] Backend regions endpoint"
if curl -fsS "${BASE_BACKEND}/api/forecasting/regions" > /tmp/gate_a_regions.json 2>&1; then
  REGION_COUNT=$(python3 -c "import json; print(len(json.load(open('/tmp/gate_a_regions.json'))))")
  if [[ "$REGION_COUNT" == "62" ]]; then
    echo "[OK] /api/forecasting/regions returns 62 regions"
  else
    echo "[FAIL] Expected 62 regions, got ${REGION_COUNT}"
    FAIL=1
  fi
else
  echo "[FAIL] Could not reach /api/forecasting/regions"
  FAIL=1
fi

echo
echo "[5] Backend forecast contract"
MN_PAYLOAD='{
  "region_id": "us_mn",
  "region_name": "Minnesota",
  "days_back": 30,
  "forecast_horizon": 7
}'

if curl -fsS -X POST "${BASE_BACKEND}/api/forecast" \
  -H "Content-Type: application/json" \
  -d "$MN_PAYLOAD" > /tmp/gate_a_forecast.json 2>&1; then

  python3 - << 'PY'
import json, sys
data = json.load(open("/tmp/gate_a_forecast.json"))
history = data.get("history", [])
forecast = data.get("forecast", [])

if not (30 <= len(history) <= 40):
    print(f"[FAIL] history length {len(history)} not in [30, 40]")
    sys.exit(1)
if len(forecast) != 7:
    print(f"[FAIL] forecast length {len(forecast)} != 7")
    sys.exit(1)

required_keys = {"history", "forecast", "risk_tier", "sources", "metadata"}
missing = [k for k in required_keys if k not in data]
if missing:
    print(f"[FAIL] Missing keys: {missing}")
    sys.exit(1)

print(f"[OK] Forecast contract valid (history={len(history)}, forecast={len(forecast)})")
PY
  if [ $? -ne 0 ]; then
    FAIL=1
  fi
else
  echo "[FAIL] POST /api/forecast failed"
  FAIL=1
fi

############################################
# 6. Frontend pages + Grafana embedding
############################################
echo
echo "[6] Frontend pages + Grafana iframe embedding"

for page in ops forecast playground live; do
  echo "  [6.${page}] GET ${BASE_FRONTEND}/${page}"

  if curl -fsS "${BASE_FRONTEND}/${page}" > /tmp/gate_a_${page}.html 2>&1; then
    echo "    [OK] /${page} HTTP 200"

    # Check for Grafana iframe embedding (skip for ops page which is just links)
    if [ "$page" != "ops" ]; then
      python3 - "${page}" << 'PY'
import sys
page = sys.argv[1]
html = open(f"/tmp/gate_a_{page}.html").read()

required_uids = ["behavior-index-global", "subindex-deep-dive"]
missing = [uid for uid in required_uids if uid not in html]

if missing:
    print(f"    [FAIL] /{page}: Missing Grafana dashboard UIDs: {missing}")
    sys.exit(1)

# Check for iframe elements
if "<iframe" not in html:
    print(f"    [FAIL] /{page}: No iframe elements found")
    sys.exit(1)

print(f"    [OK] /{page}: Grafana dashboards embedded (UIDs: {required_uids})")
PY
      if [ $? -ne 0 ]; then
        FAIL=1
      fi
    fi
  else
    echo "    [FAIL] /${page} did not respond"
    FAIL=1
  fi
done

############################################
# 7. CORS preflight check
############################################
echo
echo "[7] CORS preflight check"
CORS_RESPONSE=$(curl -is -X OPTIONS "${BASE_BACKEND}/api/forecast" \
  -H "Origin: http://localhost:3100" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" 2>&1)

if echo "$CORS_RESPONSE" | grep -iq "access-control-allow-origin"; then
  echo "[OK] CORS preflight returns access-control-allow-origin"
else
  echo "[FAIL] CORS preflight missing required headers"
  FAIL=1
fi

############################################
# 8. Final summary
############################################
echo
if [ "$FAIL" -eq 0 ]; then
  echo "=== [GATE A RESULT] GREEN: All core app invariants verified ==="
else
  echo "=== [GATE A RESULT] RED: One or more checks failed; see messages above ==="
  echo
  echo "📖 Troubleshooting Guide:"
  echo "   See docs/RUNBOOK_DASHBOARDS.md Section 2 (pipeline) and Section 7 (core app)"
  echo "   Common issues:"
  echo "   - Backend down → Section 2"
  echo "   - CORS issues → Section 7"
  echo "   - Forecast contract broken → Section 7"
  echo "   - Frontend pages not loading → Section 7"
fi

exit "$FAIL"
