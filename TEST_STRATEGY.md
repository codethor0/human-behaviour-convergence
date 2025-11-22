# Test Strategy

**Repository:** human-behaviour-convergence
**Date:** 2025-11-10
**Phase:** 1 - Test Strategy and Plan

---

## Overview

This document defines a layered test strategy for the human-behaviour-convergence repository, covering unit tests, integration tests, and end-to-end tests across Python backend, Next.js frontend, and CLI components.

---

## Test Layers

### 1. Unit Tests (Fast Path - Run on Every Commit)

**Purpose:** Test pure logic, functions, helpers, and small components in isolation.

**Scope:**
- Pure functions (`hbc/forecasting.py`)
- Data transformation logic
- CLI argument parsing (`hbc/cli.py`)
- Connector data processing (without HTTP calls)
- Helper utilities

**Framework:** pytest

**Location:** `tests/unit/`

**Naming Convention:** `test_*.py` (e.g., `test_forecasting.py`, `test_cli.py`)

**Execution Time:** < 30 seconds

**Mocking Strategy:**
- Mock external dependencies (HTTP clients, file I/O)
- Use fixtures for test data
- No real network calls
- No real database/file system (use tempdir)

**Examples:**
- `test_forecasting.py` - Forecasting logic tests (already exists)
- `test_cli.py` - CLI argument parsing (already exists)
- New: Unit tests for connector data processing (parsing, validation)

---

### 2. Integration Tests (Medium Path - Run on PR/Merge)

**Purpose:** Test components working together, API endpoints, data connectors with mocked HTTP, and database/file system interactions.

**Scope:**
- FastAPI endpoints (with TestClient)
- Data connectors (with mocked HTTP responses)
- Cache system (file-based CSV caching)
- CLI execution (with test data)
- API routes and middleware

**Framework:** pytest + FastAPI TestClient

**Location:** `tests/integration/`

**Naming Convention:** `test_*.py` (e.g., `test_api_backend.py`, `test_public_api.py`)

**Execution Time:** < 2 minutes

**Mocking Strategy:**
- Mock HTTP requests (using `responses` or `unittest.mock.patch`)
- Use temporary directories for file I/O
- Mock external APIs (Wiki, OSM, FIRMS)
- Real FastAPI app instance with test client

**Examples:**
- `test_api_backend.py` - FastAPI backend tests (already exists)
- `test_public_api.py` - Public API endpoints (already exists)
- `test_connectors.py` - Data connectors with mocked HTTP (already exists)

---

### 3. End-to-End Tests (Slow Path - Run on Demand/Nightly)

**Purpose:** Test full system behavior, frontend + backend integration, and user workflows.

**Scope:**
- Full stack integration (Next.js frontend + FastAPI backend)
- CLI end-to-end workflows
- Dockerized test execution
- Multi-component interactions

**Framework:** pytest + Playwright (or similar E2E framework)

**Location:** `tests/e2e/`

**Naming Convention:** `test_*.py` (e.g., `test_full_stack.py`, `test_cli_e2e.py`)

**Execution Time:** < 10 minutes (target)

**Mocking Strategy:**
- Minimal mocking (only external APIs)
- Real backend server
- Real frontend build
- Real HTTP communication between frontend and backend

**Examples:**
- New: `test_full_stack.py` - Frontend calls backend, displays results
- New: `test_cli_e2e.py` - CLI syncs data, generates forecasts end-to-end

---

## Test Directory Structure

### Current Structure
```
tests/
  test_api_backend.py
  test_cli.py
  test_connectors.py
  test_forecasting.py
  test_public_api.py
  test_no_emoji_script.py
  README.md
```

### Proposed Structure
```
tests/
  unit/              # Fast unit tests (< 30s)
    test_forecasting.py
    test_cli.py
    test_data_processing.py  # New
    conftest.py      # Shared fixtures

  integration/       # Integration tests (< 2min)
    test_api_backend.py
    test_public_api.py
    test_connectors.py
    test_cache.py    # New: Cache system tests
    conftest.py      # Shared fixtures (TestClient, temp dirs)

  e2e/              # End-to-end tests (< 10min)
    test_full_stack.py  # New: Frontend + Backend
    test_cli_e2e.py     # New: CLI workflows
    conftest.py      # E2E fixtures (docker compose, servers)

  fixtures/         # Shared test data
    sample_forecasts.csv
    sample_metrics.csv
    sample_wiki_data.json
    sample_osm_data.xml

  README.md         # Updated test documentation
```

**Migration Plan:**
- Move existing files to appropriate directories
- Keep backward compatibility with pytest discovery (all `test_*.py` files)
- Update imports if needed

---

## Test Frameworks

### Python (Backend/CLI)

**Primary Framework:** pytest

**Key Plugins:**
- `pytest-cov` - Coverage reporting
- `pytest-xdist` - Parallel execution (`-n auto`)
- `pytest-asyncio` - Async test support (if needed)
- `pytest-mock` - Enhanced mocking (if needed)

