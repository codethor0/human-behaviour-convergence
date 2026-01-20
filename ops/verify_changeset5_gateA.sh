#!/usr/bin/env bash
set -euo pipefail

echo "=== GATE A: ChangeSet 5 – CORS + Docker Dev Loop Verification ==="

########################################
# 0) Baseline git state
########################################
echo
echo "[0] Git baseline..."
git status -sb
git status

########################################
# 1) Backend CORS sanity (static)
########################################
echo
echo "[1] Backend CORS sanity (static check)..."
if ! grep -q "CORSMiddleware" app/backend/app/main.py; then
  echo "❌ CORSMiddleware not found in app/backend/app/main.py"
  exit 1
fi

echo "Current CORS block (first occurrence):"
python3 - << 'PY'
from pathlib import Path
import re

path = Path("app/backend/app/main.py")
text = path.read_text()

pattern = r"app\.add_middleware\(\s*CORSMiddleware,(?:.|\n)*?\)"
m = re.search(pattern, text)
if not m:
    print("❌ No CORSMiddleware block found")
else:
    print(m.group(0))
PY

echo
echo "Manually confirm it matches this shape for dev:"
echo "  allow_origins=[\"*\"]"
echo "  allow_credentials=False"
echo "  allow_methods=[\"*\"]"
echo "  allow_headers=[\"*\"]"

########################################
# 2) Backend compile + core tests
########################################
echo
echo "[2] Backend compile + core tests..."
python3 -m compileall app -q
echo "✅ python3 -m compileall app -q"

# If pytest isn't installed, this will fail for env reasons (not code).
if command -v pytest >/dev/null 2>&1; then
  python3 -m pytest \
    tests/test_state_lifetime.py \
    tests/test_regions_api.py \
    -q --tb=short
  echo "✅ Core backend tests (state_lifetime + regions) passed"
else
  echo "⚠️ pytest not installed; skipping core tests (env issue, not code)"
fi

########################################
# 3) Ensure dev_watch_docker.sh exists & is executable
########################################
echo
echo "[3] Checking ops/dev_watch_docker.sh..."
if [[ ! -f "ops/dev_watch_docker.sh" ]]; then
  echo "❌ ops/dev_watch_docker.sh is missing"
  exit 1
fi

if [[ ! -x "ops/dev_watch_docker.sh" ]]; then
  echo "❌ ops/dev_watch_docker.sh is not executable; fixing..."
  chmod +x ops/dev_watch_docker.sh
fi

echo "✅ ops/dev_watch_docker.sh exists and is executable"

########################################
# 4) Run Docker dev loop (build + up + CORS preflight + logs)
########################################
echo
echo "[4] Running ops/dev_watch_docker.sh..."
./ops/dev_watch_docker.sh &
WATCH_PID=$!

# Give it time to build/up and run its checks
sleep 20

echo
echo "[4a] Quick explicit CORS preflight check from here..."
curl -is -X OPTIONS "http://localhost:8100/api/forecast" \
  -H "Origin: http://localhost:3100" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  | sed -n '1,20p' || true

echo
echo "Look for these headers in the output above:"
echo "  Access-Control-Allow-Origin: *            (or http://localhost:3100)"
echo "  Access-Control-Allow-Methods: ... POST ..."
echo "  Access-Control-Allow-Headers: ... content-type ..."

########################################
# 5) API contract checks (regions + forecast)
########################################
echo
echo "[5] API contract checks..."

echo "5a) Backend health..."
curl -fsS http://localhost:8100/health
echo "✅ /health OK"

echo
echo "5b) Regions count (expect 62)..."
COUNT=$(curl -fsS http://localhost:8100/api/forecasting/regions | python3 - << 'PY'
import sys, json
data = json.load(sys.stdin)
print(len(data))
PY
)
echo "Regions count: ${COUNT}"
if [[ "${COUNT}" != "62" ]]; then
  echo "❌ Expected 62 regions, got ${COUNT}"
  exit 1
fi
echo "✅ Regions endpoint returns 62"

echo
echo "5c) Sample forecast (Minnesota)..."
curl -fsS -X POST http://localhost:8100/api/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "region_id": "us_mn",
    "region_name": "Minnesota (US)",
    "latitude": 46.7296,
    "longitude": -94.6859,
    "days_back": 30,
    "forecast_horizon": 7
  }' | python3 - << 'PY'
import sys, json
data = json.load(sys.stdin)
hist = data.get("history", [])
fcst = data.get("forecast", [])
print("history_len", len(hist))
print("forecast_len", len(fcst))
print("top_keys", sorted(list(data.keys())))
PY

########################################
# 6) Git hygiene (no DB/build artifacts, no prompt files)
########################################
echo
echo "[6] Git hygiene..."

echo "Tracked DB/sqlite artifacts (should be empty):"
git status --short | grep -E '\.(db|sqlite|sqlite3)$' || echo "  (none)"

echo
echo "Tracked prompt-like files (should be empty):"
git status --short | grep -Ei '(prompt|MASTER_PROMPT|agent_log)' || echo "  (none)"

echo
echo "Working tree status:"
git status --short

echo
echo "=== GATE A CHECK COMPLETE ==="
echo "Interpretation:"
echo " - If regions=62, forecast history≈36 & forecast=7, and CORS preflight shows expected headers, ChangeSet 5 backend+CORS is GREEN."
echo " - If any of those fail, capture the failing output and we'll target that specific issue."
echo
echo "Docker dev loop is running (PID: $WATCH_PID)"
echo "To stop log tailing: kill $WATCH_PID"
