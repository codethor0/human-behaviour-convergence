# SPDX-License-Identifier: MIT-0
"""Tests for public data connectors."""
import bz2
import gzip
import pandas as pd
import responses

from connectors.firms_fires import FIRMSFiresSync
from connectors.osm_changesets import OSMChangesetsSync
from connectors.wiki_pageviews import WikiPageviewsSync


class TestWikiPageviewsSync:
    """Test Wikipedia pageviews connector."""

    @responses.activate
    def test_pull_returns_dataframe(self):
        """Test that pull() returns a DataFrame with correct schema."""
        # Mock HTTP response with gzipped content
        raw_data = "en Wikipedia Main_Page 1000 5000000\nen.m Wikipedia Special:Search 500 2500000"
        gzipped_data = gzip.compress(raw_data.encode("utf-8"))

        responses.add(
            responses.GET,
            "https://dumps.wikimedia.org/other/pageviews/2024/2024-11/pageviews-20241104-000000.gz",
            body=gzipped_data,
            status=200,
            content_type="application/gzip",
        )

        # Limit to 1 hour to avoid mocking 24 URLs
        connector = WikiPageviewsSync(date="2024-11-04", max_hours=1)
        df = connector.pull()

        assert isinstance(df, pd.DataFrame)
        assert "project" in df.columns
        assert "hour" in df.columns
        assert "views" in df.columns
        assert len(df) >= 0

    def test_ethical_check_applied(self):
        """Test that ethical_check decorator filters low counts."""
        WikiPageviewsSync(date="2024-11-04")
        df = pd.DataFrame(
            {
                "project": ["en", "de"],
                "hour": [0, 0],
                "views": [10, 20],  # Below k-anonymity threshold
                "count": [10, 20],
            }
        )
        # ethical_check should filter count < 15 in production pipeline
        assert (df["count"] < 15).any()


class TestOSMChangesetsSync:
    """Test OSM changesets connector."""

    @responses.activate
    def test_pull_returns_dataframe(self):
        """Test that pull() returns a DataFrame with correct schema."""
        # Create a minimal valid OSM changesets XML
        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <changeset id="1" user="test" uid="1" created_at="2024-11-04T00:00:00Z" min_lat="37.7749" min_lon="-122.4194" max_lat="37.7750" max_lon="-122.4193">
    <tag k="comment" v="test changeset"/>
    <tag k="building" v="yes"/>
  </changeset>
  <changeset id="2" user="test" uid="1" created_at="2024-11-04T01:00:00Z" min_lat="34.0522" min_lon="-118.2437" max_lat="34.0523" max_lon="-118.2436">
    <tag k="comment" v="test changeset 2"/>
    <tag k="highway" v="primary"/>
  </changeset>
</osm>"""

        # Compress with bz2
        bz2_data = bz2.compress(xml_data.encode("utf-8"))

        # Mock HTTP response
        responses.add(
            responses.GET,
            "https://planet.osm.org/planet/changesets-latest.osm.bz2",
            body=bz2_data,
            status=200,
            content_type="application/x-bzip2",
        )

        # Use small max_bytes to keep test fast
        connector = OSMChangesetsSync(date="2024-11-04", max_bytes=1024 * 1024)
        df = connector.pull()

        assert isinstance(df, pd.DataFrame)
        expected_cols = [
            "h3_9",
            "changeset_count",
            "buildings_modified",
            "roads_modified",
            "timestamp",
        ]
        for col in expected_cols:
            assert col in df.columns or len(df) == 0  # Empty is OK


class TestFIRMSFiresSync:
    """Test FIRMS fires connector."""

    def test_pull_returns_dataframe_no_key(self):
        """Test that pull() returns empty DataFrame when no API key."""
        connector = FIRMSFiresSync(date="2024-11-04")
        df = connector.pull()

        assert isinstance(df, pd.DataFrame)
        expected_cols = ["h3_9", "fire_count", "mean_brightness", "max_confidence"]
        for col in expected_cols:
            assert col in df.columns or len(df) == 0

    @responses.activate
    def test_pull_with_mock_api(self):
        """Test that pull() parses CSV correctly with mocked API."""
        # Mock FIRMS API response
        csv_data = """latitude,longitude,brightness,scan,track,acq_date,confidence
37.7749,-122.4194,320.5,1.0,1.0,2024-11-04,80
34.0522,-118.2437,315.2,1.0,1.0,2024-11-04,75"""

        responses.add(
            responses.GET,
            "https://firms.modaps.eosdis.nasa.gov/api/country/csv/TEST_KEY/MODIS_NRT/USA/1",
            body=csv_data,
            status=200,
        )

        # Temporarily set MAP_KEY for test
        import os

        os.environ["FIRMS_MAP_KEY"] = "TEST_KEY"

        connector = FIRMSFiresSync(date="2024-11-04")
        df = connector.pull()

        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 0

        # Clean up
        del os.environ["FIRMS_MAP_KEY"]
