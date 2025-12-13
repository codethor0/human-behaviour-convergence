# Auto-Merge Configuration Guide

This document describes the GitHub repository settings required for automated Dependabot PR management.

## Required GitHub Settings

### 1. Enable Auto-Merge for Dependabot PRs

**Path:** Repository Settings → General → Pull Requests → Allow auto-merge

- ✅ Enable "Allow auto-merge"
- ✅ Enable "Allow squash merging"
- ✅ Set default merge method to "Squash and merge"

### 2. Configure Auto-Merge Rules

**Path:** Repository Settings → General → Pull Requests → Auto-merge

Create rules for Dependabot PRs:

- **Branch pattern:** `dependabot/**`
- **Merge method:** Squash and merge
- **Commit message format:** `chore(deps): $PACKAGE to $VERSION`
- **Required status checks:** All CI checks must pass
- **Required reviews:** 0 (for Dependabot PRs only)
- **Require up-to-date branch:** Yes

### 3. Enable Automatic Branch Deletion

**Path:** Repository Settings → General → Pull Requests

- ✅ Enable "Automatically delete head branches"

This will automatically delete branches after PRs are merged.

### 4. Dependabot Auto-Merge Configuration

**Path:** Repository Settings → Security → Dependabot → Auto-merge

- ✅ Enable "Allow auto-merge"
- ✅ Enable "Merge only when CI is green"
- ✅ Enable "Merge only when diff is non-breaking"

**Note:** These settings are configured via `.github/dependabot.yml` and the branch hygiene workflow.

## Current Configuration

- **Dependabot config:** `.github/dependabot.yml`
  - Groups npm updates into single weekly PR
  - Groups GitHub Actions updates into single weekly PR
  - Security-only updates for Python dependencies
  - Weekly schedule (Mondays at 09:00 UTC)

- **Branch hygiene workflow:** `.github/workflows/branch-hygiene.yml`
  - Runs nightly at 02:00 UTC
  - Cleans up merged branches
  - Closes outdated Dependabot PRs
  - Deletes stale branches

## Verification

After configuring these settings:

1. Check that auto-merge is enabled in repository settings
2. Verify Dependabot PRs are created with correct labels
3. Confirm branch hygiene workflow runs successfully
4. Test that merged branches are automatically deleted

## Manual Override

If auto-merge fails or needs manual intervention:

1. Review the PR manually
2. Merge using "Squash and merge" method
3. Ensure commit message follows format: `chore(deps): <package> to <version>`
