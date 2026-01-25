# HBC Agent Verification Suite

**4-Agent Sequential Verification System**

This document describes the 4-agent verification system for HBC, where each agent builds on the previous one and verifies with hard evidence.

## Agent Overview

### Agent 1: Baseline E2E Runtime + Visual Presence
**Role**: HBC Runtime Verifier (E2E + Visual Presence)
**Goal**: Prove the stack is running, dashboards are visible on the app main page, and embeds work.

**Stop Conditions**:
- Docker stack up and healthy
- Frontend pages return 200
- Grafana reachable and allows embedding
- App page shows expected dashboard sections and iframes
- Automated browser proof (Playwright) finds sections and iframes
- Forecast generation for 3 regions works

**Script**: `./scripts/agent1_baseline_e2e.sh`
**Test**: `app/frontend/e2e/agent1_visual_presence.spec.ts`

### Agent 2: Independent Verification + Anti-Hallucination Audit
**Role**: HBC Skeptical Auditor
**Goal**: Assume Agent 1 lied or missed something. Re-verify everything independently.

**Stop Conditions**:
- Everything Agent 1 claimed is reproducible on a fresh run
- At least 1 additional "truth gate" added
- Grafana provisioning proof (runtime + static)
- Embed correctness proof

**Script**: `./scripts/agent2_skeptical_audit.sh`
**Test**: `tests/test_grafana_embeds_contract.py` (static contract)

### Agent 3: Data Integrity + Regional Variance + Source Regionality
**Role**: HBC Data Integrity & Regionality Verifier
**Goal**: Prove data pipeline produces meaningful regional variance.

**Stop Conditions**:
- Regional variance exists in >= 3 independent sub-indices for two distant regions
- fuel_stress exists in metrics and affects economic_stress
- Cache keys include geo parameters for all regional sources
- Variance probe runs and produces expected classifications

**Script**: `./scripts/agent3_data_integrity.sh`

### Agent 4: Enterprise Paranoid Verification
**Role**: HBC Enterprise Paranoid Gatekeeper
**Goal**: Verify reproducibility, strengthen CI gates, ensure repo hygiene.

**Stop Conditions**:
- CI gates exist for all required checks
- Repo hygiene checks pass
- Repeatable "integrity loop" script exists and passes

**Script**: `./scripts/agent4_enterprise_paranoid.sh`
**CI Workflow**: `.github/workflows/integrity_gates.yml`

## Execution Order

Run agents sequentially:

```bash
# Agent 1: Baseline E2E + Visual
./scripts/agent1_baseline_e2e.sh

# Agent 2: Independent Verification
./scripts/agent2_skeptical_audit.sh

# Agent 3: Data Integrity
./scripts/agent3_data_integrity.sh

# Agent 4: Enterprise Paranoid
./scripts/agent4_enterprise_paranoid.sh
```

## Evidence Structure

Each agent creates evidence in `/tmp/hbc_agent<N>_<type>_<timestamp>/`:

- `logs/` - Execution logs
- `screenshots/` - Visual proof (Agent 1)
- `forecasts/` - Forecast JSON responses
- `metrics/` - Prometheus metrics dumps
- `grafana_api/` - Grafana API responses (Agent 2)
- `provisioning/` - Dashboard provisioning proof (Agent 2)
- `repo_audit/` - Repo hygiene reports (Agent 4)
- `ci_gates/` - CI gate test results (Agent 4)
- `FINAL_REPORT.md` - Summary report

## Common Guardrails

All agents follow these rules:

1. **No emojis** in code, docs, commits
2. **No prompt artifacts** committed
3. **One concern per commit**
4. **Surgical diffs** - minimal changes
5. **Proof or mark UNVERIFIED** - every claim must have evidence
6. **Keep everything GREEN** - no test weakening

## Quick Start

1. **Start stack**: `docker compose up -d --build`
2. **Run Agent 1**: `./scripts/agent1_baseline_e2e.sh`
3. **Review evidence**: Check `/tmp/hbc_agent1_visual_<timestamp>/`
4. **Run Agent 2**: `./scripts/agent2_skeptical_audit.sh`
5. **Continue with Agents 3 and 4**

## Troubleshooting

### Agent 1: Stack not starting
- Check Docker daemon: `docker ps`
- Check logs: `docker compose logs`
- Verify ports not in use

### Agent 2: Grafana API not accessible
- Check Grafana credentials in docker-compose.yml
- Verify Grafana health: `curl http://localhost:3001/api/health`

### Agent 3: No variance detected
- Generate forecasts for more regions
- Check cache keys include geo parameters
- Verify regional data sources are enabled

### Agent 4: CI gates failing
- Run tests locally first
- Check CI offline mode: `HBC_CI_OFFLINE_DATA=1`
- Review test output in `ci_gates/` directory

## References

- Agent 1 Evidence Contract: See `scripts/agent1_baseline_e2e.sh`
- Static Contract Test: `tests/test_grafana_embeds_contract.py`
- Integrity Loop: `scripts/integrity_loop_master.sh`
- Repo Hygiene: `scripts/repo_hygiene_audit.sh`
