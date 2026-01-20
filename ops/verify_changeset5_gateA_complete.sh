#!/usr/bin/env bash
set -euo pipefail

cd /Users/thor/Projects/human-behaviour-convergence

echo "=== GATE A: Baseline snapshot ==="
git status -sb
git status

echo
echo "=== GATE A: Sanity check CORS block in backend ==="
python3 << 'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))

from app.backend.app.main import app  # noqa: F401
from fastapi.middleware.cors import CORSMiddleware

cors = None
for m in app.user_middleware:
    if getattr(m, "cls", None) is CORSMiddleware:
        cors = m
        break

assert cors is not None, "CORSMiddleware is not configured on app"

cfg = cors.options
print("allow_origins:", cfg.get("allow_origins"))
print("allow_credentials:", cfg.get("allow_credentials"))
print("allow_methods:", cfg.get("allow_methods"))
print("allow_headers:", cfg.get("allow_headers"))

assert cfg.get("allow_origins") == ["*"], "Expected allow_origins=['*'] in dev"
assert cfg.get("allow_credentials") is False, "Expected allow_credentials=False"
assert cfg.get("allow_methods") == ["*"], "Expected allow_methods=['*']"
assert cfg.get("allow_headers") == ["*"], "Expected allow_headers=['*']"

print("✅ Backend CORS configuration matches ChangeSet 5 spec")
PY

echo
echo "=== GATE A: Ensure dev_watch_docker.sh exists and is executable ==="
if [[ ! -x "ops/dev_watch_docker.sh" ]]; then
  echo "❌ ops/dev_watch_docker.sh missing or not executable"
  exit 1
fi
echo "✅ ops/dev_watch_docker.sh present and executable"

echo
echo "=== GATE A: Run Docker dev loop (build, up, wait, CORS preflight, logs) ==="
./ops/dev_watch_docker.sh &
DEV_WATCH_PID=$!

# Give it some time to build/start; it will keep running and tail logs
echo "Waiting 15s for Docker stack to start..."
sleep 15

echo
echo "=== GATE A: Direct CORS preflight verification (OPTIONS /api/forecast) ==="
CORS_RESPONSE=$(curl -is -X OPTIONS "http://localhost:8100/api/forecast" \
  -H "Origin: http://localhost:3100" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" 2>&1 || echo "BACKEND_NOT_RUNNING")

echo "$CORS_RESPONSE" | sed -n '1,20p'

if echo "$CORS_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
  echo
  echo "✅ CORS preflight headers present"
else
  if echo "$CORS_RESPONSE" | grep -q "BACKEND_NOT_RUNNING"; then
    echo
    echo "⚠️  Backend not running yet - wait longer and re-check"
  else
    echo
    echo "⚠️  CORS preflight headers not found - check CORS configuration"
  fi
fi

echo
echo "You should see Access-Control-Allow-Origin / -Methods / -Headers above."
echo

echo "=== GATE A: Baseline backend /health and regions ==="
if curl -f http://localhost:8100/health 2>&1 | grep -q "status.*ok"; then
  echo "✅ /health OK"
else
  echo "⚠️  /health check (backend may still be starting)"
fi

echo
REGIONS_OUTPUT=$(curl -fsS "http://localhost:8100/api/forecasting/regions" 2>/dev/null | python3 - << 'PY' || echo "ERROR")
import sys, json
data = json.load(sys.stdin)
print("Total regions:", len(data))
ids = sorted(r["id"] for r in data)
print("Sample IDs:", ids[:10])
if len(data) == 62:
    print("✅ Regions count correct (62)")
else:
    print(f"⚠️  Expected 62 regions, got {len(data)}")
PY
echo "$REGIONS_OUTPUT"

echo
echo "=== GATE A: Frontend /forecast reachable ==="
if curl -f http://localhost:3100/forecast >/dev/null 2>&1; then
  echo "✅ /forecast reachable via Docker frontend"
else
  echo "⚠️  /forecast not reachable yet (frontend may still be starting)"
fi

echo
echo "=== GATE A: Manual browser verification instructions ==="
cat << 'TXT'
1) With docker logs still tailing (dev_watch_docker.sh), open:
   - http://localhost:3100/forecast
   - http://localhost:3100/playground
   - http://localhost:3100/live

2) In DevTools → Network:
   - On /forecast:
     - Select a region (e.g., Minnesota, New York City)
     - Click "Generate Forecast"
     - Confirm:
       * OPTIONS /api/forecast → 200/204
       * POST /api/forecast → 200 with JSON
       * No "Failed to fetch" banner
       * Quick Summary updates

   - On /playground and /live:
     - Confirm GET /api/forecasting/regions → 200
     - Region dropdowns populate
     - No "Failed to load regions" errors
     - No CORS errors in console

3) Watch docker logs while doing this:
   - No backend 5xx tracebacks
   - No repeated CORS failures

When finished, you can stop the tail by:
   kill $DEV_WATCH_PID
Containers will stay running.
TXT

echo
echo "=== GATE A: Quick backend compile sanity (optional, but recommended) ==="
python3 -m compileall app -q || {
  echo "❌ Backend compilation failed"
  exit 1
}
echo "✅ Backend compiles"

echo
echo "=== GATE A: DONE (runtime verification now depends on your browser checks) ==="
echo
echo "Docker dev loop is running in background (PID: $DEV_WATCH_PID)"
echo "To stop log tailing: kill $DEV_WATCH_PID"
echo "Containers will remain running."
