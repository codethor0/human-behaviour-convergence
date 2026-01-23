#!/usr/bin/env python3
"""
Non-destructive repo hygiene audit script.
Lists suspicious files, large files, and potential artifacts.
"""
import os
import subprocess
from pathlib import Path
from typing import List, Tuple


def get_tracked_files() -> List[str]:
    """Get list of tracked git files."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def get_file_size(filepath: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0


def find_largest_files(limit: int = 50) -> List[Tuple[str, int]]:
    """Find largest tracked files."""
    files = get_tracked_files()
    file_sizes = [(f, get_file_size(f)) for f in files if os.path.exists(f)]
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    return file_sizes[:limit]


def find_untracked_files() -> List[str]:
    """Find untracked files (not in .gitignore)."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        untracked = []
        for line in result.stdout.strip().split("\n"):
            if line.startswith("??"):
                filepath = line[3:].strip()
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    untracked.append(filepath)
        return untracked
    except subprocess.CalledProcessError:
        return []


def find_artifact_files() -> List[str]:
    """Find likely artifact files."""
    artifact_patterns = [
        "*.log",
        "*.tmp",
        "*evidence*",
        "*report*.txt",
        "*report*.json",
        "*screenshot*.png",
        "test-results/**",
        ".pytest_cache/**",
        "__pycache__/**",
    ]
    
    artifacts = []
    for root, dirs, files in os.walk("."):
        # Skip git and common ignore dirs
        if ".git" in root or "node_modules" in root or ".venv" in root:
            continue
        
        for file in files:
            filepath = os.path.join(root, file)
            for pattern in artifact_patterns:
                if pattern.replace("*", "") in filepath.lower():
                    artifacts.append(filepath)
                    break
    
    return artifacts[:100]  # Limit to first 100


def main():
    """Main execution."""
    output_dir = Path(os.getenv("EVIDENCE_DIR", "/tmp/hbc_repo_hygiene"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=== Repo Hygiene Audit ===\n")
    
    # Largest files
    print("Top 50 largest tracked files:")
    largest = find_largest_files(50)
    largest_file = output_dir / "largest_files.txt"
    with open(largest_file, "w") as f:
        for filepath, size in largest:
            size_mb = size / (1024 * 1024)
            line = f"{size_mb:.2f} MB\t{filepath}\n"
            f.write(line)
            if size_mb > 1.0:  # Only print files > 1MB
                print(f"  {size_mb:.2f} MB\t{filepath}")
    
    print(f"\nSaved to: {largest_file}")
    
    # Untracked files
    print("\nUntracked files (first 50):")
    untracked = find_untracked_files()[:50]
    untracked_file = output_dir / "untracked_files.txt"
    with open(untracked_file, "w") as f:
        for filepath in untracked:
            f.write(f"{filepath}\n")
            print(f"  {filepath}")
    
    print(f"\nSaved to: {untracked_file}")
    
    # Artifacts
    print("\nLikely artifact files (first 50):")
    artifacts = find_artifact_files()[:50]
    artifacts_file = output_dir / "artifact_files.txt"
    with open(artifacts_file, "w") as f:
        for filepath in artifacts:
            f.write(f"{filepath}\n")
            print(f"  {filepath}")
    
    print(f"\nSaved to: {artifacts_file}")
    
    # Summary
    print("\n=== Summary ===")
    print(f"Tracked files: {len(get_tracked_files())}")
    print(f"Large files (>1MB): {len([f for f, s in largest if s > 1024 * 1024])}")
    print(f"Untracked files: {len(untracked)}")
    print(f"Artifact files: {len(artifacts)}")
    
    # Check for secrets (basic patterns)
    print("\nChecking for potential secrets...")
    secret_patterns = [
        r"api[_-]?key\s*=\s*['\"][^'\"]{10,}",
        r"password\s*=\s*['\"][^'\"]{8,}",
        r"secret\s*=\s*['\"][^'\"]{10,}",
    ]
    
    tracked = get_tracked_files()
    suspicious = []
    for filepath in tracked[:100]:  # Check first 100 files
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, "r", errors="ignore") as f:
                content = f.read()
                for pattern in secret_patterns:
                    import re
                    if re.search(pattern, content, re.IGNORECASE):
                        suspicious.append(filepath)
                        break
        except Exception:
            continue
    
    if suspicious:
        print(f"  WARNING: {len(suspicious)} files may contain secrets")
        for f in suspicious[:10]:
            print(f"    - {f}")
    else:
        print("  ✓ No obvious secrets found in tracked files")
    
    print(f"\nAudit complete. Reports saved to: {output_dir}")


if __name__ == "__main__":
    main()
