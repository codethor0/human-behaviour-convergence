# Operations & Stability Scripts

This directory contains operational scripts inspired by DevOps-Bash-tools patterns to keep the forecasting app stable and "all green."

## Scripts

### Health & Diagnostics

- **`collect_support_bundle.sh`** - Collects system stats, logs, forecast snapshots, and integrity metadata into a tarball for diagnostics.
  ```bash
  ./ops/collect_support_bundle.sh [output_dir]
  ```

- **`scan_log_gaps.sh`** - Scans logs for large time gaps (indicating hangs or stuck workers).
  ```bash
  ./ops/scan_log_gaps.sh [log_file] [max_gap_seconds]
  ```

### Testing & Validation

- **`run_forecast_regression.py`** - Runs forecast regression tests for key regions and validates integrity expectations.
  ```bash
  python3 ops/run_forecast_regression.py [--verbose] [--output-dir DIR]
  ```

- **`check_integrity.sh`** - Master integrity check script for CI/CD. Runs config validation, unit tests, and regression tests.
  ```bash
  ./ops/check_integrity.sh [--skip-tests] [--skip-regression]
  ```

### Kubernetes (if applicable)

- **`k8s_health_check.sh`** - Checks Kubernetes deployment health (pods, restarts, logs).
  ```bash
  ./ops/k8s_health_check.sh [namespace] [deployment_name]
  ```

- **`k8s_apply_safe.sh`** - Safe Kubernetes apply with diff preview and live field stripping.
  ```bash
  ./ops/k8s_apply_safe.sh <manifest_file> [namespace] [--dry-run]
  ```

## CI Integration

Add to your CI pipeline (GitHub Actions, GitLab CI, etc.):

```yaml
# Example GitHub Actions job
- name: Forecast Integrity Check
  run: ./ops/check_integrity.sh
```

Make this job **required** for merging to main/trunk.

## Integration with Integrity Flags

When integrity flags (e.g., `REALITY_MISMATCH`) are detected:

1. Log instructions to run `collect_support_bundle.sh`
2. Optionally auto-trigger bundle collection
3. Include bundle in incident reports

## Output Directories

- `ops/support_bundles/` - Support bundle tarballs
- `ops/regression_results/` - Regression test results (JSON)
