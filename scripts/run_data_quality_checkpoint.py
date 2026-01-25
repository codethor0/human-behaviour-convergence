#!/usr/bin/env python3
# SPDX-License-Identifier: PROPRIETARY
"""Run data quality checkpoint for all data sources."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import structlog

from app.core.data_quality import DataQualityCheckpoint
from app.core.prediction import BehavioralForecaster
from app.services.ingestion.economic_fred import FREDEconomicFetcher
from app.services.ingestion.weather import EnvironmentalImpactFetcher
from app.services.ingestion.public_health import PublicHealthFetcher
from app.services.ingestion.mobility import MobilityFetcher

logger = structlog.get_logger("data_quality_checkpoint")


def main():
    """Run data quality checkpoint for all sources."""
    checkpoint = DataQualityCheckpoint()

    # Test regions
    test_regions = [
        {"name": "Minnesota", "lat": 46.7296, "lon": -94.6859, "region_id": "us_mn"},
        {"name": "California", "lat": 36.7783, "lon": -119.4179, "region_id": "us_ca"},
    ]

    logger.info("Starting data quality checkpoint", regions=len(test_regions))

    # Validate weather data (region-specific)
    weather_fetcher = EnvironmentalImpactFetcher()
    for region in test_regions:
        weather_data = weather_fetcher.fetch_regional_comfort(
            latitude=region["lat"],
            longitude=region["lon"],
            days_back=30,
        )
        checkpoint.run_checkpoint(
            source_name="weather",
            df=weather_data,
            region_id=region["region_id"],
            required_columns=["timestamp", "discomfort_score"],
            column_types={"discomfort_score": float},
            timestamp_col="timestamp",
            max_age_hours=48,
            min_rows=20,
            range_checks={"discomfort_score": {"min": 0.0, "max": 1.0}},
        )

    # Validate FRED data (national)
    fred_fetcher = FREDEconomicFetcher()
    if fred_fetcher.api_key:
        consumer_sentiment = fred_fetcher.fetch_consumer_sentiment(days_back=30)
        checkpoint.run_checkpoint(
            source_name="fred_consumer_sentiment",
            df=consumer_sentiment,
            required_columns=["timestamp", "consumer_sentiment"],
            column_types={"consumer_sentiment": float},
            timestamp_col="timestamp",
            max_age_hours=168,  # Weekly data
            min_rows=1,
            range_checks={"consumer_sentiment": {"min": 0.0, "max": 1.0}},
        )

    # Validate public health data
    health_fetcher = PublicHealthFetcher()
    for region in test_regions:
        region_code = region["region_id"]
        health_data = health_fetcher.fetch_health_risk_index(
            region_code=region_code, days_back=30
        )
        if not health_data.empty:
            checkpoint.run_checkpoint(
                source_name="public_health",
                df=health_data,
                region_id=region["region_id"],
                required_columns=["timestamp", "health_risk_index"],
                column_types={"health_risk_index": float},
                timestamp_col="timestamp",
                max_age_hours=168,
                min_rows=1,
                range_checks={"health_risk_index": {"min": 0.0, "max": 1.0}},
            )

    # Validate mobility data
    mobility_fetcher = MobilityFetcher()
    for region in test_regions:
        result = mobility_fetcher.fetch_mobility_index(
            latitude=region["lat"],
            longitude=region["lon"],
            region_code=region["region_id"],
            days_back=30,
        )
        # Handle tuple return (df, status) or just df
        if isinstance(result, tuple):
            mobility_data, _ = result
        else:
            mobility_data = result
        
        if isinstance(mobility_data, pd.DataFrame) and not mobility_data.empty:
            checkpoint.run_checkpoint(
                source_name="mobility",
                df=mobility_data,
                region_id=region["region_id"],
                required_columns=["timestamp", "mobility_index"],
                column_types={"mobility_index": float},
                timestamp_col="timestamp",
                max_age_hours=48,
                min_rows=1,
                range_checks={"mobility_index": {"min": 0.0, "max": 1.0}},
            )

    # Generate and save report
    report_path = checkpoint.save_report()
    logger.info("Data quality checkpoint complete", report_path=str(report_path))

    # Print summary
    total = len(checkpoint.results)
    passed = sum(1 for r in checkpoint.results if r.status == "PASS")
    warned = sum(1 for r in checkpoint.results if r.status == "WARN")
    failed = sum(1 for r in checkpoint.results if r.status == "FAIL")

    print(f"\nData Quality Checkpoint Summary:")
    print(f"  Total checks: {total}")
    print(f"  PASS: {passed}")
    print(f"  WARN: {warned}")
    print(f"  FAIL: {failed}")
    print(f"\nFull report: {report_path}")

    # Exit with error code if any failures
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
