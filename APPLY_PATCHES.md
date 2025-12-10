# How to Apply Level 3 Maximum Hardening Patches

This guide provides step-by-step instructions for applying all hardening patches to human-behaviour-convergence.

## Prerequisites

1. **Git configured with commit signing:**
   ```bash
   git config --global commit.gpgsign true
   git config --global user.signingkey YOUR_KEY_ID
   ```

2. **Repository is clean:**
   ```bash
   git status  # Should show clean working directory
   ```

3. **All changes committed or stashed**

## Patch Files

The following patch files have been generated:

1. `PATCH_001_REMOVE_HARDENING_ARTIFACTS.patch` - Remove artifact reports
2. `PATCH_002_ENHANCED_CI_WORKFLOW.patch` - Enhanced CI with security & E2E
3. `PATCH_003_PRE_COMMIT_ENHANCEMENT.patch` - Enhanced pre-commit hooks
4. `PATCH_004_REPRODUCIBLE_BUILD_DOCS.patch` - Reproducible build documentation

## Application Steps

### Step 1: Review Patches

Review each patch file to understand the changes:

```bash
cat PATCH_001_REMOVE_HARDENING_ARTIFACTS.patch
cat PATCH_002_ENHANCED_CI_WORKFLOW.patch
cat PATCH_003_PRE_COMMIT_ENHANCEMENT.patch
cat PATCH_004_REPRODUCIBLE_BUILD_DOCS.patch
```

### Step 2: Remove Hardening Artifacts

```bash
git rm CI_HARDENING_REPORT_human-behaviour-convergence.md \
       CODE_REPAIR_REPORT_human-behaviour-convergence.md \
       PURGE_REPORT_human-behaviour-convergence.md \
       REPO_BASELINE_REPORT_human-behaviour-convergence.md \
       SIGNATURE_VERIFICATION_REPORT_human-behaviour-convergence.md \
       .hardening_test

git commit -S -m "chore: remove hardening artifact reports

Remove temporary hardening report files generated during previous hardening runs.
These are artifacts and should not be tracked in the repository."
```

### Step 3: Apply CI Workflow Changes

The CI workflow patch (`PATCH_002_ENHANCED_CI_WORKFLOW.patch`) contains the complete enhanced workflow. You can either:

**Option A: Manual Application**
1. Open `.github/workflows/ci.yml`
2. Review the patch content
3. Apply changes manually

**Option B: Use Patch Tool**
```bash
# Extract the workflow content from the patch
grep -A 1000 "^# SPDX" PATCH_002_ENHANCED_CI_WORKFLOW.patch | grep -v "^---" > ci_new.yml
# Review ci_new.yml, then replace ci.yml
mv ci_new.yml .github/workflows/ci.yml
```

After applying:
```bash
git add .github/workflows/ci.yml
git commit -S -m "ci: add Level 3 maximum hardening features

- Add security scanning jobs (bandit, pip-audit, trivy)
- Add Docker E2E test suite
- Add architecture validation
- Add format lock enforcement (zero-drift guarantee)
- Add conventional commits validation
- Enable parallel test execution with pytest-xdist
- Add SARIF upload for security findings"
```

### Step 4: Apply Pre-Commit Changes

Similar to CI workflow, apply the pre-commit configuration:

```bash
# Review the patch
cat PATCH_003_PRE_COMMIT_ENHANCEMENT.patch

# Apply manually or extract and replace
# Then commit:
git add .pre-commit-config.yaml
git commit -S -m "chore: enhance pre-commit hooks with Level 3 hardening

- Add conventional commits validation
- Add architecture import validation
- Add format lock enforcement via black --check
- Add additional file checks (merge conflicts, case conflicts, line endings)
- Add ruff with auto-fix capability"
```

### Step 5: Add Reproducible Build Documentation

```bash
# The file should already exist from patch generation
# Verify it exists:
ls -la docs/REPRODUCIBLE_BUILDS.md

# If not, create it from PATCH_004_REPRODUCIBLE_BUILD_DOCS.patch
# Then commit:
git add docs/REPRODUCIBLE_BUILDS.md
git commit -S -m "docs: add reproducible builds documentation

- Document dependency lock file generation and usage
- Add Docker build reproducibility guidelines
- Include verification procedures
- Add troubleshooting section"
```

### Step 6: Commit New Scripts and Files

All new scripts and files should already be created. Commit them:

```bash
git add .github/scripts/validate_architecture.py
git add .github/scripts/validate_conventional_commits.py
git add .github/scripts/enforce_changelog.py
git add .github/scripts/generate_dependency_locks.sh
git add .github/scripts/run_docker_e2e.sh
git add docker-compose.test.yml
git add HARDENING_SUMMARY.md
git add APPLY_HARDENING.sh
git add APPLY_PATCHES.md

git commit -S -m "chore: add Level 3 hardening scripts and configuration

- Add architecture validation script
- Add conventional commits validator
- Add CHANGELOG enforcement script
- Add dependency lock file generator
- Add Docker E2E test runner
- Add comprehensive test docker-compose configuration
- Add hardening documentation and application scripts"
```

### Step 7: Generate Dependency Lock Files (Optional)

If you have `pip-tools` installed:

```bash
pip install pip-tools
.github/scripts/generate_dependency_locks.sh

# Commit lock files if generated:
git add requirements-lock.txt requirements-dev-lock.txt app/backend/requirements-lock.txt 2>/dev/null || true
git commit -S -m "chore: add dependency lock files with hashes

Enable reproducible builds with hash-verified dependency installation." || true
```

### Step 8: Verify All Changes

```bash
# Check status
git status

# Review what will be committed
git diff --cached

# Verify scripts are executable
ls -la .github/scripts/*.sh .github/scripts/*.py
```

### Step 9: Push and Verify

```bash
# Push all commits
git push origin main

# Wait for CI to run, then verify:
# 1. All CI jobs pass
# 2. Security scans run
# 3. Docker E2E tests pass
# 4. No regressions
```

## Verification Checklist

After pushing, verify:

- [ ] CI workflow runs successfully
- [ ] Security scanning jobs (bandit, pip-audit, trivy) execute
- [ ] Docker E2E tests pass
- [ ] Architecture validation passes
- [ ] Format lock validation passes
- [ ] Conventional commits validation works (test with a commit)
- [ ] Pre-commit hooks work locally
- [ ] All commits show "Verified" badge on GitHub

## Troubleshooting

### CI Fails

1. Check GitHub Actions logs
2. Verify all scripts are executable
3. Verify all required files exist
4. Check for syntax errors in YAML files

### Pre-Commit Hooks Fail

1. Run `pre-commit install`
2. Test individual hooks: `pre-commit run --all-files`
3. Check script permissions: `chmod +x .github/scripts/*.py`

### Docker E2E Tests Fail

1. Verify Docker is running
2. Check docker-compose.test.yml syntax
3. Review test logs: `docker-compose -f docker-compose.test.yml logs`

## Next Steps

After successful application:

1. Update CHANGELOG.md with hardening changes
2. Create a release tag if appropriate
3. Document any customizations made
4. Monitor CI for stability

## Support

If you encounter issues:

1. Review `HARDENING_SUMMARY.md` for complete change list
2. Check patch files for exact changes
3. Verify all prerequisites are met
4. Review CI logs for specific errors
