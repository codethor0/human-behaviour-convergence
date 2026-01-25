#!/usr/bin/env python3
"""
Source Regionality Audit: Classify and audit each data source for regionality.

For each source:
- Classify as GLOBAL, NATIONAL, REGIONAL, or POTENTIALLY_GLOBAL
- Verify geo inputs are actually used
- Verify cache keys include region parameters for REGIONAL sources
- Document expected variance behavior
"""
import ast
import importlib.util
import inspect
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

PROOF_DIR = os.getenv("PROOF_DIR", "/tmp/hbc_discrepancy_proof")


def classify_source(source_id: str, fetcher_class: Any) -> Dict[str, Any]:
    """
    Classify a source and audit its regionality implementation.
    
    Returns:
        Dict with classification, geo_inputs, cache_key_fields, expected_variance
    """
    result = {
        "source_id": source_id,
        "class": "UNKNOWN",
        "geo_inputs_used": [],
        "cache_key_fields": [],
        "expected_variance": None,
        "failure_mode": "unknown",
        "notes": []
    }
    
    # Get source code
    try:
        source_file = inspect.getfile(fetcher_class)
        with open(source_file, "r") as f:
            source_code = f.read()
    except Exception as e:
        result["notes"].append(f"Could not read source: {e}")
        return result
    
    # Analyze geo inputs
    # Look for method parameters: lat, lon, region_name, region_id, region_code
    geo_params = []
    if hasattr(fetcher_class, "__init__"):
        sig = inspect.signature(fetcher_class.__init__)
        for param_name in sig.parameters:
            if any(geo in param_name.lower() for geo in ["lat", "lon", "region", "location", "geo"]):
                geo_params.append(param_name)
    
    # Check fetch methods
    fetch_methods = [m for m in dir(fetcher_class) if "fetch" in m.lower() or "pull" in m.lower()]
    for method_name in fetch_methods:
        try:
            method = getattr(fetcher_class, method_name)
            if inspect.ismethod(method) or inspect.isfunction(method):
                sig = inspect.signature(method)
                for param_name in sig.parameters:
                    if any(geo in param_name.lower() for geo in ["lat", "lon", "region", "location", "geo"]):
                        geo_params.append(param_name)
        except:
            pass
    
    result["geo_inputs_used"] = list(set(geo_params))
    
    # Analyze cache key construction
    # Look for cache_key, cache_file, or similar patterns
    cache_patterns = [
        r"cache_key\s*[=:]\s*[f'\"]([^'\"]+)",
        r"cache_file\s*[=:]\s*[f'\"]([^'\"]+)",
        r"\.cache[^=]*=\s*[f'\"]([^'\"]+)",
    ]
    
    cache_key_fields = []
    for pattern in cache_patterns:
        matches = re.findall(pattern, source_code)
        for match in matches:
            # Check if match contains region/lat/lon
            if any(geo in match for geo in ["region", "lat", "lon", "location"]):
                # Extract variable names
                var_matches = re.findall(r"\{([^}]+)\}", match)
                cache_key_fields.extend(var_matches)
    
    result["cache_key_fields"] = list(set(cache_key_fields))
    
    # Classification heuristics
    # GLOBAL: No geo inputs, or explicitly global (market indices, national aggregates)
    # NATIONAL: US-wide data (TSA, national economic indicators)
    # REGIONAL: Uses lat/lon or region_name/region_id
    # POTENTIALLY_GLOBAL: Has geo inputs but may fallback to global
    
    if not result["geo_inputs_used"]:
        if any(keyword in source_id.lower() for keyword in ["market", "fred", "economic", "national"]):
            result["class"] = "GLOBAL"
            result["expected_variance"] = False
        else:
            result["class"] = "POTENTIALLY_GLOBAL"
            result["expected_variance"] = "conditional"
    elif any(keyword in source_id.lower() for keyword in ["mobility", "tsa"]):
        result["class"] = "NATIONAL"
        result["expected_variance"] = False
    elif result["geo_inputs_used"]:
        if result["cache_key_fields"]:
            result["class"] = "REGIONAL"
            result["expected_variance"] = True
        else:
            result["class"] = "POTENTIALLY_GLOBAL"
            result["expected_variance"] = "conditional"
            result["notes"].append("Has geo inputs but cache key may not include them")
    
    # Check for fallback behavior
    if "fallback" in source_code.lower() or "default" in source_code.lower():
        result["failure_mode"] = "fallback_to_global"
        result["notes"].append("Code contains fallback logic - may return global data on error")
    
    return result


