# Testing Inventory

**Repository:** human-behaviour-convergence
**Branch:** chore/spelling-behavior-standardization
**Date:** 2025-11-10
**Phase:** 0 - Repository Discovery

---

## Languages and Frameworks Detected

### Primary Language: Python 3.10+

**Python Ecosystem:**
- **Package Manager:** pip (requirements.txt, requirements-dev.txt, app/backend/requirements.txt)
- **Package Structure:**
  - `hbc/` - Main package (forecasting, CLI)
  - `connectors/` - Data connectors (Wiki, OSM, FIRMS)
  - `app/backend/` - FastAPI backend application
  - `app/frontend/` - Next.js frontend (TypeScript/React)

**Framework:**
- **Backend:** FastAPI (Python web framework)
- **Frontend:** Next.js 14.2.5 (React 18, TypeScript)
- **CLI:** Custom `hbc-cli` command via `pyproject.toml` entry point

### Project Type
**Monorepo with multiple components:**
- Library: `hbc/` package (forecasting functions)
- Service: `app/backend/` FastAPI API server
- Web App: `app/frontend/` Next.js frontend
- CLI: `hbc/cli.py` console utility

---

## Existing Test Infrastructure

### Test Framework: pytest

**Test Directory:** `tests/`
- `test_api_backend.py` - FastAPI backend API tests (15 tests)
- `test_cli.py` - CLI tool tests (2 tests)
- `test_connectors.py` - Data connector tests (4 tests)
- `test_forecasting.py` - Forecasting logic unit tests (3 tests)
- `test_public_api.py` - Public API endpoint tests (8 tests)
- `test_no_emoji_script.py` - Markdown emoji check tests (0 tests, empty)

**Total Tests:** 33 tests (all passing)

### Test Configuration

**Framework Config:**
- `pyproject.toml` - Pytest config (not explicitly found, but tests use pytest)
- No `pytest.ini` found
- Tests use pytest conventions (`test_*.py` naming)

**Test Dependencies** (from `requirements-dev.txt`):
- `pytest>=8.0.0`
- `pytest-cov>=4.1.0`
- `pytest-xdist>=3.5.0` (parallel execution)
- `responses>=0.24.0` (HTTP mocking)
- `httpx>=0.28.0` (required by FastAPI TestClient)

### Current Test Commands

**From README:**
```bash
pytest tests/ --cov --cov-report=term-missing --cov-report=xml -v
```

**From CI workflow (test.yml):**
```bash
pytest tests/ --cov --cov-report=term-missing --cov-report=xml -v -n auto
```

**From scripts/dev:**
```bash
pytest tests/ --cov
```

**Canonical Test Command:**
```bash
pytest tests/ --cov --cov-report=term-missing --cov-report=xml -v -n auto
```

### Linting and Formatting Tools

**Linters:**
- **Ruff:** `ruff check app/backend tests hbc --ignore F401,F402,F403,F405,F841,E402`
- **Black:** `black --check app/backend tests hbc`
- **Mypy:** `mypy --strict app/backend tests hbc` (non-blocking in CI)
- **Semgrep:** `semgrep --config=auto app/backend tests hbc` (security scan)

**Pre-commit Hooks:** `.pre-commit-config.yaml`
- trailing-whitespace
- end-of-file-fixer
- check-yaml
- check-json
- check-added-large-files
- black
- isort
- no-emojis-in-markdown (custom)
- enforce-american-spelling (custom)

---

## Docker Infrastructure

### Existing Docker Setup

**Dockerfile:**
- **Base Image:** `python:3.10-slim` (multi-stage build)
- **Structure:**
  - `builder` stage: Installs dependencies, builds package
  - `runtime` stage: Copy built dependencies, expose port 8000
- **Command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Purpose:** Production runtime for FastAPI app

**docker-compose.yml:**
- **Version:** 3.8
- **Services:**
  - `app`: Builds from Dockerfile, mounts source as volume, runs with reload
- **Purpose:** Development environment with hot reload
- **Ports:** 8000:8000
- **Environment Variables:**
  - `CACHE_MAX_SIZE=100`
  - `CACHE_TTL_MINUTES=5`
  - `LOG_LEVEL=INFO`
  - `ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`

### Docker Test Setup

**Current State:**
- Dockerfile exists but is focused on runtime (not optimized for tests)
- docker-compose.yml exists but only defines `app` service (no test service)
- Tests can run inside Docker but require manual setup:
  ```bash
  docker run --rm hbc-test sh -c "pip install -r requirements-dev.txt && pytest tests/ -v"
  ```

**Gap:** No dedicated test service in docker-compose.yml

---

## CI/CD Configuration

### GitHub Actions Workflows

**Test Workflows:**
1. **`.github/workflows/test.yml`** - Main test workflow
   - Triggers: push/PR to main/master, Python files changed
   - Matrix: Python 3.10, 3.11, 3.12
   - Runs: `pytest tests/ --cov --cov-report=term-missing --cov-report=xml -v -n auto`
   - Uploads: Coverage to Codecov (Python 3.12 only)

2. **`.github/workflows/ci.yml`** - CI checks workflow
   - Separate jobs: lint-format, type-check, security-scan, test, sbom-scan
   - Runs tests: `pytest --maxfail=1 --disable-warnings tests -v -n auto`

3. **`.github/workflows/quality-gates.yml`** - Quality gates workflow
   - Runs: `pytest tests/ --cov=app/backend/app --cov-report=term --cov-report=xml -v -n auto`
   - Checks: Coverage threshold (65%), complexity, maintainability

**Other Workflows:**
- `app-ci.yml` - Frontend/backend CI
- `codeql.yml` - Security analysis
- `scorecard.yml` - Supply chain security
- And 10+ other workflows

