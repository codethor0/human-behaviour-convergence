# Autonomous Execution Systems Summary

This document summarizes the three autonomous master prompt systems implemented for HBC:

1. **Paranoid-Plus Verification** - Property-based tests, metamorphic tests, mutation testing
2. **Integrity Loop** - Repeatable end-to-end verification
3. **Repository Organization** - Structural hygiene and file organization

---

## 1. Paranoid-Plus Verification System

**Script**: `./scripts/run_paranoid_suite.sh`

**Purpose**: Prove system correctness with adversarial testing.

**What It Does**:
- Runs property-based tests (P1-P7)
- Runs metamorphic tests
- Runs paranoid metrics contracts tests
- Runs mutation smoke tests
- Produces evidence bundles

**Properties Tested**:
- P1: Regionality
- P2: Determinism
- P3: Cache key regionality
- P4: Metrics truth
- P5: No label collapse
- P6: Metamorphic monotonicity
- P7: Data quality

**Evidence**: `/tmp/hbc_paranoid_plus_<timestamp>/`

**Master Prompt**: `docs/PARANOID_PLUS_MASTER_PROMPT.md`

---

## 2. Integrity Loop System

**Script**: `./scripts/paranoid_integrity_loop.sh [--reduced] [--runs N]`

**Purpose**: Repeatable end-to-end verification until integrity is intact.

**What It Does**:
- Verifies Docker stack readiness
- Checks API endpoints and proxy parity
- Seeds multi-region forecasts
- Verifies variance/discrepancy
- Checks metrics integrity
- Verifies Prometheus and Grafana
- Checks UI contracts
- Runs 3 consecutive passes

**Invariants Verified** (I1-I8):
- I1: Docker readiness
- I2: Proxy integrity
- I3: Forecast divergence
- I4: Metrics integrity
- I5: Prometheus scrape
- I6: Grafana sanity
- I7: UI contracts
- I8: Stability (3 consecutive passes)

**Evidence**: `/tmp/hbc_integrity_loop_<timestamp>/`

**Master Prompt**: `docs/INTEGRITY_LOOP_MASTER_PROMPT.md`

---

## 3. Repository Organization System

**Script**: `./scripts/autonomous_repo_organization.sh`

**Purpose**: Structural hygiene - organize, classify, consolidate, normalize.

**What It Does**:
- Classifies all tracked files
- Plans moves to canonical structure
- Executes safe moves using `git mv`
- Quarantines suspicious files
- Organizes documentation into subdirectories
- Produces metrics and evidence

**Canonical Structure**:
```
app/backend/
app/frontend/
app/core/
app/services/
connectors/
tests/
infra/grafana/
infra/prometheus/
scripts/
docs/architecture/
docs/integrity/
docs/datasets/
docs/runbooks/
```

**Evidence**: `/tmp/hbc_repo_org_<timestamp>/`

**Master Prompt**: `docs/AUTONOMOUS_REPO_ORGANIZATION_MASTER_PROMPT.md`

---

## 4. Post-Work Verification System

**Script**: `./scripts/post_work_verification.sh`

**Purpose**: Anti-hallucination verification - prove claimed changes exist and are wired correctly.

**What It Does**:
- Verifies file existence (Gate A)
- Verifies registration/references (Gate B)
- Verifies execution in running stack (Gate C)
- Verifies metrics presence (Gate D)
- Verifies Grafana visibility (Gate E)
- Produces truth report

**Evidence**: `/tmp/hbc_post_verify_<timestamp>/`

**Master Prompt**: `docs/POST_WORK_VERIFICATION_MASTER_PROMPT.md`

---

## Usage Patterns

### Before Committing Code

```bash
# Quick verification
./scripts/run_paranoid_suite.sh

# Full integrity check
./scripts/paranoid_integrity_loop.sh --reduced
```

### After Adding New Features

```bash
# Verify new features are real and wired
./scripts/post_work_verification.sh

# Full integrity loop
./scripts/paranoid_integrity_loop.sh
```

### Periodic Repository Hygiene

```bash
# Organize repository structure
./scripts/autonomous_repo_organization.sh
```

### Continuous Verification (CI/CD)

```bash
# Lightweight checks
./scripts/run_paranoid_suite.sh
./scripts/paranoid_integrity_loop.sh --reduced --runs 1
```

---

## Evidence Bundle Locations

All systems produce timestamped evidence bundles in `/tmp/`:

- Paranoid-Plus: `/tmp/hbc_paranoid_plus_<timestamp>/`
- Integrity Loop: `/tmp/hbc_integrity_loop_<timestamp>/`
- Repository Org: `/tmp/hbc_repo_org_<timestamp>/`
- Post-Work Verify: `/tmp/hbc_post_verify_<timestamp>/`

Each bundle contains:
- Classification/analysis files
- Test outputs
- Metrics dumps
- Docker logs (if failures)
- Summary reports
- BUGS.md (if failures)

---

## Key Principles

1. **Autonomous Execution**: No user prompts, auto-approve safe actions
2. **Evidence-First**: Every claim backed by proof
3. **Surgical Changes**: Smallest fix that resolves the issue
4. **No Hallucination**: Verify before claiming success
5. **Loop Until Stable**: Continue until stop conditions met

---

## References

- **Paranoid-Plus**: `docs/PARANOID_PLUS_MASTER_PROMPT.md`
- **Integrity Loop**: `docs/INTEGRITY_LOOP_MASTER_PROMPT.md`
- **Repository Org**: `docs/AUTONOMOUS_REPO_ORGANIZATION_MASTER_PROMPT.md`
- **Post-Work Verify**: `docs/POST_WORK_VERIFICATION_MASTER_PROMPT.md`
- **Verification Guide**: `docs/VERIFICATION_MASTER_PROMPTS.md`
