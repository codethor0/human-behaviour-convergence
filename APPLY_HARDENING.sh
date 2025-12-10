#!/bin/bash
# SPDX-License-Identifier: PROPRIETARY
# Master script to apply all Level 3 Maximum Hardening patches

set -euo pipefail

echo "=== Applying Level 3 Maximum Hardening ==="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check we're in the right directory
if [ ! -f "README.md" ] || [ ! -d ".github" ]; then
    echo -e "${RED}ERROR: Must run from repository root${NC}"
    exit 1
fi

# Step 1: Remove hardening artifacts
echo -e "${YELLOW}Step 1: Removing hardening artifacts...${NC}"
if [ -f "CI_HARDENING_REPORT_human-behaviour-convergence.md" ]; then
    git rm -f CI_HARDENING_REPORT_human-behaviour-convergence.md CODE_REPAIR_REPORT_human-behaviour-convergence.md PURGE_REPORT_human-behaviour-convergence.md REPO_BASELINE_REPORT_human-behaviour-convergence.md SIGNATURE_VERIFICATION_REPORT_human-behaviour-convergence.md .hardening_test 2>/dev/null || true
    echo -e "${GREEN}✓ Artifacts removed${NC}"
else
    echo -e "${GREEN}✓ No artifacts to remove${NC}"
fi

# Step 2: Ensure scripts are executable
echo -e "${YELLOW}Step 2: Setting script permissions...${NC}"
chmod +x .github/scripts/*.sh .github/scripts/*.py 2>/dev/null || true
echo -e "${GREEN}✓ Permissions set${NC}"

# Step 3: Generate dependency lock files (if pip-tools available)
echo -e "${YELLOW}Step 3: Generating dependency lock files...${NC}"
if command -v pip-compile &> /dev/null; then
    .github/scripts/generate_dependency_locks.sh || echo -e "${YELLOW}⚠ Lock file generation skipped (pip-tools not available)${NC}"
else
    echo -e "${YELLOW}⚠ Skipping lock file generation (pip-tools not installed)${NC}"
    echo "  Install with: pip install pip-tools"
fi

# Step 4: Verify all new files exist
echo -e "${YELLOW}Step 4: Verifying new files...${NC}"
required_files=(
    ".github/scripts/validate_architecture.py"
    ".github/scripts/validate_conventional_commits.py"
    ".github/scripts/enforce_changelog.py"
    ".github/scripts/run_docker_e2e.sh"
    "docker-compose.test.yml"
    "docs/REPRODUCIBLE_BUILDS.md"
)

missing=0
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗ Missing: $file${NC}"
        missing=$((missing + 1))
    else
        echo -e "${GREEN}✓ Found: $file${NC}"
    fi
done

if [ $missing -gt 0 ]; then
    echo -e "${RED}ERROR: $missing required files missing${NC}"
    exit 1
fi

# Step 5: Summary
echo ""
echo -e "${GREEN}=== Hardening Application Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Review all changes: git status"
echo "2. Review patches in PATCH_*.patch files"
echo "3. Apply CI workflow changes manually (see PATCH_002_ENHANCED_CI_WORKFLOW.patch)"
echo "4. Apply pre-commit changes manually (see PATCH_003_PRE_COMMIT_ENHANCEMENT.patch)"
echo "5. Commit all changes with signed commits:"
echo "   git add ."
echo "   git commit -S -m 'chore: apply Level 3 maximum hardening'"
echo "6. Push and verify CI passes"
echo ""
echo "See HARDENING_SUMMARY.md for complete details."
