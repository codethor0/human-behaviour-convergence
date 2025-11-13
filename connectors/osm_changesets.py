# SPDX-License-Identifier: MIT-0
"""OpenStreetMap changesets connector for public data layer."""
import bz2
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
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

    def __init__(self, date: Optional[str] = None, max_bytes: int = 100 * 1024 * 1024):
        """
        Initialize OSM changesets connector.

        Args:
            date: Date in YYYY-MM-DD format. Defaults to yesterday.
            max_bytes: Maximum number of decompressed bytes to read (safeguard).
        """
        super().__init__()
        self.date = date or (datetime.now() - timedelta(days=1)).date().strftime(
            "%Y-%m-%d"
        )
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self.max_bytes = max_bytes
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
            response = requests.get(self.BASE_URL, timeout=300)
            response.raise_for_status()

            limit = self.max_bytes
            xml_chunks: list[bytes] = []
            total_size = 0

            with bz2.BZ2File(io.BytesIO(response.content)) as bz_file:
                while total_size < limit:
                    try:
                        chunk = bz_file.read(1024 * 1024)
                    except OSError as exc:
                        if "End of stream already reached" in str(exc):
                            break
                        raise

                    if not chunk:
                        break

                    # Check if adding this chunk would exceed the limit
                    if total_size + len(chunk) > limit:
                        # Read only the remaining bytes to reach exactly the limit
                        remaining = limit - total_size
                        if remaining > 0:
                            chunk = chunk[:remaining]
                            xml_chunks.append(chunk)
                            total_size += len(chunk)
                        self.logger.warning(
                            "Reached OSM snapshot size limit",
                            bytes_read=total_size,
                            limit=limit,
                        )
                        break

                    xml_chunks.append(chunk)
                    total_size += len(chunk)

            if not xml_chunks:
                raise ValueError("No data returned from OSM changesets download")

            xml_data = b"".join(xml_chunks)

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
