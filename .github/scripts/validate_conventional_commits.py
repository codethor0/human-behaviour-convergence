#!/usr/bin/env python3
# SPDX-License-Identifier: PROPRIETARY
"""Validate commit messages follow Conventional Commits specification.

https://www.conventionalcommits.org/
"""

import os
import re
import subprocess
import sys
from pathlib import Path

CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .{1,}"
)


def validate_commit_message(message: str) -> bool:
    """Validate a commit message follows Conventional Commits."""
    lines = message.strip().split("\n")
    if not lines:
        return False

    first_line = lines[0].strip()

    # Check main pattern
    if not CONVENTIONAL_COMMIT_PATTERN.match(first_line):
        return False

    # Check length (recommended: <= 72 chars for first line)
    if len(first_line) > 72:
        print(f"WARNING: First line exceeds 72 characters ({len(first_line)} chars)")

    return True


def main():
    """Read commit message from stdin or COMMIT_EDITMSG."""
    if len(sys.argv) > 1:
        commit_msg_file = Path(sys.argv[1])
    else:
        # Try common locations
        git_dir = Path(".git")
        if git_dir.exists():
            commit_msg_file = git_dir / "COMMIT_EDITMSG"
        else:
            # Read from stdin
            commit_msg_file = None

    if commit_msg_file and commit_msg_file.exists():
        message = commit_msg_file.read_text()
    else:
        message = sys.stdin.read()

    if not message.strip():
        print("ERROR: Empty commit message")
        sys.exit(1)

    if validate_commit_message(message):
        print("PASS: Commit message follows Conventional Commits")
        sys.exit(0)
    else:
        print("ERROR: Commit message does not follow Conventional Commits")
        print("\nExpected format:")
        print("  <type>(<scope>): <subject>")
        print(
            "\nTypes: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert"
        )
        print("\nExample:")
        print("  feat(api): add new forecast endpoint")
        print("  fix(core): resolve location normalization bug")
        print("  docs(readme): update installation instructions")
        sys.exit(1)


if __name__ == "__main__":
    main()
