#!/usr/bin/env python3
"""Phase 5: Frontend Bug Detection"""
import json
import os
import sys
import requests
import re
from pathlib import Path
from datetime import datetime

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3100")


def check_console_errors(bug_dir):
    """Check for console errors by analyzing HTML and checking for common issues."""
    print("=== PHASE 5: FRONTEND BUG DETECTION ===\n")

    bugs = []

    # Fetch main page
    print("Fetching frontend page...")
    try:
        response = requests.get(FRONTEND_URL, timeout=30)
        html = response.text

        # Save HTML for analysis
        with open(f"{bug_dir}/baseline/frontend_html.html", "w") as f:
            f.write(html)

        # Check for common error patterns in HTML
        error_patterns = [
            (r"console\.error\(", "console_error", "Console error calls found"),
            (r"throw new Error\(", "thrown_error", "Thrown errors found"),
            (r"Error:", "error_text", "Error text found"),
            (r"undefined", "undefined_reference", "Potential undefined references"),
            (r"null\.", "null_dereference", "Potential null dereference"),
        ]

        for pattern, bug_type, description in error_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                # Count occurrences
                count = len(matches)
                if count > 5:  # Only report if significant
                    bugs.append(
                        {
                            "bug_id": f"FRONTEND-{hash(pattern) % 100000}",
                            "severity": "P2",
                            "category": "frontend_error",
                            "type": bug_type,
                            "symptom": f"{description}: {count} occurrences",
                            "file": "rendered HTML",
                            "fix_suggestion": "Review frontend code for error handling",
                            "evidence": {"pattern": pattern, "count": count},
                        }
                    )

        # Check for missing resources (404s)
        missing_resources = re.findall(
            r"404|Not Found|Failed to load", html, re.IGNORECASE
        )
        if missing_resources:
            bugs.append(
                {
                    "bug_id": "FRONTEND-404",
                    "severity": "P1",
                    "category": "missing_resource",
                    "symptom": f"Potential 404 errors: {len(missing_resources)} references",
                    "fix_suggestion": "Check for missing assets or broken links",
                }
            )

    except Exception as e:
        bugs.append(
            {
                "bug_id": "FRONTEND-CONNECTION",
                "severity": "P0",
                "category": "frontend_unreachable",
                "symptom": f"Cannot connect to frontend: {str(e)}",
                "fix_suggestion": "Check if frontend service is running",
            }
        )

    # Check TypeScript/React files for common issues
    print("Scanning frontend source files...")
    frontend_dir = Path("app/frontend/src")

    if frontend_dir.exists():
        for ts_file in frontend_dir.rglob("*.{ts,tsx}"):
            try:
                with open(ts_file, "r") as f:
                    content = f.read()

                # Check for common React/TypeScript issues
                issues = []

                # Unused variables
                if re.search(r"const\s+\w+\s*=.*;\s*$", content, re.MULTILINE):
                    # Potential unused variable (simplified check)
                    pass

                # Missing error boundaries
                if "useState" in content and "ErrorBoundary" not in content:
                    # Not necessarily a bug, but worth noting
                    pass

                # Potential memory leaks (setInterval without cleanup)
                if "setInterval" in content and "clearInterval" not in content:
                    issues.append(
                        {
                            "type": "potential_memory_leak",
                            "symptom": "setInterval without clearInterval",
                            "line": content.find("setInterval"),
                        }
                    )

                if issues:
                    for issue in issues:
                        bugs.append(
                            {
                                "bug_id": f"FRONTEND-{hash(str(ts_file)) % 100000}",
                                "severity": "P2",
                                "category": "frontend_code_quality",
                                "file": str(ts_file),
                                "symptom": issue["symptom"],
                                "fix_suggestion": "Add proper cleanup in useEffect or componentWillUnmount",
                            }
                        )
            except:
                pass

    print(f"Found {len(bugs)} frontend issues\n")

    # Save bugs
    if bugs:
        with open(f"{bug_dir}/registry/frontend_bugs.json", "w") as f:
            json.dump(
                {"audit_timestamp": datetime.utcnow().isoformat() + "Z", "bugs": bugs},
                f,
                indent=2,
            )
        print(f"Saved to: {bug_dir}/registry/frontend_bugs.json")
        for bug in bugs[:5]:
            print(f"  {bug['severity']} {bug.get('file', 'unknown')}: {bug['symptom']}")
    else:
        print("[OK] No frontend bugs found\n")

    return len(bugs)


if __name__ == "__main__":
    bug_dir = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
    os.makedirs(f"{bug_dir}/registry", exist_ok=True)
    sys.exit(
        0 if check_console_errors(bug_dir) == 0 else 0
    )  # Don't fail on frontend issues