**Configuration:**
- Store in `pyproject.toml` under `[tool.pytest.ini_options]`
- Or create `pytest.ini` for explicit configuration

**Test Discovery:**
- Default: `test_*.py` files in `tests/` and subdirectories
- Markers: Use pytest markers for test categorization
  ```python
  @pytest.mark.unit
  @pytest.mark.integration
  @pytest.mark.e2e
  ```

### TypeScript/JavaScript (Frontend)

**Framework:** Jest or Vitest (recommended: Vitest for Vite/Next.js compatibility)

**Location:** `app/frontend/`

**Test Files:**
- Component tests: `app/frontend/src/**/*.test.tsx`
- Page tests: `app/frontend/src/pages/**/*.test.tsx`
- Utility tests: `app/frontend/src/**/*.test.ts`

**Configuration:**
- Add to `app/frontend/package.json` scripts
- Add `vitest.config.ts` or `jest.config.js`

**Note:** Frontend tests are not yet implemented (identified as gap)

---

## Canonical Test Commands

### Local Execution (Without Docker)

**Fast Path (Unit Tests Only):**
```bash
pytest tests/unit/ -v
```

**Medium Path (Unit + Integration):**
```bash
pytest tests/unit/ tests/integration/ -v --cov --cov-report=term-missing
```

**Full Suite (All Tests):**
```bash
pytest tests/ -v --cov --cov-report=term-missing --cov-report=xml -n auto
```

**With Markers:**
```bash
# Unit tests only
pytest -m unit -v

# Integration tests only
pytest -m integration -v

# E2E tests only
pytest -m e2e -v
```

### Docker Execution (Recommended)

**Standardized Command:**
```bash
docker compose run --rm test
```

This will be implemented in Phase 2.

**Alternative (Direct Docker):**
```bash
docker build -t hbc-test .
docker run --rm hbc-test pytest tests/ -v
```

---

## Test Execution Strategy

### On Every Commit (Fast Path)

**Command:**
```bash
pytest tests/unit/ -v -n auto
```

**What Runs:**
- Unit tests only (< 30 seconds)
- Linting (ruff, black)
- Type checking (mypy, non-blocking)

**CI Trigger:** Pre-commit hooks + quick CI job

---

### On Pull Request (Medium Path)

**Command:**
```bash
pytest tests/unit/ tests/integration/ --cov --cov-report=term-missing --cov-report=xml -v -n auto
```

**What Runs:**
- Unit tests
- Integration tests
- Coverage reporting (threshold: 65%)
- Security scan (semgrep)
- Linting and formatting

**CI Trigger:** `.github/workflows/test.yml` and `.github/workflows/ci.yml`

---

### On Merge to Main (Full Suite)

**Command:**
```bash
pytest tests/ -v --cov --cov-report=term-missing --cov-report=xml -n auto
```

**What Runs:**
- All tests (unit, integration, e2e)
- Full coverage report
- Quality gates (complexity, maintainability)
- Matrix testing (Python 3.10, 3.11, 3.12)

**CI Trigger:** `.github/workflows/test.yml` (on push to main)

---

### On Demand / Nightly (E2E Tests)

**Command:**
```bash
pytest tests/e2e/ -v --cov
```

**What Runs:**
- End-to-end tests only
- Full stack integration
- Dockerized execution

**CI Trigger:** Scheduled workflow or manual trigger

---

## Test Data and Fixtures

### Fixture Strategy

**Pytest Fixtures (conftest.py):**
- `temp_results_dir` - Temporary directory for test data
- `client` - FastAPI TestClient instance
- `mock_wiki_response` - Mocked Wiki API response
- `mock_osm_response` - Mocked OSM API response
- `mock_firms_response` - Mocked FIRMS API response
- `sample_forecasts_df` - Sample pandas DataFrame for forecasts
- `sample_metrics_df` - Sample pandas DataFrame for metrics

**Test Data Files:**
- `tests/fixtures/sample_forecasts.csv` - Sample forecast data
- `tests/fixtures/sample_metrics.csv` - Sample metrics data
- `tests/fixtures/sample_wiki_data.json` - Sample Wiki API response
- `tests/fixtures/sample_osm_data.xml` - Sample OSM XML data

**Principles:**
- Keep fixtures small and focused
- Use realistic but minimal data
- Make fixtures reusable across test files
- Document fixture purpose and structure

---

## Test Naming Conventions

### File Naming
- Unit tests: `test_<module_name>.py` (e.g., `test_forecasting.py`)
- Integration tests: `test_<component>_integration.py` (e.g., `test_api_integration.py`)
- E2E tests: `test_<feature>_e2e.py` (e.g., `test_full_stack_e2e.py`)

### Test Function Naming
- Use descriptive names: `test_<what>_<expected_behavior>`
- Examples:
  - `test_forecast_shape_returns_correct_tuple`
  - `test_cache_eviction_when_limit_exceeded`
  - `test_api_endpoint_returns_422_on_invalid_input`

### Test Class Naming
- Use `Test<Component>` pattern for grouped tests
- Examples: `TestWikiPageviewsSync`, `TestPublicDataEndpoints`

