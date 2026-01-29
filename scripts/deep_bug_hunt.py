#!/usr/bin/env python3
"""
HBC Deep Bug Hunt & Forensic Registry
Enhanced version with deeper code analysis, error handling checks, and edge case detection.
"""
import json
import os
import sys
import subprocess
import ast
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

BUG_DIR = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3001")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8100")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3100")


def run_command(cmd: str, output_file: Optional[str] = None) -> Tuple[int, str, str]:
    """Run command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        if output_file:
            with open(output_file, "w") as f:
                f.write(f"Command: {cmd}\n")
                f.write(f"Exit Code: {result.returncode}\n")
                f.write(f"STDOUT:\n{result.stdout}\n")
                if result.stderr:
                    f.write(f"STDERR:\n{result.stderr}\n")
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        if output_file:
            with open(output_file, "w") as f:
                f.write(f"Command: {cmd}\n")
                f.write(f"ERROR: {str(e)}\n")
        return 1, "", str(e)


class DeepCodeAnalyzer(ast.NodeVisitor):
    """Deep AST analyzer for finding bugs."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.bugs = []
        self.current_function = None
        self.inside_try = False

    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_Try(self, node):
        old_try = self.inside_try
        self.inside_try = True
        self.generic_visit(node)
        self.inside_try = old_try

        # Check for bare except or except pass
        for handler in node.handlers:
            if handler.type is None:  # bare except
                self.bugs.append(
                    {
                        "type": "bare_except",
                        "line": handler.lineno,
                        "severity": "P1",
                        "symptom": "Bare except clause catches all exceptions including SystemExit",
                        "fix": "Use specific exception types or at least 'except Exception:'",
                    }
                )
            # Check if handler body is just pass
            if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                self.bugs.append(
                    {
                        "type": "silent_exception",
                        "line": handler.lineno,
                        "severity": "P1",
                        "symptom": "Exception caught but silently ignored",
                        "fix": "Add logging or re-raise",
                    }
                )

    def visit_Subscript(self, node):
        # Check for dictionary/list access without safety
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            # Check if it's a dict access pattern
            if isinstance(node.slice, ast.Constant) or isinstance(node.slice, ast.Str):
                # This is a potential KeyError risk
                if not self._has_safety_check(var_name, node.lineno):
                    self.bugs.append(
                        {
                            "type": "unsafe_dict_access",
                            "line": node.lineno,
                            "variable": var_name,
                            "severity": "P2",
                            "symptom": f"Dictionary access on '{var_name}' without key existence check",
                            "fix": f"Use .get() method or check '{var_name} in dict' before access",
                        }
                    )
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Check for None attribute access
        if isinstance(node.value, ast.Name) and node.value.id in [
            "result",
            "response",
            "data",
            "obj",
        ]:
            # Common patterns that might be None
            if not self._has_none_check(node.value.id, node.lineno):
                self.bugs.append(
                    {
                        "type": "potential_none_access",
                        "line": node.lineno,
                        "variable": node.value.id,
                        "severity": "P2",
                        "symptom": f"Attribute access on '{node.value.id}' that might be None",
                        "fix": "Add None check before accessing attributes",
                    }
                )
        self.generic_visit(node)

    def visit_BinOp(self, node):
        # Check for division by zero
        if isinstance(node.op, ast.Div):
            if isinstance(node.right, ast.Name):
                var_name = node.right.id
                if not self._has_zero_check(var_name, node.lineno):
                    self.bugs.append(
                        {
                            "type": "division_by_zero",
                            "line": node.lineno,
                            "variable": var_name,
                            "severity": "P2",
                            "symptom": f"Division by '{var_name}' without zero check",
                            "fix": f"Add check: if {var_name} == 0: raise ValueError(...)",
                        }
                    )
        self.generic_visit(node)

    def _has_safety_check(self, var_name: str, line: int) -> bool:
        # Simplified: check if there's a safety check nearby
        # In real implementation, would analyze control flow
        return False

    def _has_none_check(self, var_name: str, line: int) -> bool:
        # Simplified: check if there's a None check nearby
        return False

    def _has_zero_check(self, var_name: str, line: int) -> bool:
        # Check if there's a guard before this line
        # Would need to read file and check previous lines
        return False


