#!/usr/bin/env python3
"""
CI check: Validate external markdown links return successful HTTP responses.
Exit code 1 if any broken external links found (404, 410, 5xx).
Warns but does not fail on anti-bot or transient responses.
"""
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def get_tracked_markdown_files(root: Path) -> list[Path]:
    """Get list of tracked markdown files from git."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_paths = [f.strip() for f in result.stdout.splitlines() if f.strip()]

        md_files = []
        for path_str in tracked_paths:
            if path_str.endswith((".md", ".markdown")):
                file_path = root / path_str
                if file_path.exists():
                    md_files.append(file_path)

        return md_files
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[WARNING] Git command failed: {e}", file=sys.stderr)
        # Fallback: find all markdown files
        md_files = []
        for ext in (".md", ".markdown"):
            md_files.extend(root.glob(f"**/*{ext}"))
        # Exclude common build/dep directories
        excluded_dirs = {
            ".git",
            "node_modules",
            ".venv",
            ".next",
            "playwright-report",
            "test-results",
        }
        md_files = [
            f
            for f in md_files
            if not any(part in excluded_dirs for part in f.relative_to(root).parts)
        ]
        return md_files


def extract_external_links(file_path: Path) -> list[tuple[int, str, str]]:
    """Extract external links from a file. Returns list of (line_num, link_text, url)."""
    links = []
    link_pattern = re.compile(r"!?\[(?P<text>[^\]]+)\]\((?P<target>[^)]+)\)")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                for match in link_pattern.finditer(line):
                    target = match.group("target")
                    # Check if external link
                    if target.startswith(("http://", "https://", "mailto:")):
                        link_text = match.group("text")
                        links.append((line_num, link_text, target))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return links


def check_url(url: str, timeout: float = 8.0) -> tuple[int | None, str | None]:
    """
    Check URL with HTTP HEAD request.
    Returns (status_code, error_message).
    """
    # Skip mailto: links - treat as always valid
    if url.startswith("mailto:"):
        return (200, None)

    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; CI-LinkChecker/1.0)")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (resp.getcode(), None)
    except urllib.error.HTTPError as e:
        # HTTP-level error with status code
        return (e.code, None)
    except urllib.error.URLError as e:
        # Network error, DNS, SSL, etc.
        return (None, str(e.reason))
    except Exception as e:
        # Other unexpected errors
        return (None, str(e))


def classify_status(status_code: int | None, error_message: str | None) -> str:
    """
    Classify HTTP response status.
    Returns: 'ok', 'broken', or 'warn'
    """
    if status_code is None:
        # Network/transient error - warn but don't fail
        return "warn"

    if 200 <= status_code <= 399:
        return "ok"

    if status_code in (404, 410) or (500 <= status_code <= 599):
        return "broken"

    # Other non-2xx/3xx codes: 400 (non-404/410), 401, 403, 429, 999, etc.
    # These are often anti-bot or rate limiting - warn but don't fail
    return "warn"


def main():
    root = Path(__file__).parent.parent.parent
    md_files = get_tracked_markdown_files(root)

    broken_links = []
    warned_links = []

    for md_file in sorted(md_files):
        rel_path = md_file.relative_to(root)
        external_links = extract_external_links(md_file)

        for line_num, link_text, url in external_links:
            status_code, error_message = check_url(url)
            classification = classify_status(status_code, error_message)

            if classification == "broken":
                if status_code:
                    broken_links.append(
                        (rel_path, line_num, url, f"status={status_code}")
                    )
                else:
                    broken_links.append(
                        (rel_path, line_num, url, f"error={error_message}")
                    )
            elif classification == "warn":
                if status_code:
                    warned_links.append(
                        (rel_path, line_num, url, f"status={status_code}")
                    )
                else:
                    warned_links.append(
                        (rel_path, line_num, url, f"error={error_message}")
                    )

    # Report results
    if broken_links:
        print("[FAIL] Broken external markdown links found:")
        for rel_path, line_num, url, status_info in broken_links:
            print(f"  {rel_path}:{line_num}: {url} ({status_info})")

        if warned_links:
            print("")
            print("[WARN] External links with non-failing status:")
            for rel_path, line_num, url, status_info in warned_links:
                print(f"  {rel_path}:{line_num}: {url} ({status_info})")

        sys.exit(1)

    if warned_links:
        print("[WARN] External links with non-failing status:")
        for rel_path, line_num, url, status_info in warned_links:
            print(f"  {rel_path}:{line_num}: {url} ({status_info})")
        print("[PASS] No broken external markdown links detected.")
        sys.exit(0)

    print("[PASS] All external markdown links returned successful responses.")
    sys.exit(0)


if __name__ == "__main__":
    main()

