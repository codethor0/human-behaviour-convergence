# Branch protection setup

Protect your default branches to prevent force-push and ensure CI passes before merges.

## Recommended rules (master and main)

- Require a pull request before merging
  - Require approvals: 1+
  - Dismiss stale approvals when new commits are pushed
  - Require review from Code Owners (optional)
- Require status checks to pass before merging
  - Require branches to be up to date before merging
  - Select these checks after they’ve run at least once:
    - "Quality Gates / quality"
    - "Tests / test (3.12)" (or your preferred Python version)
    - "Emoji Check / check-no-emoji"
    - "Render Mermaid Diagram / render"
    - "Check Branch Protection / Verify branch protection is enabled"
- Require linear history
- Do not allow force pushes
- Do not allow deletions
- Restrict who can push to matching branches (optional)

## Enable via web UI

1. Settings → Branches → Branch protection rules → New rule.
2. Branch name pattern: `master` (repeat for `main` if used).
3. Apply the rules above and Save.

## Enable via GitHub CLI (admin only)

Fetch available status check contexts from a recent commit to use in the payload:

```zsh
# List check runs to discover exact context names
SHA=$(gh api repos/:owner/:repo/commits --jq '.[0].sha' | head -n1)
gh api repos/:owner/:repo/commits/$SHA/check-runs --paginate \
  --jq '.check_runs[].name' | sort -u
```

Then apply protection (replace CONTEXTS with the list from above):

```zsh
read -r -d '' PAYLOAD <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Quality Gates / quality",
      "Tests / test (3.12)",
      "Emoji Check / check-no-emoji",
      "Render Mermaid Diagram / render",
      "Check Branch Protection / Verify branch protection is enabled"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON

gh api -X PUT repos/:owner/:repo/branches/master/protection \
  -H 'accept: application/vnd.github+json' \
  -F required_status_checks=@- <<<"$PAYLOAD"
```

Note: You need admin rights on the repository for the commands above.

## CI guard

This repo includes `.github/workflows/check-branch-protection.yml` which fails if branch protection is missing. Once you enable protection and mark that check as required, merges will be blocked until protection remains enabled.
