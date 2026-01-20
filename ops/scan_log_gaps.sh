#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Scan logs for large time gaps (indicating hangs, stuck workers, or missing runs).
# Inspired by DevOps-Bash-tools monitoring/log_timestamp_large_intervals.sh.
#
# Usage:
#   ./ops/scan_log_gaps.sh [log_file] [max_gap_seconds]
#
# Defaults:
#   log_file: app.log (or first .log file found)
#   max_gap_seconds: 300 (5 minutes)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_FILE="${1:-}"
MAX_GAP_SECONDS="${2:-300}"

cd "${REPO_ROOT}"

# Find log file if not specified
if [ -z "${LOG_FILE}" ]; then
    if [ -f "app.log" ]; then
        LOG_FILE="app.log"
    elif [ -d "logs" ]; then
        LOG_FILE=$(find logs -name "*.log" -type f | head -1)
    else
        echo "Error: No log file found. Specify a log file or ensure app.log exists."
        exit 1
    fi
fi

if [ ! -f "${LOG_FILE}" ]; then
    echo "Error: Log file not found: ${LOG_FILE}"
    exit 1
fi

echo "Scanning ${LOG_FILE} for gaps > ${MAX_GAP_SECONDS} seconds..."
echo ""

# Extract timestamps and detect gaps
# Assumes log format with ISO timestamps or common formats
python3 << PYTHON_EOF
import re
import sys
from datetime import datetime, timedelta

log_file = "${LOG_FILE}"
max_gap = int("${MAX_GAP_SECONDS}")

# Common timestamp patterns
patterns = [
    r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})',  # ISO-like
    r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})',     # Alternative
    r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', # Bracket format
]

timestamps = []
prev_time = None
gaps_found = []

try:
    with open(log_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    ts_str = match.group(1)
                    try:
                        # Try parsing as ISO
                        if 'T' in ts_str:
                            dt = datetime.fromisoformat(ts_str.replace(' ', 'T'))
                        else:
                            # Try common formats
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']:
                                try:
                                    dt = datetime.strptime(ts_str, fmt)
                                    break
                                except ValueError:
                                    continue
                            else:
                                continue

                        if prev_time is not None:
                            gap = (dt - prev_time).total_seconds()
                            if gap > max_gap:
                                gaps_found.append({
                                    'line': line_num,
                                    'gap_seconds': gap,
                                    'gap_minutes': gap / 60,
                                    'from': prev_time.isoformat(),
                                    'to': dt.isoformat(),
                                })
                        prev_time = dt
                        break
                    except (ValueError, AttributeError):
                        continue
except FileNotFoundError:
    print(f"Error: Log file not found: {log_file}")
    sys.exit(1)
except Exception as e:
    print(f"Error reading log file: {e}")
    sys.exit(1)

if gaps_found:
    print(f"Found {len(gaps_found)} gap(s) > {max_gap} seconds:\n")
    for gap in gaps_found:
        print(f"  Line {gap['line']}: {gap['gap_minutes']:.1f} minutes ({gap['gap_seconds']:.0f}s)")
        print(f"    From: {gap['from']}")
        print(f"    To:   {gap['to']}")
        print()
    sys.exit(1)
else:
    print("No significant gaps found.")
    sys.exit(0)
PYTHON_EOF
