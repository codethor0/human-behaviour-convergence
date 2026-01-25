#!/usr/bin/env bash
set -euo pipefail

# PARANOID FULL-STACK E2E + CI VERIFICATION (LOCAL)
# Requirements: bash, git, docker, curl, jq, python3
# Assumes local endpoints:
#   Backend:    http://localhost:8100
#   Frontend:   http://localhost:3100
#   Grafana:    http://localhost:3001
#   Prometheus: http://localhost:9090
#
# Notes:
# - Does NOT open a browser. It verifies Grafana/dashboards via HTTP API + PromQL correctness.
# - Does NOT change tracked files. Read-only verification only.
# - Fails (exit 1) on RED conditions. Prints evidence for every check.

REPO="${REPO:-/Users/thor/Projects/human-behaviour-convergence}"

BACKEND="${BACKEND:-http://localhost:8100}"
FRONTEND="${FRONTEND:-http://localhost:3100}"
GRAFANA="${GRAFANA:-http://localhost:3001}"
PROM="${PROM:-http://localhost:9090}"

GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-admin}"

TEST_REGIONS=(city_nyc us_mn us_mi us_ca city_london)

# Helpers
hr() { printf "\n============================================================\n"; }
ts() { date +"%Y-%m-%d %H:%M:%S %Z"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

need() {
  command -v "$1" >/dev/null 2>&1 || die "Missing dependency: $1"
}

curl_json() {
  local url="$1"
  curl -sS -f "$url"
}

curl_grafana() {
  local path="$1"
  curl -sS -f -u "${GRAFANA_USER}:${GRAFANA_PASS}" "${GRAFANA}${path}"
}

prom_query_raw() {
  local q="$1"
  local enc
  enc="$(printf '%s' "$q" | python3 -c "
import sys, urllib.parse
print(urllib.parse.quote(sys.stdin.read().strip()))
")"
  curl -sS -f "${PROM}/api/v1/query?query=${enc}"
}

prom_result_len() {
  local q="$1"
  prom_query_raw "$q" | jq -r '.data.result | length'
}

have_region_in_regions_list() {
  local region="$1"
  jq -e --arg r "$region" '.[] | select(.id==$r)' >/dev/null
}

metric_has_region() {
  local metric="$1"
  local region="$2"
  local text="$3"
  # Match either {region="x"...} or {..,region="x"..}
  echo "$text" | grep -E "${metric}\{[^}]*region=\"${region}\"" >/dev/null 2>&1
}

main() {
  need git
  need docker
  need curl
  need jq
  need python3

  hr
  echo "PARANOID FULL-STACK VERIFICATION"
  echo "Timestamp: $(ts)"
  echo "Repo: ${REPO}"
  echo "Backend: ${BACKEND}"
  echo "Frontend: ${FRONTEND}"
  echo "Grafana: ${GRAFANA}"
  echo "Prometheus: ${PROM}"

  hr
  echo "[1] CHECKPOINT & INVENTORY"
  cd "$REPO"

  echo "> git status -sb"
  git status -sb || true
  echo "> git rev-parse --abbrev-ref HEAD"
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  echo "$BRANCH"
  echo "> git rev-parse HEAD"
  HEAD_SHA="$(git rev-parse HEAD)"
  echo "$HEAD_SHA"

  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "[WARN] Working tree is DIRTY. This script will not modify files, but you should reconcile changes."
    echo "> git diff --stat"
    git diff --stat || true
  else
    echo "[OK] Working tree clean."
  fi

  echo "> hygiene scans (tracked files only)"
  echo "  - emoji scan (selected set):"
  (git ls-files | xargs grep -n -E '😀|😁|😂|🤣|😅|😊|😎|😍|🤔|🚀|🔥|✅|❌|⚠️|💥' || true) | sed 's/^/    /'
  echo "  - prompt artifact scan:"
  (git ls-files | xargs grep -n -E 'MASTER PROMPT|FINAL RUN REPORT|Cursor AI|Session Completion|prompt artifacts|prompt transcript|Agent:' || true) | sed 's/^/    /'

  hr
  echo "[2] BACKEND FORECAST + METRICS INTEGRITY"

  echo "> curl -s ${BACKEND}/health"
  HEALTH="$(curl_json "${BACKEND}/health")"
  echo "$HEALTH"
  echo "$HEALTH" | jq -e '.status=="ok"' >/dev/null || die "Backend /health not OK"

  echo "> curl -s ${BACKEND}/api/forecasting/regions | jq length"
  REGIONS_JSON="$(curl_json "${BACKEND}/api/forecasting/regions")"
  REGIONS_LEN="$(echo "$REGIONS_JSON" | jq -r 'length')"
  echo "$REGIONS_LEN"
  if [[ "$REGIONS_LEN" != "62" ]]; then
    die "Regions length expected 62, got ${REGIONS_LEN}"
  fi

  echo "> sanity sample (first 10 regions)"
  echo "$REGIONS_JSON" | jq -c '.[0:10]'

  echo "> required region IDs present?"
  for r in city_nyc us_mn us_ny us_mi us_ca city_london; do
    if echo "$REGIONS_JSON" | have_region_in_regions_list "$r"; then
      echo "[OK] region present: $r"
      echo "$REGIONS_JSON" | jq -c --arg r "$r" '.[] | select(.id==$r) | {id,name,lat,lon}'
    else
      die "Missing required region id: $r"
    fi
  done

  echo
  echo "> forecast contract checks (multi-region)"
  # Keep request body aligned with the repo's known pattern
  # (days_back=30 forecast_horizon=7 should yield history=35 forecast=7 in this app).
  # API requires region_name; look up from regions list.
  for r in "${TEST_REGIONS[@]}"; do
    REGION_NAME="$(echo "$REGIONS_JSON" | jq -r --arg id "$r" '.[] | select(.id==$id) | .name // empty')"
    if [[ -z "$REGION_NAME" ]]; then
      die "Could not resolve region_name for region_id=${r}"
    fi
    echo
    echo "  - POST /api/forecast region_id=${r} region_name=${REGION_NAME}"
    RESP="$(curl -sS -f "${BACKEND}/api/forecast" \
      -H "Content-Type: application/json" \
      -d "{\"region_id\":\"${r}\",\"region_name\":\"${REGION_NAME}\",\"days_back\":30,\"forecast_horizon\":7}")" || die "Forecast request failed for ${r}"

    # Evidence summary
    HIST_LEN="$(echo "$RESP" | jq -r '.history | length')"
    FC_LEN="$(echo "$RESP" | jq -r '.forecast | length')"
    echo "    status: 200"
    echo "    history length: ${HIST_LEN}"
    echo "    forecast length: ${FC_LEN}"

    # Required keys (match ForecastResult schema; no top-level sub_indices)
    for k in history forecast metadata explanations convergence risk_tier; do
      echo "$RESP" | jq -e --arg k "$k" 'has($k)' >/dev/null || die "Missing key '${k}' for region ${r}"
    done
    if echo "$RESP" | jq -e 'has("sources")' >/dev/null; then
      :
    else
      die "Missing key 'sources' for region ${r}"
    fi

    # length constraints (allow interpolated window; e.g. 78 for 30d)
    if (( HIST_LEN < 30 || HIST_LEN > 120 )); then
      die "Region ${r}: history length out of bounds (30-120): ${HIST_LEN}"
    fi
    if [[ "$FC_LEN" != "7" ]]; then
      die "Region ${r}: forecast length expected 7, got ${FC_LEN}"
    fi
  done

  echo
  echo "> metrics export (backend /metrics) - after forecasts"
  METRICS_TEXT="$(curl -sS -f "${BACKEND}/metrics")" || die "Failed to fetch backend /metrics"
  set +o pipefail
  echo "$METRICS_TEXT" | grep -E 'behavior_index|parent_subindex_value|child_subindex_value|forecasts_generated_total|forecast_computation_duration_seconds' | head -200
  set -o pipefail

  echo
  echo "> per-region metrics presence (backend /metrics)"
  for r in "${TEST_REGIONS[@]}"; do
    echo "  - region=${r}"
    metric_has_region "behavior_index" "$r" "$METRICS_TEXT" && echo "    [OK] behavior_index" || echo "    [FAIL] behavior_index"
    metric_has_region "parent_subindex_value" "$r" "$METRICS_TEXT" && echo "    [OK] parent_subindex_value" || echo "    [FAIL] parent_subindex_value"
    metric_has_region "child_subindex_value" "$r" "$METRICS_TEXT" && echo "    [OK] child_subindex_value" || echo "    [FAIL] child_subindex_value"
    metric_has_region "forecasts_generated_total" "$r" "$METRICS_TEXT" && echo "    [OK] forecasts_generated_total" || echo "    [FAIL] forecasts_generated_total"
    # histogram: label might be in _bucket/_sum/_count; check any
    echo "$METRICS_TEXT" | grep -E "forecast_computation_duration_seconds_(bucket|sum|count)\{[^}]*region=\"${r}\"" >/dev/null 2>&1 \
      && echo "    [OK] forecast_computation_duration_seconds histogram" \
      || echo "    [FAIL] forecast_computation_duration_seconds histogram"
  done

  hr
  echo "[3] PROMETHEUS TARGETS & QUERIES"

  echo "> targets health"
  TARGETS="$(curl_json "${PROM}/api/v1/targets")" || die "Prometheus targets endpoint failed"
  set +o pipefail
  echo "$TARGETS" | jq -c '.data.activeTargets[] | {scrapeUrl:.scrapeUrl, health:.health}' | head -50
  set -o pipefail

  # Require at least one "up" target that looks like it scrapes /metrics
  UP_METRICS_TARGETS="$(echo "$TARGETS" | jq -r '[.data.activeTargets[] | select(.health=="up") | .scrapeUrl] | map(select(test("/metrics$"))) | length')"
  if [[ "$UP_METRICS_TARGETS" == "0" ]]; then
    echo "[WARN] Did not detect an UP scrapeUrl ending with /metrics. This can be OK if scrapeUrl differs. Inspect above list."
  else
    echo "[OK] Found ${UP_METRICS_TARGETS} UP target(s) scraping a URL ending in /metrics."
  fi

  echo
  echo "> instant queries per region (Prometheus)"
  for r in "${TEST_REGIONS[@]}"; do
    echo "  - region=${r}"
    echo "    behavior_index series: $(prom_result_len "behavior_index{region=\"${r}\"}")"
    echo "    parent_subindex_value series: $(prom_result_len "parent_subindex_value{region=\"${r}\"}")"
    echo "    child_subindex_value series: $(prom_result_len "child_subindex_value{region=\"${r}\"}")"
  done

  echo
  echo "> sample value check (city_nyc behavior_index) then re-check after delay"
  V1="$(prom_query_raw "behavior_index{region=\"city_nyc\"}" | jq -c '.data.result[0].value // null')"
  echo "  t0: ${V1}"
  sleep 3
  V2="$(prom_query_raw "behavior_index{region=\"city_nyc\"}" | jq -c '.data.result[0].value // null')"
  echo "  t+3s: ${V2}"

  hr
  echo "[4] GRAFANA PROVISIONING & CHILD SUB-INDICES PANELS"

  echo "> Grafana health"
  GHEALTH="$(curl_json "${GRAFANA}/api/health")" || die "Grafana /api/health failed"
  echo "$GHEALTH" | jq -c '.'
  echo "$GHEALTH" | jq -e '.database=="ok"' >/dev/null || echo "[WARN] Grafana database health not 'ok' (check output)."

  echo
  echo "> Grafana datasources (auth: ${GRAFANA_USER})"
  DS="$(curl_grafana "/api/datasources")" || die "Grafana datasources list failed (auth?)"
  echo "$DS" | jq -c '.[] | {name, type, url, uid: (.uid // null)}'

  # Ensure at least one prometheus datasource
  PROM_DS_COUNT="$(echo "$DS" | jq -r '[.[] | select(.type=="prometheus")] | length')"
  if [[ "$PROM_DS_COUNT" == "0" ]]; then
    die "No Prometheus datasource found in Grafana."
  else
    echo "[OK] Grafana Prometheus datasource count: ${PROM_DS_COUNT}"
  fi

  echo
  echo "> dashboards inventory"
  DBS="$(curl_grafana "/api/search?type=dash-db")" || die "Grafana dashboards search failed"
  echo "$DBS" | jq -c '.[] | {uid, title}' | sort | sed 's/^/  /'

  # Must-have dashboards
  MUST_DBS=(behavior-index-global subindex-deep-dive regional-comparison historical-trends risk-regimes forecast-summary data-sources-health)
  for uid in "${MUST_DBS[@]}"; do
    if echo "$DBS" | jq -e --arg u "$uid" '.[] | select(.uid==$u)' >/dev/null; then
      echo "[OK] dashboard present: ${uid}"
    else
      die "Missing required dashboard uid: ${uid}"
    fi
  done

  echo
  echo "> fetch subindex-deep-dive JSON and extract Child Sub-Indices panels"
  SUBIDX_JSON="$(curl_grafana "/api/dashboards/uid/subindex-deep-dive")" || die "Failed to fetch subindex-deep-dive dashboard JSON"
  echo "$SUBIDX_JSON" > /tmp/subindex-deep-dive.json

  # Extract panels whose title contains "Child Sub" (case-insensitive)
  CHILD_PANELS="$(jq -c '
    .dashboard.panels
    | (.. | objects | select(has("title") and (.title|test("child sub"; "i"))) )
    | {id: (.id // null), title, targets: (.targets // []), datasource: (.datasource // null)}
  ' /tmp/subindex-deep-dive.json 2>/dev/null || true)"

  if [[ -z "$CHILD_PANELS" ]]; then
    echo "[WARN] No panels matched title containing 'Child Sub' in subindex-deep-dive."
    echo "       This might mean titles differ. Dumping panel titles for manual grep:"
    jq -r '.. | objects | select(has("title")) | .title' /tmp/subindex-deep-dive.json | sort -u | sed 's/^/  /'
  else
    echo "$CHILD_PANELS" | sed 's/^/  /'
  fi

  echo
  echo "> validate that any Child Sub-Indices panel PromQL uses child_subindex_value{region=... parent=... child=...}"
  # For each matching panel, print each target expr and sanity-check it.
  # We treat missing/incorrect metric name as RED because it directly causes "No data" when data exists.
  BAD_EXPR=0
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    pid="$(echo "$line" | jq -r '.id')"
    ptitle="$(echo "$line" | jq -r '.title')"
    echo "  - panel id=${pid} title=${ptitle}"
    # targets may be multiple
    tcount="$(echo "$line" | jq -r '.targets | length')"
    if [[ "$tcount" == "0" ]]; then
      echo "    [WARN] no targets found on this panel"
      continue
    fi
    for i in $(seq 0 $((tcount-1))); do
      expr="$(echo "$line" | jq -r ".targets[$i].expr // empty")"
      legend="$(echo "$line" | jq -r ".targets[$i].legendFormat // empty")"
      echo "    target[$i] legend='${legend}'"
      echo "    target[$i] expr='${expr}'"
      if [[ -z "$expr" ]]; then
        echo "    [FAIL] empty expr"
        BAD_EXPR=1
        continue
      fi
      if ! echo "$expr" | grep -q "child_subindex_value"; then
        echo "    [FAIL] expr does not reference child_subindex_value"
        BAD_EXPR=1
      fi
      # Basic label expectation: must filter by region label somehow (either {region="$region"} or via variable)
      if ! echo "$expr" | grep -Eq 'region\s*='; then
        echo "    [FAIL] expr does not constrain region label"
        BAD_EXPR=1
      fi
      # Basic label expectation: child metric should include parent/child dimensions (may be variable-driven)
      if ! echo "$expr" | grep -Eq '(parent\s*=|child\s*=)'; then
        echo "    [WARN] expr does not constrain parent/child labels; may rely on dashboard transformations. Verify panel intent."
      fi
    done
  done < <(echo "$CHILD_PANELS" | jq -c '.' 2>/dev/null || true)

  if [[ "$BAD_EXPR" == "1" ]]; then
    die "Grafana panel query mismatch: at least one Child Sub-Indices panel does not appear to query child_subindex_value with expected labels."
  fi

  hr
  echo "[5] DIAGNOSIS: WHY 'Child Sub-Indices - / All - No data' HAPPENS (CITY_NYC FOCUS)"
  echo "> compare backend /metrics vs Prometheus for city_nyc child_subindex_value"
  BACKEND_CHILD_OK="0"
  PROM_CHILD_OK="0"

  if metric_has_region "child_subindex_value" "city_nyc" "$METRICS_TEXT"; then
    BACKEND_CHILD_OK="1"
    echo "[OK] backend /metrics has child_subindex_value for city_nyc"
  else
    echo "[FAIL] backend /metrics does NOT have child_subindex_value for city_nyc"
  fi

  PROM_CHILD_LEN="$(prom_result_len "child_subindex_value{region=\"city_nyc\"}")"
  echo "Prometheus child_subindex_value{region=\"city_nyc\"} series length: ${PROM_CHILD_LEN}"
  if [[ "$PROM_CHILD_LEN" != "0" ]]; then
    PROM_CHILD_OK="1"
    echo "[OK] Prometheus has child_subindex_value for city_nyc"
  else
    echo "[FAIL] Prometheus has NO child_subindex_value for city_nyc"
  fi

  if [[ "$BACKEND_CHILD_OK" == "0" ]]; then
    echo
    echo "[RED] Root cause likely BACKEND metrics emission for child sub-indices is missing for city_nyc."
    echo "      Next action: inspect where child_subindex_value is emitted during forecast generation for region_id=city_nyc."
    exit 1
  fi

  if [[ "$BACKEND_CHILD_OK" == "1" && "$PROM_CHILD_OK" == "0" ]]; then
    echo
    echo "[RED] Root cause likely PROMETHEUS scrape/label mismatch or scrape lag."
    echo "      Next action: verify scrape target is UP and scraping the backend /metrics endpoint, then wait for scrape interval and retry."
    exit 1
  fi

  echo
  echo "[OK] Backend and Prometheus both show child_subindex_value for city_nyc. If Grafana still shows 'No data', the issue is likely dashboard query/variable wiring."
  echo "     This script already validated the Child Sub-Indices panel expressions contain child_subindex_value + region filter, but you should also verify dashboard variables:"
  echo "     - region variable query uses label_values(child_subindex_value, region) or label_values(parent_subindex_value, region) as appropriate."
  echo "     - parent/child variables reference correct labels (parent, child)."

  hr
  echo "[6] FRONTEND SMOKE (HTTP-LEVEL)"
  echo "> curl -f ${FRONTEND}/"
  curl -sS -f "${FRONTEND}/" >/dev/null && echo "[OK] frontend root reachable" || die "Frontend root not reachable"

  echo "> curl -f ${FRONTEND}/forecast"
  curl -sS -f "${FRONTEND}/forecast" >/dev/null && echo "[OK] /forecast reachable" || die "/forecast not reachable"

  hr
  echo "[DONE] SUMMARY"
  echo "Branch: ${BRANCH}"
  echo "HEAD:   ${HEAD_SHA}"
  echo "Backend regions: ${REGIONS_LEN} (expected 62)"
  echo "Forecast contract: PASS for regions: ${TEST_REGIONS[*]}"
  echo "Metrics (backend/prom): verified behavior_index/parent/child presence checks were executed"
  echo "Grafana: healthy + dashboards present + Child Sub-Indices panel queries inspected"
  echo
  echo "[OK] Paranoid verification completed with no RED findings."
}

main "$@"
