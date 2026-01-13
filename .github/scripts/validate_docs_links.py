#!/usr/bin/env python3
"""
CI check: Validate internal markdown links point to existing files and headings.
Exit code 1 if any broken internal links found.
"""
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


def slugify_heading(text: str) -> str:
    """Convert heading text to GitHub-style anchor slug."""
    # Remove leading # and whitespace
    text = text.lstrip("#").strip().lower()
    # Remove punctuation except word chars, hyphen, space
    text = re.sub(r"[^\w\- ]+", "", text)
    # Replace whitespace with hyphens
    text = re.sub(r"\s+", "-", text)
    # Remove leading/trailing hyphens
    text = text.strip("-")
    return text


def extract_headings(file_path: Path) -> set[str]:
    """Extract all heading anchor slugs from a markdown file."""
    headings = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                # Match markdown headings: # Heading, ## Heading, etc.
                match = re.match(r"^(#{1,6})\s+(.+)$", line.rstrip())
                if match:
                    heading_text = match.group(2)
                    slug = slugify_heading(heading_text)
                    if slug:
                        headings.add(slug)
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    return headings


def extract_links(file_path: Path) -> list[tuple[int, str, str]]:
    """Extract all markdown links from a file. Returns list of (line_num, link_text, target)."""
    links = []
    link_pattern = re.compile(r"!?\[(?P<text>[^\]]+)\]\((?P<target>[^)]+)\)")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                for match in link_pattern.finditer(line):
                    link_text = match.group("text")
                    target = match.group("target")
                    links.append((line_num, link_text, target))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return links


def is_external_link(target: str) -> bool:
    """Check if a link target is external (http, https, mailto)."""
    return target.startswith(("http://", "https://", "mailto:"))


def resolve_link_path(base_file: Path, target: str) -> tuple[Path | None, str]:
    """
    Resolve a link target relative to the base file.
    Returns (resolved_path, anchor) where anchor may be empty.
    """
    # Split target into path and anchor
    if "#" in target:
        path_part, anchor = target.rsplit("#", 1)
        anchor = unquote(anchor)  # Handle URL-encoded anchors
    else:
        path_part = target
        anchor = ""

    # Pure anchor (starts with #)
    if target.startswith("#"):
        return (base_file, anchor.lstrip("#"))

    # Empty path means current file
    if not path_part:
        return (base_file, anchor)

    # Resolve relative path
    base_dir = base_file.parent
    resolved = (base_dir / path_part).resolve()

    # Check if resolved path is within repo root
    repo_root = Path(__file__).parent.parent.parent
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        # Path outside repo - treat as broken
        return (None, anchor)

    return (resolved, anchor)


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


def main():
    root = Path(__file__).parent.parent.parent
    md_files = get_tracked_markdown_files(root)

    violations = []

    for md_file in sorted(md_files):
        rel_path = md_file.relative_to(root)
        links = extract_links(md_file)

        for line_num, link_text, target in links:
            # Skip external links
            if is_external_link(target):
                continue

            # Resolve link path and anchor
            resolved_path, anchor = resolve_link_path(md_file, target)

            # Check file existence
            if resolved_path is None:
                violations.append(
                    f"{rel_path}:{line_num}: invalid link target: {target}"
                )
                continue

            if not resolved_path.exists():
                violations.append(
                    f"{rel_path}:{line_num}: missing target file: {target}"
                )
                continue

            # Check anchor if present
            if anchor:
                headings = extract_headings(resolved_path)
                anchor_slug = slugify_heading(anchor)
                if anchor_slug and anchor_slug not in headings:
                    target_rel = resolved_path.relative_to(root)
                    violations.append(
                        f"{rel_path}:{line_num}: missing heading anchor '{anchor}' in {target_rel}"
                    )

    if violations:
        print("[FAIL] Broken internal markdown links found:")
        for violation in violations:
            print(f"  {violation}")
        sys.exit(1)
    else:
        print("[PASS] All internal markdown links are valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
