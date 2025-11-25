#!/usr/bin/env python3
# SPDX-License-Identifier: MIT-0
"""
Exploratory script to run a live forecast using configured public data sources.

This script is for manual/exploratory testing and should not be called from CI.
It requires environment variables to be set for optional data sources.

Usage:
    # From repo root
    python scripts/run_live_forecast_demo.py

    # With optional sources configured
    export MOBILITY_API_ENDPOINT="https://api.example.com/mobility"
    export MOBILITY_API_KEY="your-key"
    python scripts/run_live_forecast_demo.py

    # Inside Docker
    docker compose run backend python scripts/run_live_forecast_demo.py
"""
import os
import sys
from pathlib import Path

# Add repo root to Python path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from app.core.prediction import BehavioralForecaster  # noqa: E402


def check_optional_sources():
    """Check which optional data sources are configured."""
    sources = {
        "mobility": bool(
            os.getenv("MOBILITY_API_ENDPOINT") and os.getenv("MOBILITY_API_KEY")
        ),
        "public_health": bool(
            os.getenv("PUBLIC_HEALTH_API_ENDPOINT")
            and os.getenv("PUBLIC_HEALTH_API_KEY")
        ),
        "search_trends": bool(
            os.getenv("SEARCH_TRENDS_API_ENDPOINT")
            and os.getenv("SEARCH_TRENDS_API_KEY")
        ),
    }
    return sources


def main():
    """Run a forecast demo and print results."""
    print("=" * 60)
    print("Behavior Convergence Forecast Demo")
    print("=" * 60)
    print()

    # Check optional sources
    optional_sources = check_optional_sources()
    print("Data Source Configuration:")
    print("  Market Sentiment (yfinance): Available")
    print("  Weather (Open-Meteo): Available")
    print(
        f"  Mobility: {'Configured' if optional_sources['mobility'] else 'Not configured'}"
    )
    print(
        f"  Public Health: {'Configured' if optional_sources['public_health'] else 'Not configured'}"
    )
    print(
        f"  Search Trends: {'Configured' if optional_sources['search_trends'] else 'Not configured'}"
    )
    print()

    if not optional_sources["mobility"] and not optional_sources["public_health"]:
        print("Note: Optional data sources (mobility, public health, search trends)")
        print("are not configured. Forecast will use market + weather data only.")
        print("To enable optional sources, set environment variables:")
        print("  MOBILITY_API_ENDPOINT, MOBILITY_API_KEY")
        print("  PUBLIC_HEALTH_API_ENDPOINT, PUBLIC_HEALTH_API_KEY")
        print("  SEARCH_TRENDS_API_ENDPOINT, SEARCH_TRENDS_API_KEY")
        print()

    # Initialize forecaster
    print("Initializing BehavioralForecaster...")
    forecaster = BehavioralForecaster()
    print("Forecaster initialized successfully.")
    print()

    # Run forecast for New York City
    print("Generating forecast for New York City...")
    print("  Latitude: 40.7128")
    print("  Longitude: -74.0060")
    print("  Days back: 30")
    print("  Forecast horizon: 7 days")
    print()

    try:
        result = forecaster.forecast(
            latitude=40.7128,
            longitude=-74.0060,
            region_name="New York City",
            days_back=30,
            forecast_horizon=7,
        )

        print("=" * 60)
        print("Forecast Results")
        print("=" * 60)
        print()

        # Metadata
        if "metadata" in result:
            meta = result["metadata"]
            print("Metadata:")
            print(f"  Region: {meta.get('region_name', 'N/A')}")
            print(f"  Model: {meta.get('model_type', 'N/A')}")
            print(f"  Forecast Date: {meta.get('forecast_date', 'N/A')}")
            print(f"  Historical Data Points: {meta.get('historical_data_points', 0)}")
            print(f"  Forecast Horizon: {meta.get('forecast_horizon', 0)} days")
            print()

        # Sources
        if "sources" in result:
            print(
                f"Data Sources Used: {', '.join(result['sources']) if result['sources'] else 'None'}"
            )
            print()

        # History
        if "history" in result and result["history"]:
            print(f"Historical Data: {len(result['history'])} points")
            if len(result["history"]) > 0:
                first = result["history"][0]
                last = result["history"][-1]
                print(
                    f"  First: {first.get('timestamp', 'N/A')} - Index: {first.get('behavior_index', 'N/A'):.3f}"
                )
                print(
                    f"  Last: {last.get('timestamp', 'N/A')} - Index: {last.get('behavior_index', 'N/A'):.3f}"
                )
            print()
        else:
            print("Historical Data: None available")
            print()

        # Forecast
        if "forecast" in result and result["forecast"]:
            print(f"Forecast: {len(result['forecast'])} days ahead")
            for i, fc in enumerate(result["forecast"][:5], 1):
                print(
                    f"  Day {i} ({fc.get('timestamp', 'N/A')}): "
                    f"Prediction={fc.get('prediction', 0):.3f}, "
                    f"Range=[{fc.get('lower_bound', 0):.3f}, {fc.get('upper_bound', 0):.3f}]"
                )
            if len(result["forecast"]) > 5:
                print(f"  ... and {len(result['forecast']) - 5} more days")
            print()
        else:
            print("Forecast: None generated (insufficient data)")
            print()

        print("=" * 60)
        print("Demo completed successfully.")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"Error generating forecast: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
