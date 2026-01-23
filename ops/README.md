# Ops Directory

This directory contains operational scripts for deployment, health checks, and CI gates.

## Purpose

Scripts in this directory focus on:
- **Operational Health**: Runtime health checks and monitoring
- **Deployment Verification**: Pre-deployment and post-deployment verification
- **CI Gates**: Scripts used in CI/CD pipeline gates
- **Runtime Monitoring**: Log analysis, gap detection, support bundle collection

## Script Categories

### Health Checks
- `check_integrity.sh` - Runtime integrity check
- `check_logs.sh` - Log analysis
- `k8s_health_check.sh` - Kubernetes health check

### Deployment Verification
- `verify_gate_a.sh` - Gate A verification (used in CI)
- `verify_gate_grafana.sh` - Grafana gate verification (used in CI)
- `verify_fred_*.sh` - FRED data source verification scripts
- `verify_subindices_*.sh` - Sub-index verification scripts

### Operations
- `dev_watch_docker.sh` - Development Docker watch script
- `collect_support_bundle.sh` - Support bundle collection
- `scan_log_gaps.sh` - Log gap scanning
- `triage_main.sh` - Main triage script

### Regression Testing
- `run_forecast_regression.py` - Forecast regression testing
- `test_scripts.sh` - Script testing harness

## Relationship to scripts/

- **ops/**: Operational health, deployment verification, runtime monitoring, CI gates
- **scripts/**: Data quality, integrity loops, E2E verification, discrepancy investigation

## CI/CD Integration

Several scripts are used in CI/CD workflows:
- `verify_gate_a.sh` - Used in gates.yml
- `verify_gate_grafana.sh` - Used in gates.yml
- `check_integrity.sh` - Used in forecast-integrity.yml

**Important**: Scripts referenced in CI must not be moved or renamed without updating workflows.

See `.github/workflows/` for full CI/CD integration.

## Usage

Most scripts can be run from the repository root:

```bash
# Run gate verification
./ops/verify_gate_a.sh

# Check integrity
./ops/check_integrity.sh

# Health check
./ops/k8s_health_check.sh
```