def check_syntax_errors() -> List[Dict]:
    """Check for Python syntax errors."""
    print("\n=== DEEP CHECK: SYNTAX ERRORS ===")
    bugs = []

    scan_paths = [Path("app"), Path("connectors"), Path("predictors")]

    for scan_path in scan_paths:
        if not scan_path.exists():
            continue

        for py_file in scan_path.rglob("*.py"):
            if any(
                skip in str(py_file)
                for skip in [".venv", "__pycache__", "node_modules"]
            ):
                continue

            try:
                with open(py_file, "r") as f:
                    content = f.read()

                try:
                    compile(content, str(py_file), "exec")
                except SyntaxError as e:
                    bugs.append(
                        {
                            "bug_id": f"SYNTAX-{hash(str(py_file)) % 100000}",
                            "severity": "P0",
                            "category": "syntax_error",
                            "component": str(py_file),
                            "location": f"line {e.lineno}",
                            "symptom": f"Syntax error: {e.msg}",
                            "root_cause": "Invalid Python syntax",
                            "evidence": {
                                "file": str(py_file),
                                "line": e.lineno,
                                "error": e.msg,
                                "text": e.text,
                            },
                            "fix_suggestion": f"Fix syntax error at line {e.lineno}",
                            "reproduction_steps": f"python3 -m py_compile {py_file}",
                            "verification_method": "File should compile without errors",
                        }
                    )
                    print(f"  [FAIL] {py_file}:{e.lineno} - {e.msg}")
            except Exception:
                pass

    print(f"  Found {len(bugs)} syntax errors")
    return bugs


def check_bare_excepts() -> List[Dict]:
    """Check for bare except clauses and silent exception handling."""
    print("\n=== DEEP CHECK: EXCEPTION HANDLING ===")
    bugs = []

    scan_paths = [Path("app"), Path("connectors")]

    for scan_path in scan_paths:
        if not scan_path.exists():
            continue

        for py_file in scan_path.rglob("*.py"):
            if any(skip in str(py_file) for skip in [".venv", "__pycache__"]):
                continue

            try:
                with open(py_file, "r") as f:
                    content = f.read()
                    lines = content.split("\n")

                try:
                    tree = ast.parse(content, filename=str(py_file))
                    analyzer = DeepCodeAnalyzer(str(py_file))
                    analyzer.visit(tree)

                    for bug in analyzer.bugs:
                        # Get context
                        context_start = max(0, bug["line"] - 3)
                        context_end = min(len(lines), bug["line"] + 2)
                        context = "\n".join(lines[context_start:context_end])

                        bugs.append(
                            {
                                "bug_id": f"EXCEPT-{hash(str(py_file) + str(bug['line'])) % 100000}",
                                "severity": bug.get("severity", "P2"),
                                "category": "exception_handling",
                                "component": str(py_file),
                                "location": f"line {bug['line']}",
                                "symptom": bug.get(
                                    "symptom", bug.get("type", "Unknown")
                                ),
                                "root_cause": bug.get("type", "Unknown"),
                                "evidence": {
                                    "file": str(py_file),
                                    "line": bug["line"],
                                    "code_context": context,
                                    "bug_type": bug.get("type"),
                                },
                                "fix_suggestion": bug.get(
                                    "fix", "Review exception handling"
                                ),
                                "reproduction_steps": f"Examine line {bug['line']} in {py_file}",
                                "verification_method": "Exception handling should be explicit and logged",
                            }
                        )
                except SyntaxError:
                    # Skip files with syntax errors (handled separately)
                    pass
            except Exception:
                pass

    print(f"  Found {len(bugs)} exception handling issues")
    return bugs


