#!/usr/bin/env python3
"""Phase 10: Bug Triage & Prioritization"""
import json
import os
import sys


def main():
    bug_dir = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
    registry_path = f"{bug_dir}/registry/MASTER_BUG_REGISTRY.json"

    if not os.path.exists(registry_path):
        print(f"ERROR: Master registry not found at {registry_path}")
        return 1

    with open(registry_path) as f:
        registry = json.load(f)

    print("=" * 60)
    print("HBC BUG TRIAGE REPORT")
    print("=" * 60)
    print(f"Audit Date: {registry.get('audit_timestamp', 'Unknown')}")
    print(f"Total Bugs: {registry.get('total_bugs', 0)}\n")

    # By severity
    print("By Severity:")
    for sev, count in registry.get("bugs_by_severity", {}).items():
        print(f"  {sev}: {count}")

    # By category
    print("\nBy Category:")
    for cat, bugs in registry.get("bugs_by_category", {}).items():
        if bugs:
            print(f"  {cat}: {len(bugs)}")

    # P0 bugs
    p0_bugs = [b for b in registry.get("all_bugs", []) if b.get("severity") == "P0"]
    if p0_bugs:
        print(f"\n[WARN]  P0 BUGS (Fix Immediately): {len(p0_bugs)}")
        # Group by category
        p0_by_category = {}
        for bug in p0_bugs:
            category = bug.get("category", "unknown")
            if category not in p0_by_category:
                p0_by_category[category] = []
            p0_by_category[category].append(bug)

        for category, bugs in p0_by_category.items():
            print(f"\n  {category.upper()} ({len(bugs)} bugs):")
            for bug in bugs[:5]:  # Show first 5
                bug_id = bug.get("bug_id", "UNKNOWN")
                symptom = bug.get(
                    "symptom", bug.get("type", bug.get("category", "Unknown"))
                )
                file = bug.get("file", "")
                if file:
                    print(f"    - {bug_id}: {symptom} ({file})")
                else:
                    print(f"    - {bug_id}: {symptom}")
            if len(bugs) > 5:
                print(f"    ... and {len(bugs) - 5} more")

    # Save triage report
    triage_path = f"{bug_dir}/BUG_TRIAGE_REPORT.txt"
    with open(triage_path, "w") as f:
        f.write("HBC BUG TRIAGE REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Audit Date: {registry.get('audit_timestamp', 'Unknown')}\n")
        f.write(f"Total Bugs: {registry.get('total_bugs', 0)}\n\n")
        f.write("By Severity:\n")
        for sev, count in registry.get("bugs_by_severity", {}).items():
            f.write(f"  {sev}: {count}\n")
        f.write("\nBy Category:\n")
        for cat, bugs in registry.get("bugs_by_category", {}).items():
            if bugs:
                f.write(f"  {cat}: {len(bugs)}\n")

    print(f"\n[OK] Triage report saved: {triage_path}")
    print(f"[OK] Master registry: {registry_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
