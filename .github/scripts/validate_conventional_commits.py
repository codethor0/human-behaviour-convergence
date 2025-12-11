#!/usr/bin/env python3
import re
import sys
import os
import subprocess

"""
New validator:
 - Works in GitHub Actions reliably
 - Reads message via git log, GITHUB_SHA, or fallback
 - Allows commit messages > 72 chars (non-blocking)
 - Rejects ONLY when missing the Conventional Commit prefix
"""

ALLOWED_TYPES = [
    "feat","fix","docs","style","refactor","perf","test",
    "build","ci","chore","revert",
]

def get_commit_message():
    """
    Robust commit message retrieval for CI:
    1. Use git log on GITHUB_SHA
    2. Fallback to COMMIT_EDITMSG
    3. Fallback to stdin
    """
    sha = os.getenv("GITHUB_SHA")
    if sha:
        try:
            out = subprocess.check_output(
                ["git", "log", "--format=%B", "-n", "1", sha],
                text=True
            )
            if out.strip():
                return out.strip()
        except Exception:
            pass

    # Fallback: COMMIT_EDITMSG
    try:
        with open(".git/COMMIT_EDITMSG") as f:
            return f.read().strip()
    except:
        pass

    # Final fallback: stdin
    data = sys.stdin.read().strip()
    return data

def validate_commit_message(message: str) -> bool:
    """Validate a commit message follows Conventional Commits."""
    if not message:
        print("ERROR: Commit message is empty")
        return False

    first = message.split("\n")[0].strip()

    # Merge commits are allowed
    if first.startswith("Merge"):
        return True

    # Check prefix
    if ":" not in first:
        print("ERROR: Commit must contain '<type>: <subject>'")
        return False

    prefix = first.split(":")[0]
    ctype = prefix.split("(")[0]

    if ctype not in ALLOWED_TYPES:
        print(f"ERROR: Invalid type '{ctype}'. Must be one of: {ALLOWED_TYPES}")
        return False

    return True


def main():
    """Read commit message and validate."""
    message = get_commit_message()

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
