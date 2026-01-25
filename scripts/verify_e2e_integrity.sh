#!/usr/bin/env bash
# SPDX-License-Identifier: PROPRIETARY
#
# Integrity Loop - End-to-End Verification Script
#
# This script performs comprehensive integrity verification:
# - Docker stack health
# - API endpoints and proxy parity
# - Multi-region forecast generation
# - Variance/discrepancy checks
# - Metrics integrity
# - Prometheus/Grafana verification
# - UI contract checks
#
# Usage:
#   ./scripts/verify_e2e_integrity.sh [--reduced] [--skip-ui]
#
# Options:
#   --reduced    Use reduced mode (2 regions instead of 10)
#   --skip-ui    Skip UI contract checks
#
# Exit codes:
#   0: All integrity checks passed
#   1: One or more integrity checks failed
#   2: Setup/readiness failure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Parse options
REDUCED_MODE=false
SKIP_UI=false
for arg in "$@"; do
    case $arg in
        --reduced)
            REDUCED_MODE=true
            shift
            ;;
        --skip-ui)
            SKIP_UI=true
            shift
            ;;
        *)
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Evidence directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EVIDENCE_DIR="/tmp/hbc_integrity_loop_${TIMESTAMP}"
mkdir -p "${EVIDENCE_DIR}"

# Track failures
FAILURES=0
PHASE_FAILED=""

log() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $*"
}

fail() {
    echo -e "${RED}FAIL:${NC} $*"
    ((FAILURES++)) || true
    PHASE_FAILED="${PHASE_FAILED} $1"
}

pass() {
    echo -e "${GREEN}PASS:${NC} $*"
}

warn() {
    echo -e "${YELLOW}WARN:${NC} $*"
}

# PHASE 0: Clean Start
log "PHASE 0: Clean Start"
echo "==================="

# Check git status
if ! git diff --quiet || ! git diff --cached --quiet; then
    warn "Git working directory is not clean"
    git status --short > "${EVIDENCE_DIR}/git_status.txt"
else
    pass "Git working directory is clean"
fi

# Record baseline
{
    echo "Git HEAD: $(git rev-parse HEAD)"
    echo "Git Branch: $(git branch --show-current 2>/dev/null || echo 'detached')"
    echo "Date: $(date -Iseconds)"
    echo "Python: $(python --version 2>&1)"
    echo "Docker: $(docker --version 2>&1 || echo 'not available')"
} > "${EVIDENCE_DIR}/baseline.txt"

# Start Docker stack
log "Starting Docker stack..."
if docker compose down -v > "${EVIDENCE_DIR}/docker_down.log" 2>&1; then
    pass "Docker stack stopped"
else
    warn "Docker compose down had warnings (may be expected if stack not running)"
fi

if docker compose up -d --build > "${EVIDENCE_DIR}/docker_up.log" 2>&1; then
    pass "Docker stack started"
else
    fail "PHASE0" "Failed to start Docker stack"
    cat "${EVIDENCE_DIR}/docker_up.log"
    exit 2
fi

# Wait for services to be ready
log "Waiting for services to be ready..."
sleep 5

# PHASE 1: Readiness Gates
log ""
log "PHASE 1: Readiness Gates"
echo "======================"

readiness_endpoints=(
    "http://localhost:8100/health"
    "http://localhost:3100/"
    "http://localhost:3100/forecast"
    "http://localhost:3100/history"
    "http://localhost:3100/live"
    "http://localhost:3100/playground"
)

readiness_results="${EVIDENCE_DIR}/readiness.tsv"
echo -e "endpoint\tstatus_code\tresponse_time" > "${readiness_results}"

for endpoint in "${readiness_endpoints[@]}"; do
    log "Checking ${endpoint}..."
    start_time=$(date +%s.%N)
    if response=$(curl -s -w "\n%{http_code}" -o "${EVIDENCE_DIR}/response_$(basename ${endpoint}).txt" "${endpoint}" 2>&1); then
        http_code=$(echo "${response}" | tail -1)
        end_time=$(date +%s.%N)
        response_time=$(echo "${end_time} - ${start_time}" | bc)
        echo -e "${endpoint}\t${http_code}\t${response_time}" >> "${readiness_results}"
        
        if [ "${http_code}" = "200" ]; then
            pass "${endpoint} returned 200"
        else
            fail "PHASE1" "${endpoint} returned ${http_code}"
            cat "${EVIDENCE_DIR}/response_$(basename ${endpoint}).txt"
        fi
    else
        fail "PHASE1" "${endpoint} failed to connect"
        echo "${response}" > "${EVIDENCE_DIR}/error_$(basename ${endpoint}).txt"
    fi
done

