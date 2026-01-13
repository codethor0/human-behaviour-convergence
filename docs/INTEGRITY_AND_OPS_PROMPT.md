# Integrity & Operations Master Prompt

This document contains the master prompt for the Reality Calibration, Integrity & Ops Stability Agent.

See the user's query for the full prompt text. This file serves as a reference.

## Key Phases

1. **Phase 0** - Discovery & Baseline Snapshot
2. **Phase 1** - Expose & Demote Synthetic Baselines
3. **Phase 2** - Increase Real-Time Signal Weights
4. **Phase 3** - Shock Multiplier + Reality Mismatch Flags
5. **Phase 4** - Economic & Macro Calibration
6. **Phase 5** - Forecast Regression Suite
7. **Phase 6** - Ops / Stability Layer (DevOps-Bash-tools style)
8. **Phase 7** - Safety, Bounds & Final Report

## Ops Scripts

All ops scripts are in `ops/` directory:
- `collect_support_bundle.sh` - Diagnostics bundle
- `scan_log_gaps.sh` - Log gap detection
- `run_forecast_regression.py` - Regression tests
- `check_integrity.sh` - CI integrity checks
- `k8s_health_check.sh` - K8s health (if applicable)
- `k8s_apply_safe.sh` - Safe K8s apply

## CI Integration

The `check_integrity.sh` script should be wired as a blocking CI job.
