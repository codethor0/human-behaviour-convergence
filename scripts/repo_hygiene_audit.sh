#!/usr/bin/env bash
# Non-destructive repo hygiene audit
# Outputs report to stdout (redirect to file if needed)

set -euo pipefail

echo "=== Top 50 Largest Tracked Files ==="
git ls-files -z | xargs -0 du -h 2>/dev/null | sort -rh | head -50 || echo "Could not compute file sizes"

echo ""
echo "=== Untracked Files (potential junk) ==="
git status --porcelain 2>/dev/null | grep "^??" | head -50 || echo "No untracked files"

echo ""
echo "=== Likely Artifacts ==="
find . -type f \( -name "*.tmp" -o -name "*evidence*" -o -name "*report*.md" -o -name "*.log" \) \
  -not -path "./node_modules/*" \
  -not -path "./.git/*" \
  -not -path "./.quarantine/*" \
  2>/dev/null | head -20 || echo "No artifacts found"

echo ""
echo "=== Suspicious Large Files (>10MB) ==="
git ls-files -z | xargs -0 du -h 2>/dev/null | awk '$1 ~ /[0-9]+M/ && $1+0 > 10' | head -20 || echo "No large files found"

echo ""
echo "=== Git Status Summary ==="
echo "Modified files: $(git status --porcelain 2>/dev/null | grep -c '^ M' || echo 0)"
echo "Untracked files: $(git status --porcelain 2>/dev/null | grep -c '^??' || echo 0)"