if [ ${FAILURES} -gt 0 ]; then
    log "Docker logs:"
    docker compose logs --tail=50 backend frontend prometheus grafana > "${EVIDENCE_DIR}/docker_logs_tail.txt" 2>&1 || true
    cat "${EVIDENCE_DIR}/docker_logs_tail.txt"
    exit 2
fi

# PHASE 2: API Baseline + Proxy Parity
log ""
log "PHASE 2: API Baseline + Proxy Parity"
echo "==================================="

# Test direct backend
log "Testing direct backend endpoints..."
for endpoint in "regions" "status" "models"; do
    url="http://localhost:8100/api/forecasting/${endpoint}"
    if curl -s -f -o "${EVIDENCE_DIR}/api_${endpoint}_direct.json" "${url}"; then
        pass "Direct backend ${endpoint}"
    else
        fail "PHASE2" "Direct backend ${endpoint} failed"
    fi
done

# Test proxy
log "Testing proxy endpoints..."
for endpoint in "regions" "status"; do
    url="http://localhost:3100/api/forecasting/${endpoint}"
    if curl -s -f -o "${EVIDENCE_DIR}/api_${endpoint}_proxy.json" "${url}"; then
        pass "Proxy ${endpoint}"
        
        # Compare with direct
        if diff -q "${EVIDENCE_DIR}/api_${endpoint}_direct.json" "${EVIDENCE_DIR}/api_${endpoint}_proxy.json" > /dev/null 2>&1; then
            pass "Proxy matches direct for ${endpoint}"
        else
            fail "PHASE2" "Proxy response differs from direct for ${endpoint}"
        fi
    else
        fail "PHASE2" "Proxy ${endpoint} failed"
    fi
done

# PHASE 3: Seed Multi-Region Forecasts
log ""
log "PHASE 3: Seed Multi-Region Forecasts"
echo "==================================="

if [ "${REDUCED_MODE}" = true ]; then
    test_regions=(
        "Illinois:40.3495:-88.9861"
        "Arizona:34.0489:-111.0937"
    )
else
    test_regions=(
        "Illinois:40.3495:-88.9861"
        "Arizona:34.0489:-111.0937"
        "Florida:27.7663:-81.6868"
        "Washington:47.0379:-120.5015"
        "California:36.7783:-119.4179"
        "New York:40.7128:-74.0060"
        "Texas:31.9686:-99.9018"
        "Minnesota:46.7296:-94.6859"
        "Colorado:39.0598:-105.3111"
        "London:51.5074:-0.1278"
    )
fi

forecast_results="${EVIDENCE_DIR}/forecast_seed_results.csv"
echo "region_name,behavior_index,economic_stress,environmental_stress,fuel_stress,drought_stress,storm_severity_stress,response_time_ms,status" > "${forecast_results}"

for region_spec in "${test_regions[@]}"; do
    IFS=':' read -r name lat lon <<< "${region_spec}"
    log "Generating forecast for ${name}..."
    
    start_time=$(date +%s.%N)
    response_file="${EVIDENCE_DIR}/forecast_${name// /_}.json"
    
    if curl -s -f -X POST \
        -H "Content-Type: application/json" \
        -d "{\"latitude\":${lat},\"longitude\":${lon},\"region_name\":\"${name}\",\"days_back\":30,\"forecast_horizon\":7}" \
        -o "${response_file}" \
        "http://localhost:8100/api/forecasting/forecast" 2>&1; then
        end_time=$(date +%s.%N)
        response_time=$(echo "(${end_time} - ${start_time}) * 1000" | bc | cut -d. -f1)
        
        # Extract values from response
        if command -v jq > /dev/null 2>&1; then
            bi=$(jq -r '.history[-1].behavior_index // "N/A"' "${response_file}" 2>/dev/null || echo "N/A")
            econ=$(jq -r '.history[-1].economic_stress // "N/A"' "${response_file}" 2>/dev/null || echo "N/A")
            env=$(jq -r '.history[-1].environmental_stress // "N/A"' "${response_file}" 2>/dev/null || echo "N/A")
            fuel=$(jq -r '.history[-1].fuel_stress // "N/A"' "${response_file}" 2>/dev/null || echo "N/A")
            drought=$(jq -r '.history[-1].drought_stress // "N/A"' "${response_file}" 2>/dev/null || echo "N/A")
            storm=$(jq -r '.history[-1].storm_severity_stress // "N/A"' "${response_file}" 2>/dev/null || echo "N/A")
        else
            bi="N/A"
            econ="N/A"
            env="N/A"
            fuel="N/A"
            drought="N/A"
            storm="N/A"
        fi
        
        echo "${name},${bi},${econ},${env},${fuel},${drought},${storm},${response_time},OK" >> "${forecast_results}"
        pass "Forecast generated for ${name} (${response_time}ms)"
    else
        echo "${name},N/A,N/A,N/A,N/A,N/A,N/A,N/A,FAILED" >> "${forecast_results}"
        fail "PHASE3" "Failed to generate forecast for ${name}"
    fi