def check_unsafe_accesses() -> List[Dict]:
    """Check for unsafe dictionary/list/attribute accesses."""
    print("\n=== DEEP CHECK: UNSAFE ACCESSES ===")
    bugs = []

    # Look for common unsafe patterns
    patterns = [
        (r'(\w+)\[["\'](\w+)["\']\]', "dict_key_access"),
        (r"(\w+)\[(\d+)\]", "list_index_access"),
        (r"(\w+)\.(\w+)", "attribute_access"),
    ]

    scan_paths = [Path("app/core"), Path("app/services")]

    for scan_path in scan_paths:
        if not scan_path.exists():
            continue

        for py_file in scan_path.rglob("*.py"):
            if any(skip in str(py_file) for skip in [".venv", "__pycache__"]):
                continue

            try:
                with open(py_file, "r") as f:
                    content = f.read()
                    lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    # Check for dict access without .get()
                    if re.search(r'\w+\[["\']\w+["\']\]', line) and ".get(" not in line:
                        # Check if it's in a try block (simplified check)
                        if "try:" not in "\n".join(
                            lines[max(0, line_num - 10) : line_num]
                        ):
                            bugs.append(
                                {
                                    "bug_id": f"ACCESS-{hash(str(py_file) + str(line_num)) % 100000}",
                                    "severity": "P2",
                                    "category": "unsafe_access",
                                    "component": str(py_file),
                                    "location": f"line {line_num}",
                                    "symptom": "Dictionary key access without .get() or try/except",
                                    "root_cause": "Potential KeyError if key doesn't exist",
                                    "evidence": {
                                        "file": str(py_file),
                                        "line": line_num,
                                        "code": line.strip(),
                                    },
                                    "fix_suggestion": "Use .get() method or wrap in try/except",
                                    "reproduction_steps": f"Examine line {line_num} in {py_file}",
                                    "verification_method": "Use safe access patterns",
                                }
                            )
            except Exception:
                pass

    print(f"  Found {len(bugs)} unsafe access patterns")
    return bugs


def check_missing_guards() -> List[Dict]:
    """Check for missing None/zero/empty checks before operations."""
    print("\n=== DEEP CHECK: MISSING GUARDS ===")
    bugs = []

    scan_paths = [Path("app/core")]

    for scan_path in scan_paths:
        if not scan_path.exists():
            continue

        for py_file in scan_path.rglob("*.py"):
            if any(skip in str(py_file) for skip in [".venv", "__pycache__"]):
                continue

            try:
                with open(py_file, "r") as f:
                    content = f.read()
                    lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    # Check for division without obvious guard
                    if "/" in line and "if" not in "\n".join(
                        lines[max(0, line_num - 5) : line_num]
                    ):
                        # Look for division by variable
                        match = re.search(r"/(\w+)", line)
                        if match:
                            var = match.group(1)
                            # Check if there's a guard in previous lines
                            prev_lines = "\n".join(
                                lines[max(0, line_num - 10) : line_num]
                            )
                            if (
                                f"if {var}" not in prev_lines
                                and f"elif {var}" not in prev_lines
                            ):
                                bugs.append(
                                    {
                                        "bug_id": f"GUARD-{hash(str(py_file) + str(line_num)) % 100000}",
                                        "severity": "P2",
                                        "category": "missing_guard",
                                        "component": str(py_file),
                                        "location": f"line {line_num}",
                                        "symptom": f"Division by '{var}' without explicit guard check",
                                        "root_cause": "Missing zero-check before division",
                                        "evidence": {
                                            "file": str(py_file),
                                            "line": line_num,
                                            "code": line.strip(),
                                            "variable": var,
                                        },
                                        "fix_suggestion": f"Add check: if {var} == 0: raise ValueError(...)",
                                        "reproduction_steps": f"Examine line {line_num} in {py_file}",
                                        "verification_method": "Add explicit guard checks",
                                    }
                                )
            except Exception:
                pass

    print(f"  Found {len(bugs)} missing guard checks")
    return bugs


def check_config_issues() -> List[Dict]:
    """Check for configuration and environment variable issues."""
    print("\n=== DEEP CHECK: CONFIGURATION ===")
    bugs = []

    # Check for hardcoded values that should be config
    config_files = [
        Path("docker-compose.yml"),
        Path("app/backend/app/main.py"),
    ]

    for config_file in config_files:
        if not config_file.exists():
            continue

        try:
            with open(config_file, "r") as f:
                content = f.read()
                lines = content.split("\n")

            # Check for hardcoded ports, hosts, etc.
            for line_num, line in enumerate(lines, 1):
                # Check for 0.0.0.0 binding (security concern)
                if "0.0.0.0" in line and "host=" in line:
                    bugs.append(
                        {
                            "bug_id": f"CONFIG-{hash(str(config_file) + str(line_num)) % 100000}",
                            "severity": "P1",
                            "category": "security_config",
                            "component": str(config_file),
                            "location": f"line {line_num}",
                            "symptom": "Binding to 0.0.0.0 (all interfaces)",
                            "root_cause": "Security risk in production",
                            "evidence": {
                                "file": str(config_file),
                                "line": line_num,
                                "code": line.strip(),
                            },
                            "fix_suggestion": "Use specific interface or environment variable",
                            "reproduction_steps": f"Examine line {line_num} in {config_file}",
                            "verification_method": "Should bind to specific interface in production",
                        }
                    )
        except Exception:
            pass

    print(f"  Found {len(bugs)} configuration issues")
    return bugs


