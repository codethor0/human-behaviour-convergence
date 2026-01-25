# Paranoid-Plus Verification & Integrity Loop Guide

This document describes the comprehensive verification system for human-behaviour-convergence, implementing property-based testing, metamorphic testing, mutation testing, and end-to-end integrity verification.

## Overview

The verification system consists of two main components:

1. **Paranoid-Plus Verification Suite**: Property-based, metamorphic, and mutation tests
2. **Integrity Loop**: End-to-end verification that runs repeatedly until all integrity checks pass

## Paranoid-Plus Verification Suite

### Purpose

Prove system correctness with adversarial testing. The suite verifies:
- **P1**: Regionality - Different regions produce different outputs
- **P2**: Determinism - Same inputs produce identical outputs in CI offline mode
- **P3**: Cache key regionality - Regional sources include geo in cache keys
- **P4**: Metrics truth - After forecasting N regions, metrics show N unique region labels
- **P5**: No label collapse - No region="None"; no "unknown_*" explosion
- **P6**: Metamorphic monotonicity - Input changes produce expected output changes
- **P7**: Data quality - Values are in valid ranges, no NaNs

### Running the Suite

```bash
# Run the full paranoid suite
./scripts/run_paranoid_suite.sh

# Or run individual test modules
HBC_CI_OFFLINE_DATA=1 pytest tests/test_property_invariants.py -v
HBC_CI_OFFLINE_DATA=1 pytest tests/test_metamorphic_regionality.py -v
pytest tests/test_metrics_contracts_paranoid.py -v

# Run mutation smoke test
./scripts/mutation_smoke.sh
```

### Test Files

- **`tests/test_property_invariants.py`**: Property-based tests (P1-P7)
- **`tests/test_metamorphic_regionality.py`**: Metamorphic transformation tests
- **`tests/test_metrics_contracts_paranoid.py`**: Strict metrics contract tests
- **`scripts/mutation_smoke.sh`**: Lightweight mutation testing

### Evidence Outputs

Each run produces:
- `/tmp/hbc_paranoid_plus_<TIMESTAMP>/` - Evidence directory
- `/tmp/HBC_PARANOID_PLUS_REPORT.md` - Summary report
- `/tmp/hbc_paranoid_plus_<TIMESTAMP>/BUGS.md` - Bug list (if failures)

## Integrity Loop

### Purpose

Repeatedly validate the entire system end-to-end until integrity is intact. Verifies:

- **I1**: Docker readiness - /health + core frontend routes return 200
- **I2**: Proxy integrity - Frontend proxy endpoints match direct backend endpoints
- **I3**: Forecast divergence - At least 2 distant regions show meaningful variance
- **I4**: Metrics integrity - /metrics contains no region="None", distinct regions >= threshold
- **I5**: Prometheus scrape - Prometheus is ready and returns non-empty for behavior_index
- **I6**: Grafana sanity - Region variable query returns >=2 regions
- **I7**: UI contracts - /forecast and /history satisfy known contracts
- **I8**: Stability - Entire loop passes 3 consecutive runs without changing code

### Running the Integrity Loop

```bash
# Full mode (10 regions, requires 3 consecutive passes)
./scripts/integrity_loop_master.sh

# Reduced mode (2 regions, faster)
./scripts/integrity_loop_master.sh --reduced

# Custom number of consecutive passes
./scripts/integrity_loop_master.sh --runs 5
```

### Phases

1. **Phase 0**: Clean start - Git status, toolchain versions, Docker restart
2. **Phase 1**: Readiness gates - Verify all HTTP endpoints return 200
3. **Phase 2**: API baseline + proxy parity - Verify frontend proxy matches backend
4. **Phase 3**: Seed multi-region forecasts - Generate forecasts for 10 regions (or 2 in reduced mode)
5. **Phase 4**: Variance / discrepancy check - Verify regional variance, check for collapse
6. **Phase 5**: Metrics integrity - Verify no region="None", count distinct regions
7. **Phase 6**: Prometheus proof - Verify Prometheus queries return data
8. **Phase 7**: Grafana proof - Verify Grafana can see multiple regions
9. **Phase 8**: UI contract proof - Lightweight UI element checks
10. **Phase 9**: Report generation - Create evidence bundle

### Evidence Outputs

Each run produces:
- `/tmp/hbc_integrity_loop_<TIMESTAMP>/` - Evidence directory containing:
  - `readiness.tsv` - HTTP status codes for all endpoints
  - `forecast_seed_results.csv` - Forecast results for all regions
  - `forecast_variance_report.txt` - Variance analysis
  - `metrics.txt` - Full metrics dump
  - `metrics_extract.txt` - Extracted relevant metrics
  - `promql_*.json` - Prometheus query results
  - `docker_logs_*.txt` - Docker container logs
  - `BUGS.md` - Bug list (if failures)
- `/tmp/HBC_INTEGRITY_LOOP_REPORT.md` - Summary report

## Usage Patterns

### Before Committing Changes

```bash
# Quick check: Run paranoid suite
./scripts/run_paranoid_suite.sh

# Full verification: Run integrity loop
./scripts/integrity_loop_master.sh --reduced
```

### Continuous Verification

```bash
# Run integrity loop repeatedly until it passes 3 times
./scripts/integrity_loop_master.sh
```

### Debugging Failures

1. Check the evidence directory: `/tmp/hbc_integrity_loop_<TIMESTAMP>/`
2. Review `BUGS.md` for specific failure details
3. Check `HBC_INTEGRITY_LOOP_REPORT.md` for summary
4. Review Docker logs in `docker_logs_*.txt`
5. Check variance report in `forecast_variance_report.txt`

## CI Integration

Both scripts are designed to work in CI environments:

- **CI Offline Mode**: Set `HBC_CI_OFFLINE_DATA=1` for deterministic behavior
- **Reduced Mode**: Use `--reduced` flag for faster CI runs
- **Exit Codes**: Scripts exit with non-zero code on failure

Example CI job:

```yaml
- name: Run Integrity Loop
  run: |
    export HBC_CI_OFFLINE_DATA=1
    ./scripts/integrity_loop_master.sh --reduced --runs 1
```

## Troubleshooting

### Integrity Loop Fails at Phase 1

- Check Docker containers: `docker compose ps`
- Check logs: `docker compose logs`
- Verify ports 8100, 3100, 9090, 3000 are available

### Integrity Loop Fails at Phase 4 (Variance)

- Check if regional sources are enabled
- Verify cache keys include geo identity
- Review `forecast_variance_report.txt` for details

### Integrity Loop Fails at Phase 5 (Metrics)

- Verify metrics endpoint is accessible: `curl http://localhost:8100/metrics`
- Check for region="None" labels: `grep 'region="None"' /tmp/hbc_integrity_loop_*/metrics.txt`
- Ensure forecasts were generated successfully

### Paranoid Suite Fails

- Check which property failed (P1-P7)
- Review test logs in evidence directory
- Run individual test modules to isolate issue

## Best Practices

1. **Run before major changes**: Always run integrity loop before merging
2. **Use reduced mode for quick checks**: `--reduced` flag for faster feedback
3. **Review evidence bundles**: Check evidence directories for detailed diagnostics
4. **Fix bugs immediately**: Don't accumulate failures - fix as you go
5. **Document known issues**: If a test is expected to fail, document why

## Related Documentation

- `docs/VERIFY_INTEGRITY.md` - General integrity verification guide
- `docs/DISCREPANCY_INVESTIGATION_FRAMEWORK.md` - Debugging discrepancies
- `docs/PARANOID_VERIFICATION_GUIDE.md` - This document
