#!/usr/bin/env python3
"""
Phase 1: Remove emojis from documentation and code files.
This script identifies and removes emojis from markdown and code files.
"""
import re
import sys
from pathlib import Path

# Common emojis found in documentation
EMOJI_PATTERN = re.compile(
    r"["
    r"\U0001F300-\U0001F9FF"  # Miscellaneous Symbols and Pictographs
    r"\U00002600-\U000026FF"  # Miscellaneous Symbols
    r"\U00002700-\U000027BF"  # Dingbats
    r"\U0001F600-\U0001F64F"  # Emoticons
    r"\U0001F680-\U0001F6FF"  # Transport and Map Symbols
    r"\U0001F1E0-\U0001F1FF"  # Flags
    r"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    r"]+",
    flags=re.UNICODE,
)

# Common emoji replacements
EMOJI_REPLACEMENTS = {
    "[OK]": "[OK]",
    "[FAIL]": "[FAIL]",
    "[WARN]": "[WARN]",
    "[TARGET]": "[TARGET]",
    "[CHART]": "[CHART]",
    "[SEARCH]": "[SEARCH]",
    "[ROCKET]": "[ROCKET]",
    "[IDEA]": "[IDEA]",
    "[NOTE]": "[NOTE]",
    "[ART]": "[ART]",
    "[TOOL]": "[TOOL]",
    "[FAST]": "[FAST]",
    "[STAR]": "[STAR]",
    "[TREND]": "[TREND]",
    "[THEATER]": "[THEATER]",
    "[CIRCUS]": "[CIRCUS]",
    "[MOVIE]": "[MOVIE]",
    "[PENDING]": "[PENDING]",
}


def remove_emojis_from_text(text: str) -> str:
    """Remove or replace emojis in text."""
    # First try replacements
    for emoji, replacement in EMOJI_REPLACEMENTS.items():
        text = text.replace(emoji, replacement)

    # Then remove any remaining emojis
    text = EMOJI_PATTERN.sub("", text)

    return text


def process_file(file_path: Path, dry_run: bool = True) -> bool:
    """Process a single file to remove emojis."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        new_content = remove_emojis_from_text(original_content)

        if original_content != new_content:
            if not dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"  Updated: {file_path}")
            else:
                print(f"  Would update: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return False


def main():
    repo_root = Path(__file__).parent.parent
    dry_run = "--apply" not in sys.argv

    if dry_run:
        print("DRY RUN MODE - Use --apply to make changes")
    else:
        print("APPLYING CHANGES")

    print("\nScanning for emojis in documentation and code files...")

    # Files to process
    patterns = [
        "**/*.md",
        "**/*.txt",
        "**/*.py",
        "**/*.ts",
        "**/*.tsx",
        "**/*.js",
        "**/*.jsx",
    ]

    updated_count = 0
    for pattern in patterns:
        for file_path in repo_root.glob(pattern):
            # Skip certain directories
            if any(
                skip in str(file_path)
                for skip in [".git", "node_modules", ".venv", ".next", "__pycache__"]
            ):
                continue

            if process_file(file_path, dry_run=dry_run):
                updated_count += 1

    print(f"\n{'Would update' if dry_run else 'Updated'} {updated_count} files")
    if dry_run:
        print("\nRun with --apply to make changes")


if __name__ == "__main__":
    main()
