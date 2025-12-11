#!/usr/bin/env python3
"""Fail pre-commit if British spellings slip into tracked files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# File extensions to scan (textual formats only)
_SCAN_EXTENSIONS = {
    ".md",
    ".mdx",
    ".txt",
    ".rst",
    ".ipynb",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".svg",
}

# Known strings that intentionally retain the old spelling (slugs, package names, etc.)
_ALLOWED_SUBSTRINGS = [
    "human-behaviour-convergence",
    "human-behaviour",
    "human_behaviour_convergence",
    "human_behaviour_predictor",
    "behaviour-convergence",
    "behaviour_convergence",
    "behaviour-convergence.mmd",
    "behaviour-convergence.svg",
    "behaviour-convergence.png",
    "codethor0/human-behaviour-convergence",
    "https://github.com/codethor0/human-behaviour-convergence",
    "human-behaviour-convergence.git",
    "human-behaviour-predictor-template",
    # Common project name variations
    "Human Behaviour",
    "Human Behaviour Convergence",
    "Behaviour Convergence",
    "behaviour convergence",
]

_PATTERN = re.compile(r"\bbehaviour(al)?\b", re.IGNORECASE)


def _git_tracked_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(line) for line in out.splitlines() if line]


def _should_scan(path: Path) -> bool:
    return path.suffix in _SCAN_EXTENSIONS


def _sanitize(text: str) -> str:
    """Replace allowed substrings with misspelled versions to prevent false positives."""
    sanitized = text
    # Process longer patterns first to avoid partial matches
    sorted_tokens = sorted(_ALLOWED_SUBSTRINGS, key=len, reverse=True)
    for token in sorted_tokens:
        # Replace with a misspelled version that won't match the pattern
        # Use case-insensitive replacement
        pattern = re.compile(re.escape(token), re.IGNORECASE)
        # Create replacement that removes "behaviour" from the pattern
        replacement = re.sub(
            r'behaviou?r', 'behavoir', token, flags=re.IGNORECASE
        )
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def main() -> int:
    failures: list[str] = []

    for path in _git_tracked_files():
        if not _should_scan(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # Skip binary/unknown encodings

        sanitized = _sanitize(text)
        match = _PATTERN.search(sanitized)
        if match:
            line_no = sanitized[: match.start()].count("\n") + 1
            failures.append(
                f"{path}: line {line_no} contains British spelling '{match.group(0)}'"
            )

    if failures:
        print(
            "American English required (behavior/behavioral). Found British spellings:",
            file=sys.stderr,
        )
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
