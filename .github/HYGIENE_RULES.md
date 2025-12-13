# Repository Hygiene Rules

This document defines the enforced repository hygiene rules for `human-behaviour-convergence`.

## Branch Management

### Protected Branches
- **main** - Default branch, protected
- **master** - Legacy branch, protected (left untouched)

### Branch Cleanup Rules
1. **Merged branches** - Automatically deleted nightly
2. **Dependabot branches** - Deleted if:
   - Fully merged into main, OR
   - Older than 30 days, OR
   - More than 50 commits behind main
3. **Remote HEAD** - Always points to `origin/main` (enforced nightly)

### Branch Hygiene Workflow
- **Schedule:** Nightly at 02:00 UTC
- **Actions:**
  - Deletes merged branches
  - Deletes stale Dependabot branches
  - Closes outdated Dependabot PRs (>30 days or >50 commits behind)
  - Ensures `origin/HEAD` points to `origin/main`

## CI Cost Optimization

### CI Workflow Rules
- **Runs on:**
  - Push to `main`
  - Pull requests to `main`
  - Manual dispatch
- **Skips:**
  - Pushes to `dependabot/**` branches (CI only runs when PR is open)

### CodeQL Workflow Rules
- **Runs on:**
  - Push to `main`
  - Pull requests to `main`
  - Weekly schedule (Sunday 00:00 UTC)
  - Manual dispatch
- **Skips:**
  - Pushes to `dependabot/**` branches (CodeQL only runs when PR is open)

## Dependabot Configuration

### Update Schedule
- **All ecosystems:** Weekly (Mondays at 09:00 UTC)
- **No daily updates:** Prevents PR spam

### Grouping Strategy
- **npm:** All updates grouped into single PR (limit: 1 open PR)
- **GitHub Actions:** All updates grouped into single PR (limit: 1 open PR)
- **Python (root & backend):** Security-only updates (limit: 5 open PRs)

### Lockfile Maintenance
- **npm:** Weekly lockfile maintenance enabled
- **Python:** Security advisories only

## Monitoring & Validation

### Hygiene Monitor Workflow
- **Schedule:** Weekly (Mondays at 10:00 UTC)
- **Validates:**
  - CI configuration (dependabot ignore)
  - CodeQL configuration (dependabot ignore)
  - Dependabot configuration (weekly, grouped, security-only)
  - Branch hygiene workflow schedule
  - Remote HEAD configuration
- **Reports:**
  - Branch status
  - PR status
  - CI cost analysis
  - Configuration health

### Health Checks
- Branch hygiene workflow must run successfully nightly
- No CI runs on dependabot branch pushes
- Dependabot PRs limited per ecosystem
- Remote HEAD always points to main

## Enforcement

All rules are enforced automatically via:
1. **Branch Hygiene Workflow** - Nightly cleanup
2. **Hygiene Monitor Workflow** - Weekly validation and reporting
3. **Workflow Configuration** - CI/CodeQL skip dependabot branches
4. **Dependabot Configuration** - Weekly grouped updates

## Manual Override

If manual intervention is needed:
1. Review the hygiene report (generated weekly)
2. Check workflow logs for failures
3. Manually trigger workflows via `workflow_dispatch`
4. Fix configuration issues if validation fails

## Cost Savings

Estimated monthly savings:
- **CI minutes:** ~20-30 minutes (no CI on dependabot pushes)
- **CodeQL minutes:** ~10-15 minutes (no CodeQL on dependabot pushes)
- **PR review time:** Reduced via grouped updates
- **Branch clutter:** Eliminated via automated cleanup
