# Bug Summary

**Repository:** human-behaviour-convergence  
**Branch:** chore/spelling-behavior-standardization  
**Date:** 2025-11-10  
**Baseline Run:** Phase 1  

## Test Results

### Tests: ✅ PASSING (33/33)

**Command:** `pytest tests/ --cov --cov-report=term-missing -v`

**Result:** All 33 tests pass successfully
- 33 passed
- 3 warnings (deprecation warnings about TestClient timeout parameter)
- Coverage: 77% overall

**Test Breakdown:**
- `test_api_backend.py`: 15 tests passed
- `test_cli.py`: 2 tests passed
- `test_connectors.py`: 4 tests passed
- `test_forecasting.py`: 3 tests passed
- `test_public_api.py`: 8 tests passed
- `test_no_emoji_script.py`: 0 tests (empty file)

**Warnings:**
- 3 deprecation warnings from `starlette.testclient` about `timeout` argument
  - `tests/test_public_api.py::test_wiki_latest_endpoint`
  - `tests/test_public_api.py::test_osm_latest_endpoint`
  - `tests/test_public_api.py::test_synthetic_score_endpoint`
  - **Root Cause:** Using deprecated `timeout` parameter in TestClient
  - **Impact:** Non-blocking, but should be removed for future compatibility

---

## Lint Results

### Ruff: ✅ PASSING

**Command:** `ruff check app/backend tests hbc --ignore F401,F402,F403,F405,F841,E402`

**Result:** All checks passed!

---

### Black: ✅ PASSING

**Command:** `black --check app/backend tests hbc`

**Result:** All 13 files would be left unchanged (properly formatted)

---

### Mypy: ❌ FAILING (Non-blocking in CI)

**Command:** `mypy --strict app/backend tests hbc`

**Result:** 44 type checking errors

**Note:** In CI workflow, mypy runs with `continue-on-error: true`, so these errors don't fail the build.

#### Failure Buckets

**1. Missing type annotations in test functions (12 errors)**
- `tests/test_forecasting.py`: 3 functions missing `-> None`
- `tests/test_connectors.py`: 5 functions missing `-> None`
- `tests/test_cli.py`: 2 functions missing type annotations

**Root Cause:** Test functions lack return type annotations required by `--strict` mode
**Hypothesis:** These are test functions that should be annotated with `-> None`

**2. Missing library stubs (14 errors)**
- `pandas`: Missing stubs (multiple files)
- `requests`: Missing stubs (multiple files)
- `h3`: Missing stubs or py.typed marker

**Root Cause:** Third-party libraries don't have type stubs installed
**Hypothesis:** Need to install `pandas-stubs`, `types-requests`, or use `mypy --install-types`

**3. Missing type parameters for generic types (10 errors)**
- `Dict` without type parameters (should be `Dict[str, Any]` or similar)
- `Callable` without type parameters

**Root Cause:** Generic types used without type parameters required by `--strict` mode
**Hypothesis:** Should specify type parameters like `Dict[str, Any]`, `Callable[[], None]`

**4. Type incompatibility errors (4 errors)**
- `connectors/osm_changesets.py`: `float()` called with `str | None` (should check None first)
- `app/backend/app/routers/public.py`: Incompatible type assignments (connector type confusion)

**Root Cause:** Type mismatches that could cause runtime errors
**Hypothesis:** Need None checks or correct type annotations

**5. Other type errors (4 errors)**
- `app/backend/app/main.py`: Returning `Any` from function declared to return `Path | None`
- `app/__init__.py`: Unused `type: ignore` comment

**Root Cause:** Type inference issues or incorrect annotations
**Hypothesis:** Fix return types or remove unused ignore comments

---

### Semgrep: ⚠️ SECURITY FINDINGS (3 blocking)

**Command:** `semgrep --config=auto app/backend tests hbc`

**Result:** 3 code findings (all blocking)

#### Failure Buckets

**1. Dangerous use of `globals()` (3 findings)**
- **Location:** `app/backend/app/main.py`
- **Lines:** 341, 555, 556
- **Rule:** `python.lang.security.dangerous-globals-use.dangerous-globals-use`
- **Severity:** High (allows arbitrary code execution)

**Root Cause:** Using `globals().get()` with non-static data as index
- Line 341: `globals().get("MAX_CACHE_SIZE", 0)`
- Line 555: `globals().get("_cache_hits", 0)`
- Line 556: `globals().get("_cache_misses", 0)`

**Hypothesis:** These are accessing module-level variables in a way that Semgrep flags as dangerous. However, they're using static string keys, not user input. This is a false positive for the pattern, but the code could be refactored to avoid `globals()` for better clarity and security posture.

**Impact:** Security tool flags this as high risk, but actual risk is low since keys are static strings, not user input.

**Recommendation:** Refactor to use module-level variables directly or a configuration class instead of `globals().get()`.

---

## Summary

### ✅ Passing Checks
- **Tests:** 33/33 passing (77% coverage)
- **Ruff:** All checks pass
- **Black:** All files properly formatted

### ⚠️ Issues Found
- **Mypy:** 44 type checking errors (non-blocking in CI)
  - Mostly missing type annotations and stub packages
  - Should be fixed for better type safety but not urgent
- **Semgrep:** 3 security findings (blocking)
  - All related to `globals()` usage
  - False positive pattern match but should be refactored

### 📊 Priority Assessment

**High Priority:**
1. **Semgrep security findings** - Should be addressed to improve security posture
   - Refactor `globals().get()` calls in `app/backend/app/main.py`

**Medium Priority:**
2. **Mypy type errors** - Improve type safety
   - Install missing stub packages (`pandas-stubs`, `types-requests`)
   - Add return type annotations to test functions
   - Fix generic type parameters

**Low Priority:**
3. **Test warnings** - Deprecation warnings in TestClient
   - Remove `timeout` parameter from TestClient calls (3 occurrences)

---

## Next Steps

1. Fix Semgrep security findings (high priority)
2. Address mypy type errors (medium priority)
3. Remove deprecated TestClient `timeout` parameter (low priority)

