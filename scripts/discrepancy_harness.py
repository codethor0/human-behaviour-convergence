#!/usr/bin/env python3
"""
Discrepancy Harness: Compute deterministic hashes of forecasts to detect region collapse.

This script:
1. Loads regions from API
2. Generates forecasts for 20+ diverse regions
3. Computes stable hashes of history, forecast, and subindices
4. Outputs variance matrix CSV
5. Flags P0 if >=80% regions share identical hashes
"""
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8100")
PROOF_DIR = os.getenv("PROOF_DIR", "/tmp/hbc_discrepancy_proof")

# Target regions: 12 US states + DC + 6 global cities
TARGET_STATES = [
    "us_mn", "us_ca", "us_ny", "us_tx", "us_fl", "us_wa",
    "us_il", "us_az", "us_co", "us_ga", "us_ma", "us_la"
]
TARGET_DC = ["us_dc"]
TARGET_CITIES = [
    "city_nyc", "city_london", "city_tokyo", "city_paris", "city_berlin", "city_sydney"
]
ALL_TARGETS = TARGET_STATES + TARGET_DC + TARGET_CITIES


def canonical_json(obj: Any) -> str:
    """Convert object to canonical JSON string for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def compute_hash(data: Any) -> str:
    """Compute SHA256 hash of canonical JSON representation."""
    json_str = canonical_json(data)
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()[:16]


def fetch_regions() -> List[Dict[str, Any]]:
    """Fetch regions catalog from API."""
    url = f"{BACKEND_URL}/api/forecasting/regions"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def generate_forecast(region_id: str, region_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Generate forecast for a region.
    
    Returns:
        Forecast response dict or None on error
    """
    # Try region_id first, fallback to region_name + lat/lon
    payload = {
        "region_id": region_id,
        "days_back": 30,
        "forecast_horizon": 7,
    }
    
    # Add region_name if available (API may require it)
    if "name" in region_data:
        payload["region_name"] = region_data["name"]
    
    # Add lat/lon if available
    if "latitude" in region_data and region_data["latitude"]:
        payload["latitude"] = region_data["latitude"]
    if "longitude" in region_data and region_data["longitude"]:
        payload["longitude"] = region_data["longitude"]
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/forecast",
            json=payload,
            timeout=120,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ERROR for {region_id}: {e}", file=sys.stderr)
        return None


def extract_subindices(forecast: Dict[str, Any]) -> Dict[str, Any]:
    """Extract all sub-index values from forecast response."""
    subindices = {}
    
    # Check top-level sub_indices (if present)
    if "sub_indices" in forecast:
        subindices["top_level"] = forecast["sub_indices"]
    
    # Extract from history items
    history = forecast.get("history", [])
    if history:
        # Get sub_indices from first history item (most recent)
        first_item = history[0]
        if "sub_indices" in first_item:
            subindices["history_first"] = first_item["sub_indices"]
        
        # Aggregate all sub_indices from history
        all_history_subindices = []
        for item in history:
            if "sub_indices" in item:
                all_history_subindices.append(item["sub_indices"])
        if all_history_subindices:
            subindices["history_all"] = all_history_subindices
    
    return subindices