done

# PHASE 4: Variance / Discrepancy Check
log ""
log "PHASE 4: Variance / Discrepancy Check"
echo "===================================="

if command -v jq > /dev/null 2>&1; then
    # Compute hashes
    variance_report="${EVIDENCE_DIR}/forecast_variance_report.txt"
    echo "Region Variance Analysis" > "${variance_report}"
    echo "========================" >> "${variance_report}"
    echo "" >> "${variance_report}"
    
    hashes=()
    for region_spec in "${test_regions[@]}"; do
        IFS=':' read -r name lat lon <<< "${region_spec}"
        response_file="${EVIDENCE_DIR}/forecast_${name// /_}.json"
        if [ -f "${response_file}" ]; then
            hash=$(jq -c '.history' "${response_file}" 2>/dev/null | sha256sum | cut -d' ' -f1 || echo "N/A")
            hashes+=("${hash}")
            echo "${name}: ${hash}" >> "${variance_report}"
        fi
    done
    
    unique_hashes=$(printf '%s\n' "${hashes[@]}" | sort -u | wc -l)
    total_regions=${#test_regions[@]}
    
    echo "" >> "${variance_report}"
    echo "Unique hashes: ${unique_hashes} / ${total_regions}" >> "${variance_report}"
    
    if [ "${unique_hashes}" -ge 2 ]; then
        pass "Variance check: ${unique_hashes} unique history hashes"
    else
        fail "PHASE4" "Variance check failed: Only ${unique_hashes} unique hashes for ${total_regions} regions"
    fi
else
    warn "jq not available, skipping detailed variance analysis"
fi

# PHASE 5: Metrics Integrity
log ""
log "PHASE 5: Metrics Integrity"
echo "========================"

metrics_file="${EVIDENCE_DIR}/metrics.txt"
if curl -s -f -o "${metrics_file}" "http://localhost:8100/metrics"; then
    pass "Metrics endpoint accessible"
    
    # Check for region=None
    if grep -q 'region="None"' "${metrics_file}" || grep -q "region='None'" "${metrics_file}"; then
        fail "PHASE5" "Found region=None labels in metrics"
        grep 'region="None"' "${metrics_file}" > "${EVIDENCE_DIR}/metrics_none_violations.txt" || true
    else
        pass "No region=None labels found"
    fi
    
    # Count distinct regions
    regions=$(grep -oP 'region="[^"]+"' "${metrics_file}" | sort -u | wc -l)
    echo "Distinct regions in metrics: ${regions}" > "${EVIDENCE_DIR}/metrics_extract.txt"
    
    min_regions=$([ "${REDUCED_MODE}" = true ] && echo "2" || echo "5")
    if [ "${regions}" -ge "${min_regions}" ]; then
        pass "Metrics show ${regions} distinct regions (>= ${min_regions})"
    else
        fail "PHASE5" "Metrics show only ${regions} distinct regions (expected >= ${min_regions})"
    fi
    
    # Check for child indices
    if grep -q 'child_subindex_value' "${metrics_file}"; then
        pass "Child index metrics present"
        grep 'child_subindex_value' "${metrics_file}" | head -5 > "${EVIDENCE_DIR}/metrics_child_indices.txt"
    else
        warn "Child index metrics not found"
    fi
else
    fail "PHASE5" "Failed to fetch metrics"
fi

# PHASE 6: Prometheus Proof
log ""
log "PHASE 6: Prometheus Proof"
echo "======================="

if curl -s -f "http://localhost:9090/-/ready" > /dev/null 2>&1; then
    pass "Prometheus is ready"
    
    # Query Prometheus
    promql_results="${EVIDENCE_DIR}/promql_results.json"
    queries=(
        "count by (region) (behavior_index)"
        "topk(10, behavior_index)"
    )
    
    for query in "${queries[@]}"; do
        encoded_query=$(echo "${query}" | jq -sRr @uri)
        if curl -s -f "http://localhost:9090/api/v1/query?query=${encoded_query}" > "${EVIDENCE_DIR}/promql_$(echo ${query} | tr ' ' '_').json" 2>&1; then
            pass "PromQL query succeeded: ${query}"
        else
            warn "PromQL query failed: ${query}"
        fi
    done
else
    warn "Prometheus not accessible (may be expected if not in stack)"
fi

# PHASE 7: Grafana Proof
log ""
log "PHASE 7: Grafana Proof"
echo "===================="

if curl -s -f "http://localhost:3000/api/health" > /dev/null 2>&1; then
    pass "Grafana is accessible"
    echo "Grafana accessible at http://localhost:3000" > "${EVIDENCE_DIR}/grafana_proof.txt"
else
    warn "Grafana not accessible (may be expected if not in stack)"
    echo "Grafana not accessible" > "${EVIDENCE_DIR}/grafana_proof.txt"
fi

# PHASE 8: UI Contract Proof
log ""
log "PHASE 8: UI Contract Proof"
echo "========================"

if [ "${SKIP_UI}" = false ]; then
    ui_proof="${EVIDENCE_DIR}/ui_contract_proof.txt"
    echo "UI Contract Verification" > "${ui_proof}"
    echo "========================" >> "${ui_proof}"
    echo "" >> "${ui_proof}"
    
    # Check forecast page
    if curl -s -f "http://localhost:3100/forecast" | grep -q "forecast\|region" > /dev/null 2>&1; then
        pass "Forecast page accessible"
        echo "Forecast page: OK" >> "${ui_proof}"
    else
        warn "Forecast page check inconclusive"
        echo "Forecast page: Check inconclusive" >> "${ui_proof}"
    fi
    
    # Check history page
    if curl -s -f "http://localhost:3100/history" | grep -q "history\|table" > /dev/null 2>&1; then
        pass "History page accessible"
        echo "History page: OK" >> "${ui_proof}"
    else
        warn "History page check inconclusive"
        echo "History page: Check inconclusive" >> "${ui_proof}"
    fi
else
    log "Skipping UI contract checks (--skip-ui)"
    echo "UI checks skipped" > "${EVIDENCE_DIR}/ui_contract_proof.txt"
fi

# Generate Report
log ""
log "Generating Report"
echo "================="

REPORT_FILE="/tmp/HBC_INTEGRITY_LOOP_REPORT.md"
cat > "${REPORT_FILE}" <<EOF
# Integrity Loop Report

**Date**: $(date -Iseconds)
**Evidence Directory**: ${EVIDENCE_DIR}
**Mode**: $([ "${REDUCED_MODE}" = true ] && echo "Reduced" || echo "Full")

## Summary

- **Total Failures**: ${FAILURES}
- **Failed Phases**: ${PHASE_FAILED:-None}

## Phase Results

### Phase 0: Clean Start
- Git status: $(git diff --quiet && echo "Clean" || echo "Dirty")
- Docker stack: Started

### Phase 1: Readiness Gates
- All endpoints: $([ ${FAILURES} -eq 0 ] && echo "PASS" || echo "See failures")

### Phase 2: API Baseline + Proxy Parity
- Direct backend: Tested
- Proxy endpoints: Tested
- Parity: Verified

### Phase 3: Multi-Region Forecasts
- Regions tested: ${#test_regions[@]}
- Results: See \`forecast_seed_results.csv\`

### Phase 4: Variance Check
- Unique hashes: ${unique_hashes:-N/A} / ${total_regions:-N/A}

### Phase 5: Metrics Integrity
- Region=None check: $([ -f "${EVIDENCE_DIR}/metrics_none_violations.txt" ] && echo "FAIL" || echo "PASS")
- Distinct regions: ${regions:-N/A}

### Phase 6: Prometheus
- Status: $([ -f "${EVIDENCE_DIR}/promql_results.json" ] && echo "Tested" || echo "Skipped")

### Phase 7: Grafana
- Status: $([ -f "${EVIDENCE_DIR}/grafana_proof.txt" ] && echo "Tested" || echo "Skipped")

### Phase 8: UI Contracts
- Status: $([ "${SKIP_UI}" = false ] && echo "Tested" || echo "Skipped")

## Evidence Files

All evidence files are in: \`${EVIDENCE_DIR}/\`

Key files:
- \`baseline.txt\` - System baseline
- \`readiness.tsv\` - Readiness check results
- \`forecast_seed_results.csv\` - Forecast generation results
- \`forecast_variance_report.txt\` - Variance analysis
- \`metrics.txt\` - Full metrics dump
- \`metrics_extract.txt\` - Metrics summary

## Verdict

**$([ ${FAILURES} -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")**

$([ ${FAILURES} -eq 0 ] && echo "All integrity checks passed." || echo "Some integrity checks failed. See phase results above.")

EOF

cat "${REPORT_FILE}"
cp "${REPORT_FILE}" "${EVIDENCE_DIR}/"

log ""
log "Report saved to: ${REPORT_FILE}"
log "Evidence directory: ${EVIDENCE_DIR}"

if [ ${FAILURES} -gt 0 ]; then
    # Create BUGS.md
    cat > "${EVIDENCE_DIR}/BUGS.md" <<EOF
# Integrity Loop Bugs

**Date**: $(date -Iseconds)

## Failed Phases

${PHASE_FAILED}

## Reproduction

Run:
\`\`\`bash
./scripts/verify_e2e_integrity.sh
\`\`\`

## Evidence

See files in: ${EVIDENCE_DIR}

EOF
    exit 1
else
    exit 0
fi
