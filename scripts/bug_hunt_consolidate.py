#!/usr/bin/env python3
"""Phase 9: Bug Registry Consolidation"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def consolidate_registry(bug_dir):
    """Consolidate all bug registries into master registry."""
    print("=== PHASE 9: BUG REGISTRY CONSOLIDATION ===\n")

    master_registry = {
        "audit_timestamp": datetime.utcnow().isoformat() + "Z",
        "total_bugs": 0,
        "bugs_by_severity": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        "bugs_by_category": {
            "data_integrity": [],
            "visualization": [],
            "mathematical": [],
            "integration": [],
            "frontend": [],
            "performance": [],
            "security": [],
            "concurrency": [],
            "configuration": [],
        },
        "all_bugs": [],
    }

    # Load all bug files
    registry_dir = Path(f"{bug_dir}/registry")
    bug_files = {
        "data_bugs.json": "data_integrity",
        "visual_bugs.json": "visualization",
        "math_bugs.json": "mathematical",
        "integration_bugs.json": "integration",
        "frontend_errors.json": "frontend",
        "performance_bugs.json": "performance",
        "security_bugs.json": "security",
        "concurrency_bugs.json": "concurrency",
        "layout_bugs.json": "frontend",
    }

    for filename, category in bug_files.items():
        filepath = registry_dir / filename
        if filepath.exists():
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    bugs = data.get("bugs", [])
                    if not bugs and isinstance(data, list):
                        bugs = data

                    for bug in bugs:
                        if isinstance(bug, dict):
                            master_registry["all_bugs"].append(bug)
                            master_registry["bugs_by_category"][category].append(bug)
                            severity = bug.get("severity", "P3")
                            if severity in master_registry["bugs_by_severity"]:
                                master_registry["bugs_by_severity"][severity] += 1
            except Exception as e:
                print(f"  [WARN]  Error loading {filename}: {e}")

    master_registry["total_bugs"] = len(master_registry["all_bugs"])

    # Save master registry
    master_path = registry_dir / "MASTER_BUG_REGISTRY.json"
    with open(master_path, "w") as f:
        json.dump(master_registry, f, indent=2)

    print(f"[OK] Consolidated {master_registry['total_bugs']} bugs")
    print(f"   Saved to: {master_path}\n")

    # Print summary
    print("=== BUG SUMMARY ===")
    print(f"Total Bugs: {master_registry['total_bugs']}")
    print("\nBy Severity:")
    for sev, count in master_registry["bugs_by_severity"].items():
        print(f"  {sev}: {count}")

    print("\nBy Category:")
    for cat, bugs in master_registry["bugs_by_category"].items():
        if bugs:
            print(f"  {cat}: {len(bugs)}")

    # List P0 bugs
    p0_bugs = [b for b in master_registry["all_bugs"] if b.get("severity") == "P0"]
    if p0_bugs:
        print("\n[WARN]  P0 BUGS (Fix Immediately):")
        for bug in p0_bugs:
            print(
                f"  - {bug.get('bug_id', 'UNKNOWN')}: {bug.get('symptom', bug.get('category', 'Unknown'))}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(consolidate_registry(os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")))
