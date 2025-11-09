# SPDX-License-Identifier: MIT-0
"""NASA FIRMS active fire connector for public data layer."""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from connectors.base import AbstractSync, ethical_check, logger


class FIRMSFiresSync(AbstractSync):
    """
    Downloads and processes NASA FIRMS active fire data.

    Source: https://firms.modaps.eosdis.nasa.gov/api/
    Returns fire counts aggregated by H3-9 cell.

    Requires MAP_KEY environment variable with FIRMS API key.
    Sign up at: https://firms.modaps.eosdis.nasa.gov/api/
    """

    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/country/csv"
    CACHE_DIR = Path("/tmp/firms_fires_cache")
    MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")

    def __init__(self, date: Optional[str] = None, country: str = "USA"):
        """
        Initialize FIRMS fires connector.

        Args:
            date: Date in YYYY-MM-DD format. Defaults to yesterday.
            country: Country code (e.g., USA, CAN, MEX). Defaults to USA.
        """
        super().__init__()
        self.date = date or (datetime.now().date() - pd.Timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        self.country = country
        self.CACHE_DIR.mkdir(exist_ok=True)

        if not self.MAP_KEY:
            self.logger.warning("FIRMS_MAP_KEY not set; using mock data")

    @ethical_check
    def pull(self) -> pd.DataFrame:
        """
        Pull FIRMS fire data for configured date and country.

        Returns:
            DataFrame with columns: [h3_9, fire_count, mean_brightness, max_confidence, count]
        """
        cache_file = self.CACHE_DIR / f"firms_fires_{self.country}_{self.date}.parquet"

        if cache_file.exists():
            self.logger.info("Loading from cache", cache_file=str(cache_file))
            return pd.read_parquet(cache_file)

        if not self.MAP_KEY:
            # Return mock data for testing
            self.logger.info("Returning mock fire data")
            return pd.DataFrame(
                {
                    "h3_9": [],
                    "fire_count": [],
                    "mean_brightness": [],
                    "max_confidence": [],
                    "count": [],
                }
            )

        # FIRMS API: /api/country/csv/{MAP_KEY}/MODIS_NRT/{country}/{dayRange}
        url = f"{self.BASE_URL}/{self.MAP_KEY}/MODIS_NRT/{self.country}/1"

        self.logger.info("Fetching FIRMS fires", url=url)

        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            # Parse CSV
            from io import StringIO

            df = pd.read_csv(StringIO(response.text))

            if df.empty:
                self.logger.warning(
                    "No fire data retrieved", date=self.date, country=self.country
                )
                return pd.DataFrame(
                    columns=[
                        "h3_9",
                        "fire_count",
                        "mean_brightness",
                        "max_confidence",
                        "count",
                    ]
                )

            # Expected columns: latitude, longitude, brightness, scan, track, acq_date, confidence
            required_cols = ["latitude", "longitude", "brightness", "confidence"]
            if not all(col in df.columns for col in required_cols):
                self.logger.error(
                    "Missing required columns", columns=df.columns.tolist()
                )
                return pd.DataFrame(
                    columns=[
                        "h3_9",
                        "fire_count",
                        "mean_brightness",
                        "max_confidence",
                        "count",
                    ]
                )

            # Add H3 index
            df = self.h3_index(df, "latitude", "longitude", res=9)

            # Aggregate by H3 cell
            df_agg = df.groupby("h3_9", as_index=False).agg(
                {"brightness": "mean", "confidence": "max"}
            )
            df_agg["fire_count"] = df.groupby("h3_9").size().values
            df_agg["count"] = df_agg["fire_count"]  # For k-anonymity check
            df_agg = df_agg.rename(
                columns={
                    "brightness": "mean_brightness",
                    "confidence": "max_confidence",
                }
            )

            # Cache result
            df_agg.to_parquet(cache_file, index=False)
            self.logger.info(
                "Cached FIRMS fires", cache_file=str(cache_file), rows=len(df_agg)
            )

            return df_agg

        except Exception as e:
            self.logger.error("Failed to fetch FIRMS fires", error=str(e))
            return pd.DataFrame(
                columns=[
                    "h3_9",
                    "fire_count",
                    "mean_brightness",
                    "max_confidence",
                    "count",
                ]
            )