def audit_all_sources() -> List[Dict[str, Any]]:
    """Audit all registered sources."""
    try:
        from app.services.ingestion.source_registry import get_all_sources, _get_fetcher_classes
        
        sources = get_all_sources()
        fetcher_classes = _get_fetcher_classes()
        
        results = []
        
        for source_id, source_def in sources.items():
            # Try to get fetcher class
            fetcher_class = None
            if source_def.fetcher_class:
                fetcher_class = source_def.fetcher_class
            else:
                # Try to find in fetcher_classes
                class_name = source_id.replace("_", "").title() + "Fetcher"
                for name, cls in fetcher_classes.items():
                    if source_id in name.lower() or name.lower() in source_id:
                        fetcher_class = cls
                        break
            
            if fetcher_class:
                audit = classify_source(source_id, fetcher_class)
                audit["display_name"] = source_def.display_name
                audit["category"] = source_def.category
                results.append(audit)
            else:
                # Manual classification based on source_id and description
                results.append({
                    "source_id": source_id,
                    "display_name": source_def.display_name,
                    "category": source_def.category,
                    "class": "UNKNOWN",
                    "geo_inputs_used": [],
                    "cache_key_fields": [],
                    "expected_variance": None,
                    "failure_mode": "unknown",
                    "notes": ["Could not locate fetcher class for analysis"]
                })
        
        return results
    except Exception as e:
        print(f"Error auditing sources: {e}", file=sys.stderr)
        return []


def main():
    """Main execution."""
    import sys
    proof_dir = Path(PROOF_DIR)
    proof_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("SOURCE REGIONALITY AUDIT")
    print("=" * 80)
    
    results = audit_all_sources()
    
    # Save manifest
    manifest = {
        "sources": results,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "classification_guide": {
            "GLOBAL": "Same everywhere by design (e.g., market indices)",
            "NATIONAL": "Same for all US states (e.g., TSA, national aggregates)",
            "REGIONAL": "Must vary by state/city (e.g., weather, air quality)",
            "POTENTIALLY_GLOBAL": "May be global depending on fallback path"
        }
    }
    
    manifest_path = proof_dir / "source_regionality_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nSaved manifest: {manifest_path}")
    print(f"\nAudited {len(results)} sources")
    
    # Print summary
    print("\n" + "=" * 80)
    print("CLASSIFICATION SUMMARY")
    print("=" * 80)
    
    by_class = {}
    for r in results:
        cls = r["class"]
        by_class.setdefault(cls, []).append(r["source_id"])
    
    for cls, source_ids in sorted(by_class.items()):
        print(f"\n{cls}: {len(source_ids)} sources")
        for sid in source_ids:
            print(f"  - {sid}")
    
    # Flag potential issues
    print("\n" + "=" * 80)
    print("POTENTIAL ISSUES")
    print("=" * 80)
    
    issues = []
    for r in results:
        if r["class"] == "REGIONAL" and not r["cache_key_fields"]:
            issues.append(f"{r['source_id']}: REGIONAL but cache key may not include geo inputs")
        if r["class"] == "REGIONAL" and not r["geo_inputs_used"]:
            issues.append(f"{r['source_id']}: REGIONAL but no geo inputs detected")
        if r["failure_mode"] == "fallback_to_global" and r["class"] == "REGIONAL":
            issues.append(f"{r['source_id']}: REGIONAL with fallback - may cause 'identical states'")
    
    if issues:
        for issue in issues:
            print(f"  [WARN] {issue}")
    else:
        print("  [OK] No obvious regionality issues detected")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys
    main()
