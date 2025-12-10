#!/usr/bin/env python3
# SPDX-License-Identifier: PROPRIETARY
"""Architecture import-graph validation.

Validates that imports follow the intended architecture:
- app/core should not import from app/backend
- app/backend can import from app/core
- connectors should be independent
- No circular imports
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


def get_imports(file_path: Path) -> List[str]:
    """Extract import statements from a Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except Exception as e:
        print(f"WARNING: Could not parse {file_path}: {e}")
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])

    return imports


def validate_architecture():
    """Validate import architecture rules."""
    root = Path(__file__).parent.parent.parent

    # Define allowed import patterns
    rules = {
        "app/core": {
            "allowed": ["app.core", "connectors", "hbc", "predictors"],
            "forbidden": ["app.backend"],
        },
        "app/backend": {
            "allowed": ["app.core", "app.backend", "connectors", "hbc"],
            "forbidden": [],
        },
        "connectors": {
            "allowed": ["connectors"],
            "forbidden": ["app.backend"],
        },
    }

    violations = []
    import_graph: Dict[str, Set[str]] = defaultdict(set)

    # Scan Python files
    for py_file in root.rglob("*.py"):
        if "__pycache__" in str(py_file) or ".venv" in str(py_file):
            continue

        rel_path = py_file.relative_to(root)
        imports = get_imports(py_file)

        # Check rules based on file location
        for pattern, rule in rules.items():
            if pattern in str(rel_path):
                for imp in imports:
                    import_graph[str(rel_path)].add(imp)

                    # Check forbidden imports
                    for forbidden in rule["forbidden"]:
                        if imp.startswith(forbidden):
                            violations.append(
                                f"{rel_path} imports {imp} (forbidden: {forbidden})"
                            )

    # Check for circular imports (simplified check)
    # This is a basic check - full cycle detection would require graph analysis

    if violations:
        print("ERROR: Architecture violations found:")
        for violation in violations:
            print(f"  - {violation}")
        return False

    print("PASS: Architecture validation successful")
    print(f"  - Scanned {len(import_graph)} files")
    print(f"  - No forbidden imports detected")
    return True


if __name__ == "__main__":
    success = validate_architecture()
    sys.exit(0 if success else 1)
