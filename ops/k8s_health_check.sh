#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Kubernetes health check for forecasting app.
# Inspired by DevOps-Bash-tools kubernetes_info.sh, kubectl_logs.sh.
#
# Usage:
#   ./ops/k8s_health_check.sh [namespace] [deployment_name]
#
# Defaults:
#   namespace: default
#   deployment_name: hbc-forecast (or first deployment with 'forecast' in name)
#
# Exit codes:
#   0: All pods healthy
#   1: Unhealthy pods or deployment issues
#   2: kubectl/configuration error

set -euo pipefail

NAMESPACE="${1:-default}"
DEPLOYMENT="${2:-}"

if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl not found. This script requires Kubernetes access."
    exit 2
fi

# Detect deployment if not specified
if [ -z "${DEPLOYMENT}" ]; then
    DEPLOYMENT=$(kubectl get deployments -n "${NAMESPACE}" -o name 2>/dev/null | \
        grep -i forecast | head -1 | sed 's/deployment.apps\///' || echo "")

    if [ -z "${DEPLOYMENT}" ]; then
        echo "Error: No forecast deployment found in namespace ${NAMESPACE}"
        exit 2
    fi
fi

echo "Checking health of deployment: ${DEPLOYMENT} in namespace: ${NAMESPACE}"
echo ""

# Check deployment status
DEPLOYMENT_STATUS=$(kubectl get deployment "${DEPLOYMENT}" -n "${NAMESPACE}" \
    -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null || echo "Unknown")

if [ "${DEPLOYMENT_STATUS}" != "True" ]; then
    echo "✗ Deployment ${DEPLOYMENT} is not Available"
    kubectl describe deployment "${DEPLOYMENT}" -n "${NAMESPACE}" | grep -A 5 "Conditions:"
    exit 1
fi

# Check pod status
PODS=$(kubectl get pods -n "${NAMESPACE}" -l app="${DEPLOYMENT}" -o name 2>/dev/null || echo "")
if [ -z "${PODS}" ]; then
    echo "✗ No pods found for deployment ${DEPLOYMENT}"
    exit 1
fi

UNHEALTHY=0
for pod in ${PODS}; do
    pod_name=$(echo "${pod}" | sed 's/pod\///')
    status=$(kubectl get pod "${pod_name}" -n "${NAMESPACE}" \
        -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")
    ready=$(kubectl get pod "${pod_name}" -n "${NAMESPACE}" \
        -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
    restarts=$(kubectl get pod "${pod_name}" -n "${NAMESPACE}" \
        -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo "0")

    if [ "${status}" != "Running" ] || [ "${ready}" != "True" ]; then
        echo "✗ Pod ${pod_name}: status=${status}, ready=${ready}"
        UNHEALTHY=$((UNHEALTHY + 1))
    elif [ "${restarts}" -gt 5 ]; then
        echo "⚠ Pod ${pod_name}: ${restarts} restarts (may indicate issues)"
    else
        echo "✓ Pod ${pod_name}: Running, Ready"
    fi
done

# Check for recent errors in logs
echo ""
echo "Checking recent pod logs for errors..."
for pod in ${PODS}; do
    pod_name=$(echo "${pod}" | sed 's/pod\///')
    error_count=$(kubectl logs "${pod_name}" -n "${NAMESPACE}" --tail=100 2>/dev/null | \
        grep -iE "(error|exception|failed|critical)" | wc -l || echo "0")
    if [ "${error_count}" -gt 10 ]; then
        echo "⚠ Pod ${pod_name}: ${error_count} error-like log lines in last 100"
    fi
done

if [ ${UNHEALTHY} -gt 0 ]; then
    echo ""
    echo "✗ ${UNHEALTHY} unhealthy pod(s) found"
    exit 1
else
    echo ""
    echo "✓ All pods healthy"
    exit 0
fi
