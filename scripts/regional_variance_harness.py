#!/usr/bin/env python3
"""
Regional variance harness: generates forecasts for multiple regions
and computes variance metrics to prove regional differentiation.
"""
import json
import hashlib
import sys
import csv
from pathlib import Path
from typing import Dict, List, Any
import requests

API_BASE = "http://localhost:8100"

# Test regions: mix of US states and global cities
TEST_REGIONS = [
    {"name": "Illinois", "lat": 40.3495, "lon": -88.9861},
    {"name": "Arizona", "lat": 34.2744, "lon": -111.6602},
    {"name": "Florida", "lat": 27.7663, "lon": -81.6868},
    {"name": "Washington", "lat": 47.0379, "lon": -120.8956},
    {"name": "California", "lat": 36.7783, "lon": -119.4179},
    {"name": "New York", "lat": 40.7128, "lon": -74.0060},
    {"name": "Texas", "lat": 31.9686, "lon": -99.9018},
    {"name": "Minnesota", "lat": 46.7296, "lon": -94.6859},
    {"name": "Colorado", "lat": 39.0598, "lon": -105.3111},
    {"name": "London", "lat": 51.5074, "lon": -0.1278},
]


def hash_value(obj: Any) -> str:
    """Compute SHA256 hash of JSON-serialized object."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def generate_forecast(region: Dict[str, Any]) -> Dict[str, Any]:
    """Generate forecast for a region."""
    url = f"{API_BASE}/api/forecast"
    payload = {
        "latitude": region["lat"],
        "longitude": region["lon"],
        "region_name": region["name"],
        "days_back": 30,
        "forecast_horizon": 7,
    }
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def compute_variance_metrics(forecasts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute variance metrics across regions."""
    results = {
        "total_regions": len(forecasts),
        "unique_hashes": {},
        "variance_matrix": [],
    }

    # Hash key fields for each region
    for forecast in forecasts:
        region_name = forecast.get("region_name", "unknown")
        hashes = {
            "history": hash_value(forecast.get("history", [])),
            "forecast": hash_value(forecast.get("forecast", [])),
            "behavior_index": hash_value(forecast.get("behavior_index", 0)),
            "sub_indices": hash_value(forecast.get("sub_indices", {})),
        }

        # Extract parent sub-indices
        sub_indices = forecast.get("sub_indices", {})
        for parent in [
            "economic_stress",
            "environmental_stress",
            "political_stress",
            "mobility_activity",
        ]:
            if parent in sub_indices:
                hashes[f"parent_{parent}"] = hash_value(sub_indices[parent])

        results["unique_hashes"][region_name] = hashes

    # Count unique hashes per field
    for field in [
        "history",
        "forecast",
        "behavior_index",
        "sub_indices",
        "parent_economic_stress",
        "parent_environmental_stress",
        "parent_political_stress",
        "parent_mobility_activity",
    ]:
        unique_values = set()
        for region_hashes in results["unique_hashes"].values():
            if field in region_hashes:
                unique_values.add(region_hashes[field])
        results["variance_matrix"].append(
            {
                "field": field,
                "unique_count": len(unique_values),
                "total_regions": len(forecasts),
                "variance_ratio": (
                    len(unique_values) / len(forecasts) if forecasts else 0
                ),
            }
        )

    return results


def main():
    """Main execution."""
    output_dir = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/hbc_variance_harness")
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating forecasts for 10 regions...")
    forecasts = []
    forecast_files = []

    for region in TEST_REGIONS:
        try:
            print(f"  Generating for {region['name']}...")
            forecast = generate_forecast(region)
            forecasts.append(forecast)

            # Save individual forecast
            forecast_file = (
                output_dir / f"forecast_{region['name'].lower().replace(' ', '_')}.json"
            )
            with open(forecast_file, "w") as f:
                json.dump(forecast, f, indent=2)
            forecast_files.append(forecast_file)
        except Exception as e:
            print(f"  ERROR for {region['name']}: {e}")
            continue

    if len(forecasts) < 2:
        print("ERROR: Need at least 2 successful forecasts")
        sys.exit(1)

    print(f"\nGenerated {len(forecasts)} forecasts")

    # Compute variance metrics
    print("Computing variance metrics...")
    variance_results = compute_variance_metrics(forecasts)

    # Save results
    results_file = output_dir / "variance_results.json"
    with open(results_file, "w") as f:
        json.dump(variance_results, f, indent=2)

    # Save CSV report
    csv_file = output_dir / "variance_report.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Field", "Unique Count", "Total Regions", "Variance Ratio"])
        for row in variance_results["variance_matrix"]:
            writer.writerow(
                [
                    row["field"],
                    row["unique_count"],
                    row["total_regions"],
                    f"{row['variance_ratio']:.2%}",
                ]
            )

    # Print summary
    print("\n=== Variance Summary ===")
    print(f"Total regions: {variance_results['total_regions']}")
    print("\nVariance by field:")
    for row in variance_results["variance_matrix"]:
        status = "" if row["unique_count"] >= 2 else ""
        print(
            f"  {status} {row['field']}: {row['unique_count']}/{row['total_regions']} unique ({row['variance_ratio']:.2%})"
        )

    # Check for P0 issues (too many identical hashes)
    p0_fields = [
        r
        for r in variance_results["variance_matrix"]
        if r["unique_count"] < 2 and r["field"] not in ["parent_mobility_activity"]
    ]
    if p0_fields:
        print(f"\nP0: {len(p0_fields)} fields show no variance across regions")
        for field in p0_fields:
            print(f"  - {field['field']}")
        sys.exit(1)

    print("\n Variance check passed")
    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
