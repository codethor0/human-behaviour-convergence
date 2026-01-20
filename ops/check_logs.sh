#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Scan logs for critical errors (Exception, Timeout, Registry Error).
# Inspired by DevOps-Bash-tools log scanning patterns.
#
# Usage:
#   ./ops/check_logs.sh [log_file] [--fail-on-errors]
#
# Defaults:
#   log_file: app.log (or first .log file found)
#   --fail-on-errors: Exit with non-zero code if errors found (for CI)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_FILE="${1:-}"
FAIL_ON_ERRORS=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --fail-on-errors)
            FAIL_ON_ERRORS=true
            shift
            ;;
        *)
            if [ -z "${LOG_FILE}" ]; then
                LOG_FILE="$1"
            fi
            shift
            ;;
    esac
done

cd "${REPO_ROOT}"

# Find log file if not specified
if [ -z "${LOG_FILE}" ]; then
    if [ -f "app.log" ]; then
        LOG_FILE="app.log"
    elif [ -d "logs" ]; then
        LOG_FILE=$(find logs -name "*.log" -type f | head -1)
    else
        echo "❌ No log file found. Specify a log file or ensure app.log exists."
        exit 1
    fi
fi

if [ ! -f "${LOG_FILE}" ]; then
    echo "❌ Log file not found: ${LOG_FILE}"
    exit 1
fi

echo "Scanning ${LOG_FILE} for critical errors..."
echo ""

# Scan for critical error patterns
ERROR_PATTERNS=(
    "Exception"
    "Timeout"
    "Registry Error"
    "CRITICAL"
    "Traceback"
    "Failed to"
)

ERRORS_FOUND=0
ERROR_DETAILS=()

for pattern in "${ERROR_PATTERNS[@]}"; do
    count=$(grep -iE "${pattern}" "${LOG_FILE}" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
    if [ "${count}" -gt 0 ]; then
        ERRORS_FOUND=$((ERRORS_FOUND + count))
        ERROR_DETAILS+=("${pattern}: ${count} occurrences")

        # Show sample lines for context
        echo "⚠️  ${pattern}: ${count} occurrence(s)"
        grep -iE "${pattern}" "${LOG_FILE}" 2>/dev/null | head -3 | sed 's/^/    /' || true
        echo ""
    fi
done

# Summary
echo "============================================================"
if [ ${ERRORS_FOUND} -eq 0 ]; then
    echo "✅ No critical errors found in logs"
    exit 0
else
    echo "❌ Found ${ERRORS_FOUND} error-like log entries"
    echo ""
    echo "Error summary:"
    for detail in "${ERROR_DETAILS[@]}"; do
        echo "  - ${detail}"
    done
    echo ""
    echo "Run: ./ops/collect_support_bundle.sh for diagnostics"

    if [ "${FAIL_ON_ERRORS}" = "true" ]; then
        exit 1
    else
        exit 0
    fi
fi
