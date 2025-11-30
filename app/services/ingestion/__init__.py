# SPDX-License-Identifier: PROPRIETARY
"""Public data ingestion services."""

from .economic_fred import FREDEconomicFetcher
from .finance import MarketSentimentFetcher
from .gdelt_events import GDELTEventsFetcher
from .health_owid import OWIDHealthFetcher
from .mobility import MobilityFetcher
from .processor import DataHarmonizer
from .public_health import PublicHealthFetcher
from .search_trends import SearchTrendsFetcher
from .usgs_earthquakes import USGSEarthquakeFetcher
from .weather import EnvironmentalImpactFetcher

__all__ = [
    "MarketSentimentFetcher",
    "FREDEconomicFetcher",
    "EnvironmentalImpactFetcher",
    "DataHarmonizer",
    "SearchTrendsFetcher",
    "PublicHealthFetcher",
    "MobilityFetcher",
    "GDELTEventsFetcher",
    "OWIDHealthFetcher",
    "USGSEarthquakeFetcher",
]
