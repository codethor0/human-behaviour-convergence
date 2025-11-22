# AI-Generated Hardening Checklist

1. SHALL add SPDX MIT-0 license header to every new file.
2. SHALL use ruff, black, mypy --strict, and semgrep in pre-commit.
3. SHALL validate all external input for type, range, and allowed values.
4. SHALL avoid magic numbers; use named constants.
5. SHALL add type hints to all functions and methods.
6. SHALL avoid unprotected file I/O and catch all exceptions.
7. SHALL ensure all plugin registries use importlib.metadata.
8. SHALL add unit tests for every new module.
9. SHALL fail CI on any linter or type checker warning.
10. SHALL generate and upload SBOM and CVE report on every CI run.
11. SHALL avoid global mutable state unless protected by locks.
12. SHALL document every public API and plugin interface.
13. SHALL use only OSI-approved licenses in dependencies.
14. SHALL avoid deprecated or insecure APIs.
15. SHALL keep test coverage at 100% for high-risk files.
16. SHALL use block-style YAML in all config files.
17. SHALL avoid shell-injection and unsafe subprocess usage.
18. SHALL review all code for performance anti-patterns.
19. SHALL keep all secrets out of source control.
20. SHALL update this checklist with every major release.
# Contributing

Thanks for your interest in improving this project!

## Quickstart
- The diagram’s source of truth is `diagram/behaviour-convergence.mmd`.
- Preview and edit via Mermaid Live (preloaded with the diagram): https://mermaid.live/edit#url=https://raw.githubusercontent.com/codethor0/human-behaviour-convergence/main/diagram/behaviour-convergence.mmd
- On merge to `main`, CI re-renders `diagram/behaviour-convergence.svg` and `.png` via GitHub Actions.

## Making changes
1. Fork and create a branch.
2. Edit `diagram/behaviour-convergence.mmd` only. Do not edit generated `.svg`/`.png` by hand.
3. If you add nodes/edges, keep labels concise and wrap long text with `\n` for readability.
4. Open a Pull Request. The render workflow will attach updated artifacts if they change.

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
