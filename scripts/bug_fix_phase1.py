#!/usr/bin/env python3
"""Phase 1: Fix False Positives in Test Files"""
import json
import os
import sys
import re
from pathlib import Path


def fix_test_file(file_path, fix_dir):
    """Refactor test file to use environment variables instead of hardcoded secrets."""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        original_content = content
        changes_made = []

        # Replace api_key="test_key" patterns
        patterns = [
            (
                r'api_key\s*=\s*["\']test_key["\']',
                'api_key=os.getenv("TEST_API_KEY", "test_key")',
            ),
            (
                r'api_key\s*=\s*["\'][^"\']*["\']',
                'api_key=os.getenv("TEST_API_KEY", "test_key")',
            ),
            (
                r'secret\s*=\s*["\']test[^"\']*["\']',
                'secret=os.getenv("TEST_SECRET", "test_secret")',
            ),
            (
                r'API_KEY\s*=\s*["\']test[^"\']*["\']',
                'API_KEY=os.getenv("TEST_API_KEY", "test_key")',
            ),
        ]

        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes_made.append(f"Replaced {pattern} with {replacement}")

        # Add import os if not present and we made changes
        if (
            changes_made
            and "import os" not in content
            and "from os import" not in content
        ):
            # Find first import line
            lines = content.split("\n")
            import_idx = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("import ") or line.strip().startswith(
                    "from "
                ):
                    import_idx = i + 1
                    break

            lines.insert(import_idx, "import os")
            content = "\n".join(lines)
            changes_made.append("Added import os")

        # Only write if changes were made
        if content != original_content:
            # Create backup
            backup_path = f"{fix_dir}/fixes/{Path(file_path).name}.backup"
            with open(backup_path, "w") as f:
                f.write(original_content)

            # Write fixed content
            with open(file_path, "w") as f:
                f.write(content)

            return {
                "file": file_path,
                "changed": True,
                "changes": changes_made,
                "backup": backup_path,
            }
        else:
            return {
                "file": file_path,
                "changed": False,
                "reason": "No hardcoded secrets found or already using env vars",
            }
    except Exception as e:
        return {"file": file_path, "changed": False, "error": str(e)}


def main():
    fix_dir = os.getenv("FIX_DIR", "/tmp/hbc_fixes_default")

    # Load test files classification
    test_files_path = f"{fix_dir}/classification/test_files.json"
    if not os.path.exists(test_files_path):
        print(f"ERROR: Test files classification not found at {test_files_path}")
        return 1

    with open(test_files_path) as f:
        test_bugs = json.load(f)

    print("=== PHASE 1: FIXING FALSE POSITIVES IN TEST FILES ===\n")

    # Get unique files
    unique_files = {}
    for bug in test_bugs:
        file_path = bug.get("file", "")
        if file_path and file_path not in unique_files:
            unique_files[file_path] = bug

    print(f"Found {len(unique_files)} unique test files to fix\n")

    results = []
    fixed_count = 0

    for file_path in sorted(unique_files.keys()):
        # Skip if file doesn't exist
        if not os.path.exists(file_path):
            continue

        # Skip virtual environment files
        if ".venv" in file_path or "node_modules" in file_path:
            continue

        print(f"Fixing {file_path}...", end=" ", flush=True)
        result = fix_test_file(file_path, fix_dir)
        results.append(result)

        if result.get("changed"):
            print("[OK] FIXED")
            fixed_count += 1
        else:
            print("SKIPPED")

    # Save results
    with open(f"{fix_dir}/fixes/test_file_fixes.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Fixed {fixed_count} test files")
    print(f"   Results saved to: {fix_dir}/fixes/test_file_fixes.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