---

## Test Coverage

**Current Coverage:** 77% overall

**Coverage by Module:**
- `app/backend/app/main.py`: 70%
- `app/backend/app/routers/public.py`: 78%
- `connectors/base.py`: 94%
- `connectors/firms_fires.py`: 48%
- `connectors/osm_changesets.py`: 72%
- `connectors/wiki_pageviews.py`: 71%
- `hbc/cli.py`: 44%
- `hbc/forecasting.py`: 95%
- `app/main.py`: 83%

**Coverage Threshold:** 65% (from quality-gates workflow)

---

## Test Types Currently Implemented

### Unit Tests
- [PASS] `test_forecasting.py` - Pure function tests for forecasting logic
- [PASS] `test_cli.py` - CLI command parsing and execution
- [PASS] `test_connectors.py` - Data connector logic (with HTTP mocking)

### Integration Tests
- [PASS] `test_api_backend.py` - FastAPI backend endpoints, cache, CSV reading
- [PASS] `test_public_api.py` - Public API endpoints with mocked connectors

### Missing Test Types
- [FAIL] E2E tests for frontend (Next.js app)
- [FAIL] Integration tests that test backend + frontend together
- [FAIL] Performance/load tests
- [FAIL] Contract tests (if applicable)

---

## Test Execution Environment

### Local Execution (Without Docker)

**Requirements:**
- Python 3.10+
- Virtual environment (`.venv`)
- Dependencies from requirements*.txt files

**Current Command:**
```bash
source .venv/bin/activate
pytest tests/ --cov --cov-report=term-missing -v
```

**Helper Script:**
- `scripts/dev` - Creates venv, installs deps, runs tests, launches API

### Docker Execution

**Current State:**
- Can build image: `docker build -t hbc-test .`
- Can run tests: `docker run --rm hbc-test sh -c "pip install -r requirements-dev.txt && pytest tests/ -v"`
- No standardized docker-compose test service

**Gap:** Need dedicated test service in docker-compose.yml for easier test execution

---

## Environment Variables and Dependencies

### Required Environment Variables

**For Tests:**
- `CI=true` - Enables network-dependent tests (optional)
- No other required env vars for basic test execution

**For Application:**
- `CACHE_MAX_SIZE` - Default: 100
- `CACHE_TTL_MINUTES` - Default: 5
- `LOG_LEVEL` - Default: INFO
- `ALLOWED_ORIGINS` - Default: http://localhost:3000,http://127.0.0.1:3000
- `RESULTS_DIR` - Auto-detected from file location

**Optional (for connectors):**
- `FIRMS_MAP_KEY` - NASA FIRMS API key (optional, returns empty data if not set)

### External Dependencies

**Services:**
- None required for tests (HTTP calls are mocked)
- Tests use `responses` library to mock HTTP requests

**Data Sources:**
- Wikipedia Pageviews API (mocked in tests)
- OSM Changesets API (mocked in tests)
- NASA FIRMS API (mocked in tests)

---

## Gaps and Opportunities

### Missing Test Infrastructure

1. **Docker Test Service:**
   - No dedicated `test` service in docker-compose.yml
   - Tests require manual Docker commands
   - Would benefit from: `docker compose run --rm test`

2. **Test Documentation:**
   - `tests/README.md` exists but outdated (references `src/` which doesn't exist)
   - No clear documentation on running tests with Docker

3. **Frontend Tests:**
   - Next.js frontend has no tests
   - No E2E tests for full stack

4. **Test Organization:**
   - All tests in single `tests/` directory
   - No clear separation between unit/integration/e2e
   - Could benefit from: `tests/unit/`, `tests/integration/`, `tests/e2e/`

### Test Coverage Gaps

1. **Low Coverage Areas:**
   - `connectors/firms_fires.py`: 48% (error handling, edge cases)
   - `hbc/cli.py`: 44% (CLI argument parsing, error handling)
   - `connectors/osm_changesets.py`: 72% (could improve edge case coverage)

2. **Missing Test Scenarios:**
   - Error handling in connectors (network failures, invalid data)
   - CLI error cases (invalid arguments, file I/O errors)
   - Cache edge cases (expiration, concurrent access)
   - API error responses (500s, validation errors)

### CI Improvements

1. **Docker in CI:**
   - CI workflows don't use Docker for tests (install deps directly)
   - Could standardize on Docker for consistent environment

2. **Test Parallelization:**
   - Already using `pytest-xdist` (`-n auto`)
   - Could further optimize with test sharding

---

## Summary

### What Exists [PASS]

- **Test Framework:** pytest with good coverage (77%)
- **Test Suite:** 33 tests, all passing
- **Docker Setup:** Dockerfile and docker-compose.yml exist
- **CI Integration:** Multiple GitHub Actions workflows
- **Linting/Formatting:** Comprehensive tooling (ruff, black, mypy, semgrep)

### What's Missing [WARN]

1. **Docker Test Service:** No dedicated test service in docker-compose.yml
2. **Frontend Tests:** No tests for Next.js frontend
3. **Test Organization:** All tests in single directory, no clear layering
4. **E2E Tests:** No end-to-end tests for full stack
5. **Test Documentation:** Outdated README, no Docker test docs

### Recommendations

1. **Add Docker Test Service:** Create `test` service in docker-compose.yml
2. **Organize Tests:** Separate into `tests/unit/`, `tests/integration/`, `tests/e2e/`
3. **Improve Coverage:** Add tests for low-coverage areas (firms_fires.py, cli.py)
4. **Add Frontend Tests:** Add basic Next.js tests (component tests, page tests)
5. **Document Docker Testing:** Update README with Docker test commands

---

**Next Phase:** Phase 1 - Test Strategy and Plan
