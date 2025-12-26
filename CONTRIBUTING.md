# Contributing

Thanks for your interest in improving this project!

## Quickstart
- The diagram’s source of truth is `diagram/behaviour-convergence.mmd`.
- Preview and edit via Mermaid Live (preloaded with the diagram): https://mermaid.live/edit#url=https://raw.githubusercontent.com/codethor0/human-behaviour-convergence/main/diagram/behaviour-convergence.mmd
- On merge to `main`, CI re-renders `diagram/behaviour-convergence.svg` and `.png` via GitHub Actions.

## Branching Strategy

- **`main` is the canonical default branch** for development and production.
- All pull requests should target `main`.
- The `master` branch is legacy and kept in sync for compatibility, but `main` is the primary branch.
- All CI workflows are configured to run on pushes and pull requests to `main`.

## Making changes
1. Fork and create a branch from `main`.
2. Edit `diagram/behaviour-convergence.mmd` only. Do not edit generated `.svg`/`.png` by hand.
3. If you add nodes/edges, keep labels concise and wrap long text with `\n` for readability.
4. Open a Pull Request targeting `main`. The render workflow will attach updated artifacts if they change.

## Commit style
- Use concise, descriptive commits. Conventional Commits are welcome, e.g., `feat(diagram): add feedback loop` or `docs(readme): clarify Pages URL`.

## Development notes
- Local render (optional):
  - Assumption: using `@mermaid-js/mermaid-cli`.
  - Example:
    - `npx @mermaid-js/mermaid-cli -i diagram/behaviour-convergence.mmd -o diagram/behaviour-convergence.svg`

## Local Workflow

Before pushing changes, follow this workflow:

### 1. Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Or use the bootstrap script:

```bash
./scripts/dev
```

### 2. Run pre-commit hooks

```bash
pre-commit run --all-files
```

If pre-commit is not installed, you can run individual checks:

```bash
# Emoji check
python .github/scripts/check_no_emoji.py

# Format check (requires black)
black --check app/backend tests hbc

# Lint check (requires ruff)
ruff check app/backend tests hbc --ignore F401,F402,F403,F405,F841,E402
```

### 3. Run tests

**Recommended: Docker**

```bash
docker compose run --rm test
```

**Local execution**

```bash
pytest tests/ --cov --cov-report=term-missing -v
```

### 4. Verify and push

After all checks pass locally:

1. Commit your changes
2. Push to your branch
3. Verify that all GitHub Actions checks are green

## CI and Governance Enforcement

All pull requests must pass automated checks before merging:

### Required CI Checks

- **Pre-Flight Checks** — Validates repository structure, YAML syntax, and required files
- **Lint & Format** — Code formatting (Black) and linting (Ruff)
- **Build** — Verifies Python package builds correctly
- **Tests** — Runs test suite across Python 3.10, 3.11, and 3.12
- **Security Scanning** — Bandit and Trivy vulnerability scanning
- **Emoji Check** — Ensures no emojis in markdown files
- **Conventional Commits** — Validates commit message format

### Governance Checks

The repository enforces governance rules via automated checks:

- **Version Contract Enforcement** — Ensures version changes are documented
- **Sub-Index Count Consistency** — Validates behavioral index documentation
- **Weight Semantics Documentation** — Ensures mathematical operations are documented
- **Drift Detection** — Prevents documentation and code divergence

See [GOVERNANCE_RULES.md](./GOVERNANCE_RULES.md) and [INVARIANTS.md](./INVARIANTS.md) for details.

### What Will Block a PR

A pull request will be blocked if:

- Any CI check fails
- Tests fail or coverage drops below threshold
- Code formatting or linting issues are detected
- Governance checks fail
- Security vulnerabilities are detected
- Commit messages don't follow Conventional Commits format

### Branch Discipline

- All changes must go through pull requests targeting `main`
- Direct pushes to `main` are blocked by branch protection
- Keep branches focused and up-to-date with `main`
- Delete branches after merging

## Code of Conduct
By participating, you agree to abide by the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Project Stewardship

Primary maintainer: **Thor Thor**
Email: [codethor@gmail.com](mailto:codethor@gmail.com)
LinkedIn: https://www.linkedin.com/in/thor-thor0 (may require manual verification due to anti-bot protection)
