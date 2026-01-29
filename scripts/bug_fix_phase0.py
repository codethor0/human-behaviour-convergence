#!/usr/bin/env python3
"""Phase 0: Triage - Classify Security Findings"""
import json
import os
import sys


def classify_findings(bug_dir, fix_dir):
    """Classify security findings into test, example, and production files."""
    registry_path = f"{bug_dir}/registry/MASTER_BUG_REGISTRY.json"

    if not os.path.exists(registry_path):
        print(f"ERROR: Master registry not found at {registry_path}")
        return 1

    with open(registry_path) as f:
        registry = json.load(f)

    security_bugs = registry.get("bugs_by_category", {}).get("security", [])

    test_files = []
    example_files = []
    production_files = []

    for bug in security_bugs:
        file_path = bug.get("file", "")
        if not file_path:
            continue

        # Classify based on path patterns
        if any(
            pattern in file_path.lower()
            for pattern in [
                "test_",
                "_test.",
                "__test__",
                "spec.",
                ".spec.",
                "/test/",
                "/tests/",
                "conftest",
                "fixture",
                "mock",
                "stub",
            ]
        ):
            test_files.append(bug)
        elif any(
            pattern in file_path.lower()
            for pattern in ["example", "sample", "demo", "tutorial"]
        ):
            example_files.append(bug)
        else:
            production_files.append(bug)

    # Save classifications
    os.makedirs(f"{fix_dir}/classification", exist_ok=True)

    with open(f"{fix_dir}/classification/test_files.json", "w") as f:
        json.dump(test_files, f, indent=2)

    with open(f"{fix_dir}/classification/example_files.json", "w") as f:
        json.dump(example_files, f, indent=2)

    with open(f"{fix_dir}/classification/production_files.json", "w") as f:
        json.dump(production_files, f, indent=2)

    # Summary
    print("=== SECURITY FINDINGS CLASSIFICATION ===\n")
    print(f"Total findings: {len(security_bugs)}")
    print(f"Test files: {len(test_files)} (false positives)")
    print(f"Example files: {len(example_files)} (false positives)")
    print(f"Production files: {len(production_files)} (require review)")

    if production_files:
        print(
            f"\n[WARN]  CRITICAL: {len(production_files)} potential real secret exposures:"
        )
        for bug in production_files[:10]:  # Show first 10
            print(f"  - {bug.get('file', 'unknown')}:{bug.get('line', '?')}")
        if len(production_files) > 10:
            print(f"  ... and {len(production_files) - 10} more")

    return 0


if __name__ == "__main__":
    bug_dir = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
    fix_dir = os.getenv("FIX_DIR", "/tmp/hbc_fixes_default")
    sys.exit(classify_findings(bug_dir, fix_dir))
