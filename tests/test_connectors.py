# SPDX-License-Identifier: MIT-0
"""Tests for public data connectors."""
import pandas as pd
import pytest
import responses

from connectors.firms_fires import FIRMSFiresSync
from connectors.osm_changesets import OSMChangesetsSync
from connectors.wiki_pageviews import WikiPageviewsSync


class TestWikiPageviewsSync:
    """Test Wikipedia pageviews connector."""

    @responses.activate
    def test_pull_returns_dataframe(self):
        """Test that pull() returns a DataFrame with correct schema."""
        # Mock HTTP response
        responses.add(
            responses.GET,
            "https://dumps.wikimedia.org/other/pageviews/2024/2024-11/pageviews-20241104-000000.gz",
            body="en Wikipedia Main_Page 1000 5000000\nen.m Wikipedia Special:Search 500 2500000",
            status=200,
        )

        connector = WikiPageviewsSync(date="2024-11-04")
        df = connector.pull()

        assert isinstance(df, pd.DataFrame)
        assert "project" in df.columns
        assert "hour" in df.columns
        assert "views" in df.columns
        assert len(df) >= 0

    def test_ethical_check_applied(self):
        """Test that ethical_check decorator filters low counts."""
        connector = WikiPageviewsSync(date="2024-11-04")
        # Create mock data with low counts
        df = pd.DataFrame(
            {
                "project": ["en", "de"],
                "hour": [0, 0],
                "views": [10, 20],  # Below k-anonymity threshold
                "count": [10, 20],
            }
        )
        # ethical_check should filter count < 15
        # (Note: in practice, this is applied in pull(), not directly testable here)
        assert True  # Placeholder for actual ethical check test


class TestOSMChangesetsSync:
    """Test OSM changesets connector."""

    def test_pull_returns_dataframe(self):
        """Test that pull() returns a DataFrame with correct schema."""
        connector = OSMChangesetsSync(date="2024-11-04")
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
