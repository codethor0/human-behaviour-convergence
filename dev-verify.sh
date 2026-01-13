#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8100}"
WEB_BASE="${WEB_BASE:-http://localhost:3003}"

echo "=== [1] Starting Docker stack (detached) ==="
# .env file is optional per docker-compose.yml
if [ ! -f ".env" ]; then
  echo "Note: .env file not found (optional, using defaults from docker-compose.yml)"
fi
docker compose up --build -d

echo
echo "=== [2] Show running containers ==="
docker compose ps

echo
echo "=== [3] Tailing logs in background (will stop when script exits) ==="
docker compose logs -f &
LOG_PID=$!
trap 'kill "$LOG_PID" 2>/dev/null || true' EXIT

echo
echo "=== [4] Waiting for backend regions endpoint ==="
REGIONS_URL="$API_BASE/api/forecasting/regions"
echo "Target: $REGIONS_URL"
until curl -fsS "$REGIONS_URL" >/dev/null 2>&1; do
  echo "Backend not ready yet, retrying in 2s..."
  sleep 2
done
echo "OK: /api/forecasting/regions is responding."

echo
echo "=== [5] Waiting for frontend /forecast route ==="
FORECAST_PAGE_URL="$WEB_BASE/forecast"
echo "Target: $FORECAST_PAGE_URL"
until curl -fsS "$FORECAST_PAGE_URL" >/dev/null 2>&1; do
  echo "Frontend not ready yet, retrying in 2s..."
  sleep 2
done
echo "OK: frontend /forecast is responding."

echo
if [ -d "app/frontend" ]; then
  echo "=== [6] Frontend build: app/frontend ==="
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
    echo "=== [7] Running pytest tests/test_state_lifetime.py ==="
    pytest tests/test_state_lifetime.py
  else
    echo "SKIP pytest: tests/test_state_lifetime.py not found."
  fi
else
  echo "SKIP pytest: pytest not installed on host."
fi

echo
echo "=== [8] All automated checks completed ==="
echo "Containers are still running."
echo "Use 'docker compose ps' to inspect or 'docker compose down' to stop them."
