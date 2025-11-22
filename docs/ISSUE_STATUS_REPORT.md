# Issue Status Report

**Date:** 2025-11-22
**Purpose:** Document completion status of all 5 open milestone issues

## Issue #6 - Milestone-0: One-Command Repo ✅ COMPLETE

All tasks completed:
- ✅ Dockerfile, docker-compose.yml exist
- ✅ Makefile with `make dev` target works
- ✅ .devcontainer/devcontainer.json exists for Codespaces
- ✅ GitPod/Codespaces badges added to README
- ✅ CI badge green (all workflows passing)

**Status:** All tasks complete. Ready to close.

---

## Issue #7 - Milestone-1: Extensibility MVP ✅ COMPLETE

All tasks completed:
- ✅ `/predictors` directory exists with registry.py and example_predictor.py
- ✅ Plugin registry uses importlib.metadata entry points
- ✅ Documentation exists at `docs/EXTENSIBILITY.md` with "Write your first predictor" guide
- ✅ `community` label exists in GitHub labels
- ℹ️ Cookie-cutter template repo referenced in docs (https://github.com/codethor0/human-behaviour-predictor-template) but doesn't exist yet - documented as "coming soon" in EXTENSIBILITY.md

**Status:** All core tasks complete. Template repo is a future enhancement. Ready to close.

---

## Issue #8 - Milestone-2: Transparency Drop ⚠️ PARTIAL

Tasks status:
- ❌ 100k synthetic row shard on Hugging Face datasets + DVC pointer - NOT STARTED
- ❌ DVC pipeline stage that reproduces notebook end-to-end - NOT STARTED
- ⚠️ HTML report published to GitHub Pages - `docs/index.html` exists, but not a DVC metrics report
- ✅ Model card exists at `docs/model-data-card.md` with limitations and ethical risks documented

**Remaining work:**
- Create Hugging Face dataset with 100k synthetic rows
- Set up DVC pipeline (dvc.yaml, stages)
- Configure DVC to generate HTML metrics report
- Publish DVC report to GitHub Pages

**Status:** Model card complete. DVC integration and Hugging Face dataset pending.

---

## Issue #9 - Milestone-3: Live Playground ❌ NOT STARTED

Tasks status:
- ❌ Streamlit/Gradio app - NOT IMPLEMENTED
- ❌ Host on Hugging Face Spaces - NOT IMPLEMENTED
- ❌ Screenshot + link in README - NOT IMPLEMENTED

**Note:** The repo has a Next.js frontend (`app/frontend/`) which could serve as the playground, but Issue #9 specifically requests Streamlit/Gradio.

**Remaining work:**
- Create Streamlit or Gradio app that loads synthetic data
- Deploy to Hugging Face Spaces
- Add screenshot and badge to README

**Status:** Not started. Requires new app implementation.

---

## Issue #10 - Milestone-4: Community Rails ⚠️ PARTIAL

Tasks status:
- ❌ all-contributors bot installed - NOT INSTALLED
- ❌ RFC template - NOT CREATED
- ❌ TSC (Technical Steering Committee) draft - NOT CREATED
- ❌ Monthly open Zoom call calendar file - NOT CREATED
- ✅ 'good first issue' template exists at `.github/ISSUE_TEMPLATE/good_first_issue.yml`

**Remaining work:**
- Set up all-contributors bot (requires GitHub App installation)
- Create RFC template (`.github/rfc-template.md`)
- Draft TSC charter document
- Create calendar file for monthly calls

**Status:** Good first issue template complete. Other tasks pending.

---

## Summary

- **Issues #6 & #7:** ✅ Complete, ready to close
- **Issue #8:** ⚠️ Partial (model card done, DVC/HF pending)
- **Issue #9:** ❌ Not started
- **Issue #10:** ⚠️ Partial (good first issue template done, other tasks pending)

## Recommendations

1. **Close Issues #6 and #7** - All tasks complete
2. **Update Issues #8, #9, #10** - Add status comments with this report
3. **Prioritize remaining work** - Focus on high-value items first (model card is already done for #8)
