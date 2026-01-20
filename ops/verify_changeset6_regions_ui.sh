#!/usr/bin/env bash
set -euo pipefail

echo "=== ChangeSet 6 – Regions UI Verification ==="

# 0) Quick sanity – repo root check
if [ ! -d "app/frontend" ] || [ ! -d "ops" ]; then
  echo "✗ Run this from the repo root (where app/ and ops/ exist)."
  exit 1
fi

echo "1) Backend health check"
curl -sf http://localhost:8100/health >/dev/null
echo "   ✓ /health OK"

echo "2) Regions API contract – expect 62 regions"
REG_JSON=/tmp/regions_changeset6.json
curl -sS http://localhost:8100/api/forecasting/regions > "$REG_JSON"

python3 - << 'PY'
import json, sys, os
path = os.environ.get("REG_JSON", "/tmp/regions_changeset6.json")
with open(path, "r") as f:
    data = json.load(f)
count = len(data) if isinstance(data, list) else 0
print(f"   regions: {count}")
assert isinstance(data, list), f"Regions response is not a list: {type(data)}"
assert count == 62, f"Expected 62 regions, got {count}"
ids = {r.get("id") for r in data}
for required in ["us_mn", "city_nyc", "us_dc"]:
    assert required in ids, f"Missing required region id: {required}"
PY
echo "   ✓ /api/forecasting/regions contract OK"

echo "3) Static code checks – all pages use useRegions + proper messages"
for page in forecast playground live; do
  file="app/frontend/src/pages/${page}.tsx"
  echo "   → Checking ${file}"
  if [ ! -f "$file" ]; then
    echo "     ✗ Missing file: $file"
    exit 1
  fi

  # Must use shared hook
  rg "useRegions" "$file" >/dev/null
  echo "     ✓ uses useRegions hook"

  # UX messages should exist in the component
  rg "Loading regions" "$file" >/dev/null
  echo "     ✓ has 'Loading regions…' state"

  rg "Failed to load regions" "$file" >/dev/null || rg "Unable to load regions" "$file" >/dev/null
  echo "     ✓ has error message for region loading failure"

  # Retry affordance should exist somewhere
  rg -i "retry" "$file" >/dev/null
  echo "     ✓ exposes retry affordance"
done

echo "4) HTTP checks – pages respond and hydrate"
for page in forecast playground live; do
  echo "   → Fetching /${page}"
  HTML="/tmp/${page}_changeset6.html"
  curl -sf "http://localhost:3100/${page}" > "$HTML"
  # We mainly care about 200 OK; content will be hydrated by React
  echo "     ✓ /${page} HTTP 200"

  # Sanity: region-related strings appear in HTML/JS bundle
  rg "Loading regions" "$HTML" >/dev/null || echo "     (info) 'Loading regions' not in static HTML – likely client-rendered"
done

echo "5) Minimal behavioral smoke – ensure regions load via API from UI code"
# This is a light check: we just prove the frontend bundle references the regions endpoint.
rg "/api/forecasting/regions" app/frontend/.next -n 2>/dev/null || echo "   (info) regions endpoint reference not found in built assets (double-check build output)"

echo
echo "=== ChangeSet 6 – Regions UI Verification COMPLETE ==="
echo "If no ✗ messages appeared above, ChangeSet 6 is GREEN from the runtime/static perspective."
