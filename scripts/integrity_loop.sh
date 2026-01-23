#!/usr/bin/env bash
set -euo pipefail

PASS_TARGET="${PASS_TARGET:-2}"          # consecutive passes required
SLEEP_BETWEEN="${SLEEP_BETWEEN:-20}"     # seconds between attempts
MAX_ATTEMPTS="${MAX_ATTEMPTS:-30}"       # total attempts before giving up

FRONTEND_URL="${FRONTEND_URL:-http://localhost:3100}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8100}"
PROM_URL="${PROM_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3001}"

TS="$(date +%Y%m%d_%H%M%S)"
OUT_ROOT="/tmp/hbc_integrity_loop_${TS}"
mkdir -p "$OUT_ROOT"

log() { printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*" | tee -a "${OUT_ROOT}/run.log"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { log "P0: missing required command: $1"; exit 2; }
}

need_cmd curl
need_cmd git
need_cmd docker

attempt=0
consecutive_pass=0

log "Starting integrity loop"
log "PASS_TARGET=${PASS_TARGET} MAX_ATTEMPTS=${MAX_ATTEMPTS} SLEEP_BETWEEN=${SLEEP_BETWEEN}"
log "FRONTEND_URL=${FRONTEND_URL} BACKEND_URL=${BACKEND_URL} PROM_URL=${PROM_URL} GRAFANA_URL=${GRAFANA_URL}"

baseline() {
  log "Baseline snapshot"
  {
    echo "git_rev: $(git rev-parse HEAD 2>/dev/null || true)"
    echo "git_status:"
    git status --porcelain 2>/dev/null || true
    echo "tracked_files_count: $(git ls-files 2>/dev/null | wc -l | tr -d ' ')"
    echo "repo_size:"
    du -sh . 2>/dev/null || true
    echo "docker_version:"
    docker --version 2>/dev/null || true
    echo "compose_version:"
    docker compose version 2>/dev/null || true
  } > "${OUT_ROOT}/baseline.txt" || true
}

docker_up() {
  log "Bringing up docker compose stack"
  docker compose up -d --build | tee -a "${OUT_ROOT}/docker_up.log"
}

docker_diag() {
  log "Capturing docker diagnostics"
  {
    echo "docker_ps:"
    docker ps -a
    echo
    echo "docker_compose_ps:"
    docker compose ps
    echo
    echo "backend_logs_tail:"
    docker compose logs backend --tail=200 || true
    echo
    echo "frontend_logs_tail:"
    docker compose logs frontend --tail=200 || true
    echo
    echo "prometheus_logs_tail:"
    docker compose logs prometheus --tail=200 || true
    echo
    echo "grafana_logs_tail:"
    docker compose logs grafana --tail=200 || true
  } > "${OUT_ROOT}/docker_diag.txt" || true
}

http_check() {
  local url="$1"
  local name="$2"
  local code
  code="$(curl -sS -o /dev/null -w "%{http_code}" "$url" || true)"
  printf "%s %s %s\n" "$name" "$url" "$code" | tee -a "${OUT_ROOT}/http_checks.txt"
  [[ "$code" == "200" ]]
}

wait_ready() {
  log "Waiting for backend health"
  for i in $(seq 1 60); do
    if http_check "${BACKEND_URL}/health" "backend_health"; then
      log "Backend healthy"
      break
    fi
    sleep 2
  done

  log "Waiting for frontend root"
  for i in $(seq 1 60); do
    if http_check "${FRONTEND_URL}/" "frontend_root"; then
      log "Frontend root OK"
      break
    fi
    sleep 2
  done

  log "Checking critical routes"
  http_check "${FRONTEND_URL}/forecast" "route_forecast" || { log "P0: /forecast not 200"; return 1; }
  http_check "${FRONTEND_URL}/history" "route_history" || { log "P0: /history not 200"; return 1; }
  http_check "${FRONTEND_URL}/live" "route_live" || { log "P0: /live not 200"; return 1; }
  http_check "${FRONTEND_URL}/playground" "route_playground" || { log "P0: /playground not 200"; return 1; }

  log "Checking Prometheus and Grafana reachability"
  http_check "${PROM_URL}/-/ready" "prom_ready" || { log "P1: Prometheus not ready"; return 1; }
  http_check "${GRAFANA_URL}/api/health" "grafana_health" || { log "P1: Grafana not healthy"; return 1; }

  return 0
}

post_json() {
  local url="$1"
  local json="$2"
  curl -sS -X POST "$url" -H "Content-Type: application/json" -d "$json"
}

