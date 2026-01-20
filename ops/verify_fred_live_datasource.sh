#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Verification script for FRED as a normal live data source (no key UX, no baseline state)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "=== FRED Live Data Source Verification ==="
echo ""

# Scenario A: No FRED_API_KEY set
echo "--- Scenario A: No FRED_API_KEY ---"
unset FRED_API_KEY || true
export FRED_API_KEY=""

echo "1. Stopping Docker stack..."
docker compose down >/dev/null 2>&1 || true

echo "2. Starting Docker stack (canonical dev loop)..."
if ! "${REPO_ROOT}/ops/dev_watch_docker.sh" >/dev/null 2>&1; then
    echo "❌ dev_watch_docker.sh failed"
    exit 1
fi

echo "3. Waiting for health endpoint..."
timeout=60
elapsed=0
while ! curl -sS http://localhost:8100/health >/dev/null 2>&1; do
    if [ $elapsed -ge $timeout ]; then
        echo "❌ Health endpoint not available after ${timeout}s"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo "✅ Backend health OK"

echo "4. Checking regions endpoint..."
REGIONS_COUNT=$(curl -sS http://localhost:8100/api/forecasting/regions | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [ "$REGIONS_COUNT" != "62" ]; then
    echo "❌ Expected 62 regions, got ${REGIONS_COUNT}"
    exit 1
fi
echo "✅ Regions endpoint returns ${REGIONS_COUNT} regions"

echo "5. Checking forecast contract..."
FORECAST_JSON=$(curl -sS -X POST http://localhost:8100/api/forecast \
    -H "Content-Type: application/json" \
    -d '{"region_id":"us_mn","region_name":"Minnesota (US)","latitude":46.7296,"longitude":-94.6859,"days_back":30,"forecast_horizon":7}' || echo "")
if [ -z "$FORECAST_JSON" ]; then
    echo "❌ Forecast endpoint returned empty response"
    exit 1
fi
HISTORY_LEN=$(echo "$FORECAST_JSON" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('history', [])))" 2>/dev/null || echo "0")
FORECAST_LEN=$(echo "$FORECAST_JSON" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('forecast', [])))" 2>/dev/null || echo "0")
if [ "$HISTORY_LEN" -lt 30 ] || [ "$HISTORY_LEN" -gt 40 ]; then
    echo "❌ History length ${HISTORY_LEN} not in [30, 40]"
    exit 1
fi
if [ "$FORECAST_LEN" != "7" ]; then
    echo "❌ Forecast length ${FORECAST_LEN} != 7"
    exit 1
fi
echo "✅ Forecast contract: history=${HISTORY_LEN}, forecast=${FORECAST_LEN}"

echo "6. Checking FRED entry in data-sources (Scenario A: no key)..."
FRED_JSON=$(curl -sS http://localhost:8100/api/forecasting/data-sources | python3 -c "
import sys, json
data = json.load(sys.stdin)
fred = [s for s in data if 'fred' in (s.get('name','').lower()) or s.get('id') == 'fred_economic']
if fred:
    print(json.dumps(fred[0], indent=2))
else:
    print('{}')
" 2>/dev/null || echo "{}")
if [ -z "$FRED_JSON" ] || [ "$FRED_JSON" = "{}" ]; then
    echo "❌ FRED entry not found in data-sources"
    exit 1
fi

FRED_STATUS=$(echo "$FRED_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null || echo "")
FRED_MESSAGE=$(echo "$FRED_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('message', '') or '')" 2>/dev/null || echo "")
if [ "$FRED_STATUS" != "active" ]; then
    echo "❌ FRED status is '${FRED_STATUS}', expected 'active'"
    exit 1
fi
if echo "$FRED_MESSAGE" | grep -qiE "FRED_API_KEY|not configured|baseline|set.*env|\.env"; then
    echo "❌ FRED message contains forbidden strings: ${FRED_MESSAGE}"
    exit 1
fi
echo "✅ FRED status: ${FRED_STATUS}, message: ${FRED_MESSAGE:-'(empty)'}"

# Scenario B: FRED_API_KEY set
echo ""
echo "--- Scenario B: FRED_API_KEY set ---"
export FRED_API_KEY="TEST_FRED_KEY_SHOULD_BE_VISIBLE_IN_CONTAINER"

echo "7. Restarting Docker stack with FRED_API_KEY set..."
docker compose down >/dev/null 2>&1 || true
if ! "${REPO_ROOT}/ops/dev_watch_docker.sh" >/dev/null 2>&1; then
    echo "❌ dev_watch_docker.sh failed"
    exit 1
fi

echo "8. Waiting for health endpoint..."
timeout=60
elapsed=0
while ! curl -sS http://localhost:8100/health >/dev/null 2>&1; do
    if [ $elapsed -ge $timeout ]; then
        echo "❌ Health endpoint not available after ${timeout}s"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo "✅ Backend health OK"

echo "9. Checking FRED entry in data-sources (Scenario B: key set)..."
FRED_JSON=$(curl -sS http://localhost:8100/api/forecasting/data-sources | python3 -c "
import sys, json
data = json.load(sys.stdin)
fred = [s for s in data if 'fred' in (s.get('name','').lower()) or s.get('id') == 'fred_economic']
if fred:
    print(json.dumps(fred[0], indent=2))
else:
    print('{}')
" 2>/dev/null || echo "{}")
if [ -z "$FRED_JSON" ] || [ "$FRED_JSON" = "{}" ]; then
    echo "❌ FRED entry not found in data-sources"
    exit 1
fi

FRED_STATUS=$(echo "$FRED_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null || echo "")
FRED_MESSAGE=$(echo "$FRED_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('message', '') or '')" 2>/dev/null || echo "")
if [ "$FRED_STATUS" != "active" ]; then
    echo "❌ FRED status is '${FRED_STATUS}', expected 'active'"
    exit 1
fi
if echo "$FRED_MESSAGE" | grep -qiE "FRED_API_KEY|not configured|baseline|set.*env|\.env"; then
    echo "❌ FRED message contains forbidden strings: ${FRED_MESSAGE}"
    exit 1
fi
echo "✅ FRED status: ${FRED_STATUS}, message: ${FRED_MESSAGE:-'(empty)'}"

echo ""
echo "=== ✅ All checks passed ==="
echo "FRED behaves as a normal live data source (always active, no key UX)"
