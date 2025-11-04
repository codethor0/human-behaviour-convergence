# Repository Audit & Improvement Plan
> Generated: November 4, 2025

## Executive Summary

**Status:** Repository is clean, functional, and well-structured
**Issues found:** 3 minor (organizational debt, outdated docs)
**Priority improvements:** 5 high-impact items identified

---

## 1. Current State Assessment

### Strengths
- **Security posture:** Excellent (Scorecard, Dependabot, community files all present)
- **CI/CD:** 3 workflows running (diagram render, app CI, tests, Scorecard)
- **Documentation:** Comprehensive (README, ETHICS, CONTRIBUTING, SECURITY, SUPPORT)
- **Code quality:** No linting errors, clean TypeScript/Python
- **Testing:** pytest structure in place with CI
- **App scaffold:** FastAPI + Next.js minimal but functional

### Issues Found

#### Minor Issues (3)
1. **SNAPSHOT-2024-11-03-1900-UTC.md** — Outdated status doc from initial commit (refers to v1.0.0, missing features now shipped)
2. **CHANGELOG.md** — "Unreleased" section lists items that are already done (notebooks, tests, results all exist)
3. **Branch confusion** — GitHub has both `main` and `master`; should consolidate to `main` only

#### No Critical Issues
- No security vulnerabilities detected
- No broken imports
- No duplicate or conflicting files
- No dead links in docs (all GitHub URLs valid)

---

## 2. Recommended Improvements

### Priority 1: Clean Up Documentation Debt (15 min)

**Action Items:**
- [ ] Update CHANGELOG.md: move completed items from "Unreleased" to new [0.2.0] section
- [ ] Archive or delete SNAPSHOT-2024-11-03-1900-UTC.md (outdated)
- [ ] Update CITATION.cff version from 0.1.0 → 0.2.0
- [ ] Add app/ scaffold and CI to CHANGELOG

**Impact:** Removes confusion, makes release history accurate

---

### Priority 2: Enhance Application (30-60 min)

**Action Items:**
- [ ] Add visual polish to frontend:
  - Tailwind CSS integration
  - Responsive layout
  - Dark mode toggle
- [ ] Add chart visualization (Recharts or Visx) for forecasts
- [ ] Create `/diagram` page that embeds the Mermaid diagram
- [ ] Add navigation header with links to diagram, results, GitHub

**Impact:** Makes app usable and impressive for demos

---

### Priority 3: Strengthen Testing & Quality (20 min)

**Action Items:**
- [ ] Add backend unit tests (pytest) for each endpoint
- [ ] Add frontend snapshot tests (if using Jest)
- [ ] Verify test coverage >80% and add coverage badge to README
- [ ] Add pre-commit hooks for Python (black, ruff) and TypeScript (prettier, eslint)

**Impact:** Increases reliability, professional credibility

---

### Priority 4: GitHub Repository Settings (5 min)

**Action Items:**
- [ ] Delete `master` branch (keep only `main`)
- [ ] Enable GitHub Pages (Settings → Pages → main branch / root)
- [ ] Add repository description: "Population-scale behavioural forecasting in a zero-restriction data regime"
- [ ] Add topics: `mermaid`, `forecasting`, `ai-ethics`, `population-scale`, `fastapi`, `nextjs`
- [ ] Upload social preview banner (assets/social-preview.svg exists)

**Impact:** Better discovery, cleaner history

---

### Priority 5: Polish Documentation (20 min)

**Action Items:**
- [ ] Add "Getting Started" video or animated GIF to README
- [ ] Create ARCHITECTURE.md explaining system design
- [ ] Add API documentation (FastAPI auto-docs already available at `/docs`)
- [ ] Link to API docs in README: `http://localhost:8000/docs` when running locally
- [ ] Add Binder or Colab badge for notebooks once environment is stable

**Impact:** Lowers barrier to entry for contributors

---

## 3. File Organization Review

