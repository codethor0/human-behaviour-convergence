#!/usr/bin/env python3
"""
Cache Key Audit: Verify that REGIONAL sources include geo parameters in cache keys.

This script analyzes source code to find cache key construction patterns and flags
sources that should be regional but don't include geo parameters in cache keys.
"""
import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).parent.parent
INGESTION_DIR = REPO_ROOT / "app" / "services" / "ingestion"


def find_cache_key_patterns(file_path: Path) -> List[Tuple[str, int, str]]:
    """
    Find cache key construction patterns in a file.
    
    Returns:
        List of (pattern, line_number, context) tuples
    """
    patterns = []
    
    try:
        with open(file_path, "r") as f:
            content = f.read()
            lines = content.split("\n")
            
            # Look for cache_key = f"..."
            for i, line in enumerate(lines, 1):
                # Match: cache_key = f"..."
                match = re.search(r'cache_key\s*=\s*f?["\']([^"\']+)["\']', line)
                if match:
                    pattern = match.group(1)
                    # Get context (surrounding lines) - extended to catch region_key assignment
                    context_start = max(0, i - 10)  # Look further back for region_key assignment
                    context_end = min(len(lines), i + 3)
                    context = "\n".join(lines[context_start:context_end])
                    patterns.append((pattern, i, context))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
    
    return patterns


def classify_cache_key(pattern: str, source_id: str, context: str = "") -> Dict[str, any]:
    """
    Classify a cache key pattern and check if it includes geo parameters.
    
    Args:
        pattern: The cache key pattern string
        source_id: Source identifier
        context: Surrounding code context to check for variable assignments
    
    Returns:
        Dict with classification and flags
    """
    result = {
        "pattern": pattern,
        "includes_lat_lon": False,
        "includes_region": False,
        "includes_region_name": False,
        "includes_region_code": False,
        "includes_region_id": False,
        "geo_params_found": [],
        "is_global_cache": False,
        "issue": None
    }
    
    # Check for geo parameters in pattern
    geo_patterns = {
        "latitude": r"\{?latitude",
        "longitude": r"\{?longitude",
        "lat": r"\{?lat[^_]",
        "lon": r"\{?lon[^_]",
        "region_name": r"\{?region_name",
        "region_code": r"\{?region_code",
        "region_id": r"\{?region_id",
        "region": r"\{?region[^_]",
        "region_key": r"\{?region_key",  # For mobility
        "state_name": r"\{?state_name",
        "location": r"\{?location",
    }
    
    # Check pattern itself
    for param_name, regex in geo_patterns.items():
        if re.search(regex, pattern, re.IGNORECASE):
            result["geo_params_found"].append(param_name)
            if "lat" in param_name.lower():
                result["includes_lat_lon"] = True
            if "region" in param_name.lower() or "state" in param_name.lower():
                result["includes_region"] = True
                if "name" in param_name.lower():
                    result["includes_region_name"] = True
                if "code" in param_name.lower():
                    result["includes_region_code"] = True
                if "id" in param_name.lower():
                    result["includes_region_id"] = True
    
    # Also check context for region_key variable (mobility case)
    if "region_key" in pattern.lower() or re.search(r"region_key\s*=", context, re.IGNORECASE):
        if "region_key" not in result["geo_params_found"]:
            result["geo_params_found"].append("region_key")
            result["includes_region"] = True
    
    # Determine if this is a global cache (no geo params)
    if not result["geo_params_found"]:
        result["is_global_cache"] = True
    
    # Classify source as REGIONAL based on source_id
    regional_sources = [
        "weather", "openaq", "nws", "usgs", "search_trends",
        "political", "crime", "misinformation", "social_cohesion",
        "openstates", "openfema"
    ]
    
    is_regional_source = any(reg in source_id.lower() for reg in regional_sources)
    
    # Flag issue if REGIONAL source has global cache
    if is_regional_source and result["is_global_cache"]:
        result["issue"] = f"REGIONAL source '{source_id}' uses global cache key (no geo params)"
    
    return result


def audit_all_ingestion_files() -> Dict[str, List[Dict]]:
    """Audit all ingestion files for cache key patterns."""
    results = {}
    
    for file_path in INGESTION_DIR.glob("*.py"):
        if file_path.name == "__init__.py":
            continue
        
        source_id = file_path.stem
        patterns = find_cache_key_patterns(file_path)
        
        if patterns:
            results[source_id] = []
            for pattern, line_num, context in patterns:
                analysis = classify_cache_key(pattern, source_id, context)
                analysis["line_number"] = line_num
                analysis["file"] = str(file_path.relative_to(REPO_ROOT))
                results[source_id].append(analysis)
    
    return results


def main():
    """Main execution."""
    import json
    import os
    import sys
    
    proof_dir = Path(os.getenv("PROOF_DIR", "/tmp/hbc_discrepancy_proof"))
    proof_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("CACHE KEY AUDIT")
    print("=" * 80)
    
    results = audit_all_ingestion_files()
    
    # Save detailed results
    audit_path = proof_dir / "cache_key_audit.json"
    with open(audit_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nSaved audit: {audit_path}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("CACHE KEY SUMMARY")
    print("=" * 80)
    
    issues = []
    for source_id, analyses in results.items():
        for analysis in analyses:
            print(f"\n{source_id} (line {analysis['line_number']}):")
            print(f"  Pattern: {analysis['pattern']}")
            print(f"  Geo params: {analysis['geo_params_found'] or 'None'}")
            print(f"  Global cache: {analysis['is_global_cache']}")
            
            if analysis["issue"]:
                print(f"  [ISSUE] {analysis['issue']}")
                issues.append({
                    "source": source_id,
                    "file": analysis["file"],
                    "line": analysis["line_number"],
                    "pattern": analysis["pattern"],
                    "issue": analysis["issue"]
                })
    
    # Save issues
    if issues:
        issues_path = proof_dir / "cache_key_issues.json"
        with open(issues_path, "w") as f:
            json.dump(issues, f, indent=2)
        print(f"\n[P0] Found {len(issues)} cache key issues")
        print(f"  Saved to: {issues_path}")
    else:
        print("\n[OK] No cache key issues detected")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
