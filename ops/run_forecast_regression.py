#!/usr/bin/env python3
# SPDX-License-Identifier: PROPRIETARY
"""Forecast regression test suite.

Runs forecasts for key regions and validates integrity expectations.
Inspired by DevOps-Bash-tools check_* pattern for CI blocking.

Usage:
    python3 ops/run_forecast_regression.py [--verbose] [--output-dir DIR] [--markdown]

Exit codes:
    0: All assertions pass
    1: One or more assertions fail
    2: Configuration or setup error
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.core.prediction import BehavioralForecaster

# Test regions: (name, lat, lon)
TEST_REGIONS = [
    ("Minnesota", 46.7296, -94.6859),
    ("New York", 40.7128, -74.0060),
    ("California", 34.0522, -118.2437),
    ("Texas", 31.9686, -99.9018),
    ("District of Columbia", 38.9072, -77.0369),
]

# Regression expectations
# These are encoded assertions that fail loudly when calibration drifts
EXPECTATIONS = {
    "minnesota_high_shock": {
        "description": "Minnesota with high shock events (≥40) should show elevated stress",
        "condition": lambda r: r.get("shock_events", 0) >= 40,
        "assertions": [
            lambda r: (r.get("behavior_index", 0) > 0.50,
                      f"behavior_index {r.get('behavior_index', 0):.3f} should be > 0.50 with {r.get('shock_events', 0)} shock events"),
            lambda r: (r.get("political_stress", 0) >= 0.40,
                      f"political_stress {r.get('political_stress', 0):.3f} should be >= 0.40 with high shock events"),
            lambda r: (r.get("social_cohesion_stress", 0) >= 0.40,
                      f"social_cohesion_stress {r.get('social_cohesion_stress', 0):.3f} should be >= 0.40 with high shock events"),
        ],
    },
    "high_shock_general": {
        "description": "Any region with high shock events (≥40) should have behavior_index > 0.50",
        "condition": lambda r: r.get("shock_events", 0) >= 40 and "error" not in r,
        "assertions": [
            lambda r: (r.get("behavior_index", 0) > 0.50,
                      f"behavior_index {r.get('behavior_index', 0):.3f} should be > 0.50 with {r.get('shock_events', 0)} shock events"),
        ],
    },
    "integrity_flags": {
        "description": "Integrity metadata should be present and valid",
        "condition": lambda r: "error" not in r,  # Skip if forecast failed
        "assertions": [
            lambda r: ("metadata" in r, "metadata should be present"),
            lambda r: ("integrity" in r.get("metadata", {}), "metadata.integrity should be present"),
            lambda r: (isinstance(r.get("metadata", {}).get("integrity", {}).get("shock_multiplier_applied"), bool),
                      "shock_multiplier_applied should be a boolean"),
        ],
    },
    "numeric_bounds": {
        "description": "All indices must be in [0.0, 1.0]",
        "condition": lambda r: "error" not in r,
        "assertions": [
            lambda r: (0.0 <= r.get("behavior_index", 0) <= 1.0,
                      f"behavior_index {r.get('behavior_index', 0):.3f} must be in [0.0, 1.0]"),
            lambda r: (0.0 <= r.get("political_stress", 0) <= 1.0,
                      f"political_stress {r.get('political_stress', 0):.3f} must be in [0.0, 1.0]"),
            lambda r: (0.0 <= r.get("social_cohesion_stress", 0) <= 1.0,
                      f"social_cohesion_stress {r.get('social_cohesion_stress', 0):.3f} must be in [0.0, 1.0]"),
        ],
    },
}


def run_forecast(forecaster: BehavioralForecaster, region_name: str, lat: float, lon: float) -> Dict:
    """Run forecast for a region."""
    try:
        result = forecaster.forecast(
            latitude=lat,
            longitude=lon,
            region_name=region_name,
            days_back=30,
            forecast_horizon=7,
        )

        # Extract key metrics
        history = result.get("history", [])
        if not history:
            return {"error": "Empty history"}

        latest = history[-1]
        metadata = result.get("metadata", {})
        integrity = metadata.get("integrity", {})
        shock_events = result.get("shock_events", [])

        return {
            "region_name": region_name,
            "behavior_index": latest.get("behavior_index", 0.0),
            "political_stress": latest.get("political_stress", 0.0),
            "social_cohesion_stress": latest.get("social_cohesion_stress", 0.0),
            "crime_stress": latest.get("crime_stress", 0.0),
            "economic_stress": latest.get("economic_stress", 0.0),
            "shock_events": len(shock_events) if isinstance(shock_events, list) else 0,
            "risk_tier": result.get("risk_tier", {}).get("tier", "unknown"),
            "risk_score": result.get("risk_tier", {}).get("risk_score", 0.0),
            "metadata": metadata,
            "integrity": integrity,
        }
    except Exception as e:
        return {"error": str(e), "region_name": region_name}


def check_expectations(result: Dict, expectations: Dict) -> List[Dict]:
    """Check regression expectations against forecast result.

    Returns list of failure dicts with details.
    """
    failures = []

    for exp_name, exp_config in expectations.items():
        condition = exp_config["condition"]
        if not condition(result):
            continue  # Condition not met, skip this expectation

        for assertion in exp_config["assertions"]:
            try:
                assertion_result = assertion(result)
                # Handle tuple (bool, message) or just bool
                if isinstance(assertion_result, tuple):
                    passed, message = assertion_result
                else:
                    passed = assertion_result
                    message = "Assertion failed"

                if not passed:
                    failures.append({
                        "expectation": exp_name,
                        "description": exp_config["description"],
                        "region": result.get("region_name", "unknown"),
                        "message": message,
                        "assertion_failed": True,
                    })
            except Exception as e:
                failures.append({
                    "expectation": exp_name,
                    "description": exp_config["description"],
                    "region": result.get("region_name", "unknown"),
                    "assertion_error": str(e),
                })

    return failures


def generate_markdown_report(report: Dict, output_file: Path) -> None:
    """Generate human-readable markdown report."""
    with open(output_file, "w") as f:
        f.write("# Forecast Regression Test Report\n\n")
        f.write(f"**Generated:** {report['timestamp']}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Regions tested: {report['regions_tested']}\n")
        f.write(f"- Total failures: {report['summary']['total_failures']}\n")
        f.write(f"- Regions with errors: {report['summary']['regions_with_errors']}\n\n")

        if report['summary']['total_failures'] == 0:
            f.write("[OK] **All assertions passed**\n\n")
        else:
            f.write("[FAIL] **Assertions failed**\n\n")

        f.write("## Results by Region\n\n")
        for result in report['results']:
            region = result.get('region_name', 'unknown')
            f.write(f"### {region}\n\n")

            if 'error' in result:
                f.write(f"**Error:** {result['error']}\n\n")
                continue

            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            f.write(f"| behavior_index | {result.get('behavior_index', 0):.3f} |\n")
            f.write(f"| political_stress | {result.get('political_stress', 0):.3f} |\n")
            f.write(f"| social_cohesion_stress | {result.get('social_cohesion_stress', 0):.3f} |\n")
            f.write(f"| crime_stress | {result.get('crime_stress', 0):.3f} |\n")
            f.write(f"| economic_stress | {result.get('economic_stress', 0):.3f} |\n")
            f.write(f"| shock_events | {result.get('shock_events', 0)} |\n")
            f.write(f"| risk_tier | {result.get('risk_tier', 'unknown')} |\n")
            f.write(f"| risk_score | {result.get('risk_score', 0):.3f} |\n")

            integrity = result.get('integrity', {})
            if integrity.get('shock_multiplier_applied'):
                f.write("\n**Shock Multiplier Applied:** [OK]\n")
                f.write(f"- Shock count: {integrity.get('shock_count', 'N/A')}\n")
                f.write(f"- Multiplier: {integrity.get('shock_multiplier_value', 'N/A')}\n")
            else:
                f.write("\n**Shock Multiplier Applied:** [FAIL]\n")

            f.write("\n")

        if report['failures']:
            f.write("## Failures\n\n")
            for failure in report['failures']:
                f.write(f"**{failure.get('region', 'unknown')}** - {failure.get('description', 'Unknown')}\n")
                f.write(f"- Expectation: `{failure.get('expectation', 'unknown')}`\n")
                if 'message' in failure:
                    f.write(f"- Message: {failure['message']}\n")
                elif 'error' in failure:
                    f.write(f"- Error: {failure['error']}\n")
                f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Run forecast regression tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--output-dir", "-o", type=str, default="ops/regression_results",
                       help="Output directory for results")
    parser.add_argument("--markdown", "-m", action="store_true",
                       help="Generate markdown report in addition to JSON")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"regression_{timestamp}.json"
    markdown_file = output_dir / f"regression_{timestamp}.md" if args.markdown else None

    print("Running forecast regression tests...")
    print(f"  Regions: {len(TEST_REGIONS)}")
    print(f"  Expectations: {len(EXPECTATIONS)}")
    print()

    forecaster = BehavioralForecaster()
    all_results = []
    all_failures = []

    for region_name, lat, lon in TEST_REGIONS:
        if args.verbose:
            print(f"  Testing {region_name}...")

        result = run_forecast(forecaster, region_name, lat, lon)
        all_results.append(result)

        if "error" in result:
            print(f"    ERROR: {result['error']}")
            all_failures.append({
                "region": region_name,
                "error": result["error"],
            })
            continue

        # Check expectations
        failures = check_expectations(result, EXPECTATIONS)
        all_failures.extend(failures)

        if args.verbose:
            if "error" in result:
                print(f"    ERROR: {result['error']}")
            else:
                print(f"    behavior_index: {result.get('behavior_index', 0):.3f}")
                print(f"    political_stress: {result.get('political_stress', 0):.3f}")
                print(f"    social_cohesion_stress: {result.get('social_cohesion_stress', 0):.3f}")
                print(f"    shock_events: {result.get('shock_events', 0)}")
                print(f"    risk_tier: {result.get('risk_tier', 'unknown')}")
                integrity = result.get('integrity', {})
                if integrity.get('shock_multiplier_applied'):
                    print(f"    shock_multiplier: {integrity.get('shock_multiplier_value', 'N/A')} (applied)")
                if failures:
                    print(f"    [WARN] FAILURES: {len(failures)}")
                else:
                    print("    [OK] PASSED")

    # Save results
    report = {
        "timestamp": timestamp,
        "regions_tested": len(TEST_REGIONS),
        "results": all_results,
        "failures": all_failures,
        "summary": {
            "total_failures": len(all_failures),
            "regions_with_errors": len([r for r in all_results if "error" in r]),
        },
    }

    with open(results_file, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Generate markdown report if requested
    if markdown_file:
        generate_markdown_report(report, markdown_file)

    # Print summary
    print()
    print("=" * 60)
    print("Regression Test Summary")
    print("=" * 60)
    print(f"Regions tested: {len(TEST_REGIONS)}")
    print(f"Total failures: {len(all_failures)}")
    print(f"Results saved: {results_file}")
    if markdown_file:
        print(f"Markdown report: {markdown_file}")
    print()

    if all_failures:
        print("FAILURES:")
        for failure in all_failures:
            region = failure.get('region', 'unknown')
            desc = failure.get('description', failure.get('error', 'unknown'))
            message = failure.get('message', '')
            print(f"  - {region}: {desc}")
            if message:
                print(f"    {message}")
        print()
        return 1
    else:
        print("[OK] All assertions passed.")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
