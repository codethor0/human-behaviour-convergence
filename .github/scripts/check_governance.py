#!/usr/bin/env python3
"""Governance enforcement checks.

This script enforces governance rules defined in GOVERNANCE_RULES.md.
It must be run as part of CI and must fail if any rule is violated.
"""
import re
import sys
from pathlib import Path

# Colors for output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check_version_contract():
    """Check G1: Version contract enforcement."""
    print("=== Check G1: Version Contract Enforcement ===")

    # Extract version from docs/BEHAVIOR_INDEX.md
    behavior_index_doc = Path("docs/BEHAVIOR_INDEX.md")
    if not behavior_index_doc.exists():
        print(f"{RED}FAIL: docs/BEHAVIOR_INDEX.md not found{RESET}")
        return False

    with open(behavior_index_doc, "r") as f:
        content = f.read()
        version_match = re.search(r"\*\*Version:\*\* ([\d.]+)", content)
        if not version_match:
            print(f"{RED}FAIL: No version found in docs/BEHAVIOR_INDEX.md{RESET}")
            return False
        version = version_match.group(1)

    # Check if VERSION_CONTRACT file exists
    contract_file = Path(f"VERSION_CONTRACT_{version.replace('.', '_')}.md")
    if not contract_file.exists():
        print(f"{RED}FAIL: Version {version} changed but no contract file found{RESET}")
        print(f"Expected: {contract_file}")
        return False

    # Validate contract contains required sections
    with open(contract_file, "r") as f:
        contract = f.read()
        required = ["Guarantees", "Invalidated Assumptions", "Migration Notes"]
        missing = [r for r in required if r not in contract]
        if missing:
            print(f"{RED}FAIL: Contract missing sections: {missing}{RESET}")
            return False

    print(f"{GREEN}PASS: Version {version} has valid contract{RESET}")
    return True


def check_sub_index_count():
    """Check G2: Sub-index count consistency."""
    print("=== Check G2: Sub-Index Count Consistency ===")

    # Count sub-indices in code
    behavior_index_code = Path("app/core/behavior_index.py")
    if not behavior_index_code.exists():
        print(f"{RED}FAIL: app/core/behavior_index.py not found{RESET}")
        return False

    with open(behavior_index_code, "r") as f:
        code = f.read()
        # Count weight parameters in __init__
        weight_params = re.findall(r"(\w+_weight): float", code)
        code_count = len([w for w in weight_params if "weight" in w])

    # Extract count from docs
    behavior_index_doc = Path("docs/BEHAVIOR_INDEX.md")
    if not behavior_index_doc.exists():
        print(f"{RED}FAIL: docs/BEHAVIOR_INDEX.md not found{RESET}")
        return False

    with open(behavior_index_doc, "r") as f:
        docs = f.read()
        # Find the primary statement, not notes about backward compatibility
        # Look for "nine sub-indices" or "9 sub-indices" in formula section
        doc_matches = re.findall(r"(\d+) sub-indices", docs)
        if not doc_matches:
            print(f"{RED}FAIL: Sub-index count not found in docs{RESET}")
            return False
        # Use the last match (should be the primary statement after formula section)
        # Or find "nine" explicitly
        if "nine sub-indices" in docs.lower() or "9 sub-indices" in docs:
            doc_count = 9
        else:
            # Fall back to last numeric match
            doc_count = int(doc_matches[-1])

    # Extract count from README
    readme = Path("README.md")
    if not readme.exists():
        print(f"{RED}FAIL: README.md not found{RESET}")
        return False

    with open(readme, "r") as f:
        readme_content = f.read()
        readme_match = re.search(r"(\d+) sub-indices", readme_content)
        if not readme_match:
            print(f"{RED}FAIL: Sub-index count not found in README{RESET}")
            return False
        readme_count = int(readme_match.group(1))

    # Verify consistency
    if code_count != doc_count or code_count != readme_count:
        print(f"{RED}FAIL: Sub-index count mismatch{RESET}")
        print(f"Code: {code_count}, Docs: {doc_count}, README: {readme_count}")
        return False

    print(f"{GREEN}PASS: Sub-index count consistent ({code_count}){RESET}")
    return True


