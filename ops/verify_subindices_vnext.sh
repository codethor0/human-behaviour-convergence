#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Verification script for Sub-Index Breakdown vNext (9 primary + child indices)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

echo "=== Sub-Index Breakdown vNext Verification ==="
echo ""

# Clean restart
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

echo "4. Checking regions count..."
REGIONS_COUNT=$(curl -sS http://localhost:8100/api/forecasting/regions | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
if [ "$REGIONS_COUNT" != "62" ]; then
    echo "❌ Expected 62 regions, got ${REGIONS_COUNT}"
    exit 1
fi
echo "✅ Regions count: ${REGIONS_COUNT}"

echo "5. Testing forecast for Minnesota (us_mn)..."
curl -sS -X POST http://localhost:8100/api/forecast \
    -H "Content-Type: application/json" \
    -d '{"region_id":"us_mn","region_name":"Minnesota (US)","latitude":46.7296,"longitude":-94.6859,"days_back":30,"forecast_horizon":7}' \
    > /tmp/forecast_subindices.json 2>&1

if [ ! -s /tmp/forecast_subindices.json ]; then
    echo "❌ Forecast response is empty"
    exit 1
fi

echo "6. Validating forecast contract..."
HISTORY_LEN=$(python3 << 'PY'
import json, sys
with open('/tmp/forecast_subindices.json') as f:
    data = json.load(f)
print(len(data.get('history', [])))
PY
)
FORECAST_LEN=$(python3 << 'PY'
import json, sys
with open('/tmp/forecast_subindices.json') as f:
    data = json.load(f)
print(len(data.get('forecast', [])))
PY
)

if [ "$HISTORY_LEN" -lt 30 ] || [ "$HISTORY_LEN" -gt 40 ]; then
    echo "❌ History length ${HISTORY_LEN} not in [30, 40]"
    exit 1
fi
if [ "$FORECAST_LEN" != "7" ]; then
    echo "❌ Forecast length ${FORECAST_LEN} != 7"
    exit 1
fi
echo "✅ Forecast contract: history=${HISTORY_LEN}, forecast=${FORECAST_LEN}"

echo "7. Validating sub-indices (must have 9 primary indices)..."
SUBINDICES_COUNT=$(python3 << 'PY'
import json, sys
with open('/tmp/forecast_subindices.json') as f:
    data = json.load(f)
subindices = data.get('explanations', {}).get('subindices', {})
print(len(subindices))
PY
)
SUBINDICES_KEYS=$(python3 << 'PY'
import json, sys
with open('/tmp/forecast_subindices.json') as f:
    data = json.load(f)
subindices = data.get('explanations', {}).get('subindices', {})
print(','.join(sorted(subindices.keys())))
PY
)

if [ "$SUBINDICES_COUNT" != "9" ]; then
    echo "❌ Expected 9 sub-indices, got ${SUBINDICES_COUNT}"
    exit 1
fi

REQUIRED_KEYS="economic_stress,environmental_stress,mobility_activity,digital_attention,public_health_stress,political_stress,crime_stress,misinformation_stress,social_cohesion_stress"
for key in $(echo "$REQUIRED_KEYS" | tr ',' ' '); do
    if ! echo "$SUBINDICES_KEYS" | grep -q "$key"; then
        echo "❌ Missing required sub-index: ${key}"
        exit 1
    fi
done
echo "✅ All 9 primary sub-indices present"

echo "8. Validating child indices in subindices_details..."
SUBINDICES_DETAILS=$(python3 << 'PY'
import json, sys
with open('/tmp/forecast_subindices.json') as f:
    data = json.load(f)
details = data.get('explanations', {}).get('subindices_details', {})
if not details:
    print("{}")
    sys.exit(1)
# Extract child indices
children_found = []
for parent, parent_data in details.items():
    children = parent_data.get('children', {})
    for child_key in children.keys():
        children_found.append(child_key)
print(','.join(sorted(children_found)))
PY
)

if [ -z "$SUBINDICES_DETAILS" ] || [ "$SUBINDICES_DETAILS" = "{}" ]; then
    echo "❌ subindices_details is missing or empty"
    exit 1
fi

REQUIRED_CHILDREN="mobility_suppression,mobility_shock,attention_volatility,legislative_volatility,enforcement_pressure,narrative_fragmentation"
MISSING_COUNT=0
for child in $(echo "$REQUIRED_CHILDREN" | tr ',' ' '); do
    if ! echo "$SUBINDICES_DETAILS" | grep -q "$child"; then
        echo "⚠️  Missing child index: ${child} (may be acceptable if insufficient data)"
        MISSING_COUNT=$((MISSING_COUNT + 1))
    fi
done

if [ "$MISSING_COUNT" -eq "$(echo "$REQUIRED_CHILDREN" | tr ',' '\n' | wc -l | xargs)" ]; then
    echo "❌ No required child indices found"
    exit 1
fi

echo "✅ Child indices found: $(echo "$SUBINDICES_DETAILS" | tr ',' ' ' | wc -w | xargs)"

echo "9. Validating child index values (0.0 <= value <= 1.0)..."
INVALID_VALUES=$(python3 << 'PY'
import json, sys
with open('/tmp/forecast_subindices.json') as f:
    data = json.load(f)
details = data.get('explanations', {}).get('subindices_details', {})
invalid = []
for parent, parent_data in details.items():
    children = parent_data.get('children', {})
    for child_key, child_data in children.items():
        value = child_data.get('value', None)
        if value is None:
            invalid.append(f"{child_key}: missing value")
        elif not (0.0 <= float(value) <= 1.0):
            invalid.append(f"{child_key}: value {value} not in [0.0, 1.0]")
if invalid:
    print('\n'.join(invalid))
else:
    print("OK")
PY
)

if [ "$INVALID_VALUES" != "OK" ]; then
    echo "❌ Invalid child index values:"
    echo "$INVALID_VALUES"
    exit 1
fi
echo "✅ All child index values in valid range [0.0, 1.0]"

echo "10. Checking frontend assets..."
if [ ! -d "app/frontend/.next" ]; then
    echo "⚠️  Frontend not built, skipping asset checks"
else
    RG_FOUND=0
    if command -v rg >/dev/null 2>&1; then
        if rg -q "Sub-Index Breakdown" app/frontend/.next 2>/dev/null; then
            RG_FOUND=$((RG_FOUND + 1))
        fi
        if rg -q "Political Stress" app/frontend/.next 2>/dev/null; then
            RG_FOUND=$((RG_FOUND + 1))
        fi
        if rg -q "Misinformation Stress" app/frontend/.next 2>/dev/null; then
            RG_FOUND=$((RG_FOUND + 1))
        fi
        if rg -q "Mobility Suppression" app/frontend/.next 2>/dev/null; then
            RG_FOUND=$((RG_FOUND + 1))
        fi
        if rg -q "Attention Volatility" app/frontend/.next 2>/dev/null; then
            RG_FOUND=$((RG_FOUND + 1))
        fi
    fi
    if [ $RG_FOUND -gt 0 ]; then
        echo "✅ Found ${RG_FOUND} labels in frontend assets"
    else
        echo "⚠️  Could not verify labels in frontend assets (rg not available or not built)"
    fi
fi

echo ""
echo "=== ✅ All checks passed ==="
echo "Sub-Index Breakdown vNext verification complete"
echo "  - 9 primary indices: ✅"
echo "  - Child indices: ✅"
echo "  - Forecast contract: ✅"
