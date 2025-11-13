# Pull Request Description

## Summary

Fixed high-priority Semgrep security findings and low-priority TestClient deprecation warnings. All tests pass (33/33, 0 warnings), and Semgrep reports 0 findings.

## What Changed

### Security Fixes (High Priority)
- **Fixed 3 Semgrep security findings** about dangerous `globals()` usage in `app/backend/app/main.py`
  - Replaced `globals().get()` calls with direct module-level variable access
  - No functional behavior change, improved security posture
  - Verified: Semgrep reports 0 findings (down from 3)

### Deprecation Warnings (Low Priority)
- **Fixed 3 TestClient deprecation warnings** in `tests/test_public_api.py`
  - Removed deprecated `timeout` parameter from TestClient calls
  - Verified: Test suite runs with 0 warnings (down from 3)

## Files Changed

- `app/backend/app/main.py` - Replaced `globals().get()` with direct variable access (5 changes)
- `tests/test_public_api.py` - Removed deprecated `timeout` parameter (3 changes)

**Total:** 2 files, 8 lines modified

## Verification

### Tests
```bash
pytest tests/ --cov --cov-report=term-missing -v
```
✅ **Result:** 33 passed, 0 warnings

### Linters
```bash
ruff check app/backend tests hbc --ignore F401,F402,F403,F405,F841,E402
black --check app/backend tests hbc
```
✅ **Result:** All checks passed

### Security Scan
```bash
semgrep --config=auto app/backend tests hbc
```
✅ **Result:** 0 findings (previously 3)

## Risks

**None identified.**

- Changes are minimal and targeted
- No API changes or breaking changes
- All tests pass with no warnings
- Direct variable access is equivalent to `globals().get()` for module-level variables
- Removing `timeout` parameter doesn't affect TestClient behavior (in-process calls)

## Breaking Changes

None.

## Remaining Issues

### Mypy Type Errors (Non-blocking)
44 type checking errors remain but are non-blocking in CI (`continue-on-error: true`). Can be addressed in a future phase.

**Recommendation:** Install stub packages (`pandas-stubs`, `types-requests`) and add return type annotations to test functions when type safety improvements are prioritized.

## Testing

1. **Test suite:** Run `pytest tests/ -v` (all 33 tests pass)
2. **Linters:** Run `ruff check` and `black --check` (all pass)
3. **Security scan:** Run `semgrep --config=auto app/backend tests hbc` (0 findings)

All commands pass on the final commit.

## Follow-up

Consider addressing mypy type errors in a future phase:
- Install missing stub packages
- Add return type annotations to test functions
- Fix generic type parameters

---

**Status:** ✅ Ready for review  
**Priority:** High (security fixes)  
**Type:** Bug fix (security & deprecation)

