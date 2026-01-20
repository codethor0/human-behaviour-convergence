#!/usr/bin/env bash
set -euo pipefail

cd /Users/thor/Projects/human-behaviour-convergence

echo "=== Validation Agent: ChangeSet 5 (CORS + Docker Dev Loop) + FRED Baseline UI ==="
echo

########################################
# Step 1: Bring stack up
########################################
echo "[1] Starting Docker dev stack via dev_watch_docker.sh..."
./ops/dev_watch_docker.sh &
DEV_WATCH_PID=$!

echo "Waiting 30s for Docker stack to be ready..."
sleep 30

BASE_BACKEND="${BASE_BACKEND:-http://localhost:8100}"
BASE_FRONTEND="${BASE_FRONTEND:-http://localhost:3100}"

########################################
# Step 2: API health checks
########################################
echo
echo "[2] API Health Checks"

echo "  - Backend /health:"
if curl -fsS "${BASE_BACKEND}/health" > /dev/null 2>&1; then
  echo "    ✅ Backend /health OK"
else
  echo "    ❌ Backend /health failed (may still be starting)"
  kill $DEV_WATCH_PID 2>/dev/null || true
  exit 1
fi

echo
echo "  - Regions endpoint (expect 62, has us_mn):"
REGIONS_OUTPUT=$(curl -fsS "${BASE_BACKEND}/api/forecasting/regions" 2>/dev/null | python3 - << 'PY' || echo "ERROR")
import sys, json
d = json.load(sys.stdin)
count = len(d)
has_mn = any(r.get("id") == "us_mn" for r in d)
print(f"    regions: {count}")
print(f"    has_mn: {has_mn}")
if count != 62:
    raise SystemExit(f"    ❌ Expected 62 regions, got {count}")
if not has_mn:
    raise SystemExit("    ❌ Minnesota (us_mn) not found")
print("    ✅ Regions contract PASS")
PY

if [[ "$REGIONS_OUTPUT" == "ERROR" ]]; then
  echo "    ❌ Regions check failed (backend may still be starting)"
  kill $DEV_WATCH_PID 2>/dev/null || true
  exit 1
else
  echo "$REGIONS_OUTPUT"
fi

echo
echo "  - Forecast POST (Minnesota, expect history 30-40, forecast=7):"
FORECAST_OUTPUT=$(curl -fsS -X POST "${BASE_BACKEND}/api/forecast" \
  -H "Content-Type: application/json" \
  -d '{
    "region_id": "us_mn",
    "region_name": "Minnesota (US)",
    "latitude": 46.7296,
    "longitude": -94.6859,
    "days_back": 30,
    "forecast_horizon": 7
  }' 2>/dev/null | python3 - << 'PY' || echo "ERROR")
import sys, json
data = json.load(sys.stdin)
history = data.get("history", [])
forecast = data.get("forecast", [])
keys = set(data.keys())
hist_len = len(history)
fc_len = len(forecast)
print(f"    history_len: {hist_len}")
print(f"    forecast_len: {fc_len}")
print(f"    keys: {sorted(keys)}")
required_keys = {"history", "forecast", "behavior_index", "risk_tier", "sources", "metadata"}
missing = required_keys - keys
if missing:
    raise SystemExit(f"    ❌ Missing keys: {sorted(missing)}")
if not (30 <= hist_len <= 40):
    raise SystemExit(f"    ❌ history_len {hist_len} not in range [30, 40]")
if fc_len != 7:
    raise SystemExit(f"    ❌ forecast_len {fc_len} not equal to 7")
print("    ✅ Forecast contract PASS")
PY

if [[ "$FORECAST_OUTPUT" == "ERROR" ]]; then
  echo "    ❌ Forecast check failed"
  kill $DEV_WATCH_PID 2>/dev/null || true
  exit 1
else
  echo "$FORECAST_OUTPUT"
fi

########################################
# Step 3: FRED backend entry
########################################
echo
echo "[3] FRED Backend Entry Check:"
FRED_OUTPUT=$(curl -fsS "${BASE_BACKEND}/api/forecasting/data-sources" 2>/dev/null | python3 - << 'PY' || echo "ERROR")
import sys, json
data = json.load(sys.stdin)
fred = [s for s in data if s.get("name") == "fred_economic" or s.get("id") == "fred_economic" or "fred" in s.get("name", "").lower()]
if not fred:
    raise SystemExit("    ❌ FRED entry not found")
entry = fred[0]
print(f"    name: {entry.get('name')}")
print(f"    optional: {entry.get('optional')}")
print(f"    env_var: {entry.get('env_var')}")
print(f"    status: {entry.get('status')}")
print(f"    message: {entry.get('message', 'N/A')[:80]}")
if entry.get("optional") is not True:
    raise SystemExit("    ❌ FRED optional should be True")
