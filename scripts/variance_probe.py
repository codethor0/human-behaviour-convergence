#!/usr/bin/env python3
"""
Variance probe - compute per-source variance score across regions.

Hardens variance detection to alert if region-aware sources have near-zero variance.
"""
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


def load_forecasts(forecasts_dir: str) -> Dict[str, Dict]:
    """Load forecast JSONs from directory."""
    forecasts = {}
    for path in Path(forecasts_dir).glob("forecast_*.json"):
        region_id = path.stem.replace("forecast_", "")
        with open(path) as f:
            forecasts[region_id] = json.load(f)
    return forecasts


def compute_variance_score(values: List[float]) -> Dict[str, float]:
    """Compute variance statistics for a list of values."""
    if not values or len(values) < 2:
        return {
            "unique_count": len(set(values)) if values else 0,
            "variance": 0.0,
            "std_dev": 0.0,
            "range": 0.0,
            "mean": statistics.mean(values) if values else 0.0,
        }

    unique_count = len(set(values))
    variance = statistics.variance(values) if len(values) > 1 else 0.0
    std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
    value_range = max(values) - min(values)

    return {
        "unique_count": unique_count,
        "variance": variance,
        "std_dev": std_dev,
        "range": value_range,
        "mean": statistics.mean(values),
        "min": min(values),
        "max": max(values),
    }


def extract_source_values(forecasts: Dict[str, Dict], source_name: str) -> List[float]:
    """Extract values for a specific source/index from forecasts."""
    values = []
    for region_id, forecast in forecasts.items():
        history = forecast.get("history", [])
        if history:
            first = history[0] if isinstance(history, list) else None
            if isinstance(first, dict):
                # Try to extract from sub_indices
                sub_indices = first.get("sub_indices", {})
                value = sub_indices.get(source_name)
                if value is not None:
                    values.append((region_id, value))

    # Return just values (region_id tracked separately if needed)
    return [v for _, v in values]


def classify_source(source_name: str) -> str:
    """Classify source as global, national, or regional."""
    global_sources = [
        "economic_stress",  # VIX/SPY global
        "digital_attention",  # GDELT global tone
    ]
    national_sources = [
        "mobility_activity",  # TSA national
    ]
    regional_sources = [
        "environmental_stress",  # Weather by lat/lon
        "political_stress",  # GDELT with region filter
        "crime_stress",  # Region-specific
        "misinformation_stress",  # Region-specific
        "social_cohesion_stress",  # Region-specific
        "fuel_stress",  # EIA gasoline prices by state (MVP1)
        "drought_stress",  # U.S. Drought Monitor by state (MVP2)
        "heatwave_stress",  # NOAA Storm Events by state (MVP3)
        "flood_risk_stress",  # NOAA Storm Events by state (MVP3)
        "storm_severity_stress",  # NOAA Storm Events by state (MVP3)
    ]
    
    # Sources that may be global or regional depending on configuration
    potentially_global_sources = [
        "public_health_stress",  # May be global (OWID fallback) or regional (if API configured)
    ]

    if source_name in global_sources:
        return "global"
    elif source_name in national_sources:
        return "national"
    elif source_name in regional_sources:
        return "regional"
    elif source_name in potentially_global_sources:
        return "potentially_global"  # May be constant if using global fallback
    else:
        return "unknown"