def main():
    os.makedirs(f"{BUG_DIR}/registry", exist_ok=True)

    print("=" * 60)
    print("HBC DEEP BUG HUNT & FORENSIC REGISTRY")
    print("=" * 60)
    print(f"Bug Directory: {BUG_DIR}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    all_bugs = []

    # Run comprehensive bug hunt first
    print("\nRunning comprehensive bug hunt...")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/comprehensive_bug_hunt.py"],
            env={**os.environ, "BUG_DIR": BUG_DIR},
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(f"  [WARN]  Comprehensive bug hunt had issues: {result.stderr[:200]}")
    except Exception as e:
        print(f"  [WARN]  Could not run comprehensive bug hunt: {e}")

    # Deep checks
    all_bugs.extend(check_syntax_errors())
    all_bugs.extend(check_bare_excepts())
    all_bugs.extend(check_unsafe_accesses())
    all_bugs.extend(check_missing_guards())
    all_bugs.extend(check_config_issues())

    # Load existing bugs from comprehensive hunt
    try:
        with open(f"{BUG_DIR}/registry/MASTER_BUG_REGISTRY.json", "r") as f:
            existing_registry = json.load(f)
            # Extract bugs from existing registry
            for category, bugs in existing_registry.get("bugs_by_category", {}).items():
                all_bugs.extend(bugs)
    except FileNotFoundError:
        pass

    # Consolidate
    bugs_by_category = {
        "syntax_error": [],
        "exception_handling": [],
        "unsafe_access": [],
        "missing_guard": [],
        "security_config": [],
        "data_integrity": [],
        "visualization": [],
        "mathematical": [],
        "integration": [],
        "frontend": [],
        "performance": [],
        "security": [],
    }

    bugs_by_severity = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}

    for bug in all_bugs:
        category = bug.get("category", "unknown")
        if category in bugs_by_category:
            bugs_by_category[category].append(bug)
        else:
            bugs_by_category["missing_guard"].append(bug)

        severity = bug.get("severity", "P3")
        bugs_by_severity[severity] = bugs_by_severity.get(severity, 0) + 1

    registry = {
        "audit_timestamp": datetime.now().isoformat() + "Z",
        "total_bugs": len(all_bugs),
        "bugs_by_severity": bugs_by_severity,
        "bugs_by_category": bugs_by_category,
    }

    # Save master registry
    with open(f"{BUG_DIR}/registry/MASTER_BUG_REGISTRY.json", "w") as f:
        json.dump(registry, f, indent=2)

    # Generate report
    print("\n" + "=" * 60)
    print("HBC DEEP BUG HUNT REPORT")
    print("=" * 60)
    print(f"Total Bugs: {registry['total_bugs']}")
    print("\nBy Severity:")
    for sev, count in registry["bugs_by_severity"].items():
        print(f"  {sev}: {count}")

    print("\nBy Category:")
    for cat, bugs in registry["bugs_by_category"].items():
        if bugs:
            print(f"  {cat}: {len(bugs)}")

    print("\n[WARN]  P0 BUGS (Fix Immediately):")
    for category, bugs in registry["bugs_by_category"].items():
        for bug in bugs:
            if bug.get("severity") == "P0":
                print(
                    f"  - {bug.get('bug_id', 'UNKNOWN')}: {bug.get('symptom', 'Unknown')}"
                )

    print(f"\n[OK] Master registry saved: {BUG_DIR}/registry/MASTER_BUG_REGISTRY.json")

    return 0 if registry["total_bugs"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
