#!/usr/bin/env bash
# SPDX-License-Identifier: PROPRIETARY
# Verification script for FRED UI configured state (Scenario A: no key, Scenario B: key set)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "=== FRED Configured UI Verification ==="
echo ""

# Color helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

check_health() {
    echo "[Health] Checking /health..."
    if curl -fsS http://localhost:8100/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} /health OK"
        return 0
    else
        echo -e "${RED}✗${NC} /health failed"
        return 1
    fi
}

check_regions() {
    echo "[Regions] Checking /api/forecasting/regions..."
    REG_JSON=$(curl -sS http://localhost:8100/api/forecasting/regions)
    COUNT=$(echo "$REG_JSON" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d))")
    HAS_MN=$(echo "$REG_JSON" | python3 -c "import sys, json; d=json.load(sys.stdin); print(any(r.get('id') == 'us_mn' for r in d))")
    
    if [ "$COUNT" = "62" ] && [ "$HAS_MN" = "True" ]; then
        echo -e "${GREEN}✓${NC} Regions: 62 (includes us_mn)"
        return 0
    else
        echo -e "${RED}✗${NC} Regions: $COUNT (expected 62), has_mn: $HAS_MN"
        return 1
    fi
}

check_forecast_contract() {
    echo "[Forecast] Checking /api/forecast contract..."
    FORECAST_JSON=$(curl -sS -X POST http://localhost:8100/api/forecast \
        -H "Content-Type: application/json" \
        -d '{"region_id":"us_mn","region_name":"Minnesota (US)","latitude":46.7296,"longitude":-94.6859,"days_back":30,"forecast_horizon":7}')
    
    eval "$(echo "$FORECAST_JSON" | python3 << 'PY'
import sys, json
try:
    data = json.load(sys.stdin)
    history = data.get("history", [])
    forecast = data.get("forecast", [])
    print(f"history_len={len(history)}")
    print(f"forecast_len={len(forecast)}")
    print(f"has_history={'history' in data}")
    print(f"has_forecast={'forecast' in data}")
    print(f"has_risk_tier={'risk_tier' in data}")
    print(f"has_sources={'sources' in data}")
    print(f"has_metadata={'metadata' in data}")
except Exception as e:
    print(f"parse_error=1")
    print(f"error_msg='{str(e)}'")
PY
)"
    
    if [ "${parse_error:-0}" = "1" ]; then
        echo -e "${RED}✗${NC} Forecast contract: JSON parse error"
        return 1
    fi
    
    if [ "${history_len:-0}" -ge 30 ] && [ "${history_len:-0}" -le 40 ] && [ "${forecast_len:-0}" = "7" ] && \
       [ "${has_history}" = "True" ] && [ "${has_forecast}" = "True" ] && [ "${has_risk_tier}" = "True" ] && \
       [ "${has_sources}" = "True" ] && [ "${has_metadata}" = "True" ]; then
        echo -e "${GREEN}✓${NC} Forecast contract: history_len=${history_len} (30-40), forecast_len=${forecast_len} (7), all keys present"
        return 0
    else
        echo -e "${RED}✗${NC} Forecast contract: history_len=${history_len} (expected 30-40), forecast_len=${forecast_len} (expected 7)"
        return 1
    fi
}

