#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Collect support bundle for forecasting app diagnostics.
# Inspired by DevOps-Bash-tools monitoring/dump_stats.sh pattern.
#
# Usage:
#   ./ops/collect_support_bundle.sh [output_dir]
#
# Collects:
#   - System stats (CPU, RAM, disk, processes)
#   - Forecast app logs
#   - Recent forecast responses for key regions
#   - Integrity metadata snapshots
#   - Calibration config state
#
# Output: support_bundle_<timestamp>.tar.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${1:-${REPO_ROOT}/ops/support_bundles}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BUNDLE_NAME="support_bundle_${TIMESTAMP}"
BUNDLE_DIR="${OUTPUT_DIR}/${BUNDLE_NAME}"

mkdir -p "${BUNDLE_DIR}"
cd "${REPO_ROOT}"

echo "Collecting support bundle: ${BUNDLE_NAME}"

# System stats
echo "  - Collecting system stats..."
{
    echo "=== CPU Info ==="
    lscpu 2>/dev/null || sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "CPU info unavailable"
    echo ""
    echo "=== Memory Info ==="
    free -h 2>/dev/null || vm_stat 2>/dev/null || echo "Memory info unavailable"
    echo ""
    echo "=== Disk Usage ==="
    df -h 2>/dev/null || echo "Disk info unavailable"
    echo ""
    echo "=== Process List (forecast-related) ==="
    ps aux | grep -E "(python|forecast|hbc)" | grep -v grep || echo "No forecast processes found"
} > "${BUNDLE_DIR}/system_stats.txt" 2>&1

# App logs (if available)
echo "  - Collecting app logs..."
if [ -d "logs" ]; then
    find logs -type f -name "*.log" -mtime -7 -exec cp {} "${BUNDLE_DIR}/" \;
elif [ -f "app.log" ]; then
    tail -n 1000 app.log > "${BUNDLE_DIR}/app.log.tail" 2>/dev/null || true
fi

# Recent forecast responses (if API is running)
echo "  - Collecting forecast snapshots..."
FORECAST_REGIONS=("Minnesota:46.7296:-94.6859" "New York:40.7128:-74.0060" "California:34.0522:-118.2437")
for region_spec in "${FORECAST_REGIONS[@]}"; do
    IFS=':' read -r name lat lon <<< "${region_spec}"
    echo "    - ${name}..."
    curl -s -X POST http://localhost:8100/api/forecast \
        -H "Content-Type: application/json" \
        -d "{\"region_name\":\"${name}\",\"latitude\":${lat},\"longitude\":${lon},\"days_back\":7,\"forecast_horizon\":7}" \
        > "${BUNDLE_DIR}/forecast_${name// /_}.json" 2>/dev/null || \
        echo "{\"error\":\"API unavailable\"}" > "${BUNDLE_DIR}/forecast_${name// /_}.json"
done

# Calibration config state
echo "  - Collecting calibration config..."
if [ -f "app/services/calibration/config.py" ]; then
    cp app/services/calibration/config.py "${BUNDLE_DIR}/config.py"
    python3 -c "
from app.services.calibration.config import (
    BEHAVIOR_INDEX_WEIGHTS, SHOCK_MULTIPLIER, REALITY_BLEND_WEIGHTS
)
import json
print(json.dumps({
    'behavior_index_weights': BEHAVIOR_INDEX_WEIGHTS,
    'shock_multiplier': SHOCK_MULTIPLIER,
    'reality_blend_weights': REALITY_BLEND_WEIGHTS,
}, indent=2))
" > "${BUNDLE_DIR}/config_state.json" 2>/dev/null || echo "{\"error\":\"Config load failed\"}" > "${BUNDLE_DIR}/config_state.json"
fi

# Integrity metadata summary
echo "  - Collecting integrity metadata..."
python3 << 'PYTHON_EOF' > "${BUNDLE_DIR}/integrity_summary.txt" 2>&1 || true
import json
import glob
import os

print("=== Integrity Metadata Summary ===\n")

# Scan forecast JSON files for integrity flags
forecast_files = glob.glob("${BUNDLE_DIR}/forecast_*.json")
for fpath in forecast_files:
    try:
        with open(fpath, 'r') as f:
            data = json.load(f)
            region = os.path.basename(fpath).replace('forecast_', '').replace('.json', '')
            print(f"\nRegion: {region}")
            if 'metadata' in data and 'integrity' in data['metadata']:
                integrity = data['metadata']['integrity']
                print(f"  Shock multiplier applied: {integrity.get('shock_multiplier_applied', False)}")
                if integrity.get('shock_multiplier_applied'):
                    print(f"    Shock count: {integrity.get('shock_count', 'N/A')}")
                    print(f"    Multiplier: {integrity.get('shock_multiplier_value', 'N/A')}")
                if 'synthetic_usage' in integrity:
                    print(f"  Synthetic usage: {integrity['synthetic_usage']}")
            if 'risk_tier' in data:
                tier = data['risk_tier']
                print(f"  Risk tier: {tier.get('tier', 'N/A')}")
                print(f"  Risk score: {tier.get('risk_score', 'N/A')}")
    except Exception as e:
        print(f"  Error reading {fpath}: {e}")
PYTHON_EOF

# Git state (if in repo)
echo "  - Collecting git state..."
if [ -d ".git" ]; then
    {
        echo "=== Git Status ==="
        git status --short || true
        echo ""
        echo "=== Recent Commits ==="
        git log --oneline -10 || true
        echo ""
        echo "=== Current Branch ==="
        git branch --show-current || true
    } > "${BUNDLE_DIR}/git_state.txt" 2>&1
fi

# Environment info
echo "  - Collecting environment info..."
{
    echo "=== Python Version ==="
    python3 --version || echo "Python unavailable"
    echo ""
    echo "=== Installed Packages (forecast-related) ==="
    pip list | grep -E "(pandas|numpy|requests|structlog)" || echo "pip list unavailable"
    echo ""
    echo "=== Environment Variables (HBC-related) ==="
    env | grep -E "(HBC|FORECAST|API)" || echo "No HBC env vars found"
} > "${BUNDLE_DIR}/environment.txt" 2>&1

# Create tarball
echo "  - Creating tarball..."
cd "${OUTPUT_DIR}"
tar -czf "${BUNDLE_NAME}.tar.gz" "${BUNDLE_NAME}" 2>/dev/null || \
    (cd "${BUNDLE_DIR}" && tar -czf "../${BUNDLE_NAME}.tar.gz" .)

# Cleanup temp directory
rm -rf "${BUNDLE_DIR}"

echo ""
echo "Support bundle created: ${OUTPUT_DIR}/${BUNDLE_NAME}.tar.gz"
echo "  Size: $(du -h "${OUTPUT_DIR}/${BUNDLE_NAME}.tar.gz" | cut -f1)"
