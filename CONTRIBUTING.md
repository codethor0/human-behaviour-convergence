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

## Code of Conduct
By participating, you agree to abide by the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Project Stewardship

Primary maintainer: **Thor Thor**  
Email: [codethor@gmail.com](mailto:codethor@gmail.com)  
LinkedIn: [https://www.linkedin.com/in/thor-thor0](https://www.linkedin.com/in/thor-thor0)
