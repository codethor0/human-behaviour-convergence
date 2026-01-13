#!/usr/bin/env bash
set -euo pipefail

BASE_BACKEND="${BASE_BACKEND:-http://localhost:8100}"
BASE_FRONTEND="${BASE_FRONTEND:-http://localhost:3100}"

echo "== [1/5] Docker compose build =="
docker compose build

echo "== [2/5] Docker compose up (detached) =="
docker compose up -d

echo "== [3/5] Waiting for backend at ${BASE_BACKEND}/health =="
for i in $(seq 1 60); do
  if curl -sf "${BASE_BACKEND}/health" > /dev/null; then
    echo "Backend is up (attempt $i)"
    break
  fi
  sleep 1
done

echo "== [4/5] Waiting for frontend at ${BASE_FRONTEND}/forecast =="
for i in $(seq 1 60); do
  if curl -sf "${BASE_FRONTEND}/forecast" > /dev/null; then
    echo "Frontend is up (attempt $i)"
    break
  fi
  sleep 1
done

echo "== [5/5] CORS sanity check for /api/forecast from http://localhost:3100 =="

curl -is -X OPTIONS "${BASE_BACKEND}/api/forecast" \
  -H "Origin: http://localhost:3100" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" || true

echo
echo "If you see Access-Control-Allow-Origin and Access-Control-Allow-Headers above, CORS is good."
echo
echo "Docker services:"
docker compose ps

echo
echo "Tailing backend + frontend logs (Ctrl+C to stop tail, containers stay running)..."
docker compose logs -f backend frontend
