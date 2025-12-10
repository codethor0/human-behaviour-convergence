#!/usr/bin/env python3
# SPDX-License-Identifier: PROPRIETARY
"""Enforce CHANGELOG.md updates for conventional commits.

Validates that commits with certain types (feat, fix) include CHANGELOG updates.
"""

import re
import subprocess
import sys
from pathlib import Path


def get_commit_messages():
    """Get commit messages from git."""
    try:
        result = subprocess.run(
            ['git', 'log', '--format=%B', 'HEAD~1..HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def parse_conventional_commit(message: str):
    """Parse conventional commit message."""
    pattern = re.compile(r'^(feat|fix|perf|refactor)(\(.+\))?: (.+)')
    match = pattern.match(message.split('\n')[0])
    if match:
        return {
            'type': match.group(1),
            'scope': match.group(2),
            'subject': match.group(3)
        }
    return None


def check_changelog_updated():
    """Check if CHANGELOG.md was updated."""
    changelog_path = Path('CHANGELOG.md')
    if not changelog_path.exists():
        print("WARNING: CHANGELOG.md not found")
        return False
    
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True,
            text=True,
            check=True
        )
        staged_files = result.stdout.strip().split('\n')
        return 'CHANGELOG.md' in staged_files
    except subprocess.CalledProcessError:
        # If no staged files, check if CHANGELOG was modified
        try:
            result = subprocess.run(
                ['git', 'diff', 'HEAD', '--name-only'],
                capture_output=True,
                text=True,
                check=True
            )
            modified_files = result.stdout.strip().split('\n')
            return 'CHANGELOG.md' in modified_files
        except subprocess.CalledProcessError:
            return False


def main():
    """Main validation logic."""
    commit_msg = get_commit_messages()
    if not commit_msg:
        print("INFO: No commit messages to validate")
        sys.exit(0)
    
    parsed = parse_conventional_commit(commit_msg)
    if not parsed:
        print("INFO: Not a conventional commit requiring CHANGELOG update")
        sys.exit(0)
    
    # Types that require CHANGELOG updates
    changelog_required_types = ['feat', 'fix', 'perf']
    
    if parsed['type'] in changelog_required_types:
        if not check_changelog_updated():
            print(f"ERROR: {parsed['type']} commits require CHANGELOG.md updates")
            print(f"Commit: {parsed['type']}: {parsed['subject']}")
            print("\nPlease update CHANGELOG.md with your changes.")
            sys.exit(1)
        else:
            print("PASS: CHANGELOG.md updated")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
