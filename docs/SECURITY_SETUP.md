# Branch Protection & Security Setup Guide

## Critical: Enable Branch Protection

Your `main` branch is currently unprotected. Follow these steps to secure it:

### 1. Enable Branch Protection Rules

1. Go to: https://github.com/codethor0/human-behaviour-convergence/settings/branches
2. Click **Add rule** (or **Add branch protection rule**)
3. Branch name pattern: `main`
4. Enable these protections:

#### Required Settings
- **Require a pull request before merging**
  - Require approvals: 1 (or 0 if you're solo, but use PRs for documentation)
  - Dismiss stale pull request approvals when new commits are pushed
- **Require status checks to pass before merging**
  - Select: `Backend (FastAPI)`, `Frontend (Next.js)`, `test` (from workflows)
  - Require branches to be up to date before merging
- **Require conversation resolution before merging**
- **Require linear history** (prevents merge commits, keeps history clean)
- **Do not allow bypassing the above settings**

#### Optional but Recommended
- **Require signed commits** (if you have GPG key set up)
- **Include administrators** (enforce rules even for repo owner)
- **Restrict who can push to matching branches** (if you have team members)

5. Click **Create** or **Save changes**

---

### 2. Enable Secret Scanning & Push Protection

1. Go to: https://github.com/codethor0/human-behaviour-convergence/settings/security_analysis
2. Enable:
   - **Dependency graph** (should already be on)
   - **Dependabot alerts** (should already be on)
   - **Dependabot security updates**
   - **Secret scanning** (detects committed secrets)
   - **Push protection** (blocks pushes with secrets)

---

### 3. Set Up Required Reviewers (Optional)

If you have collaborators:

1. Go to: https://github.com/codethor0/human-behaviour-convergence/settings/access
2. Add collaborators with appropriate permissions:
   - **Write**: Can push to branches, open PRs (not main directly)
   - **Maintain**: Can manage some settings
   - **Admin**: Full access
3. Update `CODEOWNERS` to auto-request reviews

---

### 4. Enable GitHub Pages (Optional)

Make the diagram publicly accessible:

1. Go to: https://github.com/codethor0/human-behaviour-convergence/settings/pages
2. Source: **Deploy from a branch**
3. Branch: `main` / `(root)`
4. Click **Save**
5. After deploy, diagram will be at:
   ```
   https://codethor0.github.io/human-behaviour-convergence/diagram/behaviour-convergence.svg
   ```

---

### 5. Add Repository Metadata

1. Go to: https://github.com/codethor0/human-behaviour-convergence
2. Click the gear icon (top-right, next to About)
3. Add:
   - **Description**: `Population-scale behavioural forecasting in a zero-restriction data regime`
   - **Website**: (optional) your docs URL or Pages URL
   - **Topics**: `mermaid`, `forecasting`, `ai-ethics`, `population-scale`, `fastapi`, `nextjs`, `surveillance-tech`, `machine-learning`
4. Click **Save changes**

---

### 6. Upload Social Preview

1. Go to: https://github.com/codethor0/human-behaviour-convergence/settings
2. Scroll to **Social preview**
3. Click **Edit** → **Upload an image**
4. Upload: `assets/social-preview.svg` (or a 1280×640 PNG/JPG version)
5. This image appears when you share the repo link on Twitter, LinkedIn, etc.

---

### 7. Delete `master` Branch (Already Done)

We already synced `main` → `master` and pushed. To delete the old branch:

```bash
git push origin --delete master
```

Or via GitHub UI:
1. Go to: https://github.com/codethor0/human-behaviour-convergence/branches
2. Find `master`, click the trash icon

---

## Security Checklist

### Already Implemented
- [x] Dependabot for GitHub Actions
- [x] OpenSSF Scorecard workflow
- [x] SECURITY.md with responsible disclosure
- [x] CODEOWNERS file
- [x] No secrets in git history (verified)
- [x] `.gitignore` for sensitive files (`.env`, `.pem`, etc.)
- [x] Clean project dependencies (no vulnerabilities in venv)

### ⏳ Manual Steps Required (GitHub UI)
- [ ] Enable branch protection rules on `main`
- [ ] Enable secret scanning + push protection
- [ ] Enable GitHub Pages
- [ ] Add repository description and topics
- [ ] Upload social preview image
- [ ] Delete `master` branch (optional cleanup)

### 🔄 Optional Enhancements
- [ ] Add CodeQL workflow for static analysis
- [ ] Set up signed commits (GPG)
- [ ] Enable 2FA on your GitHub account (if not already)
- [ ] Review Dependabot PRs regularly

---

## Testing Branch Protection

After setup, test the protection:

```bash
# This should FAIL (blocked by branch protection)
git checkout main
echo "test" >> README.md
git commit -am "test: try direct push"
git push origin main

# This should SUCCEED (via PR)
git checkout -b test/branch-protection
echo "test" >> README.md
git commit -am "test: via PR"
git push origin test/branch-protection
# Then open PR on GitHub and merge
```

---

## Quick Command Reference

### Delete remote branch
```bash
git push origin --delete master
```

### Check security alerts
```bash
gh api repos/codethor0/human-behaviour-convergence/vulnerability-alerts
```

### View branch protection rules
```bash
gh api repos/codethor0/human-behaviour-convergence/branches/main/protection
```

---

**Important**: Branch protection settings can ONLY be changed via the GitHub web UI. The steps above must be done manually in your browser.
