#!/usr/bin/env python3
"""
CI check: Block emojis in Markdown files to maintain professional documentation.
Exit code 1 if any emojis found.
"""
import re
import sys
from pathlib import Path

# Comprehensive emoji pattern covering most Unicode emoji ranges
EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f700-\U0001f77f"  # alchemical
    "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
    "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
    "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
    "\U0001fa00-\U0001fa6f"  # Chess Symbols
    "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
    "\U00002702-\U000027b0"  # Dingbats
    "\U000024c2-\U0001f251"
    "]+"
)


def check_file(file_path: Path) -> list[tuple[int, str]]:
    """Return list of (line_number, line_content) for lines containing emojis."""
    violations = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                if EMOJI_PATTERN.search(line):
                    violations.append((line_num, line.rstrip()))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    return violations


def main():
    root = Path(__file__).parent.parent.parent
    md_files = list(root.glob("**/*.md"))

    # Exclude files in hidden directories, node_modules, or specific paths
    md_files = [
        f
        for f in md_files
        if not any(part.startswith(".") for part in f.relative_to(root).parts[:-1])
        and "node_modules" not in f.parts
        and ".venv" not in f.parts
        and "venv" not in f.parts
    ]

    # Exclude audit reports that document emojis as findings
    md_files = [f for f in md_files if "REPO_HEALTH_AUDIT" not in f.name]
    md_files = [f for f in md_files if "ISSUE_STATUS_REPORT" not in f.name]

    found_emojis = False

    for md_file in sorted(md_files):
        violations = check_file(md_file)
        if violations:
            found_emojis = True
            rel_path = md_file.relative_to(root)
            print(f"\n[FAIL] Emojis found in {rel_path}:")
            for line_num, line_content in violations:
                print(f"  Line {line_num}: {line_content}")

    if found_emojis:
        print("\n[FAIL] CI FAILED: Emojis detected in Markdown files.")
        print("Please remove all emojis to maintain professional documentation.")
        sys.exit(1)
    else:
        print("[PASS] No emojis found in Markdown files.")
        sys.exit(0)


if __name__ == "__main__":
    main()
