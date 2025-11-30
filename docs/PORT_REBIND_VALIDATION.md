# Port Rebind Validation Report

**Date:** 2025-01-XX
**Repository:** https://github.com/codethor0/human-behaviour-convergence
**Branch:** main
**HEAD Commit:** `8c8be75637d587fe64b6ebf7e3f4b7cfeed0b76d` - "docs: add data sources registry and system status report"

**Maintainer:** Thor Thor (codethor@gmail.com)

---

## Port Configuration Update

**Previous Ports:**
- Backend: 8000 (conflicted with AIWatchdog Staging Backend)
- Frontend: 3000 (conflicted with another frontend service)

**New Ports:**
- **Backend:** 8100 (host) → 8000 (container internal)
- **Frontend:** 3100 (host) → 3000 (container internal)

**Internal Container Ports:** Unchanged (8000 for backend, 3000 for frontend)

---

## Docker Status

### Build Status

**Status:** [PASS] PASS

**Command:** `docker compose build`

**Results:**
- [PASS] Backend container: Built successfully
- [PASS] Frontend container: Built successfully
- [PASS] Test container: Built successfully

### Services Running

**Status:** [PASS] PASS

**Command:** `docker compose up -d backend frontend`

**Results:**
- [PASS] Backend started and health check passed
- [PASS] Frontend started successfully
- [PASS] All services operational on new ports

### Health Checks

**Backend Health:**
```bash
curl http://localhost:8100/health
# Response: {"status":"ok"}
```

**Backend API Status:**
```bash
curl http://localhost:8100/api/forecasting/status
# Response: Valid JSON with system status
```

**Frontend:**
```bash
curl http://localhost:3100/
# Response: HTML page loads successfully
```

---

## Tests & Coverage

### Test Results

**Status:** [PASS] PASS

**Command:** `docker compose run --rm test`

**Results:**
- **Total Tests:** 71 passed
- **Warnings:** 3 (ValueWarning from statsmodels, expected)
- **Exit Code:** 0

### Coverage

**Status:** [PASS] PASS

**Coverage:** 82% (TOTAL: 2079 statements, 377 missed, 1702 covered)

**Minimum Requirements Met:**
- [PASS] Test count ≥ 68 (actual: 71)
- [PASS] Coverage ≥ 82% (actual: 82%)

---

## Hygiene Verification

### Prompt Files

**Status:** [PASS] PASS

- No files matching `*prompt*.md`, `*prompt*.txt`, `*prompt*.json`
- No `master_prompt*` or `*_prompt*` files found

### LLM Meta Text

**Status:** [PASS] PASS

- No LLM-specific instructional text found
- Only reference is in documentation describing that none were found

### Emojis

**Status:** [PASS] PASS

- Emoji check script passed
- No emojis found in any files

### Secrets

**Status:** [PASS] PASS

- No hardcoded secrets found
- All API keys referenced as environment variables only
- `.gitignore` properly configured

### Maintainer Info

**Status:** [PASS] PASS

**Maintainer Details (consistent across all files):**
- **Name:** Thor Thor
- **Email:** codethor@gmail.com
- **LinkedIn:** https://www.linkedin.com/in/thor-thor0

---

## Documentation Updates

**Updated Files:**
- `docker-compose.yml` - Port mappings and CORS origins
- `README.md` - Updated curl examples and port references
- `docs/RUNNING_WITH_DOCKER.md` - Updated all port references
- `docs/VALIDATION_REPORT.md` - Updated service URLs

**New Service URLs:**
- Backend API: http://localhost:8100
- Backend Docs: http://localhost:8100/docs
- Frontend UI: http://localhost:3100
- Forecast Page: http://localhost:3100/forecast

---

## Branch Status

**Active Branches:**
- [PASS] `origin/main` - Canonical primary branch
- [PASS] `origin/dependabot/*` - Active dependency PRs (5 branches)

**Candidate for Manual Deletion (GitHub UI):**
- [WARN] `origin/master` - Old default branch, fully merged into main

---

## Bug/Issue Status

### Bugs Found

**Status:** [PASS] None

All tests pass, services run successfully, no errors in logs.

### GitHub Issues

**Issues #8, #9, #10:**
- These are **roadmap milestones**, not bugs
- Correctly documented in `docs/ROADMAP.md`
- Status: Planned (as expected)

---

## Summary

**Port Rebind:** Successfully completed
**Docker Status:** All services operational on new ports
**Tests:** 71 passed, 82% coverage
**Hygiene:** All checks passed
**Documentation:** Updated with new port references

**The repository is in a zero-known-bug state under current test and Docker coverage, and the local Docker environment is accessible at http://localhost:8100 (backend) and http://localhost:3100 (frontend), without conflicting with other applications.**

---

**Report Generated:** 2025-01-XX
**Validated By:** Port Rebind Validation Process