### Current Structure (Good)
```
.
- .github/                 Comprehensive (workflows, templates, community)
- app/                     Clean separation (backend, frontend)
  - backend/              FastAPI with .gitignore, requirements
  - frontend/             Next.js TypeScript with clean structure
- diagram/                Source .mmd and generated assets
- docs/                   App plan documented
- notebooks/              Demo notebook present
- results/                CSV data files
- tests/                  pytest structure
- CHANGELOG.md            Needs update
- CITATION.cff            Version bump needed
- CODE_OF_CONDUCT.md      present
- CONTRIBUTING.md         present
- ETHICS.md               present
- LICENSE                 present
- README.md               Comprehensive
- SECURITY.md             present
- SUPPORT.md              present
- requirements*.txt       present
```

### Suggestions
- Move `SNAPSHOT-2024-11-03-1900-UTC.md` to `docs/archive/` or delete
- Consider `docs/ARCHITECTURE.md` for system design
- Consider `.pre-commit-config.yaml` for automated quality checks

---

## 4. Dependency Management

### Backend (Python)
Clean and minimal:
- fastapi, uvicorn, pandas (backend)
- pytest, pytest-cov (dev)
- All versions pinned or with >=

### Frontend (Node)
Clean and minimal:
- next, react, react-dom
- typescript, @types/* (dev)

**Recommendation:** Add `package-lock.json` to app-ci.yml cache (already done)

---

## 5. Security & Compliance

### Already Implemented
- OpenSSF Scorecard workflow
- Dependabot for GitHub Actions
- SECURITY.md with responsible disclosure
- ETHICS.md with privacy and IRB details
- CODEOWNERS file

### Optional Enhancements
- [ ] Add CodeQL workflow for Python/TypeScript scanning
- [ ] Add branch protection rules (require PR reviews, status checks)
- [ ] Enable secret scanning and push protection in Settings

---

## 6. CI/CD Pipeline

### Current Workflows (All Functional)
1. **render-diagram.yml** — Auto-renders Mermaid on push
2. **app-ci.yml** — Backend health check + frontend build
3. **test.yml** — Python tests with coverage
4. **scorecard.yml** — Security scanning

### Suggestions
- [ ] Add workflow_dispatch triggers for manual runs
- [ ] Add caching for Python deps in test.yml (like app-ci.yml)
- [ ] Consider adding a "Release" workflow that tags and publishes to PyPI (future)

---

## 7. Implementation Plan

### Phase 1: Quick Wins (30 min)
1. Update CHANGELOG.md with [0.2.0] release notes
2. Update CITATION.cff version
3. Delete or archive SNAPSHOT file
4. Delete `master` branch on GitHub
5. Enable Pages, add description/topics

### Phase 2: App Enhancement (2-3 hours)
1. Add Tailwind CSS to frontend
2. Create chart visualization for forecasts
3. Add diagram embed page
4. Add navigation and polish

### Phase 3: Quality & Testing (1 hour)
1. Add backend unit tests
2. Set up pre-commit hooks
3. Verify test coverage

### Phase 4: Documentation (1 hour)
1. Create ARCHITECTURE.md
2. Add API docs link to README
3. Record demo GIF or video

---

## 8. Success Metrics

After completing improvements, the repository should have:
- 100% accurate documentation (no outdated files)
- Single default branch (`main` only)
- GitHub Pages enabled with live diagram
- Polished web app with charts and navigation
- >80% test coverage
- Pre-commit hooks enforcing code quality
- Clear ARCHITECTURE.md for onboarding

---

## Next Steps

**Choose your path:**

**Option A: Quick cleanup (30 min)**
Focus on Phase 1 only — update docs, clean branches, enable Pages

**Option B: Full polish (4-5 hours)**
Execute all 4 phases — production-ready repository with impressive app

**Option C: Targeted improvements**
Pick specific items from Priority list based on your goals

---

## Appendix: Commands Reference

### Delete master branch
```bash
git push origin --delete master
```

### Enable Pages (via API)
```bash
curl -X POST \
  -H "Authorization: token YOUR_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/codethor0/human-behaviour-convergence/pages \
  -d '{"source":{"branch":"main","path":"/"}}'
```

### Generate coverage badge
```bash
pytest tests/ --cov --cov-report=term --cov-report=html
# Use https://shields.io for badge generation
```

---

**End of Audit** — Ready for implementation
