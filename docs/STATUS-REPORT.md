# Status Report - Phase 0 Inventory
**Date:** 2025-11-10
**Branch:** `chore/spelling-behavior-standardization`
**Purpose:** Inventory and consistency sweep before multi-phase hardening

---

## Executive Summary

The repository is in a **functional but inconsistent** state. Core features (diagram rendering, FastAPI backend, Next.js frontend, tests, CI workflows) are implemented and working, but documentation contains conflicting information about version numbers, branch names, and project status.

**Key Finding:** The codebase is more complete than the documentation suggests. Several "planned" items in CHANGELOG are already implemented.

---

## Current State Overview

### What Exists and Works

✅ **Diagram System**
- Source Mermaid file: `diagram/behaviour-convergence.mmd`
- Rendered assets: `diagram/behaviour-convergence.svg`, `.png`
- CI workflow: `.github/workflows/render-diagram.yml` (auto-renders on push)
- Interactive HTML: `docs/interactive-diagram.html`
- GitHub Pages deployment: `.github/workflows/deploy-pages.yml`

✅ **Application Stack**
- FastAPI backend: `app/backend/app/main.py` (functional with routers)
- Next.js frontend: `app/frontend/` (TypeScript, configured)
- CLI tool: `hbc/cli.py` (syncing public data)
- Data connectors: `connectors/` (Wiki, OSM, FIRMS)

✅ **Testing & CI**
- Test suite: `tests/` (api_backend, connectors, public_api, cli, forecasting)
- Test workflow: `.github/workflows/test.yml` (runs on Python 3.10-3.12)
- CI workflow: `.github/workflows/ci.yml` (lint, type-check, security-scan, sbom-scan)
- 13 active workflows total (including CodeQL, Dependabot, scorecard, etc.)

✅ **Data & Results**
- Results directory: `results/` (contains forecasts.csv, ground_truth.csv, metrics.csv, intervals.csv, manifest.json)
- Public data snapshots: `data/public/` (with latest/ and dated directories)
- Jupyter notebook: `notebooks/demo.ipynb`

✅ **Documentation**
- Core docs: README.md, CHANGELOG.md, CONTRIBUTING.md, ETHICS.md, SECURITY.md
- Extended docs: `docs/` (app-plan.md, model-data-card.md, blog posts, etc.)
- Citation: CITATION.cff

---

## Inconsistencies Identified

### 1. Version Number Conflicts

| Source | Version | Status Description |
|--------|---------|-------------------|
| README.md (lines 49, 107) | v0.1 | "Proof-of-concept (v0.1) — research artifact" |
| SNAPSHOT-2024-11-03-1900-UTC.md | v1.0.0 | "Status: LIVE & FUNCTIONAL – v1.0.0 tagged – ready for public use" |
| CHANGELOG.md | 0.1.0 | "[0.1.0] - 2025-11-03" + note: "v0.1.0 is a proof-of-concept release" |
| CITATION.cff | 0.1.0 | "version: 0.1.0" |

**Impact:** Confusing for contributors and users. The SNAPSHOT claims v1.0.0, but all other sources say v0.1.0.

**Recommendation:** Align everything to v0.1.0 (proof-of-concept) unless a formal v1.0.0 release was actually tagged and shipped.

---

### 2. Branch Name Inconsistencies

| Location | Branch Referenced | Context |
|----------|------------------|---------|
| README badges (lines 29-31, 96) | `main` | Workflow badge URLs |
| README line 134 | `main` | Mermaid Live URL |
| README line 180 | `master` | Colab badge URL |
| README line 380 | `master` | GitHub Pages setup instructions |
| SNAPSHOT.md | `main` | Default branch listed |
| Workflows | `main, master` | Most workflows trigger on both |

**Impact:** Mixed signals about default branch. Badges use `main`, but some links and instructions reference `master`.

**Recommendation:**
- Confirm actual default branch (likely `main` based on SNAPSHOT and badge URLs)
- Update README line 180 (Colab badge) to use `main` instead of `master`
- Update README line 380 (Pages setup) to say `main` instead of `master`
- Ensure all workflows and links consistently use `main`

---

### 3. GitHub Pages Configuration

| Location | Information |
|----------|-------------|
| README line 380 | Says to deploy from `master` branch |
| README line 382 | Base URL: `https://codethor0.github.io/human-behaviour-convergence/` |
| deploy-pages.yml | Triggers on `main, master, feat/public-layer` branches |
| Interactive diagram | Referenced at `codethor0.github.io/.../docs/interactive-diagram.html` |

**Impact:** Instructions say `master`, but workflow supports `main`. Need to verify actual Pages configuration.

**Recommendation:**
- Update README line 380 to say `main` (or check actual repo settings)
- Verify Pages is enabled and deploying correctly
- Test all referenced URLs work

---

### 4. CHANGELOG "Planned" Items Already Implemented

