# SPDX-License-Identifier: MIT-0
"""Wikipedia pageviews connector for public data layer."""
import bz2
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from connectors.base import AbstractSync, ethical_check, logger


class WikiPageviewsSync(AbstractSync):
    """
    Downloads and processes Wikipedia pageviews data.

    Source: https://dumps.wikimedia.org/other/pageviews/
    Returns hourly pageview counts aggregated by project (language) and hour.
    """

    BASE_URL = "https://dumps.wikimedia.org/other/pageviews"
    CACHE_DIR = Path("/tmp/wiki_pageviews_cache")
    PROJECTS = ["en", "de", "fr", "es", "zh"]  # Top 5 languages

    def __init__(self, date: Optional[str] = None):
        """
        Initialize Wikipedia pageviews connector.

        Args:
            date: Date in YYYY-MM-DD format. Defaults to yesterday.
        """
        super().__init__()
        self.date = date or (datetime.now().date() - pd.Timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        self.CACHE_DIR.mkdir(exist_ok=True)

    @ethical_check
    def pull(self) -> pd.DataFrame:
        """
        Pull Wikipedia pageviews for configured date.

        Returns:
            DataFrame with columns: [project, hour, views]
        """
        cache_file = self.CACHE_DIR / f"wiki_pageviews_{self.date}.parquet"

        if cache_file.exists():
            self.logger.info("Loading from cache", cache_file=str(cache_file))
            return pd.read_parquet(cache_file)

        year, month, day = self.date.split("-")
        all_data = []

        for hour in range(24):
            filename = f"pageviews-{year}{month}{day}-{hour:02d}0000.gz"
            url = f"{self.BASE_URL}/{year}/{year}-{month}/{filename}"

            self.logger.info("Fetching pageviews", url=url)

            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                # Parse pageviews format: project page_title count_views total_response_size
                lines = response.content.decode("utf-8").strip().split("\n")

                for line in lines:
                    parts = line.split()
                    if len(parts) < 3:
                        continue

                    project, page_title, views = parts[0], parts[1], int(parts[2])

                    # Filter to configured projects only
                    project_code = project.split(".")[0]
                    if project_code in self.PROJECTS:
                        all_data.append(
                            {
                                "project": project_code,
                                "hour": hour,
                                "views": views,
                                "page_title": page_title,
                            }
                        )

            except Exception as e:
                self.logger.warning("Failed to fetch hour", hour=hour, error=str(e))
                continue

        if not all_data:
            self.logger.warning("No data retrieved", date=self.date)
            return pd.DataFrame(columns=["project", "hour", "views"])

        df = pd.DataFrame(all_data)

        # Aggregate by project and hour (sum views)
        df_agg = df.groupby(["project", "hour"], as_index=False).agg({"views": "sum"})

        # Add count column for k-anonymity check
        df_agg["count"] = df_agg["views"]

        # Cache result
        df_agg.to_parquet(cache_file, index=False)
        self.logger.info(
            "Cached pageviews", cache_file=str(cache_file), rows=len(df_agg)
        )

        return df_agg
