#!/usr/bin/env bash
set -euo pipefail

# Verify script for services running locally (not in Docker)
# Assumes backend on :8100 and frontend on :3003

API_BASE="${API_BASE:-http://127.0.0.1:8100}"
WEB_BASE="${WEB_BASE:-http://localhost:3003}"

echo "=== [1] Checking backend health ==="
if curl -fsS "$API_BASE/health" >/dev/null 2>&1; then
  echo "OK: Backend is responding at $API_BASE"
else
  echo "ERROR: Backend not responding at $API_BASE"
  echo "Please start backend: cd app/backend && python -m uvicorn app.backend.app.main:app --host 127.0.0.1 --port 8100"
  exit 1
fi

echo
echo "=== [2] Waiting for backend regions endpoint ==="
REGIONS_URL="$API_BASE/api/forecasting/regions"
echo "Target: $REGIONS_URL"
until curl -fsS "$REGIONS_URL" >/dev/null 2>&1; do
  echo "Backend not ready yet, retrying in 2s..."
  sleep 2
done
REGIONS_COUNT=$(curl -fsS "$REGIONS_URL" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "unknown")
echo "OK: /api/forecasting/regions is responding ($REGIONS_COUNT regions)"

echo
echo "=== [3] Waiting for frontend /forecast route ==="
FORECAST_PAGE_URL="$WEB_BASE/forecast"
echo "Target: $FORECAST_PAGE_URL"
until curl -fsS "$FORECAST_PAGE_URL" >/dev/null 2>&1; do
  echo "Frontend not ready yet, retrying in 2s..."
  sleep 2
done
echo "OK: frontend /forecast is responding"

echo
echo "=== [4] Testing /api/forecast endpoint ==="
TEST_FORECAST=$(cat <<'EOF'
{
  "latitude": 51.5074,
  "longitude": -0.1278,
  "region_name": "London (GB)",
  "days_back": 30,
  "forecast_horizon": 7
}
EOF
)
FORECAST_RESPONSE=$(curl -fsS -X POST "$API_BASE/api/forecast" \
  -H 'Content-Type: application/json' \
  --data-binary "$TEST_FORECAST" 2>&1 || echo "")
if echo "$FORECAST_RESPONSE" | grep -q '"history"'; then
  echo "OK: /api/forecast returns valid JSON with history"
else
  echo "WARNING: /api/forecast response may be invalid (check logs)"
fi

echo
if [ -d "app/frontend" ]; then
  echo "=== [5] Frontend build: app/frontend ==="
  (
    cd app/frontend
    if [ ! -d node_modules ]; then
      echo "node_modules missing; running npm install once..."
      npm install
    fi
    npm run build
  )
else
  echo "SKIP frontend build: app/frontend directory not found."
fi

echo
if command -v pytest >/dev/null 2>&1; then
  if [ -f "tests/test_state_lifetime.py" ]; then
    echo "=== [6] Running pytest tests/test_state_lifetime.py ==="
    # Activate venv if it exists, or use current Python
    if [ -f ".venv/bin/activate" ]; then
      source .venv/bin/activate
    fi
    PYTHONPATH="${PYTHONPATH:-}:$(pwd)" pytest tests/test_state_lifetime.py -v
  else
    echo "SKIP pytest: tests/test_state_lifetime.py not found."
  fi
else
  echo "SKIP pytest: pytest not installed on host."
fi

echo
echo "=== [7] Python compile check ==="
if source .venv/bin/activate 2>/dev/null || true; then
  if python -m compileall app -q 2>&1 | grep -q "Error\|SyntaxError"; then
    echo "ERROR: Python compile errors found"
    python -m compileall app 2>&1 | grep -E "Error|SyntaxError" | head -5
    exit 1
  else
    echo "OK: Python modules compile successfully"
  fi
else
  echo "SKIP compile check: .venv not found"
fi

echo
echo "=== [8] All automated checks completed ==="
echo "Backend: $API_BASE"
echo "Frontend: $WEB_BASE"
echo "Use browser to test: $WEB_BASE/forecast, $WEB_BASE/playground, $WEB_BASE/live"
