# SPDX-License-Identifier: MIT-0
"""Wikipedia pageviews connector for public data layer."""
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from connectors.base import AbstractSync, ethical_check


class WikiPageviewsSync(AbstractSync):
    """
    Downloads and processes Wikipedia pageviews data.

    Source: https://dumps.wikimedia.org/other/pageviews/
    Returns hourly pageview counts aggregated by project (language) and hour.
    """

    BASE_URL = "https://dumps.wikimedia.org/other/pageviews"
    # nosec B108: /tmp usage acceptable for transient cache, not security-sensitive
    CACHE_DIR = Path("/tmp/wiki_pageviews_cache")
    PROJECTS = ["en", "de", "fr", "es", "zh"]  # Top 5 languages

    def __init__(self, date: Optional[str] = None, max_hours: int = 24):
        """
        Initialize Wikipedia pageviews connector.

        Args:
            date: Date in YYYY-MM-DD format. Defaults to yesterday.
            max_hours: Maximum number of hourly files to fetch (0-24).
        """
        super().__init__()
        self.date = date or (datetime.now() - timedelta(days=1)).date().strftime(
            "%Y-%m-%d"
        )
        if not 1 <= max_hours <= 24:
            raise ValueError("max_hours must be between 1 and 24")
        self.max_hours = max_hours
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

        # Validate and parse date components (prevents SSRF via URL injection)
        try:
            parsed_date = datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {self.date} (must be YYYY-MM-DD)")

        # Extract validated date components
        year = parsed_date.strftime("%Y")
        month = parsed_date.strftime("%m")
        day = parsed_date.strftime("%d")

        # Ensure date components are numeric and within valid ranges
        if not (year.isdigit() and month.isdigit() and day.isdigit()):
            raise ValueError(f"Invalid date format: {self.date}")
        if not (1 <= int(month) <= 12 and 1 <= int(day) <= 31):
            raise ValueError(f"Invalid date values: {self.date}")

        all_data = []

        for hour in range(self.max_hours):
            filename = f"pageviews-{year}{month}{day}-{hour:02d}0000.gz"
            url = f"{self.BASE_URL}/{year}/{year}-{month}/{filename}"

            self.logger.info("Fetching pageviews", url=url)

            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                decompressed = gzip.decompress(response.content).decode(
                    "utf-8", errors="ignore"
                )
                for line in decompressed.splitlines():
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split()
                    if len(parts) < 3:
                        continue

                    try:
                        views = int(parts[2])
                    except ValueError:
                        self.logger.debug(
                            "Skipping non-integer view count",
                            line_sample=line[:120],
                            hour=hour,
                        )
                        continue

                    project, page_title = parts[0], parts[1]

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
