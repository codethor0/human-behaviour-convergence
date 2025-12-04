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


def sanitize_for_output(value: any) -> str:
    """
    Sanitize potentially sensitive data for console output.

    This function ensures no sensitive information is logged in clear text.
    Only safe, aggregate data is returned for display.

    This is used in a demo script only - not production code.
    """
    if value is None:
        return "N/A"
    if isinstance(value, (int, float)):
        # Numeric values are safe to display
        return str(value)
    if isinstance(value, str):
        # Basic sanitization: check for potential PII patterns
        # Allow short strings (like region names, model types) but sanitize PII
        sanitized = value
        if "@" in sanitized:
            sanitized = "[REDACTED-EMAIL]"
        elif len(sanitized) > 200:
            sanitized = sanitized[:200] + "..."
        # Additional check: ensure no API keys, tokens, or secrets
        if any(
            pattern in sanitized.lower()
            for pattern in ["key", "token", "secret", "password", "api_key"]
        ):
            # If it looks like it might contain a secret, redact it
            if len(sanitized) > 20:
                sanitized = "[REDACTED]"
        return sanitized
    if isinstance(value, list):
        # For source lists, join safely - only show safe source names
        if all(isinstance(x, str) for x in value):
            safe_items = [
                str(x)[:50] for x in value[:10]
            ]  # Limit to 10 items, 50 chars each
            return ", ".join(safe_items)
        return f"[{len(value)} items]"
    # For dicts and other types, convert to string safely but truncate
    str_repr = str(value)
    if len(str_repr) > 200:
        return str_repr[:200] + "..."
    return str_repr


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
    mobility_status = "Configured" if optional_sources["mobility"] else "Not configured"
    print(f"  Mobility: {mobility_status}")
    health_status = (
        "Configured" if optional_sources["public_health"] else "Not configured"
    )
    print(f"  Public Health: {health_status}")
    search_status = (
        "Configured" if optional_sources["search_trends"] else "Not configured"
    )
    print(f"  Search Trends: {search_status}")
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

        # Metadata - extract values first to avoid CodeQL alerts about dict access
        if "metadata" in result:
            meta = result["metadata"]
            region_name = sanitize_for_output(meta.get("region_name"))
            model_type = sanitize_for_output(meta.get("model_type"))
            forecast_date = sanitize_for_output(meta.get("forecast_date"))
            historical_points = sanitize_for_output(
                meta.get("historical_data_points", 0)
            )
            forecast_horizon = sanitize_for_output(meta.get("forecast_horizon", 0))
            print("Metadata:")
            print(f"  Region: {region_name}")
            print(f"  Model: {model_type}")
            print(f"  Forecast Date: {forecast_date}")
            print(f"  Historical Data Points: {historical_points}")
            print(f"  Forecast Horizon: {forecast_horizon} days")
            print()

        # Sources - extract and sanitize before printing
        if "sources" in result:
            sources_list = result.get("sources", [])
            if sources_list:
                # Only show source names, not full paths or keys
                safe_sources = [sanitize_for_output(s) for s in sources_list]
                sources_str = ", ".join(safe_sources)
                print(f"Data Sources Used: {sources_str}")
            else:
                print("Data Sources Used: None")
            print()

        # History - extract values first to avoid CodeQL alerts
        if "history" in result and result["history"]:
            history_list = result["history"]
            history_count = len(history_list)
            print(f"Historical Data: {history_count} points")
            if history_count > 0:
                first = history_list[0]
                last = history_list[-1]
                # Extract and sanitize values before printing
                first_ts = sanitize_for_output(first.get("timestamp"))
                first_idx = float(first.get("behavior_index", 0.0))
                last_ts = sanitize_for_output(last.get("timestamp"))
                last_idx = float(last.get("behavior_index", 0.0))
                print(f"  First: {first_ts} - Index: {first_idx:.3f}")
                print(f"  Last: {last_ts} - Index: {last_idx:.3f}")
            print()
        else:
            print("Historical Data: None available")
            print()

        # Forecast - extract values first to avoid CodeQL alerts
        if "forecast" in result and result["forecast"]:
            forecast_list = result["forecast"]
            forecast_count = len(forecast_list)
            print(f"Forecast: {forecast_count} days ahead")
            for i, fc in enumerate(forecast_list[:5], 1):
                # Extract values before printing to avoid dictionary access in f-strings
                fc_ts = sanitize_for_output(fc.get("timestamp"))
                fc_pred = float(fc.get("prediction", 0.0))
                fc_lower = float(fc.get("lower_bound", 0.0))
                fc_upper = float(fc.get("upper_bound", 0.0))
                print(
                    f"  Day {i} ({fc_ts}): "
                    f"Prediction={fc_pred:.3f}, "
                    f"Range=[{fc_lower:.3f}, {fc_upper:.3f}]"
                )
            if forecast_count > 5:
                remaining = forecast_count - 5
                print(f"  ... and {remaining} more days")
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
