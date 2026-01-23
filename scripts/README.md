# Scripts Directory

This directory contains development, verification, and data quality scripts.

## Purpose

Scripts in this directory focus on:
- **Data Quality**: Auditing, validation, and quality checks
- **Integrity Verification**: End-to-end integrity loops and verification
- **Discrepancy Investigation**: Tools for investigating data discrepancies
- **Demo Scripts**: Demonstration and example scripts

## Script Categories

### Integrity & Verification
- `verify_e2e_integrity.sh` - Comprehensive end-to-end integrity verification
- `integrity_loop_master.sh` - Master integrity loop with 3-pass enforcement
- `run_paranoid_suite.sh` - Paranoid-Plus verification test suite
- `mutation_smoke.sh` - Mutation testing to verify test effectiveness

### Data Quality
- `run_data_quality_checkpoint.py` - Data quality checkpoint validation
- `source_regionality_audit.py` - Audit regional data sources
- `cache_key_audit.py` - Audit cache key regionality

### Discrepancy Investigation
- `discrepancy_harness.py` - Discrepancy investigation framework
- `run_full_discrepancy_investigation.sh` - Full discrepancy investigation

### Demo & Examples
- `run_live_forecast_demo.py` - Live forecast demonstration

## Relationship to ops/

- **scripts/**: Data quality, integrity loops, E2E verification, discrepancy investigation
- **ops/**: Operational health, deployment verification, runtime monitoring, CI gates

## Usage

Most scripts can be run from the repository root:

```bash
# Run integrity loop
./scripts/integrity_loop_master.sh --reduced

# Run paranoid suite
./scripts/run_paranoid_suite.sh

# Run data quality checkpoint
HBC_CI_OFFLINE_DATA=1 python3 scripts/run_data_quality_checkpoint.py
```

## CI/CD Integration

Some scripts are used in CI/CD workflows:
- `run_data_quality_checkpoint.py` - Used in integrity_gates.yml

See `.github/workflows/` for full CI/CD integration.