def main():
    """Main variance probe."""
    import argparse

    parser = argparse.ArgumentParser(description="Variance probe for HBC forecasts")
    parser.add_argument(
        "--forecasts-dir",
        default="/tmp/hbc_discrepancy",
        help="Directory containing forecast JSONs",
    )
    parser.add_argument(
        "--output-csv", default="/tmp/variance_probe_report.csv", help="Output CSV"
    )
    parser.add_argument(
        "--output-report",
        default="/tmp/variance_probe_report.txt",
        help="Human-readable report",
    )
    parser.add_argument(
        "--alert-threshold",
        type=float,
        default=0.01,
        help="Variance threshold for regional sources (default: 0.01)",
    )
    args = parser.parse_args()

    # Load forecasts
    forecasts = load_forecasts(args.forecasts_dir)
    if not forecasts:
        print(f"ERROR: No forecasts found in {args.forecasts_dir}")
        sys.exit(1)

    print(f"Loaded {len(forecasts)} forecasts from {args.forecasts_dir}")

    # Analyze each source/index
    sources = [
        "behavior_index",
        "economic_stress",
        "environmental_stress",
        "mobility_activity",
        "digital_attention",
        "public_health_stress",
        "political_stress",
        "crime_stress",
        "misinformation_stress",
        "social_cohesion_stress",
        "fuel_stress",  # MVP1: EIA fuel prices by state
        "drought_stress",  # MVP2: U.S. Drought Monitor by state
        "heatwave_stress",  # MVP3: NOAA Storm Events by state
        "flood_risk_stress",  # MVP3: NOAA Storm Events by state
        "storm_severity_stress",  # MVP3: NOAA Storm Events by state
    ]

    results = []
    alerts = []

    for source in sources:
        values = extract_source_values(forecasts, source)
        if not values:
            continue

        stats = compute_variance_score(values)
        classification = classify_source(source)

        result = {
            "source": source,
            "classification": classification,
            "region_count": len(values),
            "unique_count": stats["unique_count"],
            "variance": stats["variance"],
            "std_dev": stats["std_dev"],
            "range": stats["range"],
            "mean": stats["mean"],
            "min": stats["min"],
            "max": stats["max"],
        }
        results.append(result)

        # Alert logic
        if classification == "regional":
            if stats["range"] < args.alert_threshold:
                alerts.append(
                    {
                        "source": source,
                        "severity": "HIGH",
                        "message": f"Regional source {source} has near-zero variance "
                        f"(range={stats['range']:.6f}), likely mis-parameterized",
                    }
                )
            elif stats["unique_count"] == 1:
                alerts.append(
                    {
                        "source": source,
                        "severity": "CRITICAL",
                        "message": f"Regional source {source} has zero variance "
                        f"(all regions identical), likely bug",
                    }
                )
        elif classification == "potentially_global":
            # Potentially global sources are allowed to be constant if using fallback
            if stats["unique_count"] == 1:
                result["status"] = "OK (may be constant if using global fallback)"
            else:
                result["status"] = "VARIES (region-specific data available)"
        elif classification == "global" or classification == "national":
            # Global/national sources are allowed to be constant
            if stats["unique_count"] == 1:
                result["status"] = "OK (expected constant)"
            else:
                result["status"] = "VARIES (unexpected but not necessarily wrong)"

    # Write CSV
    with open(args.output_csv, "w") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    # Write human-readable report
    with open(args.output_report, "w") as f:
        f.write("HBC Variance Probe Report\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Forecasts analyzed: {len(forecasts)}\n")
        f.write(f"Sources analyzed: {len(results)}\n\n")

        f.write("Variance Analysis:\n")
        f.write("-" * 80 + "\n")
        for result in results:
            f.write(f"\n{result['source']} ({result['classification']}):\n")
            f.write(f"  Regions: {result['region_count']}\n")
            f.write(f"  Unique values: {result['unique_count']}\n")
            f.write(f"  Range: {result['range']:.6f}\n")
            f.write(f"  Std dev: {result['std_dev']:.6f}\n")
            f.write(f"  Mean: {result['mean']:.6f}\n")
            if "status" in result:
                f.write(f"  Status: {result['status']}\n")

        if alerts:
            f.write("\n\nALERTS:\n")
            f.write("-" * 80 + "\n")
            for alert in alerts:
                f.write(
                    f"\n[{alert['severity']}] {alert['source']}:\n"
                    f"  {alert['message']}\n"
                )
        else:
            f.write("\n\nNo alerts - all sources show expected variance patterns.\n")

    print(f"\nReport written to: {args.output_report}")
    print(f"CSV written to: {args.output_csv}")

    if alerts:
        print(f"\n⚠️  {len(alerts)} alert(s) found:")
        for alert in alerts:
            print(f"  [{alert['severity']}] {alert['source']}: {alert['message']}")
        sys.exit(1)
    else:
        print("\n✅ No alerts - variance patterns are correct")
        sys.exit(0)


if __name__ == "__main__":
    main()
