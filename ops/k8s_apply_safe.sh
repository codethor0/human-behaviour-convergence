#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Safe Kubernetes apply with diff preview and live field stripping.
# Inspired by DevOps-Bash-tools kubernetes_yaml_strip_live_fields.sh, kubectl_diff_apply.sh.
#
# Usage:
#   ./ops/k8s_apply_safe.sh <manifest_file> [namespace] [--dry-run]
#
# Features:
#   - Strips live-only fields before apply
#   - Shows diff before applying
#   - Prevents immutable field errors

set -euo pipefail

MANIFEST="${1:-}"
NAMESPACE="${2:-default}"
DRY_RUN=false

if [ -z "${MANIFEST}" ]; then
    echo "Usage: $0 <manifest_file> [namespace] [--dry-run]"
    exit 2
fi

if [[ "$*" == *"--dry-run"* ]]; then
    DRY_RUN=true
fi

if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl not found"
    exit 2
fi

if [ ! -f "${MANIFEST}" ]; then
    echo "Error: Manifest file not found: ${MANIFEST}"
    exit 2
fi

echo "Processing manifest: ${MANIFEST}"
echo "Namespace: ${NAMESPACE}"
echo ""

# Strip live-only fields (similar to kubernetes_yaml_strip_live_fields.sh)
CLEANED_MANIFEST=$(mktemp)
python3 << PYTHON_EOF > "${CLEANED_MANIFEST}"
import yaml
import sys

# Fields to strip (live-only, immutable, or auto-generated)
STRIP_PATHS = [
    'metadata.uid',
    'metadata.resourceVersion',
    'metadata.creationTimestamp',
    'metadata.generation',
    'metadata.managedFields',
    'status',
    'spec.clusterIP',  # Service immutable field
]

def strip_fields(obj, path=''):
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            if current_path in STRIP_PATHS:
                continue  # Skip this field
            result[key] = strip_fields(value, current_path)
        return result
    elif isinstance(obj, list):
        return [strip_fields(item, path) for item in obj]
    else:
        return obj

try:
    with open('${MANIFEST}', 'r') as f:
        data = yaml.safe_load(f)

    cleaned = strip_fields(data)
    yaml.dump(cleaned, sys.stdout, default_flow_style=False, sort_keys=False)
except Exception as e:
    print(f"Error processing manifest: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF

# Show diff
echo "Diff preview:"
kubectl diff -f "${CLEANED_MANIFEST}" -n "${NAMESPACE}" || true
echo ""

if [ "${DRY_RUN}" = "true" ]; then
    echo "Dry-run mode: would apply cleaned manifest"
    rm -f "${CLEANED_MANIFEST}"
    exit 0
fi

# Prompt for confirmation
read -p "Apply cleaned manifest? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    rm -f "${CLEANED_MANIFEST}"
    exit 0
fi

# Apply
echo "Applying..."
if kubectl apply -f "${CLEANED_MANIFEST}" -n "${NAMESPACE}"; then
    echo "✓ Applied successfully"
    rm -f "${CLEANED_MANIFEST}"
    exit 0
else
    echo "✗ Apply failed"
    rm -f "${CLEANED_MANIFEST}"
    exit 1
fi