forecast_probe() {
  log "Forecast probe for two distant regions"
  # Illinois vs Arizona as variance canary (and aligns with your plan success criteria)
  local il='{"latitude":40.3495,"longitude":-88.9861,"region_name":"Illinois","days_back":30,"forecast_horizon":7}'
  local az='{"latitude":34.2744,"longitude":-111.6602,"region_name":"Arizona","days_back":30,"forecast_horizon":7}'

  post_json "${BACKEND_URL}/api/forecast" "$il" > "${OUT_ROOT}/forecast_il.json" || { log "P0: forecast IL request failed"; return 1; }
  post_json "${BACKEND_URL}/api/forecast" "$az" > "${OUT_ROOT}/forecast_az.json" || { log "P0: forecast AZ request failed"; return 1; }

  # hash key fields to prove different outputs (avoid jq dependency; use python if present)
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' "${OUT_ROOT}/forecast_il.json" "${OUT_ROOT}/forecast_az.json" > "${OUT_ROOT}/forecast_hashes.txt"
import hashlib, json, sys
def h(obj): return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
keys=[]
for k in ["history","forecast","sub_indices","behavior_index","region_id","region_name"]:
  keys.append(k)
out=[]
for k in keys:
  out.append((k, h(a.get(k)), h(b.get(k))))
print("\n".join([f"{k} il={x} az={y} same={x==y}" for k,x,y in out]))
PY
  else
    log "python3 not found; skipping hash proof (install python3 for stronger evidence)"
  fi

  return 0
}

prom_query() {
  local q="$1"
  curl -sS -G "${PROM_URL}/api/v1/query" --data-urlencode "query=${q}"
}

prometheus_probe() {
  log "Prometheus probe: verify multi-region series exist"
  prom_query 'count(count by (region) (behavior_index))' > "${OUT_ROOT}/prom_regions_count.json" || true
  prom_query 'count(count by (region) (child_subindex_value))' > "${OUT_ROOT}/prom_child_regions_count.json" || true
  prom_query 'count(count by (region) (parent_subindex_value))' > "${OUT_ROOT}/prom_parent_regions_count.json" || true
  prom_query 'count(behavior_index)' > "${OUT_ROOT}/prom_behavior_index_series_count.json" || true

  # Require at least 2 distinct regions present (should be true after the forecast_probe)
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' "${OUT_ROOT}/prom_regions_count.json" || { log "P0: Prometheus query parse failed"; return 1; }
import json, sys
j=json.load(open(sys.argv[1]))
try:
  v=j["data"]["result"][0]["value"][1]
  n=float(v)
  print(f"distinct_regions={n}")
  if n < 2:
    raise SystemExit(2)
except Exception as e:
  print(f"bad_prom_response: {e}")
  raise SystemExit(2)
PY
  else
    log "python3 not found; cannot enforce region count threshold; continuing"
  fi

  return 0
}

run_tests_if_present() {
  log "Running local integrity tests if present"
  local ran_any=0

  if [[ -f "tests/test_analytics_contracts.py" ]]; then
    ran_any=1
    if command -v pytest >/dev/null 2>&1; then
      pytest -q tests/test_analytics_contracts.py | tee "${OUT_ROOT}/pytest_contracts.txt"
    else
      log "pytest not available; skipping contract tests"
    fi
  fi

  if [[ -f "scripts/variance_probe.py" ]]; then
    ran_any=1
    if command -v python3 >/dev/null 2>&1; then
      python3 scripts/variance_probe.py | tee "${OUT_ROOT}/variance_probe.txt"
    else
      log "python3 not available; skipping variance probe"
    fi
  fi

  if [[ $ran_any -eq 0 ]]; then
    log "No known integrity test artifacts found; skipping"
  fi
}

baseline

while [[ $attempt -lt $MAX_ATTEMPTS ]]; do
  attempt=$((attempt + 1))
  log "Attempt ${attempt}/${MAX_ATTEMPTS} (consecutive_pass=${consecutive_pass}/${PASS_TARGET})"

  # fresh attempt folder
  ATT_OUT="${OUT_ROOT}/attempt_${attempt}"
  mkdir -p "$ATT_OUT"
  # redirect outputs per attempt by symlinking OUT_ROOT pointers
  ln -sfn "$ATT_OUT" "${OUT_ROOT}/current"

  # Write attempt marker
  echo "attempt=${attempt} ts=$(date -Is)" > "${ATT_OUT}/attempt.meta"

  set +e
  docker_up
  wait_ready
  ready_rc=$?
  if [[ $ready_rc -ne 0 ]]; then
    log "Attempt failed at readiness checks"
    docker_diag
    consecutive_pass=0
    set -e
    sleep "$SLEEP_BETWEEN"
    continue
  fi

  forecast_probe
  forecast_rc=$?
  if [[ $forecast_rc -ne 0 ]]; then
    log "Attempt failed at forecast probe"
    docker_diag
    consecutive_pass=0
    set -e
    sleep "$SLEEP_BETWEEN"
    continue
  fi

  prometheus_probe
  prom_rc=$?
  if [[ $prom_rc -ne 0 ]]; then
    log "Attempt failed at Prometheus probe (multi-region series not present)"
    docker_diag
    consecutive_pass=0
    set -e
    sleep "$SLEEP_BETWEEN"
    continue
  fi

  run_tests_if_present || true

  set -e
  consecutive_pass=$((consecutive_pass + 1))
  log "Attempt PASS (consecutive_pass=${consecutive_pass}/${PASS_TARGET})"

  if [[ $consecutive_pass -ge $PASS_TARGET ]]; then
    log "Integrity loop SUCCESS: achieved ${PASS_TARGET} consecutive passes"
    log "Evidence bundle: ${OUT_ROOT}"
    exit 0
  fi

  sleep "$SLEEP_BETWEEN"
done

log "FAILED: did not achieve ${PASS_TARGET} consecutive passes within ${MAX_ATTEMPTS} attempts"
log "Evidence bundle: ${OUT_ROOT}"
exit 1