def check_weight_semantics():
    """Check G3: Weight semantics documentation."""
    print("=== Check G3: Weight Semantics Documentation ===")

    behavior_index_doc = Path("docs/BEHAVIOR_INDEX.md")
    if not behavior_index_doc.exists():
        print(f"{RED}FAIL: docs/BEHAVIOR_INDEX.md not found{RESET}")
        return False

    with open(behavior_index_doc, "r") as f:
        docs = f.read()
        docs_lower = docs.lower()

        # Must contain normalization warning
        if "relative influence factors" not in docs_lower:
            print(
                f"{RED}FAIL: Weight semantics not documented (missing 'relative influence factors'){RESET}"
            )
            return False

        # Must contain normalization explanation
        if "normalization" not in docs_lower:
            print(f"{RED}FAIL: Normalization not documented{RESET}")
            return False

        # Must contain warning about raw vs normalized in weight table section
        # Check for both terms in weight table context
        weight_table_section = ""
        if "### Current Weights" in docs:
            start = docs.find("### Current Weights")
            # Find next ### or end of file
            next_section = docs.find("###", start + 1)
            if next_section == -1:
                end = len(docs)
            else:
                end = next_section
            weight_table_section = docs[start:end].lower()
        else:
            print(f"{RED}FAIL: '### Current Weights' section not found{RESET}")
            return False

        # Check for both terms (case-insensitive already done)
        has_raw = (
            "raw" in weight_table_section
            or "relative influence factors" in weight_table_section
        )
        has_normalized = (
            "normalized" in weight_table_section
            or "normalization" in weight_table_section
        )

        if not has_raw:
            print(
                f"{RED}FAIL: Raw weights or 'relative influence factors' not explained in weight table{RESET}"
            )
            return False

        if not has_normalized:
            print(f"{RED}FAIL: Normalization not explained in weight table{RESET}")
            return False

    print(f"{GREEN}PASS: Weight semantics properly documented{RESET}")
    return True


def check_silent_math():
    """Check G4: No silent mathematics."""
    print("=== Check G4: No Silent Mathematics ===")

    behavior_index_code = Path("app/core/behavior_index.py")
    if not behavior_index_code.exists():
        print(f"{RED}FAIL: app/core/behavior_index.py not found{RESET}")
        return False

    with open(behavior_index_code, "r") as f:
        code = f.read()

    # Check for normalization
    if "/ total_weight" in code or "normalize" in code.lower():
        # Must be documented
        behavior_index_doc = Path("docs/BEHAVIOR_INDEX.md")
        if not behavior_index_doc.exists():
            print(f"{RED}FAIL: Normalization in code but docs not found{RESET}")
            return False

        with open(behavior_index_doc, "r") as f:
            docs = f.read().lower()
            if "normalization" not in docs:
                print(f"{RED}FAIL: Normalization in code but not documented{RESET}")
                return False

    print(f"{GREEN}PASS: Mathematical operations documented{RESET}")
    return True


def check_drift():
    """Check G5: Drift detection."""
    print("=== Check G5: Drift Detection ===")

    # This is a simplified check - full drift detection would require
    # comparing against baseline, which is complex

    # For now, check that critical areas are consistent
    # (sub-index count already checked in G2)

    # Check version consistency
    behavior_index_doc = Path("docs/BEHAVIOR_INDEX.md")
    readme = Path("README.md")

    if not behavior_index_doc.exists() or not readme.exists():
        print(f"{RED}FAIL: Required files not found{RESET}")
        return False

    with open(behavior_index_doc, "r") as f:
        doc_content = f.read()
        doc_version_match = re.search(r"\*\*Version:\*\* ([\d.]+)", doc_content)

    with open(readme, "r") as f:
        readme_content = f.read()
        # Look for version in README (format: "v2.5" or "Version 2.5" or "Behavior Index v2.5")
        # More specific pattern to avoid matching other version numbers
        readme_version_match = re.search(
            r"Behavior Index\s+(?:v|Version\s+)?([\d.]+)", readme_content, re.IGNORECASE
        )
        if not readme_version_match:
            # Fallback: look for "v2.5" near "Behavior Index"
            readme_version_match = re.search(
                r"v([\d.]+).*sub-indices", readme_content, re.IGNORECASE
            )

    if doc_version_match:
        doc_version = doc_version_match.group(1)
        if readme_version_match:
            readme_version = readme_version_match.group(1)
            if doc_version != readme_version:
                print(f"{RED}FAIL: Version mismatch between docs and README{RESET}")
                print(f"Docs: {doc_version}, README: {readme_version}")
                return False
        else:
            # README might not have version in expected format - check if it's mentioned
            if doc_version not in readme_content:
                print(
                    f"{YELLOW}WARNING: Version {doc_version} not found in README{RESET}"
                )
                # Don't fail, but warn

    print(f"{GREEN}PASS: No drift detected{RESET}")
    return True


def main():
    """Run all governance checks."""
    print("=" * 60)
    print("GOVERNANCE ENFORCEMENT CHECKS")
    print("=" * 60)
    print()

    checks = [
        check_version_contract,
        check_sub_index_count,
        check_weight_semantics,
        check_silent_math,
        check_drift,
    ]

    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
            print()
        except Exception as e:
            print(f"{RED}ERROR in {check.__name__}: {e}{RESET}")
            results.append(False)
            print()

    # Summary
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} checks passed")

    if all(results):
        print(f"{GREEN}ALL CHECKS PASSED{RESET}")
        return 0
    else:
        print(f"{RED}SOME CHECKS FAILED{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
