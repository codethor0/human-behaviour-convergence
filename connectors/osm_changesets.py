# SPDX-License-Identifier: MIT-0
"""OpenStreetMap changesets connector for public data layer."""
import bz2
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from connectors.base import AbstractSync, ethical_check, logger


class OSMChangesetsSync(AbstractSync):
    """
    Downloads and processes OpenStreetMap changesets data.

    Source: https://planet.osm.org/planet/changesets-latest.osm.bz2
    Returns changeset counts aggregated by H3-9 cell.
    """

    BASE_URL = "https://planet.osm.org/planet/changesets-latest.osm.bz2"
    CACHE_DIR = Path("/tmp/osm_changesets_cache")

    def __init__(self, date: Optional[str] = None):
        """
        Initialize OSM changesets connector.

        Args:
            date: Date in YYYY-MM-DD format. Defaults to today.
        """
        super().__init__()
        self.date = date or datetime.now().date().strftime("%Y-%m-%d")
        self.CACHE_DIR.mkdir(exist_ok=True)

    @ethical_check
    def pull(self) -> pd.DataFrame:
        """
        Pull OSM changesets for configured date.

        Returns:
            DataFrame with columns: [h3_9, changeset_count, buildings_modified, roads_modified, timestamp]
        """
        cache_file = self.CACHE_DIR / f"osm_changesets_{self.date}.parquet"

        if cache_file.exists():
            self.logger.info("Loading from cache", cache_file=str(cache_file))
            return pd.read_parquet(cache_file)

        self.logger.info("Fetching OSM changesets", url=self.BASE_URL)

        try:
            response = requests.get(self.BASE_URL, timeout=300, stream=True)
            response.raise_for_status()

            # Decompress bz2 on the fly
            decompressor = bz2.BZ2Decompressor()
            xml_data = b""

            for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                if chunk:
                    xml_data += decompressor.decompress(chunk)
                    # Limit to first 100MB to avoid memory issues
                    if len(xml_data) > 100 * 1024 * 1024:
                        break

            # Parse XML
            root = ET.fromstring(xml_data)

            changesets = []
            for changeset in root.findall("changeset"):
                min_lat = changeset.get("min_lat")
                max_lat = changeset.get("max_lat")
                min_lon = changeset.get("min_lon")
                max_lon = changeset.get("max_lon")
                timestamp = changeset.get("created_at", "")

                if not all([min_lat, max_lat, min_lon, max_lon]):
                    continue

                # Bbox centroid
                lat = (float(min_lat) + float(max_lat)) / 2
                lon = (float(min_lon) + float(max_lon)) / 2

                # Count tag changes (proxy for buildings/roads)
                tags = {tag.get("k"): tag.get("v") for tag in changeset.findall("tag")}
                buildings_modified = 1 if "building" in str(tags) else 0
                roads_modified = 1 if "highway" in str(tags) else 0

                changesets.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "buildings_modified": buildings_modified,
                        "roads_modified": roads_modified,
                        "timestamp": timestamp,
                    }
                )

            if not changesets:
                self.logger.warning("No changesets parsed", date=self.date)
                return pd.DataFrame(
                    columns=[
                        "h3_9",
                        "changeset_count",
                        "buildings_modified",
                        "roads_modified",
                        "timestamp",
                    ]
                )

            df = pd.DataFrame(changesets)

            # Add H3 index
            df = self.h3_index(df, "latitude", "longitude", res=9)

            # Aggregate by H3 cell
            df_agg = df.groupby("h3_9", as_index=False).agg(
                {
                    "buildings_modified": "sum",
                    "roads_modified": "sum",
                    "timestamp": "max",
                }
            )
            df_agg["changeset_count"] = df.groupby("h3_9").size().values
            df_agg["count"] = df_agg["changeset_count"]  # For k-anonymity check

            # Cache result
            df_agg.to_parquet(cache_file, index=False)
            self.logger.info(
                "Cached OSM changesets", cache_file=str(cache_file), rows=len(df_agg)
            )

            return df_agg

        except Exception as e:
            self.logger.error("Failed to fetch OSM changesets", error=str(e))
            return pd.DataFrame(
                columns=[
                    "h3_9",
                    "changeset_count",
                    "buildings_modified",
                    "roads_modified",
                    "timestamp",
                ]
            )