---

## Coverage Strategy

### Coverage Targets

**Overall Coverage:** 77% (current), maintain ≥ 75%

**Module-Specific Targets:**
- Critical modules (app/backend/app/main.py): ≥ 70% (current: 70%)
- Data connectors: ≥ 70% (current: 48-72%)
- CLI tools: ≥ 60% (current: 44%)
- Pure functions: ≥ 90% (current: 95% for forecasting)

**Coverage Threshold (CI):** 65% (from quality-gates workflow)

### Coverage Exclusions

**Appropriate Exclusions:**
- Type checking imports (`if TYPE_CHECKING:`)
- Debug/development code (`if os.getenv("DEBUG")`)
- Exception-only code paths (unlikely error handlers)
- Test files themselves

**Configuration:**
- Use `.coveragerc` or `[tool.coverage.run]` in `pyproject.toml`

---

## Test Quality Principles

### 1. Deterministic Tests
- No reliance on random data (use fixed seeds)
- No reliance on timestamps (use mock time if needed)
- No reliance on external services (mock HTTP/file I/O)

### 2. Fast Execution
- Unit tests: < 1 second each
- Integration tests: < 10 seconds each
- E2E tests: < 60 seconds each

### 3. Clear Assertions
- Use descriptive assertion messages
- Test one behavior per test function
- Use pytest's built-in assertion introspection

### 4. Isolation
- Tests should not depend on each other
- Tests should not depend on execution order
- Use fixtures for setup/teardown, not global state

### 5. Maintainability
- Keep tests simple and readable
- Use helper functions for common patterns
- Document complex test logic

---

## Docker Test Environment

### Test Service in docker-compose.yml

**Proposed Service:**
```yaml
services:
  test:
    build:
      context: .
      dockerfile: Dockerfile
      target: builder  # Use builder stage with all deps
    volumes:
      - .:/app
      - /app/.pytest_cache  # Exclude pytest cache from mount
    working_dir: /app
    command: pytest tests/ -v --cov --cov-report=term-missing
    environment:
      - CI=true
      - PYTHONUNBUFFERED=1
    networks:
      - default
```

**Usage:**
```bash
# Run all tests
docker compose run --rm test

# Run unit tests only
docker compose run --rm test pytest tests/unit/ -v

# Run with coverage
docker compose run --rm test pytest tests/ --cov --cov-report=html
```

**Benefits:**
- Consistent environment across developers
- No local Python version conflicts
- Matches CI environment

---

## Frontend Testing Strategy

### Phase 1: Component Tests (Not Yet Implemented)

**Framework:** Vitest + React Testing Library

**Target:**
- Test individual React components
- Test page rendering
- Test API integration (with mocked backend)

**Location:** `app/frontend/src/**/*.test.tsx`

**Example:**
```typescript
import { render, screen } from '@testing-library/react'
import HomePage from '../pages/index'

test('renders Behavior Convergence Explorer title', () => {
  render(<HomePage />)
  expect(screen.getByText('Behavior Convergence Explorer')).toBeInTheDocument()
})
```

### Phase 2: E2E Tests (Future)

**Framework:** Playwright or Cypress

**Target:**
- Test full user workflows
- Test frontend + backend integration
- Test in real browser environment

**Location:** `tests/e2e/frontend/`

---

## Known Limitations and Workarounds

### 1. Network-Dependent Tests
**Issue:** Some tests may need network access for external APIs
**Workaround:** Mock all HTTP requests using `responses` or `unittest.mock`
**Status:** [PASS] Already implemented (tests use mocking)

### 2. File System Tests
**Issue:** Tests may need to read/write files
**Workaround:** Use `tempfile.TemporaryDirectory` or pytest's `tmpdir` fixture
**Status:** [PASS] Already implemented (tests use temp directories)

### 3. Frontend Tests
**Issue:** No frontend tests currently exist
**Workaround:** Add basic component tests as part of this workflow
**Status:** [WARN] To be implemented

### 4. E2E Tests
**Issue:** No E2E tests currently exist
**Workaround:** Add basic E2E tests for critical user flows
**Status:** [WARN] To be implemented

---

## Success Criteria

### Phase 2 (Docker Test Environment)
- [PASS] `docker compose run --rm test` works reliably
- [PASS] Tests pass in Docker environment
- [PASS] Test execution time < 2 minutes for unit+integration

### Phase 3 (Test Augmentation)
- [PASS] Unit test coverage ≥ 80% for core modules
- [PASS] Integration test coverage ≥ 70% for API endpoints
- [PASS] At least 1 E2E test for critical user flow

### Phase 4 (CI Integration)
- [PASS] CI runs canonical test command
- [PASS] Tests pass reliably in CI
- [PASS] Coverage reports uploaded correctly

### Final State
- [PASS] All tests pass (unit, integration, e2e)
- [PASS] Tests run in Docker consistently
- [PASS] Tests documented in README
- [PASS] New contributors can run tests with one command

---

**Next Phase:** Phase 2 - Dockerized Test Environment
