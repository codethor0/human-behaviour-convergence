# Test Plan

**Repository:** human-behaviour-convergence
**Branch:** chore/spelling-behavior-standardization
**Date:** 2025-11-10

## Detected Languages & Frameworks

- **Primary:** Python 3.10+ (requires >=3.10)
- **Package Manager:** pip (requirements.txt, requirements-dev.txt, app/backend/requirements.txt)
- **Package Structure:**
  - `hbc/` - Main package
  - `connectors/` - Data connectors
  - `app/backend/` - FastAPI backend
  - `tests/` - Test suite

## Intended Test Commands

### Primary Test Command (from CI workflow)
```bash
pytest tests/ --cov --cov-report=term-missing --cov-report=xml -v -n auto
```
- Uses pytest with coverage
- Parallel execution with pytest-xdist (`-n auto`)
- Coverage reports: terminal and XML (for Codecov)

### Alternative Test Commands

From `scripts/dev`:
```bash
pytest tests/ --cov
```

From CI workflow (quality-gates):
```bash
pytest tests/ --cov=app/backend/app --cov-report=term --cov-report=xml -v -n auto
coverage report --fail-under=65
```

From CI workflow (test.yml):
```bash
pytest tests/ --cov --cov-report=term-missing --cov-report=xml -v -n auto
```

### Test Files
- `tests/test_api_backend.py` - FastAPI backend tests
- `tests/test_cli.py` - CLI tool tests
- `tests/test_connectors.py` - Data connector tests
- `tests/test_forecasting.py` - Forecasting logic tests
- `tests/test_public_api.py` - Public API endpoint tests
- `tests/test_no_emoji_script.py` - Markdown emoji check tests

## Intended Lint/Format Commands

### From CI workflow (ci.yml)

**Ruff Lint:**
```bash
ruff check app/backend tests hbc --ignore F401,F402,F403,F405,F841,E402
```

**Black Format Check:**
```bash
black --check app/backend tests hbc
```

**Mypy Type Check (non-blocking):**
```bash
mypy --strict app/backend tests hbc
```
- Note: `continue-on-error: true` in CI, so type errors don't fail the build

**Semgrep Security Scan:**
```bash
semgrep --config=auto app/backend tests hbc
```

### Pre-commit Hooks

Pre-commit hooks configured in `.pre-commit-config.yaml`:
- `trailing-whitespace` - Removes trailing whitespace
- `end-of-file-fixer` - Ensures files end with newline
- `check-yaml` - Validates YAML files
- `check-json` - Validates JSON files
- `check-added-large-files` - Prevents large file commits
- `black` - Python code formatter
- `isort` - Import sorter (profile: black)
- `no-emojis-in-markdown` - Custom hook (local)
- `enforce-american-spelling` - Custom hook (local)

Run pre-commit hooks:
```bash
pre-commit run --all-files
```

## Environment Variables

From CI workflows:
- `CI=true` - Enables network-dependent tests (set automatically in GitHub Actions)
- `PYTHON_VERSION` - Python version from matrix (3.10, 3.11, 3.12)
- `DISK_CAP_GB=10` - Maximum disk usage in GB (enforced in workflows)
- `MAX_LOG_MB=5` - Maximum log file size in MB (logs are trimmed if exceeded)

## Required Services

Based on test files:
- **Network access:** Tests may make HTTP requests (connectors, public API tests)
  - Connectors: Wiki pageviews, OSM changesets, FIRMS fires
  - Tests may use mocking (responses library) to avoid real network calls
- **Local filesystem:** Tests read/write CSV files in `results/` and `data/public/`

## Dependency Installation

Install all dependencies:
```bash
pip install --upgrade pip
pip install -r app/backend/requirements.txt
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

For linting/formatting:
```bash
pip install black ruff mypy semgrep
```

## Test Execution Strategy

1. **Primary:** Run full test suite with coverage
   ```bash
   pytest tests/ --cov --cov-report=term-missing --cov-report=xml -v -n auto
   ```

2. **If that fails:** Run tests sequentially (without -n auto)
   ```bash
   pytest tests/ --cov -v
   ```

3. **If still failing:** Run individual test files
   ```bash
   pytest tests/test_api_backend.py -v
   pytest tests/test_connectors.py -v
   pytest tests/test_public_api.py -v
   ```

4. **Lint checks:** Run in order
   ```bash
   ruff check app/backend tests hbc --ignore F401,F402,F403,F405,F841,E402
   black --check app/backend tests hbc
   mypy --strict app/backend tests hbc || true  # Non-blocking
   semgrep --config=auto app/backend tests hbc
   ```

## Coverage Requirements

From quality-gates workflow:
- **Minimum coverage:** 65% (`coverage report --fail-under=65`)
- **Coverage target:** app/backend/app module

## Notes

- Tests use `pytest-xdist` for parallel execution (`-n auto`)
- Some tests may require network access but should be mocked
- Type checking is non-blocking (`mypy --strict` with `continue-on-error: true`)
- Security scanning uses Semgrep with auto-config
- Pre-commit hooks must pass before commits (but may fail on missing Python executable)
