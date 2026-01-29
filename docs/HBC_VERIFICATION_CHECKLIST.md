# HBC Verification Checklist

Use this before merging to main or tagging a release.

1. Run `./scripts/hbc_verify_all.sh` from the repo root.
2. Confirm:
   - All backend tests pass.
   - Optional linters (Ruff, mypy) are clean if enabled.
   - Optional frontend lint/tests pass if enabled.
   - **Local vs CI:** Locally, frontend failures are non-fatal (script exits 0 with a message). In CI (`CI=true` or `GITHUB_ACTIONS=true`), frontend failures are fatal and fail the job. To reproduce CI locally: `CI=true ./scripts/hbc_verify_all.sh`.
3. Confirm latest bug status is reflected in:
   - `docs/BUG_HUNT_SURGICAL_REPORT.md`
   - `docs/BUG_HUNT_BUGS.json`
4. Open the app and perform a quick smoke test:
   - Hub page loads
   - Region selector works (empty regions show "No regions available")
   - Grafana dashboards render
   - Anomaly/health dashboards show data
5. Push changes and ensure the GitHub Actions CI run is green.

**CI:** The canonical verification job is `hbc-verify` in `.github/workflows/ci.yml`; it runs `./scripts/hbc_verify_all.sh` with `CI=true`. Frontend Lint workflow (`.github/workflows/frontend-lint.yml`) runs ESLint on frontend changes.

**Branches:** Long-lived branch is `main`. Other remote branches (e.g. `fix/*`, `dependabot/*`) are short-lived. After merging a fix branch into main, delete the remote branch to keep the repo at two or fewer active branches: `git push origin --delete <branch-name>`. The Branch Hygiene workflow (`.github/workflows/branch-hygiene.yml`) runs on a schedule to clean merged and stale Dependabot branches.