check_fred_backend_status() {
    local expected_status=$1
    local should_have_message=$2
    local scenario_name=$3
    
    echo "[FRED Backend] Checking FRED status (${scenario_name})..."
    FRED_JSON=$(curl -sS http://localhost:8100/api/forecasting/data-sources | python3 << 'PY'
import sys, json
data = json.load(sys.stdin)
fred = [s for s in data if 'fred' in (s.get('name','').lower()) or s.get('id') == 'fred_economic']
if fred:
    print(json.dumps(fred[0], indent=2))
else:
    print("{}")
PY
)
    
    if [ "$FRED_JSON" = "{}" ]; then
        echo -e "${RED}✗${NC} FRED entry not found in /api/forecasting/data-sources"
        return 1
    fi
    
    eval "$(echo "$FRED_JSON" | python3 << 'PY'
import sys, json
data = json.load(sys.stdin)
status = data.get("status", "").lower()
optional = data.get("optional", False)
env_var = data.get("env_var", "")
message = data.get("message", "") or ""
print(f"fred_status='{status}'")
print(f"fred_optional={optional}")
print(f"fred_env_var='{env_var}'")
print(f"fred_message='{message}'")
PY
)"
    
    echo "  FRED entry: status='${fred_status}', optional=${fred_optional}, env_var='${fred_env_var}'"
    if [ -n "${fred_message}" ]; then
        echo "  message: '${fred_message:0:80}...'"
    fi
    
    # Check status
    if [ "${fred_status}" != "${expected_status}" ]; then
        echo -e "${RED}✗${NC} FRED status: '${fred_status}' (expected '${expected_status}')"
        return 1
    fi
    
    # Check optional flag
    if [ "${fred_optional}" != "True" ]; then
        echo -e "${RED}✗${NC} FRED optional: ${fred_optional} (expected True)"
        return 1
    fi
    
    # Check env_var
    if [ "${fred_env_var}" != "FRED_API_KEY" ]; then
        echo -e "${RED}✗${NC} FRED env_var: '${fred_env_var}' (expected 'FRED_API_KEY')"
        return 1
    fi
    
    # Check message presence
    if [ "${should_have_message}" = "true" ] && [ -z "${fred_message}" ]; then
        echo -e "${RED}✗${NC} FRED should have baseline message but message is empty"
        return 1
    fi
    
    if [ "${should_have_message}" = "false" ] && [ -n "${fred_message}" ]; then
        echo -e "${RED}✗${NC} FRED should NOT have baseline message but message='${fred_message:0:60}'"
        return 1
    fi
    
    echo -e "${GREEN}✓${NC} FRED backend status matches expected: status='${expected_status}', message=${should_have_message}"
    return 0
}

# SCENARIO A: No FRED_API_KEY
echo "=== Scenario A: No FRED_API_KEY ==="
echo ""

# Ensure FRED_API_KEY is unset
unset FRED_API_KEY
export FRED_API_KEY=""

echo "[Env] FRED_API_KEY is unset"

# Check health and basic endpoints
if ! check_health || ! check_regions || ! check_forecast_contract; then
    echo -e "${RED}✗${NC} Scenario A: Basic health/regions/forecast checks failed"
    FAILED=1
fi

# Check FRED backend status (should be inactive with message)
if ! check_fred_backend_status "inactive" "true" "Scenario A (no key)"; then
    FAILED=1
fi

echo ""

# SCENARIO B: FRED_API_KEY is set
echo "=== Scenario B: FRED_API_KEY is set ==="
echo ""

# Set FRED_API_KEY
export FRED_API_KEY="TEST_FRED_KEY_SHOULD_BE_VISIBLE_IN_CONTAINER"
echo "[Env] FRED_API_KEY is set to TEST_FRED_KEY_SHOULD_BE_VISIBLE_IN_CONTAINER"

# Restart stack with new env
echo "[Docker] Restarting stack with FRED_API_KEY..."
docker compose down > /dev/null 2>&1 || true
./ops/dev_watch_docker.sh > /dev/null 2>&1 &

# Wait for stack to be ready
echo "[Wait] Waiting for stack to be ready..."
for i in {1..30}; do
    if curl -fsS http://localhost:8100/health > /dev/null 2>&1 && \
       curl -fsS http://localhost:3100/forecast > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Stack ready (attempt $i)"
        break
    fi
    sleep 2
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗${NC} Stack did not become ready after 60 seconds"
        exit 1
    fi
done

# Check health and basic endpoints
if ! check_health || ! check_regions || ! check_forecast_contract; then
    echo -e "${RED}✗${NC} Scenario B: Basic health/regions/forecast checks failed"
    FAILED=1
fi

# Check FRED backend status (should be active without message)
if ! check_fred_backend_status "active" "false" "Scenario B (key set)"; then
    FAILED=1
fi

echo ""

# Final summary
echo "=== Verification Summary ==="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All checks passed"
    echo ""
    echo "Scenario A (no key): FRED shows inactive with baseline message ✓"
    echo "Scenario B (key set): FRED shows active without baseline message ✓"
    echo "Forecast contract preserved: 62 regions, correct history/forecast lengths ✓"
    exit 0
else
    echo -e "${RED}✗${NC} Some checks failed"
    exit 1
fi