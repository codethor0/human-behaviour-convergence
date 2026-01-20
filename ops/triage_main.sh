#!/usr/bin/env bash
set -euo pipefail

echo "=== HBC MAIN TRIAGE: LOCAL VS CI ==="

if [ ! -f "README.md" ] || [ ! -d "app" ]; then
  echo "Run this from the human-behaviour-convergence repo root."
  exit 1
fi

echo
echo "[1] Quick git + env sanity..."
git status --short || true
python3 --version || true
node --version || true
npm --version || true

echo
echo "[2] Backend compile check..."
python3 -m compileall app -q

echo
echo "[3] Core backend tests (match CI baseline as much as possible)..."
if command -v pytest >/dev/null 2>&1; then
  python3 -m pytest tests/test_state_lifetime.py tests/test_regions_api.py -q --tb=short
else
  echo "pytest is not installed in this environment. Backend tests skipped (ENVIRONMENT ISSUE)."
fi

echo
echo "[4] Frontend checks (lint + build)..."
cd app/frontend
if [ -d "node_modules" ]; then
  npm run lint || echo "NOTE: lint failed (may include pre-existing issues)."
else
  echo "node_modules missing, running npm install..."
  npm install
  npm run lint || echo "NOTE: lint failed (may include pre-existing issues)."
fi
npm run build
cd ../..

echo
echo "[5] Docker stack up + health..."
docker compose up -d --build

echo "Waiting 10s for containers..."
sleep 10

echo "Backend health:"
curl -fsS http://localhost:8100/health || { echo "Backend health failed"; exit 1; }

echo "Frontend root:"
curl -fsS http://localhost:3100/ >/dev/null || { echo "Frontend root failed"; exit 1; }

echo
echo "[6] Forecast contract quick check (backend)..."
echo "Regions count:"
curl -fsS http://localhost:8100/api/forecasting/regions | python3 -c "import sys, json; print(len(json.load(sys.stdin)))"

echo "Sample forecast (Minnesota):"
cat >/tmp/hbc_forecast_mn.json <<'EOF'
{
  "region_id": "US-MN",
  "days_back": 30,
  "forecast_horizon": 7
}
EOF
curl -fsS -X POST http://localhost:8100/api/forecast \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/hbc_forecast_mn.json \
  | python3 - << 'EOF'
import sys, json
data = json.load(sys.stdin)
hist = data.get("history", [])
fcst = data.get("forecast", [])
print(f"history={len(hist)}, forecast={len(fcst)}, keys={list(data.keys())}")
EOF

echo
echo "[7] CORS preflight sanity for /api/forecast..."
curl -is -X OPTIONS "http://localhost:8100/api/forecast" \
  -H "Origin: http://localhost:3100" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  | grep -Ei 'access-control-allow-(origin|methods|headers|max-age)' || true

echo
echo "[8] (Optional) Playwright smoke tests if installed..."
cd app/frontend
if npx --yes playwright --version >/dev/null 2>&1; then
  PLAYWRIGHT_BASE_URL=http://localhost:3100 npx playwright test e2e/forecast.smoke.spec.ts e2e/history.smoke.spec.ts
else
  echo "Playwright not installed; skipping E2E (ENVIRONMENT ISSUE)."
fi
cd ../..

echo
echo "=== HBC MAIN TRIAGE COMPLETE ==="
