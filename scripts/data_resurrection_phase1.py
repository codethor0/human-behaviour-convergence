#!/usr/bin/env python3
"""Phase 1: Force Data Generation for Multiple Regions"""
import json
import os
import sys
import requests
import time

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8100")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

REGIONS = [
    "New York City (US)",
    "Illinois",
    "Arizona",
    "London",
    "Tokyo",
]


def generate_forecast(region: str, days_back: int = 30, forecast_horizon: int = 7):
    """Generate forecast for a region."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/forecast",
            json={
                "region": region,
                "days_back": days_back,
                "forecast_horizon": forecast_horizon,
            },
            timeout=60,
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  ERROR: HTTP {response.status_code} for {region}")
            return None
    except Exception as e:
        print(f"  ERROR: {e} for {region}")
        return None


def check_metrics_for_region(region: str):
    """Check if metrics exist for a region."""
    try:
        # Check behavior_index
        query = f'behavior_index{{region="{region}"}}'
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", {}).get("result", [])
            return len(results) > 0
        return False
    except:
        return False


def check_region_count():
    """Check how many regions have data."""
    try:
        query = "count(count by (region) (behavior_index))"
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", {}).get("result", [])
            if results:
                return int(float(results[0]["value"][1]))
        return 0
    except:
        return 0


def main():
    resurrection_dir = os.getenv("RESURRECTION_DIR", "/tmp/hbc_resurrection_default")
    os.makedirs(f"{resurrection_dir}/proofs", exist_ok=True)

    print("=== PHASE 1: FORCE DATA GENERATION ===\n")

    # Step 1.1: Generate for NYC (default)
    print("Step 1.1: Generating forecast for NYC (default region)...")
    nyc_result = generate_forecast("New York City (US)")
    if nyc_result:
        print("  [OK] NYC forecast generated")
        with open(f"{resurrection_dir}/proofs/nyc_forecast.json", "w") as f:
            json.dump(nyc_result, f, indent=2)
    else:
        print("  [FAIL] NYC forecast generation failed")
        return 1

    # Wait for metrics to be scraped
    print("\nWaiting for Prometheus to scrape metrics (10s)...")
    time.sleep(10)

    # Verify NYC metrics
    print("Verifying NYC metrics...")
    if check_metrics_for_region("New York City (US)"):
        print("  [OK] NYC metrics found in Prometheus")
    else:
        print("  [WARN]  NYC metrics not yet in Prometheus (may need more time)")

    # Step 1.2: Generate for additional regions
    print("\nStep 1.2: Generating forecasts for additional regions...")
    results = {}
    for region in REGIONS[1:]:  # Skip NYC, already done
        print(f"  Generating for {region}...", end=" ", flush=True)
        result = generate_forecast(region)
        if result:
            print("[OK]")
            results[region] = result
            with open(
                f"{resurrection_dir}/proofs/{region.replace(' ', '_')}_forecast.json",
                "w",
            ) as f:
                json.dump(result, f, indent=2)
        else:
            print("[FAIL]")

    # Wait for all metrics to be scraped
    print("\nWaiting for Prometheus to scrape all metrics (15s)...")
    time.sleep(15)

    # Verify multi-region coverage
    print("\nVerifying multi-region coverage...")
    region_count = check_region_count()
    print(f"  Regions with data: {region_count}")

    if region_count < 3:
        print(f"  [WARN]  WARNING: Only {region_count} regions have data (expected ≥3)")
        print("  Metrics may need more time to propagate")
    else:
        print(f"  [OK] {region_count} regions have data")

    # Verify each region individually
    print("\nVerifying individual regions...")
    region_status = {}
    for region in REGIONS:
        has_data = check_metrics_for_region(region)
        status = "[OK]" if has_data else "[WARN]"
        region_status[region] = has_data
        print(f"  {status} {region}: {'Has data' if has_data else 'No data yet'}")

    # Summary
    regions_with_data = sum(1 for v in region_status.values() if v)

    print("\n=== SUMMARY ===")
    print(f"Regions attempted: {len(REGIONS)}")
    print(f"Regions with data: {regions_with_data}")
    print(f"Forecasts generated: {len(results) + 1}")  # +1 for NYC

    if regions_with_data >= 3:
        print("\n[OK] PHASE 1 PASSED - Sufficient region coverage")
        return 0
    else:
        print("\n[WARN]  PHASE 1 PARTIAL - Some regions may need more time")
        print("   Proceeding to Phase 2 to check individual panels...")
        return 0  # Continue anyway to check what we have


if __name__ == "__main__":
    sys.exit(main())