if entry.get("env_var") != "FRED_API_KEY":
    raise SystemExit("    ❌ FRED env_var should be FRED_API_KEY")
print("    ✅ FRED backend entry PASS")
PY

if [[ "$FRED_OUTPUT" == "ERROR" ]]; then
  echo "    ❌ FRED backend check failed"
  kill $DEV_WATCH_PID 2>/dev/null || true
  exit 1
else
  echo "$FRED_OUTPUT"
fi

########################################
# Step 4: UI/HTTP checks
########################################
echo
echo "[4] UI/HTTP Checks:"

echo "  - Forecast page HTML:"
if curl -fsS "${BASE_FRONTEND}/forecast" > /tmp/forecast_page.html 2>/dev/null; then
  if grep -q "<!DOCTYPE html\|<html" /tmp/forecast_page.html; then
    echo "    ✅ /forecast returns HTML"
  else
    echo "    ⚠️  /forecast response doesn't look like HTML"
  fi
else
  echo "    ❌ /forecast not reachable"
  kill $DEV_WATCH_PID 2>/dev/null || true
  exit 1
fi

echo
echo "  - Playground page:"
if curl -fsS "${BASE_FRONTEND}/playground" > /dev/null 2>&1; then
  echo "    ✅ /playground reachable"
else
  echo "    ❌ /playground not reachable"
fi

echo "  - Live page:"
if curl -fsS "${BASE_FRONTEND}/live" > /dev/null 2>&1; then
  echo "    ✅ /live reachable"
else
  echo "    ❌ /live not reachable"
fi

echo
echo "  - FRED UI text in /forecast HTML:"
NEW_STATUS_COUNT=$(rg -c "baseline \(live FRED feed not configured; optional\)" /tmp/forecast_page.html 2>/dev/null || echo "0")
NEW_HINT_COUNT=$(rg -c "Using built-in baseline economic indicators; set FRED_API_KEY in \.env to enable live FRED data \(optional\)\." /tmp/forecast_page.html 2>/dev/null || echo "0")
OLD_MSG_COUNT=$(rg -c "FRED API not configured; using baseline economic indicators only" /tmp/forecast_page.html 2>/dev/null || echo "0")

echo "    New status text matches: ${NEW_STATUS_COUNT}"
echo "    New hint text matches: ${NEW_HINT_COUNT}"
echo "    Old message text matches: ${OLD_MSG_COUNT}"

if [[ "$NEW_STATUS_COUNT" -gt 0 ]] && [[ "$NEW_HINT_COUNT" -gt 0 ]] && [[ "$OLD_MSG_COUNT" -eq 0 ]]; then
  echo "    ✅ FRED UI text verification PASS"
else
  echo "    ⚠️  FRED UI text verification:"
  echo "       - New strings present: $([ "$NEW_STATUS_COUNT" -gt 0 ] && echo 'YES' || echo 'NO')"
  echo "       - Old strings absent: $([ "$OLD_MSG_COUNT" -eq 0 ] && echo 'YES' || echo 'NO')"
fi

########################################
# Step 5: CORS sanity
########################################
echo
echo "[5] CORS Preflight Check:"
CORS_HEADERS=$(curl -is -X OPTIONS "${BASE_BACKEND}/api/forecast" \
  -H "Origin: http://localhost:3100" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" 2>&1 | grep -i "access-control-" || echo "")

if echo "$CORS_HEADERS" | grep -qi "access-control-allow-origin"; then
  echo "    ✅ Access-Control-Allow-Origin present"
else
  echo "    ❌ Access-Control-Allow-Origin missing"
fi

if echo "$CORS_HEADERS" | grep -qi "access-control-allow-methods"; then
  echo "    ✅ Access-Control-Allow-Methods present"
else
  echo "    ❌ Access-Control-Allow-Methods missing"
fi

if echo "$CORS_HEADERS" | grep -qi "access-control-allow-headers"; then
  echo "    ✅ Access-Control-Allow-Headers present"
else
  echo "    ❌ Access-Control-Allow-Headers missing"
fi

########################################
# Step 6: Logs check
########################################
echo
echo "[6] Backend/Frontend Logs (last 50 lines):"
docker compose logs backend frontend --tail=50 2>&1 | tail -20 || echo "    ⚠️  Could not read logs (containers may not be fully up)"

echo
echo "=== Validation Summary ==="
echo
echo "Runtime checks completed. Review output above for any ❌ failures."
echo
echo "Next: Manual browser checks"
echo "  1. Open http://localhost:3100/forecast"
echo "     - Verify FRED card shows new baseline messaging"
echo "     - Generate forecast for Minnesota/NYC"
echo "     - Confirm no 'Failed to fetch' errors"
echo "  2. Open http://localhost:3100/playground and /live"
echo "     - Confirm regions load without errors"
echo
echo "Docker dev loop still running (PID: $DEV_WATCH_PID)"
echo "To stop: kill $DEV_WATCH_PID"
