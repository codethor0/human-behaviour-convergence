# Patch Report

**Repository:** human-behaviour-convergence  
**Branch:** chore/spelling-behavior-standardization  
**Date:** 2025-11-10  
**Phase:** 2-3 (Targeted Fixes & Re-run)  

## Summary

Fixed **high-priority** Semgrep security findings and **low-priority** TestClient deprecation warnings. All tests pass (33/33, no warnings), and Semgrep reports 0 findings.

---

## Fixes Applied

### 1. Semgrep Security Findings - `globals()` Usage (High Priority)

**Files Changed:**
- `app/backend/app/main.py`

**Root Cause:**
Semgrep flagged 3 instances of `globals().get()` as security vulnerabilities because using non-static data as an index to `globals()` can allow arbitrary code execution. While the actual keys were static strings (not user input), this pattern should be avoided for better security posture.

**Specific Changes:**

1. **Line 325** - `_get_results_dir()` function:
   ```python
   # Before:
   return globals().get("RESULTS_DIR")
   
   # After:
   return RESULTS_DIR  # Direct module-level variable access
   ```

2. **Line 341** - `_get_cache_limit()` function:
   ```python
   # Before:
   return int(globals().get("MAX_CACHE_SIZE", 0))
   
   # After:
   return int(MAX_CACHE_SIZE)  # Direct module-level variable access
   ```

3. **Lines 555-556** - `get_cache_status()` endpoint:
   ```python
   # Before:
   hits = globals().get("_cache_hits", 0)
   misses = globals().get("_cache_misses", 0)
   
   # After:
   hits = _cache_hits  # Direct module-level variable access
   misses = _cache_misses  # Direct module-level variable access
   ```

4. **Line 158** - Debug message:
   ```python
   # Before:
   f"max_cache={globals().get('MAX_CACHE_SIZE')} id={id(globals())}"
   
   # After:
   f"max_cache={MAX_CACHE_SIZE} id={id(globals())}"
   ```

**Why It's Safe:**
- All variables (`RESULTS_DIR`, `MAX_CACHE_SIZE`, `_cache_hits`, `_cache_misses`) are module-level variables defined at the top of the file
- Direct access is equivalent to `globals().get()` for module-level variables
- The shim module override logic still works (checks `vars(main_mod)` first before fallback)
- No functional behavior change, just improved security posture

**Tests:**
- All 33 tests pass
- `test_cache_eviction` passes (verifies cache limit logic still works)
- `test_cache_status_endpoint` passes (verifies cache stats endpoint still works)
- `test_find_results_dir` passes (verifies RESULTS_DIR logic still works)

**Verification:**
- Semgrep reports **0 findings** (down from 3)
- Security scan passes cleanly

---

### 2. TestClient Deprecation Warnings (Low Priority)

**Files Changed:**
- `tests/test_public_api.py`

**Root Cause:**
The `timeout` parameter in `TestClient.get()` is deprecated in Starlette. TestClient doesn't make real network requests, so the timeout parameter is unnecessary.

**Specific Changes:**

1. **Line 38** - `test_wiki_latest_endpoint`:
   ```python
   # Before:
   response = client.get("/api/public/wiki/latest?date=2024-11-04", timeout=5.0)
   
   # After:
   response = client.get("/api/public/wiki/latest?date=2024-11-04")
   ```

2. **Line 66** - `test_osm_latest_endpoint`:
   ```python
   # Before:
   response = client.get("/api/public/osm/latest?date=2024-11-04", timeout=5.0)
   
   # After:
   response = client.get("/api/public/osm/latest?date=2024-11-04")
   ```

3. **Line 106** - `test_synthetic_score_endpoint`:
   ```python
   # Before:
   response = client.get("/api/public/synthetic_score/9/2024-11-04", timeout=5.0)
   
   # After:
   response = client.get("/api/public/synthetic_score/9/2024-11-04")
   ```

**Why It's Safe:**
- `TestClient` doesn't make real network requests (in-process calls)
- Removing `timeout` parameter doesn't affect test behavior
- Matches current Starlette best practices

**Tests:**
- All 7 tests in `test_public_api.py` pass
- No deprecation warnings in test output

**Verification:**
- Test suite runs cleanly with **0 warnings** (down from 3 deprecation warnings)

---

## Test Results After Fixes

### Test Suite: ✅ PASSING (33/33)

**Command:** `pytest tests/ --cov --cov-report=term-missing -v`

**Result:**
- ✅ 33 tests passed
- ✅ 0 warnings (fixed 3 deprecation warnings)
- ✅ 77% coverage (unchanged)
- ✅ All test files pass

### Lint Checks: ✅ PASSING

**Ruff:**
```bash
ruff check app/backend tests hbc --ignore F401,F402,F403,F405,F841,E402
```
✅ All checks passed

**Black:**
```bash
black --check app/backend tests hbc
```
✅ All files properly formatted

**Semgrep:**
```bash
semgrep --config=auto app/backend tests hbc
```
✅ **0 findings** (fixed 3 security findings)

**Mypy:**
```bash
mypy --strict app/backend tests hbc
```
⚠️ 44 type checking errors (non-blocking in CI, not addressed in this phase)

---

## Files Changed

1. **app/backend/app/main.py** (5 lines changed)
   - Removed `globals().get()` calls, replaced with direct variable access
   - Added comments explaining the change

2. **tests/test_public_api.py** (3 lines changed)
   - Removed `timeout=5.0` parameter from TestClient calls

**Total Changes:** 2 files, 8 lines modified

---

## Commands Run for Verification

1. **Tests:**
   ```bash
   pytest tests/ --cov --cov-report=term-missing -v
   ```
   ✅ **Result:** 33 passed, 0 warnings

2. **Lint:**
   ```bash
   ruff check app/backend tests hbc --ignore F401,F402,F403,F405,F841,E402
   black --check app/backend tests hbc
   ```
   ✅ **Result:** All checks passed

3. **Security Scan:**
   ```bash
   semgrep --config=auto app/backend tests hbc
   ```
   ✅ **Result:** 0 findings (previously 3)

---

## Remaining Known Issues

### Mypy Type Errors (Non-blocking)

**Status:** Not addressed in this phase (non-blocking in CI)

**Issue:** 44 type checking errors with `mypy --strict`
- Missing type annotations in test functions (12 errors)
- Missing library stubs (`pandas`, `requests`, `h3`) (14 errors)
- Missing type parameters for generic types (10 errors)
- Type incompatibility errors (4 errors)
- Other type errors (4 errors)

**Recommendation:** Address in future phase when type safety improvements are prioritized. Can install stub packages (`pandas-stubs`, `types-requests`) and add return type annotations to test functions.

---

## Final Status

✅ **All high-priority issues fixed**
- Semgrep security findings: **0** (down from 3)
- TestClient deprecation warnings: **0** (down from 3)

✅ **Test suite status:**
- Tests: **33/33 passing** (100%)
- Warnings: **0** (100% clean)
- Coverage: **77%** (maintained)

✅ **Lint status:**
- Ruff: **Passing**
- Black: **Passing**
- Semgrep: **0 findings**

⚠️ **Non-blocking issues remaining:**
- Mypy type errors: 44 (addressed in future phase)

---

## Verification Commands

All fixes verified with these commands:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run tests (should pass with 0 warnings)
pytest tests/ --cov --cov-report=term-missing -v

# Run linters (should pass)
ruff check app/backend tests hbc --ignore F401,F402,F403,F405,F841,E402
black --check app/backend tests hbc

# Run security scan (should report 0 findings)
semgrep --config=auto app/backend tests hbc
```

All commands pass on the final commit.

