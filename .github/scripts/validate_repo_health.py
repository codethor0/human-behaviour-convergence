#!/usr/bin/env python3
# SPDX-License-Identifier: PROPRIETARY
"""Repository health validation script.

Validates:
- Folder structure
- Required files
- Import resolution
- Test discovery
- Workflow YAML syntax
- Version consistency
"""

import os
import sys
import yaml
from pathlib import Path


def validate_folder_structure():
    """Validate required directories exist."""
    required_dirs = [
        "app",
        "app/backend",
        "app/frontend",
        "tests",
        "scripts",
        ".github/scripts",
    ]
    
    missing = []
    for dir_path in required_dirs:
        if not os.path.isdir(dir_path):
            missing.append(dir_path)
    
    if missing:
        print(f"ERROR: Missing directories: {', '.join(missing)}")
        return False
    
    print("PASS: All required directories exist")
    return True


def validate_required_files():
    """Validate required files exist."""
    required_files = [
        "requirements.txt",
        "requirements-dev.txt",
        "app/backend/requirements.txt",
        "pyproject.toml",
        ".python-version",
    ]
    
    missing = []
    for file_path in required_files:
        if not os.path.isfile(file_path):
            missing.append(file_path)
    
    if missing:
        print(f"ERROR: Missing files: {', '.join(missing)}")
        return False
    
    print("PASS: All required files exist")
    return True


def validate_workflow_yaml():
    """Validate all workflow YAML files."""
    workflow_dir = Path(".github/workflows")
    errors = 0
    
    for yaml_file in workflow_dir.glob("*.yml"):
        try:
            with open(yaml_file, 'r') as f:
                workflow = yaml.safe_load(f)
            
            if not isinstance(workflow, dict):
                print(f"ERROR: {yaml_file.name}: Not a valid YAML dictionary")
                errors += 1
            elif 'name' not in workflow or 'on' not in workflow or 'jobs' not in workflow:
                print(f"ERROR: {yaml_file.name}: Missing required fields")
                errors += 1
            else:
                print(f"PASS: {yaml_file.name}")
        except yaml.YAMLError as e:
            print(f"ERROR: {yaml_file.name}: YAML syntax error - {e}")
            errors += 1
        except Exception as e:
            print(f"ERROR: {yaml_file.name}: Error - {e}")
            errors += 1
    
    for yaml_file in workflow_dir.glob("*.yaml"):
        try:
            with open(yaml_file, 'r') as f:
                workflow = yaml.safe_load(f)
            
            if not isinstance(workflow, dict):
                print(f"ERROR: {yaml_file.name}: Not a valid YAML dictionary")
                errors += 1
            elif 'name' not in workflow or 'on' not in workflow or 'jobs' not in workflow:
                print(f"ERROR: {yaml_file.name}: Missing required fields")
                errors += 1
            else:
                print(f"PASS: {yaml_file.name}")
        except yaml.YAMLError as e:
            print(f"ERROR: {yaml_file.name}: YAML syntax error - {e}")
            errors += 1
        except Exception as e:
            print(f"ERROR: {yaml_file.name}: Error - {e}")
            errors += 1
    
    if errors > 0:
        print(f"ERROR: Found {errors} workflow YAML errors")
        return False
    
    print("PASS: All workflow YAML files are valid")
    return True


def validate_imports():
    """Validate critical imports work."""
    sys.path.insert(0, os.getcwd())
    
    critical_imports = [
        'app',
        'app.core',
        'app.core.location_normalizer',
        'app.core.regions',
        'connectors',
    ]
    
    errors = 0
    for module in critical_imports:
        try:
            __import__(module)
            print(f"PASS: {module}")
        except ImportError as e:
            print(f"ERROR: {module} - {e}")
            errors += 1
    
    if errors > 0:
        print(f"ERROR: Found {errors} import errors")
        return False
    
    print("PASS: All critical imports work")
    return True


def validate_test_discovery():
    """Validate test discovery works."""
    try:
        import subprocess
        result = subprocess.run(
            ['python3', '-m', 'pytest', '--collect-only', '-q', 'tests/'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"ERROR: Test discovery failed: {result.stderr}")
            return False
        print("PASS: Test discovery works")
        return True
    except Exception as e:
        print(f"ERROR: Test discovery error: {e}")
        return False


def validate_version_consistency():
    """Validate version consistency."""
    try:
        with open('.python-version', 'r') as f:
            python_version = f.read().strip()
        
        if not python_version:
            print("ERROR: .python-version is empty")
            return False
        
        major_minor = '.'.join(python_version.split('.')[:2])
        expected = '3.10'
        
        if major_minor != expected:
            print(f"ERROR: Python version mismatch")
            print(f"Expected: {expected}")
            print(f"Found: {major_minor}")
            return False
        
        print(f"PASS: Python version consistent: {major_minor}")
        return True
    except Exception as e:
        print(f"ERROR: Version validation error: {e}")
        return False


def main():
    """Run all validations."""
    print("=== Repository Health Validation ===\n")
    
    checks = [
        ("Folder Structure", validate_folder_structure),
        ("Required Files", validate_required_files),
        ("Workflow YAML", validate_workflow_yaml),
        ("Imports", validate_imports),
        ("Test Discovery", validate_test_discovery),
        ("Version Consistency", validate_version_consistency),
    ]
    
    failed = []
    for name, check_func in checks:
        print(f"\n--- {name} ---")
        if not check_func():
            failed.append(name)
    
    print("\n=== Validation Summary ===")
    if failed:
        print(f"ERROR: {len(failed)} checks failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("PASS: All checks passed")
        sys.exit(0)


if __name__ == '__main__':
    main()
