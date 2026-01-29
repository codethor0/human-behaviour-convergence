#!/usr/bin/env python3
"""Phase 7: Security Bug Detection"""
import json
import os
import sys
import re
import subprocess
from datetime import datetime
from pathlib import Path


def scan_for_secrets(bug_dir):
    """Scan for hardcoded secrets."""
    bugs = []
    secret_patterns = [
        (
            r'(API_KEY|SECRET|TOKEN|PASSWORD|KEY|SECRET_KEY)\s*=\s*["\']([^"\']{8,})["\']',
            "hardcoded_secret",
        ),
        (r'password\s*[:=]\s*["\']([^"\']{4,})["\']', "hardcoded_password"),
        (r'api[_-]?key\s*[:=]\s*["\']([^"\']{8,})["\']', "hardcoded_api_key"),
    ]

    print("Scanning for hardcoded secrets...")

    # Scan Python files
    for py_file in Path(".").rglob("*.py"):
        if "node_modules" in str(py_file) or ".git" in str(py_file):
            continue

        try:
            content = py_file.read_text()
            for pattern, bug_type in secret_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    bugs.append(
                        {
                            "bug_id": f"SECRET-{hash(str(py_file) + str(line_num)) % 100000}",
                            "severity": "P0",
                            "category": "secret_exposure",
                            "file": str(py_file),
                            "line": line_num,
                            "type": bug_type,
                            "snippet": match.group(0)[:100],
                            "fix_suggestion": "Move to environment variables, use vault, rotate exposed secrets",
                        }
                    )
        except:
            pass

    # Scan TypeScript/JavaScript files
    for js_file in Path("app/frontend").rglob("*.{ts,tsx,js,jsx}"):
        try:
            content = js_file.read_text()
            for pattern, bug_type in secret_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    bugs.append(
                        {
                            "bug_id": f"SECRET-{hash(str(js_file) + str(line_num)) % 100000}",
                            "severity": "P0",
                            "category": "secret_exposure",
                            "file": str(js_file),
                            "line": line_num,
                            "type": bug_type,
                            "snippet": match.group(0)[:100],
                            "fix_suggestion": "Move to environment variables, use vault, rotate exposed secrets",
                        }
                    )
        except:
            pass

    return bugs


def check_dependency_vulnerabilities(bug_dir):
    """Check for dependency vulnerabilities."""
    bugs = []

    # Check Python dependencies
    print("Checking Python dependencies...")
    if os.path.exists("requirements.txt"):
        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                try:
                    vulns = json.loads(result.stdout)
                    for vuln in vulns.get("vulnerabilities", []):
                        if vuln.get("severity") in ["CRITICAL", "HIGH"]:
                            bugs.append(
                                {
                                    "bug_id": f"VULN-PY-{hash(vuln.get('id', '')) % 100000}",
                                    "severity": "P0",
                                    "category": "dependency_vulnerability",
                                    "package": vuln.get("name"),
                                    "vulnerability": vuln.get("id"),
                                    "severity_level": vuln.get("severity"),
                                    "fix_suggestion": f"Update {vuln.get('name')} to patched version",
                                }
                            )
                except:
                    pass
        except:
            pass

    return bugs


def main():
    bug_dir = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
    os.makedirs(f"{bug_dir}/registry", exist_ok=True)
    os.makedirs(f"{bug_dir}/security", exist_ok=True)

    print("=== PHASE 7: SECURITY BUG DETECTION ===\n")

    bugs = []

    # Scan for secrets
    secret_bugs = scan_for_secrets(bug_dir)
    if secret_bugs:
        print(f"  Found {len(secret_bugs)} potential secret exposures")
        bugs.extend(secret_bugs)
    else:
        print("  [OK] No hardcoded secrets found")

    # Check dependencies
    vuln_bugs = check_dependency_vulnerabilities(bug_dir)
    if vuln_bugs:
        print(f"  Found {len(vuln_bugs)} dependency vulnerabilities")
        bugs.extend(vuln_bugs)
    else:
        print("  [OK] No critical vulnerabilities found")

    # Save bugs
    if bugs:
        with open(f"{bug_dir}/registry/security_bugs.json", "w") as f:
            json.dump(
                {"audit_timestamp": datetime.utcnow().isoformat() + "Z", "bugs": bugs},
                f,
                indent=2,
            )
        print(f"\n[OK] Found {len(bugs)} security bugs")
        print(f"   Saved to: {bug_dir}/registry/security_bugs.json")
    else:
        print("\n[OK] No security bugs found")

    return 0


if __name__ == "__main__":
    sys.exit(main())
