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
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"
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

    # Exclude files in hidden directories or specific paths
    md_files = [
        f
        for f in md_files
        if not any(part.startswith(".") for part in f.relative_to(root).parts[:-1])
    ]

    found_emojis = False

    for md_file in sorted(md_files):
        violations = check_file(md_file)
        if violations:
            found_emojis = True
            rel_path = md_file.relative_to(root)
            print(f"\n❌ Emojis found in {rel_path}:")
            for line_num, line_content in violations:
                print(f"  Line {line_num}: {line_content}")

    if found_emojis:
        print("\n❌ CI FAILED: Emojis detected in Markdown files.")
        print("Please remove all emojis to maintain professional documentation.")
        sys.exit(1)
    else:
        print("✅ No emojis found in Markdown files.")
        sys.exit(0)


if __name__ == "__main__":
    main()