CHANGELOG.md [Unreleased] section lists as "Planned":
- ❌ "Jupyter notebook with synthetic data demo" → **Actually exists:** `notebooks/demo.ipynb`
- ❌ "Unit tests and CI workflow for tests" → **Actually exists:** `tests/` directory + `test.yml` workflow
- ❌ "Results folder with example CSVs" → **Actually exists:** `results/` with forecasts.csv, metrics.csv, etc.
- ❌ "Python package structure with requirements.txt" → **Actually exists:** `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`

**Impact:** Misleading to contributors. Makes it seem like less is done than actually is.

**Recommendation:** Move these items from "Planned" to "Added" in [Unreleased] section, or remove them entirely.

---

### 5. README Structure Duplication

README.md contains:
- Lines 15-111: First section (TL;DR, badges, diagram, architecture table)
- Lines 93-394: Second section (appears to be a duplicate/older version with similar content)
  - Lines 103-111: Duplicate "What is this?" section
  - Lines 114-119: Duplicate diagram reference

**Impact:** README is longer than necessary and may confuse readers.

**Recommendation:** Consolidate duplicate sections. Keep the more polished version (likely the first one).

---

### 6. app/README.md Duplication

`app/README.md` contains:
- Lines 1-44: "Behavior Convergence App" section (describes running backend/frontend)
- Lines 46-66: "Behavior Convergence Explorer" section (describes planned structure)

**Impact:** Mixing current state with planning. Confusing for someone trying to run the app.

**Recommendation:**
- Merge into one coherent document
- Clearly separate "What exists" from "What's planned"
- Update to reflect current state (both backend and frontend exist)

---

### 7. SNAPSHOT Status Claims

SNAPSHOT-2024-11-03-1900-UTC.md says:
- "Status: LIVE & FUNCTIONAL – v1.0.0 tagged – ready for public use"
- But also lists "GitHub Pages | OFF (one-click away)" and "Social preview card | missing"

**Impact:** Contradictory. Can't be "LIVE & FUNCTIONAL" if Pages is off.

**Recommendation:**
- Update SNAPSHOT to match actual state (v0.1.0, proof-of-concept)
- Or update to reflect current state if Pages is now enabled
- Clarify what "LIVE" means (code works locally vs. deployed publicly)

---

### 8. Missing File References Check

**References to verify:**
- `docs/model-data-card.md` (referenced in README line 336) → **Exists** ✅
- `docs/app-plan.md` (referenced in README line 357) → **Exists** ✅
- `docs/releases/v0.1.0.md` (referenced in README line 394) → **Exists** ✅
- `docs/blog/0001-rationale.md` (referenced in README line 392) → **Exists** ✅
- `docs/repo-polish.md` (referenced in README line 393) → **Exists** ✅
- `CODE_OF_CONDUCT.md` (referenced in CONTRIBUTING.md line 48) → **Exists** ✅

All file references appear valid. ✅

---

## Proposed Fixes by Category

### Documentation Fixes

1. **Version alignment**
   - Update SNAPSHOT-2024-11-03-1900-UTC.md to v0.1.0 (or verify if v1.0.0 tag actually exists)
   - Ensure all docs consistently say "Proof-of-concept v0.1.0"

2. **Branch name alignment**
   - Update README line 180: Colab badge URL to use `main`
   - Update README line 380: Pages setup to say `main`
   - Verify default branch in repo settings

3. **CHANGELOG cleanup**
   - Move implemented items from "Planned" to "Added"
   - Remove items that are clearly done

4. **README consolidation**
   - Remove duplicate sections (lines 93-111, possibly others)
   - Keep one clear, consistent narrative

5. **app/README.md rewrite**
   - Single coherent document
   - Clear separation of current vs. planned
   - Accurate running instructions

### Code Fixes

None needed in Phase 0 (inventory only).

### CI Fixes

None needed - workflows appear correct and functional.

### Data Fixes

None needed - data structures exist and appear valid.

### Community Fixes

1. **Update SNAPSHOT.md**
   - Reflect actual state (not aspirational)
   - Mark items as complete/incomplete accurately

---

## Files Requiring Updates

1. `README.md` - Branch references, duplicate sections
2. `SNAPSHOT-2024-11-03-1900-UTC.md` - Version number, status claims
3. `CHANGELOG.md` - Move "Planned" items to "Added"
4. `app/README.md` - Consolidate and clarify current state

---

## Next Steps

**Phase 1** should address:
1. ✅ Fix all documentation inconsistencies
2. ✅ Align version numbers across all files
3. ✅ Fix branch name references
4. ✅ Clean up CHANGELOG
5. ✅ Consolidate README
6. ✅ Rewrite app/README.md

**Phase 2** should address:
1. Verify diagram rendering works
2. Test GitHub Pages deployment
3. Fix any broken links/images
4. Ensure all badges are green

---

## Notes

- Current working branch: `chore/spelling-behavior-standardization` (feature branch)
- Default branch appears to be `main` (based on SNAPSHOT and badge URLs)
- Repository appears to be in active development with recent commits
- Most inconsistencies are documentation-only; code appears sound

---

**Report Generated:** 2025-11-10
**Next Phase:** Phase 1 - Docs and Diagram Alignment