def analyze_forecast(region_id: str, forecast: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze forecast and extract key metrics."""
    history = forecast.get("history", [])
    forecast_series = forecast.get("forecast", [])
    metadata = forecast.get("metadata", {})
    
    # Extract behavior_index from metadata or compute from history
    behavior_index = metadata.get("behavior_index")
    if behavior_index is None and history:
        # Try to extract from last history item
        last_item = history[-1]
        behavior_index = last_item.get("behavior_index")
    
    # Extract parent subindices
    parent_subindices = {}
    if history:
        last_item = history[-1]
        if "sub_indices" in last_item:
            for parent, value in last_item["sub_indices"].items():
                if isinstance(value, (int, float)):
                    parent_subindices[parent] = value
    
    # Extract child subindices (nested)
    child_subindices = {}
    if history:
        last_item = history[-1]
        if "sub_indices" in last_item:
            for parent, children in last_item["sub_indices"].items():
                if isinstance(children, dict):
                    for child, value in children.items():
                        if isinstance(value, (int, float)):
                            child_subindices[f"{parent}.{child}"] = value
    
    # Compute hashes
    history_hash = compute_hash(history)
    forecast_hash = compute_hash(forecast_series)
    subindices_hash = compute_hash(extract_subindices(forecast))
    
    return {
        "region_id": region_id,
        "history_len": len(history),
        "forecast_len": len(forecast_series),
        "behavior_index": behavior_index,
        "history_hash": history_hash,
        "forecast_hash": forecast_hash,
        "subindex_hash": subindices_hash,
        "parent_subindices": parent_subindices,
        "child_subindices": child_subindices,
    }


def main():
    """Main execution."""
    proof_dir = Path(PROOF_DIR)
    proof_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("DISCREPANCY HARNESS: Forecast Variance Analysis")
    print("=" * 80)
    print(f"Backend: {BACKEND_URL}")
    print(f"Proof Dir: {proof_dir}")
    print()
    
    # Step 1: Fetch regions catalog
    print("[1] Fetching regions catalog...")
    regions_catalog = fetch_regions()
    regions_dict = {r["id"]: r for r in regions_catalog}
    
    # Save catalog
    with open(proof_dir / "regions.json", "w") as f:
        json.dump(regions_catalog, f, indent=2)
    print(f"  Loaded {len(regions_catalog)} regions")
    
    # Step 2: Filter to target regions
    print(f"\n[2] Filtering to {len(ALL_TARGETS)} target regions...")
    available_targets = []
    missing_targets = []
    
    for target_id in ALL_TARGETS:
        if target_id in regions_dict:
            available_targets.append(target_id)
        else:
            missing_targets.append(target_id)
    
    print(f"  Available: {len(available_targets)}")
    if missing_targets:
        print(f"  Missing: {missing_targets}")
    
    if len(available_targets) < 10:
        print(f"ERROR: Only {len(available_targets)} target regions available (need >=10)")
        sys.exit(1)
    
    # Step 3: Generate forecasts
    print(f"\n[3] Generating forecasts for {len(available_targets)} regions...")
    results = []
    
    for i, region_id in enumerate(available_targets, 1):
        region_data = regions_dict[region_id]
        print(f"  [{i}/{len(available_targets)}] {region_id}...", end=" ", flush=True)
        
        forecast = generate_forecast(region_id, region_data)
        if forecast is None:
            print("FAILED")
            continue
        
        # Save raw forecast
        with open(proof_dir / f"forecast_{region_id}.json", "w") as f:
            json.dump(forecast, f, indent=2)
        
        # Analyze
        analysis = analyze_forecast(region_id, forecast)
        results.append(analysis)
        bi = analysis["behavior_index"]
        bi_str = f"{bi:.4f}" if bi is not None else "N/A"
        print(f"OK (bi={bi_str})")
    
    print(f"\n  Generated {len(results)} forecasts")
    
    # Step 4: Compute variance matrix
    print("\n[4] Computing variance matrix...")
    
    # Build CSV rows
    csv_rows = []
    for r in results:
        row = {
            "region_id": r["region_id"],
            "history_len": r["history_len"],
            "forecast_len": r["forecast_len"],
            "behavior_index": r["behavior_index"],
            "history_hash": r["history_hash"],
            "forecast_hash": r["forecast_hash"],
            "subindex_hash": r["subindex_hash"],
        }
        # Add parent subindices
        for parent, value in r["parent_subindices"].items():
            row[f"parent_{parent}"] = value
        # Add key child subindices (sample)
        for child_key, value in list(r["child_subindices"].items())[:5]:
            row[f"child_{child_key}"] = value
        csv_rows.append(row)
    
    df = pd.DataFrame(csv_rows)
    csv_path = proof_dir / "forecast_variance_matrix.csv"
    df.to_csv(csv_path, index=False)
    print(f"  Saved: {csv_path}")
    
    # Step 5: Variance analysis
    print("\n[5] Variance Analysis:")
    print("-" * 80)
    
    # Count unique hashes
    history_hashes = df["history_hash"].unique()
    forecast_hashes = df["forecast_hash"].unique()
    subindex_hashes = df["subindex_hash"].unique()
    
    print(f"  History hashes: {len(history_hashes)} unique / {len(df)} total")
    print(f"  Forecast hashes: {len(forecast_hashes)} unique / {len(df)} total")
    print(f"  Subindex hashes: {len(subindex_hashes)} unique / {len(df)} total")
    
    # Check for collapse
    total_regions = len(df)
    history_collapse_pct = (total_regions - len(history_hashes)) / total_regions * 100
    forecast_collapse_pct = (total_regions - len(forecast_hashes)) / total_regions * 100
    subindex_collapse_pct = (total_regions - len(subindex_hashes)) / total_regions * 100
    
    print(f"\n  Collapse percentages:")
    print(f"    History: {history_collapse_pct:.1f}% (threshold: 80%)")
    print(f"    Forecast: {forecast_collapse_pct:.1f}% (threshold: 80%)")
    print(f"    Subindex: {subindex_collapse_pct:.1f}% (threshold: 80%)")
    
    # P0 decision
    max_collapse = max(history_collapse_pct, forecast_collapse_pct, subindex_collapse_pct)
    if max_collapse >= 80:
        print(f"\n  [P0] STATE COLLAPSE DETECTED: {max_collapse:.1f}% regions share identical hashes")
        print("  → Proceeding to Phase 7: Root Cause Investigation")
        with open(proof_dir / "p0_collapse_detected.txt", "w") as f:
            f.write(f"Max collapse: {max_collapse:.1f}%\n")
            f.write(f"History collapse: {history_collapse_pct:.1f}%\n")
            f.write(f"Forecast collapse: {forecast_collapse_pct:.1f}%\n")
            f.write(f"Subindex collapse: {subindex_collapse_pct:.1f}%\n")
        sys.exit(1)
    else:
        print(f"\n  [OK] Variance detected: {100 - max_collapse:.1f}% regions have unique hashes")
        print("  → Proceeding to Phase 5: Metrics Truth Layer")
    
    # Behavior index variance
    if "behavior_index" in df.columns:
        bi_values = df["behavior_index"].dropna()
        if len(bi_values) > 0:
            bi_unique = bi_values.nunique()
            bi_variance = bi_values.std()
            print(f"\n  Behavior Index:")
            print(f"    Unique values: {bi_unique} / {len(bi_values)}")
            print(f"    Std deviation: {bi_variance:.6f}")
            print(f"    Range: [{bi_values.min():.6f}, {bi_values.max():.6f}]")
    
    # Sample hash distribution
    print(f"\n  Sample hash distribution (first 5 regions):")
    for _, row in df.head(5).iterrows():
        print(f"    {row['region_id']}: H={row['history_hash'][:8]}, F={row['forecast_hash'][:8]}, S={row['subindex_hash'][:8]}")
    
    print("\n" + "=" * 80)
    print("DISCREPANCY HARNESS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
