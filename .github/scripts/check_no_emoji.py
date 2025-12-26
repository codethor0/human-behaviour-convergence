#!/usr/bin/env python3
"""
CI check: Block emojis in Markdown and code files to maintain professional documentation.
Exit code 1 if any emojis found.
"""
import re
import sys
from pathlib import Path

# File extensions to check
ALLOWED_EXTENSIONS = (".md", ".markdown", ".py", ".ts", ".tsx", ".js", ".jsx")

# Directories to exclude
EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    ".healthcheck-venv",
    ".next",
    "playwright-report",
    "test-results",
    "dist",
    "build",
    "__pycache__",
    "site-packages",
    ".pytest_cache",
    "htmlcov",
    "coverage",
}

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


def should_exclude_file(file_path: Path, root: Path) -> bool:
    """Check if file should be excluded from checking."""
    rel_path = file_path.relative_to(root)
    parts = rel_path.parts
    
    # Check if any part of the path matches excluded directories
    for part in parts[:-1]:  # Exclude filename itself
        if part in EXCLUDED_DIRS:
            return True
        # Check for hidden directories (except .github which we want to check)
        if part.startswith(".") and part != ".github":
            return True
    
    # Exclude specific audit report files that document emojis as findings
    if "REPO_HEALTH_AUDIT" in file_path.name or "ISSUE_STATUS_REPORT" in file_path.name:
        return True
    
    return False


def get_tracked_files(root: Path) -> list[Path]:
    """Get list of tracked files matching allowed extensions."""
    import subprocess
    
    try:
        # Get all tracked files from git
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_paths = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        
        files_to_check = []
        for path_str in tracked_paths:
            file_path = root / path_str
            # Check extension
            if file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                # Check exclusions
                if not should_exclude_file(file_path, root):
                    if file_path.exists():
                        files_to_check.append(file_path)
        
        return files_to_check
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # Fallback: walk filesystem if git not available
        print(f"[WARNING] Git command failed: {e}, checking all files", file=sys.stderr)
        files_to_check = []
        for ext in ALLOWED_EXTENSIONS:
            for file_path in root.glob(f"**/*{ext}"):
                if not should_exclude_file(file_path, root):
                    files_to_check.append(file_path)
        return files_to_check


def main():
    root = Path(__file__).parent.parent.parent
    
    files_to_check = get_tracked_files(root)
    
    found_emojis = False
    
    for file_path in sorted(files_to_check):
        violations = check_file(file_path)
        if violations:
            found_emojis = True
            rel_path = file_path.relative_to(root)
            print(f"\n[FAIL] Emojis found in {rel_path}:")
            for line_num, line_content in violations:
                print(f"  Line {line_num}: {line_content}")

    if found_emojis:
        print("\n[FAIL] CI FAILED: Emojis detected in tracked files.")
        print("Please remove all emojis to maintain professional documentation and code.")
        sys.exit(1)
    else:
        print("[PASS] No emojis found in tracked files.")
        sys.exit(0)


if __name__ == "__main__":
    main()
