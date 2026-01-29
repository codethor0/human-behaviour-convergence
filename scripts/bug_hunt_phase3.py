#!/usr/bin/env python3
"""Phase 3: Mathematical Bug Detection"""
import json
import os
import sys
import ast
from pathlib import Path
from datetime import datetime


class MathBugFinder(ast.NodeVisitor):
    def __init__(self, file_path):
        self.file_path = file_path
        self.bugs = []

    def visit_BinOp(self, node):
        # Check for division by zero risk
        if isinstance(node.op, ast.Div):
            self.check_division_by_zero(node)
            self.check_integer_division(node)

        self.generic_visit(node)

    def check_division_by_zero(self, node):
        # Check if denominator is a literal zero
        if isinstance(node.right, ast.Constant) and node.right.value == 0:
            self.bugs.append(
                {
                    "type": "division_by_zero",
                    "line": node.lineno,
                    "critical": True,
                    "snippet": f"Division by literal zero at line {node.lineno}",
                }
            )
        # Check if denominator could be zero (variable that might be 0)
        elif isinstance(node.right, ast.Name):
            # This is a potential risk - variable could be zero
            self.bugs.append(
                {
                    "type": "potential_division_by_zero",
                    "line": node.lineno,
                    "variable": node.right.id,
                    "critical": False,
                    "snippet": f"Division by variable '{node.right.id}' that might be zero",
                }
            )

    def check_integer_division(self, node):
        # In Python 3, / is float division, but check for potential issues
        # Check if both operands are integers and result might need float
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            if isinstance(node.left.value, int) and isinstance(node.right.value, int):
                # This is fine in Python 3, but log for awareness
                pass


def scan_python_files(bug_dir):
    """Scan all Python files for mathematical bugs."""
    print("=== PHASE 3: MATHEMATICAL BUG DETECTION ===\n")

    bugs = []
    files_scanned = 0

    # Scan Python files in app/ and tests/
    scan_paths = [
        Path("app"),
        Path("tests"),
        Path("hbc"),
        Path("connectors"),
        Path("predictors"),
    ]

    for scan_path in scan_paths:
        if not scan_path.exists():
            continue

        for py_file in scan_path.rglob("*.py"):
            # Skip virtual environments and cache
            if any(
                skip in str(py_file)
                for skip in [".venv", "__pycache__", "node_modules"]
            ):
                continue

            try:
                with open(py_file, "r") as f:
                    content = f.read()

                try:
                    tree = ast.parse(content, filename=str(py_file))
                    finder = MathBugFinder(str(py_file))
                    finder.visit(tree)

                    if finder.bugs:
                        for bug in finder.bugs:
                            bugs.append(
                                {
                                    "bug_id": f"MATH-{hash(str(py_file) + str(bug['line'])) % 100000}",
                                    "severity": "P0" if bug.get("critical") else "P2",
                                    "category": "mathematical",
                                    "file": str(py_file),
                                    "line": bug["line"],
                                    "symptom": bug.get(
                                        "snippet", bug.get("type", "Unknown")
                                    ),
                                    "root_cause": bug.get("type", "Unknown"),
                                    "fix_suggestion": (
                                        "Add zero-check before division"
                                        if "division" in bug.get("type", "")
                                        else "Review mathematical operation"
                                    ),
                                    "reproduction_steps": f"Examine line {bug['line']} in {py_file}",
                                }
                            )

                    files_scanned += 1
                except SyntaxError:
                    # Skip files with syntax errors
                    pass
            except Exception:
                # Skip files we can't read
                pass

    print(f"Scanned {files_scanned} Python files")

    if bugs:
        print(f"Found {len(bugs)} potential mathematical bugs\n")
        for bug in bugs[:10]:  # Show first 10
            print(f"  {bug['severity']} {bug['file']}:{bug['line']} - {bug['symptom']}")
        if len(bugs) > 10:
            print(f"  ... and {len(bugs) - 10} more")
    else:
        print("[OK] No mathematical bugs found\n")

    # Save bugs
    if bugs:
        with open(f"{bug_dir}/registry/math_bugs.json", "w") as f:
            json.dump(
                {"audit_timestamp": datetime.utcnow().isoformat() + "Z", "bugs": bugs},
                f,
                indent=2,
            )
        print(f"Saved to: {bug_dir}/registry/math_bugs.json")

    return len(bugs)


if __name__ == "__main__":
    bug_dir = os.getenv("BUG_DIR", "/tmp/hbc_bugs_default")
    os.makedirs(f"{bug_dir}/registry", exist_ok=True)
    sys.exit(0 if scan_python_files(bug_dir) == 0 else 1)
